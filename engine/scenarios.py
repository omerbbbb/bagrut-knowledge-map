"""Deterministic simulated students, shared by pipeline/05_simulate.py and the parity test.

A student "does not know" a set of skills and everything above them (their
descendants in the whole map). Every other answer is correct. A bagrut
section is answered correctly only if every one of its skills is known.
"""
from __future__ import annotations

from engine.diagnostic import Diagnostic, scope_from_map
from engine.graph import BAGRUT_FILE, KnowledgeMap, load_json

ALGEBRA = [
    {"id": "all_known", "title": "יודע הכול", "gaps": [], "expect": "~20 שאלות, 0 פערים"},
    {"id": "gap_al7", "title": "לא יודע al7 (פירוק טרינום) וכל מה שמעליו", "gaps": ["al7"],
     "expect": "~15 שאלות, פער שורש יחיד: al7"},
    {"id": "gap_ar4", "title": "לא יודע ar4 (מספרים שליליים) וכל מה שמעליו", "gaps": ["ar4"],
     "expect": "~11 שאלות, ירידה al7→al5→al4→al3→al1→ar4"},
    {"id": "gap_al15_al13", "title": "לא יודע al15 ו־al13 (וכל מה שמעליהם)", "gaps": ["al15", "al13"],
     "expect": "שני פערי שורש בדיוק, בלי סימפטומים"},
]
JOURNEY = [
    {"id": "journey_ca4", "title": "מסע: נופל בסעיף ד׳ (קיצון) בגלל ca4 (נגזרת מנה)", "gaps": ["ca4"],
     "expect": "פער שורש ca4; סעיפי ד׳ ו־ז׳ מוסברים דרכו"},
]


def algebra_scope(km: KnowledgeMap) -> dict:
    return scope_from_map(km, [s for s in km.order if km.domain(s) in ("ar", "al")])


def journey_scope(km: KnowledgeMap, qtype: str = "q13") -> dict:
    return scope_from_map(km, km.closure(km.question_type(qtype)["skills"]))


def unknown_set(km: KnowledgeMap, gaps) -> list[str]:
    out = set(gaps)
    for g in gaps:
        out |= km.descendants[g]
    return [s for s in km.order if s in out]


def section_results(unknown, bagrut: dict | None = None) -> list[dict]:
    bagrut = bagrut or load_json(BAGRUT_FILE)
    unk = set(unknown)
    return [
        {"id": s["id"], "skills": s["skills"], "correct": not any(x in unk for x in s["skills"])}
        for s in bagrut["sections"]
    ]


def run(scope: dict, unknown, sections: list[dict] | None = None, max_steps: int = 500) -> dict:
    """Run the adaptive engine against a deterministic student. Mirrors tests/js_runner.js."""
    unk = set(unknown)
    d = Diagnostic(scope)
    if sections is not None:
        d.start_journey(sections)
    steps = []
    for _ in range(max_steps):
        q = d.next_question()
        if q is None:
            break
        ok = q["skill"] not in unk
        steps.append({"skill": q["skill"], "reason": q["reason"], "correct": ok})
        d.answer(q["skill"], ok)
    return {"steps": steps, "log": d.log, "status": d.status, "summary": d.summary()}
