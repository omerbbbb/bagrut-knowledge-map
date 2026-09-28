"""שלב 5 – סימולציה של המנוע האדפטיבי.

מה עשינו בשלב הזה ולמה
-----------------------
המבחן הסטטי שואל 15 שאלות קבועות. המנוע האדפטיבי בוחר כל שאלה לפי מה שכבר ידוע:

  * אחרי כישלון הוא מעלה **השערה** – "X נכשל; אולי הבעיה באחד הקדמים הישירים
    שלו" – ויורד לבדוק אותם אחד־אחד, עד שהוא מגיע למקום שבו כל הקדמים ידועים.
    שם נמצא **פער השורש**.
  * כשאין השערה פתוחה הוא בוחר **שאלה מאוזנת**: מיומנות שיש לה גם הרבה לא־ידוע
    מתחתיה וגם הרבה לא־ידוע מעליה (ציון min(a,d)·10 + a + d), כך שכל תשובה –
    נכונה או שגויה – מבטלת הרבה אי־ודאות.

הסקריפט מריץ את המנוע על תלמידים מדומים ודטרמיניסטיים: תלמיד "לא יודע" קבוצת
מיומנויות וכל מה שמעליהן, ועונה נכון על כל השאר. אלה ארבעת התסריטים שבדקנו
במקור על מפת האלגברה (37 מיומנויות), ועוד תסריט מסע אחד על שאלת הבגרות.

קלט:  data/*.json
פלט:  build/simulations.md, build/simulations.json
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.graph import BAGRUT_FILE, BUILD, KnowledgeMap, load_json, write_json  # noqa: E402
from engine.scenarios import (  # noqa: E402
    ALGEBRA, JOURNEY, algebra_scope, journey_scope, run, section_results, unknown_set,
)


def step_text(km: KnowledgeMap, step: dict) -> str:
    mark = "✓" if step["correct"] else "✗"
    r = step["reason"]
    if r["kind"] == "hypothesis":
        why = f"השערה: {r['label']} נכשל ← בודקים {r['ask']}"
        if r["rest"]:
            why += f" (אחר כך: {', '.join(r['rest'])})"
    else:
        why = f"מאוזנת: a={r['a']} d={r['d']} ציון={r['score']}"
    return f"{mark} {step['skill']:<5} {km.label(step['skill'])}  —  {why}"


def log_text(km: KnowledgeMap, e: dict) -> str | None:
    t = e["type"]
    if t == "section":
        return f"סעיף {e['id']}: {'✓' if e['correct'] else '✗'}"
    if t == "root":
        return f"◆ מסקנה: פער שורש ב־{e['id']} {km.label(e['id'])} – כל הקדמים ידועים"
    if t == "caused":
        name = f"סעיף {e['id']}" if e["kind"] == "section" else e["id"]
        return f"↳ מסקנה: {name} נכשל בגלל {', '.join(e['by'])}"
    if t == "integration":
        return f"◆ מסקנה: סעיף {e['id']} – קושי בשילוב (כל המיומנויות ידועות בנפרד)"
    return None


def describe(km: KnowledgeMap, case: dict, res: dict, sections=None) -> list[str]:
    s = res["summary"]
    lines = [f"### {case['title']}", "", f"צפוי: {case['expect']}", ""]
    if sections is not None:
        lines.append("**שלב 1 – שאלת הבגרות:** " + "  ".join(
            f"{x['id']} {'✓' if x['correct'] else '✗'}" for x in sections))
        lines.append("")
        lines.append("**שלב 2 – המנוע על הסגור של q13:**")
        lines.append("")
    lines.append("```")
    for i, st in enumerate(res["steps"], 1):
        lines.append(f"{i:>2}. {step_text(km, st)}")
    lines.append("```")
    lines.append("")
    concl = [t for t in (log_text(km, e) for e in res["log"] if e["type"] != "section") if t]
    if concl:
        lines += ["מסלול ההיסק:", ""] + [f"- {c}" for c in concl] + [""]
    roots = [r["skill"] for r in s["rootGaps"]]
    lines.append(f"- שאלות: **{s['asked']}**")
    lines.append(f"- פערי שורש: **{', '.join(roots) or 'אין'}**")
    lines.append(f"- מסלול השלמה: {' → '.join(s['path']) or '—'}")
    if s["risk"]:
        lines.append(f"- לא נבדקו (בסיכון, ייבדקו אחרי ההשלמה): {len(s['risk'])}")
    if s["integration"]:
        lines.append(f"- קושי בשילוב: {', '.join('סעיף ' + x for x in s['integration'])}")
    if sections is not None:
        failed = [x["id"] for x in sections if not x["correct"]]
        if failed:
            lines.append(
                "- שלב 3 – סוף המסלול: " + ", ".join(f"שאלת בגרות חדשה מאותו סוג, סעיף {x}" for x in failed)
            )
    lines.append("")
    return lines


def main() -> int:
    km = KnowledgeMap.load()
    bagrut = load_json(BAGRUT_FILE)
    alg, jrn = algebra_scope(km), journey_scope(km)
    table, detail, dump = [], [], {}

    print(f"מפת האלגברה: {len(alg['skills'])} מיומנויות · סגור q13: {len(jrn['skills'])} מיומנויות\n")
    for case in ALGEBRA + JOURNEY:
        unknown = unknown_set(km, case["gaps"])
        is_journey = case in JOURNEY
        sections = section_results(unknown, bagrut) if is_journey else None
        res = run(jrn if is_journey else alg, unknown, sections)
        s = res["summary"]
        roots = [r["skill"] for r in s["rootGaps"]]
        print(f"■ {case['title']}")
        if sections:
            print("  סעיפים: " + " ".join(f"{x['id']}{'✓' if x['correct'] else '✗'}" for x in sections))
        print("  " + " ".join(("✓" if x["correct"] else "✗") + x["skill"] for x in res["steps"]))
        print(f"  → {s['asked']} שאלות · פערי שורש: {', '.join(roots) or 'אין'} · צפוי: {case['expect']}\n")

        table.append(
            f"| {case['title']} | {', '.join(case['gaps']) or '—'} | {s['asked']} | "
            f"{', '.join(roots) or '—'} | {len(s['path'])} | {len(s['risk'])} | {case['expect']} |"
        )
        detail += describe(km, case, res, sections)
        dump[case["id"]] = {"case": case, "sections": sections, **res}

    md = [
        "# תוצאות הסימולציות",
        "",
        "> נוצר ע״י `pipeline/05_simulate.py`. תלמיד מדומה \"לא יודע\" את המיומנויות",
        "> בעמודת הפער וכל מה שמעליהן, ועונה נכון על כל השאר.",
        "",
        "| תסריט | פער אמיתי | שאלות | פערי שורש שנמצאו | במסלול | בסיכון | צפוי |",
        "|---|---|---|---|---|---|---|",
        *table,
        "",
        "## פירוט",
        "",
        *detail,
    ]
    (BUILD / "simulations.md").write_text("\n".join(md), encoding="utf-8")
    write_json(BUILD / "simulations.json", dump)
    print("→ build/simulations.md")
    print("→ build/simulations.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
