"""Diagnostic engine over a subset of the knowledge map.

Pure data in, pure data out, so engine/diagnostic.js can mirror it exactly.
Skill iteration always follows `order` (source-file order) to keep ties
deterministic across the two implementations.

States: na, known, inferred, failed, risk.
"""
from __future__ import annotations

NA, KNOWN, INFERRED, FAILED, RISK = "na", "known", "inferred", "failed", "risk"
OK_STATES = (KNOWN, INFERRED)


def scope_from_map(km, skill_ids) -> dict:
    """Build the engine input for a subset of the map. Prerequisites are cut to the subset."""
    ids = [s for s in km.order if s in set(skill_ids)]
    inside = set(ids)
    return {
        "skills": [
            {
                "id": s,
                "label": km.label(s),
                "domain": km.domain(s),
                "layer": km.layers[s],
                "prerequisites": [p for p in km.prereqs(s) if p in inside],
            }
            for s in ids
        ]
    }


class Diagnostic:
    def __init__(self, scope: dict):
        self.order: list[str] = [s["id"] for s in scope["skills"]]
        self.info: dict[str, dict] = {s["id"]: s for s in scope["skills"]}
        self.pre: dict[str, list[str]] = {s["id"]: list(s["prerequisites"]) for s in scope["skills"]}
        self.index = {s: i for i, s in enumerate(self.order)}

        # ancestors: prerequisites come before dependants only if the file is sorted,
        # so resolve recursively with memo, then store as ordered lists.
        anc_sets: dict[str, set[str]] = {}

        def anc(s: str) -> set[str]:
            if s not in anc_sets:
                r: set[str] = set()
                for p in self.pre[s]:
                    r.add(p)
                    r |= anc(p)
                anc_sets[s] = r
            return anc_sets[s]

        for s in self.order:
            anc(s)
        self.ancestors = {s: [x for x in self.order if x in anc_sets[s]] for s in self.order}
        self.descendants = {s: [x for x in self.order if s in anc_sets[x]] for s in self.order}

        self.status: dict[str, str] = {s: NA for s in self.order}
        self.root_gap: dict[str, bool] = {s: False for s in self.order}
        self.stack: list[dict] = []
        self.asked: list[dict] = []  # [{skill, correct}]
        self.log: list[dict] = []  # structured events; UIs render text from these
        self.integration: list[str] = []  # section ids: every skill known, section still failed
        self.section_causes: dict[str, list[str]] = {}
        self.current: dict | None = None  # last question returned by next_question

    # --- state updates ---------------------------------------------------

    def layer(self, s: str) -> int:
        return self.info[s]["layer"]

    def by_layer(self, ids) -> list[str]:
        return sorted(ids, key=lambda s: (self.layer(s), self.index[s]))

    def _mark_correct(self, s: str) -> None:
        self.status[s] = KNOWN
        for a in self.ancestors[s]:
            if self.status[a] in (NA, RISK):
                self.status[a] = INFERRED

    def _mark_failed(self, s: str) -> None:
        self.status[s] = FAILED
        for d in self.descendants[s]:
            if self.status[d] == NA:
                self.status[d] = RISK

    def answer(self, s: str, correct: bool) -> None:
        cur = self.current
        if cur and cur["skill"] == s and cur["reason"]["kind"] == "hypothesis":
            r = cur["reason"]
            self.log.append({"type": "hypothesis", "id": r["failed"], "kind": r["failedKind"],
                             "ask": s, "rest": list(r["rest"])})
        self.current = None
        self.asked.append({"skill": s, "correct": bool(correct)})
        self.log.append({"type": "answer", "skill": s, "correct": bool(correct)})
        if correct:
            self._mark_correct(s)
            return
        self._mark_failed(s)
        pending = [p for p in self.pre[s] if self.status[p] == NA]
        if pending:
            self.stack.append({"kind": "skill", "id": s, "pre": list(self.pre[s]), "pending": pending})
        elif all(self.status[p] in OK_STATES for p in self.pre[s]):
            self.root_gap[s] = True
            self.log.append({"type": "root", "id": s, "kind": "skill"})

    # --- adaptive selection ----------------------------------------------

    def _conclude(self, entry: dict) -> None:
        failed = [p for p in entry["pre"] if self.status[p] == FAILED]
        if entry["kind"] == "section":
            self.section_causes[entry["id"]] = failed
        if failed:
            self.log.append({"type": "caused", "id": entry["id"], "kind": entry["kind"], "by": failed})
            return
        if entry["kind"] == "skill":
            self.root_gap[entry["id"]] = True
            self.log.append({"type": "root", "id": entry["id"], "kind": "skill"})
        else:
            self.integration.append(entry["id"])
            self.log.append({"type": "integration", "id": entry["id"], "kind": "section"})

    def balance_scores(self) -> dict[str, dict]:
        out = {}
        for s in self.order:
            if self.status[s] != NA:
                continue
            a = sum(1 for x in self.ancestors[s] if self.status[x] == NA)
            d = sum(1 for x in self.descendants[s] if self.status[x] == NA)
            out[s] = {"a": a, "d": d, "score": min(a, d) * 10 + a + d}
        return out

    def next_question(self) -> dict | None:
        """Return {skill, reason} or None when there is nothing left to ask."""
        while self.stack:
            top = self.stack[-1]
            top["pending"] = [p for p in top["pending"] if self.status[p] == NA]
            if top["pending"]:
                ask = top["pending"][0]
                reason = {
                    "kind": "hypothesis",
                    "failed": top["id"],
                    "failedKind": top["kind"],
                    "label": top.get("label", top["id"]),
                    "ask": ask,
                    "rest": top["pending"][1:],
                    "candidates": list(top["pending"]),
                }
                self.current = {"skill": ask, "reason": reason}
                return self.current
            self.stack.pop()
            self._conclude(top)

        scores = self.balance_scores()
        if not scores:
            self.current = None
            return None
        best = None
        for s in self.order:  # first maximum in source order
            if s in scores and (best is None or scores[s]["score"] > scores[best]["score"]):
                best = s
        self.current = {"skill": best, "reason": {"kind": "balanced", **scores[best]}}
        return self.current

    def finish(self) -> None:
        """Stop early: close every open hypothesis with what is known now."""
        while self.stack:
            top = self.stack.pop()
            top["pending"] = [p for p in top["pending"] if self.status[p] == NA]
            self._conclude(top)

    # --- journey ---------------------------------------------------------

    def start_journey(self, sections: list[dict]) -> None:
        """sections: [{id, skills, correct}] in the order of the bagrut question."""
        for sec in sections:
            self.log.append({"type": "section", "id": sec["id"], "correct": bool(sec["correct"])})
            if sec["correct"]:
                for s in sec["skills"]:
                    self._mark_correct(s)
        failed = [sec for sec in sections if not sec["correct"]]
        for sec in reversed(failed):
            pending = [s for s in sec["skills"] if self.status[s] not in OK_STATES]
            self.stack.append(
                {
                    "kind": "section",
                    "id": sec["id"],
                    "label": "סעיף " + sec["id"],
                    "pre": list(sec["skills"]),
                    "pending": pending,
                }
            )

    # --- summary ---------------------------------------------------------

    def failed_pre(self, s: str) -> list[str]:
        return [p for p in self.pre[s] if self.status[p] == FAILED]

    def summary(self) -> dict:
        failed = [s for s in self.order if self.status[s] == FAILED]
        roots = [s for s in failed if self.root_gap[s] or not self.failed_pre(s)]
        contradictions = [
            {"skill": s, "failedAncestors": [a for a in self.ancestors[s] if self.status[a] == FAILED]}
            for s in self.order
            if self.status[s] == KNOWN and any(self.status[a] == FAILED for a in self.ancestors[s])
        ]
        counts = {k: 0 for k in (NA, KNOWN, INFERRED, FAILED, RISK)}
        for s in self.order:
            counts[self.status[s]] += 1
        return {
            "asked": len(self.asked),
            "counts": counts,
            "rootGaps": [
                {
                    "skill": s,
                    # confirmed = every direct prerequisite was shown to be fine
                    "confirmed": all(self.status[p] in OK_STATES for p in self.pre[s]),
                }
                for s in self.by_layer(roots)
            ],
            "path": self.by_layer(failed),
            "risk": self.by_layer(s for s in self.order if self.status[s] == RISK),
            "contradictions": contradictions,
            "integration": list(self.integration),
            "sectionCauses": dict(self.section_causes),
        }


