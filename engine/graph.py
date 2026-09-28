"""Graph utilities for the 571 knowledge map.

Everything here is derived from data/knowledge_map_571.json. Nothing is stored
back into the data: layers, ancestors and descendants are always computed.
"""
from __future__ import annotations

import json
from collections import defaultdict
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BUILD = ROOT / "build"

MAP_FILE = DATA / "knowledge_map_571.json"
QUESTIONS_FILE = DATA / "diagnostic_questions.json"
BAGRUT_FILE = DATA / "bagrut_rational_function.json"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


class KnowledgeMap:
    """Read-only view of the skill DAG. Skill order follows the source file."""

    def __init__(self, raw: dict):
        self.raw = raw
        self.meta = raw["meta"]
        self.domains: dict[str, str] = raw["meta"]["domains"]
        self.skills: dict[str, dict] = {s["id"]: s for s in raw["skills"]}
        self.order: list[str] = [s["id"] for s in raw["skills"]]
        self.question_types: list[dict] = raw["questionTypes"]

    @classmethod
    def load(cls, path: Path = MAP_FILE) -> "KnowledgeMap":
        return cls(load_json(path))

    # --- basic structure -------------------------------------------------

    def prereqs(self, sid: str) -> list[str]:
        return self.skills[sid]["prerequisites"]

    def label(self, sid: str) -> str:
        return self.skills[sid]["label"]

    def domain(self, sid: str) -> str:
        return self.skills[sid]["domain"]

    @cached_property
    def children(self) -> dict[str, list[str]]:
        ch: dict[str, list[str]] = defaultdict(list)
        for sid in self.order:
            for p in self.prereqs(sid):
                ch[p].append(sid)
        return {sid: ch.get(sid, []) for sid in self.order}

    @property
    def edges(self) -> list[tuple[str, str]]:
        """(prerequisite, skill) pairs."""
        return [(p, s) for s in self.order for p in self.prereqs(s)]

    def roots(self) -> list[str]:
        return [s for s in self.order if not self.prereqs(s)]

    def leaves(self) -> list[str]:
        return [s for s in self.order if not self.children[s]]

    # --- computed properties (assume a valid DAG) ------------------------

    @cached_property
    def layers(self) -> dict[str, int]:
        """layer(n) = 0 without prerequisites, else 1 + max(layer(p))."""
        memo: dict[str, int] = {}

        def layer(sid: str) -> int:
            if sid not in memo:
                ps = self.prereqs(sid)
                memo[sid] = 0 if not ps else 1 + max(layer(p) for p in ps)
            return memo[sid]

        for sid in self.order:
            layer(sid)
        return {sid: memo[sid] for sid in self.order}

    @cached_property
    def ancestors(self) -> dict[str, set[str]]:
        memo: dict[str, set[str]] = {}

        def anc(sid: str) -> set[str]:
            if sid not in memo:
                r: set[str] = set()
                for p in self.prereqs(sid):
                    r.add(p)
                    r |= anc(p)
                memo[sid] = r
            return memo[sid]

        for sid in self.order:
            anc(sid)
        return memo

    @cached_property
    def descendants(self) -> dict[str, set[str]]:
        desc: dict[str, set[str]] = {sid: set() for sid in self.order}
        for sid, anc in self.ancestors.items():
            for a in anc:
                desc[a].add(sid)
        return desc

    def sort_key(self, sid: str) -> tuple[int, int]:
        """Stable order: by layer, then by position in the source file."""
        return (self.layers[sid], self.order.index(sid))

    def sorted(self, sids) -> list[str]:
        return sorted(sids, key=self.sort_key)

    def closure(self, sids) -> set[str]:
        """The skills themselves plus all their ancestors."""
        out: set[str] = set()
        for s in sids:
            out.add(s)
            out |= self.ancestors[s]
        return out

    def question_type(self, qid: str) -> dict:
        return next(q for q in self.question_types if q["id"] == qid)

    def redundant_edges(self) -> list[tuple[str, str]]:
        """Edges p→s where p is already an ancestor of another prerequisite of s."""
        out = []
        for s in self.order:
            ps = self.prereqs(s)
            for p in ps:
                if any(p in self.ancestors[o] for o in ps if o != p):
                    out.append((p, s))
        return out
