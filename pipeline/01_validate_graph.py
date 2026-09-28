"""שלב 1 – אימות המפה.

מה עשינו בשלב הזה ולמה
-----------------------
המפה (156 מיומנויות, קשרי קדם, 16 סוגי שאלות) נבנתה ידנית, בשיחות ובסבבי
ביקורת. הקוד לא "מגלה" אותה – הוא בודק שהיא עקבית לפני שבונים עליה משהו.
כל שלב אחר בפייפליין מניח שהגרף הוא DAG תקין; אם הבדיקה הזאת נכשלת, אין טעם
להמשיך.

בדיקות שגורמות לכישלון (קוד יציאה 1):
  * כל prerequisite מצביע על מיומנות קיימת, ואין מיומנות שתלויה בעצמה.
  * אין מעגלים – הגרף הוא DAG.
  * אין קשר כפול (אותו prerequisite פעמיים באותה רשימה) ואין id כפול.
  * אין מיומנות מבודדת (בלי קדם ובלי המשך), חוץ מ־ar1 – שורש המפה.
  * כל questionType מצביע על מיומנויות קיימות.
  * קידומת ה־id תואמת ל־domain, וה־domain מוגדר ב־meta.

אזהרות (לא נכשלות, נרשמות ב־build/data_issues.md):
  * קשתות עודפות: p→s כאשר p כבר נגיש דרך prerequisite אחר של s. הן לא
    משנות שכבות או סגורים, אבל ייתכן שהן לא מכוונות.
  * מיומנויות שאף סוג שאלה לא דורש (לא בסגור של אף questionType).

קלט:  data/knowledge_map_571.json, data/diagnostic_questions.json
פלט:  build/data_issues.md, סיכום לטרמינל
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.graph import BUILD, MAP_FILE, KnowledgeMap, load_json  # noqa: E402

ALLOWED_ISOLATED = {"ar1"}

# Observations from reading the data by hand. Recorded, never auto-fixed.
MANUAL_NOTES = [
    (
        "diagnostic_questions.json · ar4",
        "המסיח ‎−10‎ ב־(−3) − (−7) מתויג \"חיסור של מספר שלילי הופך לחיבור\". "
        "זה הכלל הנכון, לא השגיאה – השגיאה היא *לא* להפוך לחיבור "
        "(−3 − 7 = −10). ניסוח בלבד; לא שונה.",
    ),
    (
        "diagnostic_questions.json · an3, an4",
        "27 השאלות שמעבר לחשבון/אלגברה מתוארות כ\"פונקציות/חדו״א\", אבל שתיים "
        "מהן (an3, an4) שייכות לתחום האנליטית. הן בסגור של q13, כך שהכיסוי נכון.",
    ),
]


def find_cycle(skills: dict[str, dict]) -> list[str] | None:
    """Return one cycle as a list of ids, or None. Iterative DFS, 3 colors."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {s: WHITE for s in skills}
    parent: dict[str, str] = {}
    for start in skills:
        if color[start] != WHITE:
            continue
        stack = [(start, iter(skills[start]["prerequisites"]))]
        color[start] = GRAY
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[node] = BLACK
                stack.pop()
                continue
            if nxt not in skills:
                continue
            if color[nxt] == GRAY:
                cycle = [nxt, node]
                while cycle[-1] != nxt:
                    cycle.append(parent[cycle[-1]])
                return list(reversed(cycle))
            if color[nxt] == WHITE:
                parent[nxt] = node
                color[nxt] = GRAY
                stack.append((nxt, iter(skills[nxt]["prerequisites"])))
    return None


def validate(raw: dict) -> list[str]:
    errors: list[str] = []
    ids = [s["id"] for s in raw["skills"]]
    for sid, n in Counter(ids).items():
        if n > 1:
            errors.append(f"id כפול: {sid} ({n} פעמים)")
    skills = {s["id"]: s for s in raw["skills"]}
    domains = raw["meta"]["domains"]

    for s in raw["skills"]:
        sid, ps = s["id"], s["prerequisites"]
        if s["domain"] not in domains:
            errors.append(f"{sid}: domain לא מוגדר '{s['domain']}'")
        prefix = re.match(r"[a-z]+", sid)
        if not prefix or prefix.group(0) != s["domain"]:
            errors.append(f"{sid}: הקידומת לא תואמת ל־domain '{s['domain']}'")
        for p in ps:
            if p not in skills:
                errors.append(f"{sid}: prerequisite לא קיים '{p}'")
            if p == sid:
                errors.append(f"{sid}: תלוי בעצמו")
        for p, n in Counter(ps).items():
            if n > 1:
                errors.append(f"{sid}: קשר כפול אל {p}")

    cycle = find_cycle(skills)
    if cycle:
        errors.append("מעגל: " + " → ".join(cycle))

    has_child = {p for s in raw["skills"] for p in s["prerequisites"]}
    for sid in ids:
        if not skills[sid]["prerequisites"] and sid not in has_child and sid not in ALLOWED_ISOLATED:
            errors.append(f"{sid}: מיומנות מבודדת – בלי קדם ובלי המשך")

    qids = [q["id"] for q in raw["questionTypes"]]
    for qid, n in Counter(qids).items():
        if n > 1:
            errors.append(f"questionType כפול: {qid}")
    for q in raw["questionTypes"]:
        if not q["skills"]:
            errors.append(f"{q['id']}: אין מיומנויות")
        for sid in q["skills"]:
            if sid not in skills:
                errors.append(f"{q['id']}: מצביע על מיומנות לא קיימת '{sid}'")
    return errors