def guided_ladder(scope: dict, targets, depth: int = 1, status: dict | None = None) -> list[str]:
    """Guiding questions for `targets`, generated from the graph alone.

    Take the targets plus their prerequisites up to `depth` levels down, drop
    anything already known/inferred (personal mode, when `status` is given),
    and order bottom-up by layer. Each rung is one existing diagnostic question.
    """
    d = Diagnostic(scope)
    picked = set(t for t in targets if t in d.info)
    frontier = list(picked)
    for _ in range(depth):
        nxt = []
        for s in frontier:
            for p in d.pre[s]:
                if p not in picked:
                    picked.add(p)
                    nxt.append(p)
        frontier = nxt
    if status:
        picked = {s for s in picked if status.get(s, NA) not in OK_STATES}
    return d.by_layer(picked)


def interpret_static(scope: dict, answers: dict[str, bool | None]) -> dict:
    """Static test: apply every answer (None = "don't know" = wrong), then summarize.

    The result is order-independent: a tested skill keeps its own result, inferred
    beats risk, and failed beats inferred.
    """
    d = Diagnostic(scope)
    for s in d.order:
        if s in answers:
            if answers[s]:
                d._mark_correct(s)
    for s in d.order:
        if s in answers and not answers[s]:
            d._mark_failed(s)
    for s in d.order:
        if s in answers:
            d.asked.append({"skill": s, "correct": bool(answers[s])})
    return {"status": dict(d.status), "summary": d.summary()}
