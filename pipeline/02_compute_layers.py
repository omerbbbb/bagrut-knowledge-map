"""שלב 2 – חישוב שכבות.

מה עשינו בשלב הזה ולמה
-----------------------
הניסיון הראשון של המפה חילק ~76 "נושאים" ל־9 שכבות שנקבעו ביד – "חשבון",
"אלגברה בסיסית", "אלגברה מתקדמת", "פונקציות", "חדו״א" וכו'. בביקורת התברר
ששכבה ידנית לא אומרת כלום: היא תווית של פרק בספר, לא טענה על הידע. אפשר היה
לשים שני נושאים באותה "שכבה" כשאחד תלוי בשני, ואף אחד לא היה שם לב. הניסיון
הזה נזרק (ראה docs/process.md).

ההגדרה שהחליפה אותו: שכבה היא **המסלול הארוך ביותר לבסיס**.

    layer(n) = 0                          אם אין ל־n קדם
    layer(n) = 1 + max(layer(p))          על כל קדם p של n

השכבה לא נשמרת בנתונים – היא נגזרת מהקשרים, ולכן לא יכולה לסתור אותם.
התכונה שמתקבלת בחינם, ושהסקריפט בודק במפורש: **שתי מיומנויות באותה שכבה לעולם
לא תלויות זו בזו** (אם a קדם של b, אז layer(b) > layer(a)). בנוסף, שכבה k תמיד
מכילה לפחות מיומנות אחת שיש לה קדם בשכבה k−1 – אין "חורים".

קלט:  data/knowledge_map_571.json
פלט:  build/layers.json – {"layers": {id: layer}, "byLayer": [[ids…], …]}
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.graph import BUILD, KnowledgeMap, write_json  # noqa: E402


def check_same_layer_independent(km: KnowledgeMap) -> list[tuple[str, str]]:
    """Pairs in the same layer where one is an ancestor of the other (should be empty)."""
    bad = []
    by_layer = defaultdict(list)
    for s in km.order:
        by_layer[km.layers[s]].append(s)
    for members in by_layer.values():
        mset = set(members)
        for s in members:
            for a in km.ancestors[s] & mset:
                bad.append((a, s))
    return bad


def main() -> int:
    km = KnowledgeMap.load()
    layers = km.layers
    n_layers = max(layers.values()) + 1
    by_layer = [[s for s in km.order if layers[s] == k] for k in range(n_layers)]

    print(f"{len(km.order)} מיומנויות ב־{n_layers} שכבות מחושבות\n")
    print(f"{'שכבה':>4}  {'#':>3}  דוגמאות")
    for k, members in enumerate(by_layer):
        sample = ", ".join(f"{s} {km.label(s)}" for s in members[:3])
        more = f" (+{len(members) - 3})" if len(members) > 3 else ""
        print(f"{k:>4}  {len(members):>3}  {sample}{more}")

    bad = check_same_layer_independent(km)
    if bad:
        print(f"\n✗ {len(bad)} זוגות באותה שכבה עם תלות – לא אמור לקרות:")
        for a, s in bad:
            print(f"  {a} → {s}")
        return 1
    n_pairs = sum(len(m) * (len(m) - 1) // 2 for m in by_layer)
    print(f"\n✓ נבדקו {n_pairs} זוגות בתוך שכבות: אף מיומנות לא תלויה באחרת מאותה שכבה")

    # Every edge goes strictly upward, and every non-root has a prereq exactly one layer below.
    assert all(layers[p] < layers[s] for p, s in km.edges)
    assert all(
        any(layers[p] == layers[s] - 1 for p in km.prereqs(s)) for s in km.order if km.prereqs(s)
    )
    print("✓ כל קשת עולה שכבה; לכל מיומנות שאינה שורש יש קדם בשכבה שמתחתיה בדיוק")

    top = by_layer[-1]
    print(f"\nהשכבה העליונה ({n_layers - 1}): " + ", ".join(f"{s} {km.label(s)}" for s in top))

    out = BUILD / "layers.json"
    write_json(out, {"layerCount": n_layers, "layers": layers, "byLayer": by_layer})
    print(f"\n→ {out.relative_to(BUILD.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