def validate_questions(km: KnowledgeMap, questions: dict) -> list[str]:
    errors = []
    seen = Counter(q["skill"] for q in questions["questions"])
    for sid, n in seen.items():
        if sid not in km.skills:
            errors.append(f"שאלת אבחון למיומנות לא קיימת: {sid}")
        if n > 1:
            errors.append(f"יותר משאלה אחת למיומנות {sid}")
    for q in questions["questions"]:
        texts = [d["text"] for d in q["distractors"]]
        if q["correct"] in texts:
            errors.append(f"{q['skill']}: התשובה הנכונה מופיעה גם כמסיח")
        if len(set(texts)) != len(texts):
            errors.append(f"{q['skill']}: מסיח כפול")
    return errors


def write_issues(km: KnowledgeMap, redundant, unused) -> Path:
    lines = [
        "# בעיות אפשריות בנתונים",
        "",
        "> נוצר אוטומטית ע״י `pipeline/01_validate_graph.py`. שום דבר כאן לא תוקן בנתונים –",
        "> זו רשימה לבדיקה ידנית.",
        "",
        f"## קשתות עודפות ({len(redundant)})",
        "",
        "הקדם p כבר נגיש דרך קדם אחר של s, ולכן הקשת p→s לא משנה שכבות או סגורים.",
        "היא כן משפיעה על המנוע האדפטיבי: כש־s נכשל, p נכנס לרשימת ההשערות הישירות.",
        "ייתכן שהיא מכוונת (\"כישלון ב־s חשוד קודם כול ב־p\") וייתכן שלא.",
        "",
        "| מיומנות s | קדם עודף p | נגיש דרך |",
        "|---|---|---|",
    ]
    for p, s in redundant:
        via = [o for o in km.prereqs(s) if o != p and p in km.ancestors[o]]
        lines.append(f"| {s} {km.label(s)} | {p} {km.label(p)} | {', '.join(via)} |")
    lines += [
        "",
        f"## מיומנויות שאף סוג שאלה לא דורש ({len(unused)})",
        "",
        "לא נמצאות בסגור של אף אחד מ־16 סוגי השאלות. עבור bx זה צפוי (מעבר ל־571).",
        "",
    ]
    for s in unused:
        note = " _(beyond)_" if km.skills[s]["note"] == "beyond" else ""
        lines.append(f"- `{s}` {km.label(s)}{note}")
    lines += ["", "## הערות מקריאה ידנית", ""]
    for where, text in MANUAL_NOTES:
        lines.append(f"- **{where}** – {text}")
    lines.append("")
    out = BUILD / "data_issues.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main() -> int:
    raw = load_json(MAP_FILE)
    print(f"טוען {MAP_FILE.relative_to(MAP_FILE.parent.parent)}")
    errors = validate(raw)
    if errors:
        print(f"\n✗ {len(errors)} שגיאות במפה:")
        for e in errors:
            print("  -", e)
        return 1

    km = KnowledgeMap(raw)
    from engine.graph import QUESTIONS_FILE
    q_errors = validate_questions(km, load_json(QUESTIONS_FILE))
    if q_errors:
        print(f"\n✗ {len(q_errors)} שגיאות בשאלות האבחון:")
        for e in q_errors:
            print("  -", e)
        return 1

    print("✓ כל ה־prerequisites קיימים")
    print("✓ אין מעגלים (DAG)")
    print("✓ אין קשרים כפולים")
    print("✓ אין מיומנויות מבודדות (מלבד ar1)")
    print("✓ כל סוגי השאלות מצביעים על מיומנויות קיימות")
    print("✓ שאלות האבחון מצביעות על מיומנויות קיימות, אחת לכל מיומנות")

    print(f"\nמיומנויות: {len(km.order)}   קשתות: {len(km.edges)}   סוגי שאלות: {len(km.question_types)}")
    print("\nלפי תחום:")
    counts = Counter(km.domain(s) for s in km.order)
    for d, name in km.domains.items():
        print(f"  {d:<3} {counts[d]:>3}  {name}")
    print(f"\nשורשים ({len(km.roots())}): {', '.join(km.roots())}")
    leaves = km.leaves()
    print(f"עלים ({len(leaves)}): {', '.join(leaves)}")

    redundant = km.redundant_edges()
    required = km.closure(s for q in km.question_types for s in q["skills"])
    unused = [s for s in km.order if s not in required]
    print(f"\n⚠ {len(redundant)} קשתות עודפות (לא שגיאה, ראה data_issues.md)")
    print(f"⚠ {len(unused)} מיומנויות שאף סוג שאלה לא דורש: {', '.join(unused)}")
    out = write_issues(km, redundant, unused)
    print(f"\n→ {out.relative_to(BUILD.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
