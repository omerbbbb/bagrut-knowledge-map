"""שלב 7 – שאלות מנחות מתוך רשת הידע.

מה עשינו בשלב הזה ולמה
-----------------------
זה המוצר: ברגע שיש רשת ידע (מיומנות = צומת, קשר קדם = קשת) ושאלה אחת לכל
צומת, **שאלות מנחות לא צריך לכתוב – הן נגזרות מהגרף.**

לשאלה קשה (סעיף בגרות, או מיומנות) לוקחים את המיומנויות שהיא בודקת, מוסיפים את
הקדמים הישירים שלהן (עומק 1, או 2 לסולם ארוך יותר), וממיינים לפי שכבה – מלמטה
למעלה. כל שלב בסולם הוא שאלת האבחון הקיימת של אותה מיומנות, והשלב האחרון הוא
השאלה הקשה עצמה. במצב אישי (אחרי אבחון) מדלגים על מה שהתלמיד כבר יודע, ונשאר
רק מה שהוא צריך.

אותה פונקציה (engine.diagnostic.guided_ladder / guidedLadder ב־JS) משמשת את
הדף web/guided.html ואת סיכום המסע; tests/test_parity.py בודק ששתיהן זהות.

קלט:  data/*.json
פלט:  build/guided_questions.json, build/guided_questions.md
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.diagnostic import guided_ladder, scope_from_map  # noqa: E402
from engine.graph import BAGRUT_FILE, BUILD, QUESTIONS_FILE, KnowledgeMap, load_json, write_json  # noqa: E402
from engine.scenarios import journey_scope, run, section_results, unknown_set  # noqa: E402


def question_scope(km: KnowledgeMap, questions: dict) -> dict:
    """All skills that have a diagnostic question. The set is closed downward."""
    ids = [s for s in km.order if s in questions]
    assert all(p in questions for s in ids for p in km.prereqs(s)), "question bank must be closed downward"
    return scope_from_map(km, ids)


def main() -> int:
    km = KnowledgeMap.load()
    questions = {q["skill"]: q for q in load_json(QUESTIONS_FILE)["questions"]}
    bagrut = load_json(BAGRUT_FILE)
    scope = question_scope(km, questions)

    out = {"sections": [], "coverage": {}}
    md = [
        "# שאלות מנחות – נגזרות מרשת הידע",
        "",
        "> נוצר ע״י `pipeline/07_guided_questions.py`. אף שאלה כאן לא נכתבה במיוחד: כל שלב",
        "> הוא שאלת האבחון הקיימת של מיומנות, והסדר נקבע רק מהגרף (קדמים ישירים, לפי שכבה).",
        "",
        f"## שאלת הבגרות: `{bagrut['function']}`",
        "",
    ]
    print(f"בנק השאלות: {len(scope['skills'])} מיומנויות (סגור כלפי מטה)\n")
    for sec in bagrut["sections"]:
        ladder = guided_ladder(scope, sec["skills"], 1)
        out["sections"].append({"id": sec["id"], "title": sec["title"], "targets": sec["skills"], "ladder": ladder})
        print(f"סעיף {sec['id']} {sec['title']}: {len(ladder)} שלבים  " + " → ".join(ladder))
        md += [f"### סעיף {sec['id']} – {sec['title']}", ""]
        for i, s in enumerate(ladder, 1):
            q = questions[s]
            tag = " **(מיומנות הסעיף)**" if s in sec["skills"] else ""
            md.append(f"{i}. `{s}` {km.label(s)} (שכבה {km.layers[s]}){tag}  ")
            md.append(f"   {q['prompt']}  →  {q['correct']}")
        md += [f"{len(ladder) + 1}. **הסעיף עצמו:** {sec['title']}  →  {sec['correct']}", ""]

    # Personal mode example: after the journey diagnostic, keep only what is missing.
    unknown = unknown_set(km, ["ca4"])
    status = run(journey_scope(km), unknown, section_results(unknown, bagrut))["status"]
    personal = guided_ladder(scope, ["ca6", "ca12"], 1, status)
    md += [
        "## מצב אישי – אחרי אבחון",
        "",
        "תלמיד שלא יודע `ca4` (נגזרת מנה) ונפל בסעיף ד׳: מתוך 7 השלבים של הסולם נשארים רק",
        f"**{len(personal)}** – {' → '.join(personal)} – ואז הסעיף עצמו. כל השאר כבר הוכח באבחון.",
        "",
    ]
    out["personalExample"] = {"student": "does not know ca4", "section": "ד", "ladder": personal}

    # How far the bank already goes, and what one new question would unlock.
    have = set(questions)
    ready = [s for s in km.order if s not in have and all(p in have for p in km.prereqs(s))]
    out["coverage"] = {"withLadder": len(have), "total": len(km.order), "oneQuestionAway": ready}
    md += [
        "## כיסוי",
        "",
        f"- ל־**{len(have)}** מיומנויות יש כבר סולם מלא (הן וכל הקדמים שלהן בבנק).",
        f"- **{len(ready)}** מיומנויות נוספות רחוקות שאלה אחת בלבד: כל הקדמים שלהן בבנק,",
        "  וכתיבת שאלה אחת עבורן נותנת סולם מלא מיד:",
        "",
        "  " + ", ".join(f"`{s}`" for s in ready),
        "",
    ]
    print(f"\nמצב אישי (לא יודע ca4, סעיף ד׳): {' → '.join(personal)}")
    print(f"כיסוי: {len(have)}/{len(km.order)} עם סולם מלא; {len(ready)} רחוקות שאלה אחת")

    write_json(BUILD / "guided_questions.json", out)
    (BUILD / "guided_questions.md").write_text("\n".join(md), encoding="utf-8")
    print("\n→ build/guided_questions.json\n→ build/guided_questions.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
