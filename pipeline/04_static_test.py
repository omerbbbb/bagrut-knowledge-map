"""שלב 4 – מבחן האבחון הסטטי באלגברה.

מה עשינו בשלב הזה ולמה
-----------------------
המבחן הראשון שנבנה מהמפה: 15 שאלות קבועות מתוך 37 מיומנויות החשבון והאלגברה,
כל תלמיד עונה על כולן. הרעיון – לא לבדוק הכול, אלא לבחור מיומנויות שהתשובה
עליהן אומרת הרבה על מיומנויות אחרות דרך הגרף:

  * תשובה נכונה  ⇒ המיומנות "ידועה", וכל ה־ancestors שלה "נגזרים" כידועים.
  * תשובה שגויה  ⇒ המיומנות "נכשלה", וכל ה־descendants שלה "בסיכון".
  * **פער שורש** = מיומנות שנכשלה ואין לה ancestor שנכשל. זה המקום שבו צריך
    להתחיל את ההשלמה; כל שאר הכישלונות הם (אולי) סימפטומים.

בתהליך המקורי הבחירה נעשתה ביד, לפי שני עקרונות: פיזור בין שכבות, ועדיפות
למיומנויות עם fan-out גבוה. יצאה הרשימה:
  ar4, ar5, al10, al11, al3, al5, al7, al8, al12, al13, al14, al15, al17, al19, al22

הסקריפט מנסה לשחזר את הבחירה בכלל מפורש:

    score(s) = fanout(s) × depth(s)
      fanout(s) = מספר המיומנויות (בכל המפה) שמונות את s כקדם ישיר
      depth(s)  = s עצמה + ה־ancestors שלה בתוך חשבון/אלגברה – כל מה שתשובה נכונה מוכיחה

  * fan-out לבד מעדיף את השורשים (ar1, ar2…) – אבל תשובה נכונה עליהם לא מוכיחה
    כמעט כלום, ולכן כופלים ב־depth: שאלה טובה מספרת גם על מה שמתחת וגם על מה
    שמעל.
  * מדלגים על "חוליות בשרשרת": s שכל ה־descendants שלו עוברים דרך ילד יחיד c.
    את c עדיף לשאול – אותו מידע כלפי מעלה, יותר מידע כלפי מטה.
  * פיזור: לכל היותר 4 מיומנויות מאותה שכבה.

הכלל לא מגיע לרשימה המקורית בדיוק; הפלט מסביר כל הבדל. **הרשימה המקורית היא זו
שנכנסת לדף** – היא התוצר של התהליך, והכלל הוא ניסיון להסביר אותה, לא להחליף.

קלט:  data/knowledge_map_571.json, data/diagnostic_questions.json
פלט:  build/static_test_algebra.json
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.diagnostic import interpret_static, scope_from_map  # noqa: E402
from engine.graph import BUILD, QUESTIONS_FILE, KnowledgeMap, load_json, write_json  # noqa: E402

ORIGINAL = "ar4 ar5 al10 al11 al3 al5 al7 al8 al12 al13 al14 al15 al17 al19 al22".split()
SIZE = 15
LAYER_CAP = 4


def algebra_ids(km: KnowledgeMap) -> list[str]:
    return [s for s in km.order if km.domain(s) in ("ar", "al")]


def is_chain_link(km: KnowledgeMap, s: str) -> str | None:
    """Return the child c if every descendant of s goes through c, else None."""
    for c in km.children[s]:
        if km.descendants[s] == {c} | km.descendants[c]:
            return c
    return None


def select(km: KnowledgeMap) -> tuple[list[str], dict[str, dict]]:
    pool = algebra_ids(km)
    inside = set(pool)
    info = {}
    for s in pool:
        fanout = len(km.children[s])
        depth = 1 + len(km.ancestors[s] & inside)
        info[s] = {
            "fanout": fanout,
            "depth": depth,
            "score": fanout * depth,
            "chainTo": is_chain_link(km, s),
            "layer": km.layers[s],
        }
    ranked = sorted(pool, key=lambda s: (-info[s]["score"], km.sort_key(s)))
    chosen: list[str] = []
    per_layer: Counter[int] = Counter()
    for s in ranked:
        if info[s]["chainTo"]:
            info[s]["skipped"] = f"חוליה בשרשרת – כל ההמשך עובר דרך {info[s]['chainTo']}"
            continue
        if per_layer[km.layers[s]] >= LAYER_CAP:
            info[s]["skipped"] = f"שכבה {km.layers[s]} כבר מלאה ({LAYER_CAP})"
            continue
        if len(chosen) >= SIZE:
            info[s]["skipped"] = "מחוץ ל־15 הראשונים"
            continue
        chosen.append(s)
        per_layer[km.layers[s]] += 1
    for rank, s in enumerate(ranked, 1):
        info[s]["rank"] = rank
    return chosen, info


def explain(km: KnowledgeMap, s: str, info: dict, original: bool) -> str:
    i = info[s]
    base = f"{s} {km.label(s)} (שכבה {i['layer']}, fanout={i['fanout']}, depth={i['depth']}, ציון={i['score']}, דירוג {i['rank']})"
    if original:
        reason = i.get("skipped", "")
        if i["depth"] <= 3:
            reason += " · מעט ancestors: תשובה נכונה מוכיחה מעט, והכלל מעדיף לשאול מעליה"
        return f"{base}: {reason.strip(' ·')}"
    why = []
    if i["fanout"] >= 5:
        why.append(f"פותחת {i['fanout']} מיומנויות ישירות")
    if i["depth"] >= 11:
        why.append(f"נשענת על {i['depth'] - 1} מיומנויות – תשובה נכונה מוכיחה הרבה")
    return f"{base}: " + ("; ".join(why) or "ציון גבוה")


def main() -> int:
    km = KnowledgeMap.load()
    questions = {q["skill"]: q for q in load_json(QUESTIONS_FILE)["questions"]}
    pool = algebra_ids(km)
    assert len(pool) == 37 and all(s in questions for s in pool)

    chosen, info = select(km)
    same = [s for s in ORIGINAL if s in chosen]
    missing = [s for s in ORIGINAL if s not in chosen]
    extra = [s for s in chosen if s not in ORIGINAL]

    print(f"מאגר: {len(pool)} מיומנויות חשבון/אלגברה\n")
    print("הבחירה המחושבת (לפי ציון):")
    for s in chosen:
        mark = "=" if s in ORIGINAL else "+"
        i = info[s]
        print(f"  {mark} {s:<5} שכבה {i['layer']:>2}  fanout {i['fanout']:>2} × depth {i['depth']:>2} = {i['score']:>3}  {km.label(s)}")
    print(f"\nחפיפה עם הבחירה המקורית: {len(same)}/{SIZE}")
    if missing or extra:
        print("\nלמה לא בדיוק אותה רשימה:")
        print("  במקורית ולא בכלל:")
        for s in missing:
            print("   -", explain(km, s, info, True))
        print("  בכלל ולא במקורית:")
        for s in extra:
            print("   +", explain(km, s, info, False))
        print(
            "\n  המשותף: הבחירה המקורית העדיפה בסיס של חשבון (ar4, ar5, al3) ו״ענפים״ בודדים\n"
            "  שכל אחד מהם הוא סוג אחר של כישלון; הכלל המספרי מעדיף מיומנויות עמוקות עם\n"
            "  הרבה המשכים ישירים (al2, al16, al24, al25). ההבדל הוא שיפוט דידקטי – אילו\n"
            "  בסיסים שווה לבדוק במפורש – שלא נמצא בגרף עצמו."
        )

    layers_orig = Counter(km.layers[s] for s in ORIGINAL)
    print("\nפיזור הבחירה המקורית לפי שכבות: " + ", ".join(f"L{k}:{v}" for k, v in sorted(layers_orig.items())))

    scope = scope_from_map(km, pool)
    all_right = interpret_static(scope, {s: True for s in ORIGINAL})["summary"]["counts"]
    print(
        f"\nאם כל 15 התשובות נכונות: {all_right['known']} ידועות + {all_right['inferred']} נגזרות, "
        f"{all_right['na']} נשארות לא ידועות"
    )

    out = BUILD / "static_test_algebra.json"
    write_json(
        out,
        {
            "rule": {
                "score": "fanout(s) × depth(s)",
                "fanout": "number of skills (whole map) listing s as a direct prerequisite",
                "depth": "1 + number of ancestors of s inside ar/al (what a correct answer proves)",
                "skipChainLinks": True,
                "layerCap": LAYER_CAP,
            },
            "original": ORIGINAL,
            "computed": chosen,
            "overlap": same,
            "onlyOriginal": missing,
            "onlyComputed": extra,
            "used": ORIGINAL,
            "scores": info,
            "interpretation": {
                "correct": "skill → known; every ancestor → inferred",
                "wrong": "skill → failed; every untested descendant → risk",
                "rootGap": "failed skill with no failed ancestor",
            },
            "scope": scope,
            "questions": [questions[s] for s in ORIGINAL],
        },
    )
    print(f"\n→ {out.relative_to(BUILD.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
