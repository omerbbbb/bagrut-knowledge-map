"""שלב 3 – סגורים וכיסוי.

מה עשינו בשלב הזה ולמה
-----------------------
אחרי שהוחלט שסוגי שאלות הם ציר נפרד מהמיומנויות (סוג שאלה לא צומת בגרף, אלא
מצביע על המיומנויות הישירות שהוא משלב), צריך לדעת מה *באמת* נדרש לכל סוג
שאלה: לא רק המיומנויות הישירות, אלא כל מה שמתחתיהן.

לכל מיומנות מחושבים:
  * ancestors – כל מה שצריך לדעת לפניה (הסגור כלפי מטה).
  * descendants – כל מה שהיא פותחת (הסגור כלפי מעלה). זה ה־fan-out שקובע כמה
    מידע נותנת תשובה עליה: כישלון בה מסכן את כל ה־descendants.

לכל questionType: הסגור המלא (המיומנויות הישירות + כל ה־ancestors שלהן),
ופירוט לפי תחום. הסגור של q13 ("חקירת פונקציה רציונלית") – 55 מיומנויות – הוא
מרחב החיפוש של המסע (journey).

דוח הכיסוי עונה על שתי שאלות: אילו מיומנויות משותפות להרבה סוגי שאלות (ה"צמתים
החמים" – פער בהן פוגע בכל הבגרות), ואילו לא נדרשות לאף סוג שאלה.

קלט:  data/knowledge_map_571.json
פלט:  build/closures.json, build/coverage_report.md
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.graph import BUILD, KnowledgeMap, write_json  # noqa: E402

HOT_TOP = 20


def main() -> int:
    km = KnowledgeMap.load()

    skills_out = {
        s: {
            "ancestors": km.sorted(km.ancestors[s]),
            "descendants": km.sorted(km.descendants[s]),
        }
        for s in km.order
    }

    qt_out = {}
    usage: Counter[str] = Counter()
    for q in km.question_types:
        closure = km.sorted(km.closure(q["skills"]))
        usage.update(closure)
        by_domain = {d: [s for s in closure if km.domain(s) == d] for d in km.domains}
        qt_out[q["id"]] = {
            "label": q["label"],
            "direct": q["skills"],
            "closure": closure,
            "size": len(closure),
            "byDomain": {d: v for d, v in by_domain.items() if v},
        }

    write_json(BUILD / "closures.json", {"skills": skills_out, "questionTypes": qt_out})

    # --- terminal log ----------------------------------------------------
    print("סגור לכל סוג שאלה:\n")
    for qid, q in qt_out.items():
        dom = " ".join(f"{d}:{len(v)}" for d, v in q["byDomain"].items())
        print(f"  {qid:<4} {q['size']:>3}  {q['label']:<32} {dom}")

    fan = sorted(km.order, key=lambda s: (-len(km.descendants[s]), km.sort_key(s)))
    print("\nה־fan-out הגבוה ביותר (מספר descendants):")
    for s in fan[:8]:
        print(f"  {s:<5} {len(km.descendants[s]):>3}  {km.label(s)}")

    unused = [s for s in km.order if usage[s] == 0]
    n_q = len(km.question_types)
    everywhere = [s for s in km.order if usage[s] == n_q]
    print(f"\nנדרשות לכל {n_q} סוגי השאלות: {len(everywhere)} מיומנויות ({', '.join(everywhere)})")
    print(f"לא נדרשות לאף סוג שאלה: {len(unused)} ({', '.join(unused)})")

    # --- coverage report -------------------------------------------------
    hot = sorted(
        (s for s in km.order if usage[s]),
        key=lambda s: (-usage[s], -len(km.descendants[s]), km.sort_key(s)),
    )
    lines = [
        "# דוח כיסוי – מיומנויות מול סוגי שאלות",
        "",
        "> נוצר ע״י `pipeline/03_closures.py`. \"שימוש\" = בכמה מתוך "
        f"{n_q} סוגי השאלות המיומנות נמצאת בסגור.",
        "",
        "## גודל הסגור לכל סוג שאלה",
        "",
        "| סוג | שם | ישירות | סגור | לפי תחום |",
        "|---|---|---|---|---|",
    ]
    for qid, q in qt_out.items():
        dom = ", ".join(f"{d} {len(v)}" for d, v in q["byDomain"].items())
        lines.append(f"| {qid} | {q['label']} | {len(q['direct'])} | {q['size']} | {dom} |")
    lines += [
        "",
        f"## הצמתים החמים (Top {HOT_TOP})",
        "",
        "פער באחת מאלה פוגע כמעט בכל שאלה בבגרות – ולכן הן המועמדות הראשונות לאבחון.",
        "",
        "| מיומנות | שם | שכבה | סוגי שאלות | descendants |",
        "|---|---|---|---|---|",
    ]
    for s in hot[:HOT_TOP]:
        lines.append(
            f"| {s} | {km.label(s)} | {km.layers[s]} | {usage[s]}/{n_q} | {len(km.descendants[s])} |"
        )
    lines += [
        "",
        "## התפלגות",
        "",
        "| מספר סוגי שאלות | מיומנויות |",
        "|---|---|",
    ]
    dist = Counter(usage[s] for s in km.order)
    for k in sorted(dist, reverse=True):
        lines.append(f"| {k} | {dist[k]} |")
    lines += [
        "",
        f"## לא נדרשות לאף סוג שאלה ({len(unused)})",
        "",
    ]
    for s in unused:
        note = " – beyond (שאלון 582)" if km.skills[s]["note"] == "beyond" else ""
        lines.append(f"- `{s}` {km.label(s)} (שכבה {km.layers[s]}){note}")
    lines.append("")
    (BUILD / "coverage_report.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n→ build/closures.json")
    print("→ build/coverage_report.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
