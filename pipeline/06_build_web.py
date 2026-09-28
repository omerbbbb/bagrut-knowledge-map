"""שלב 6 – בניית דפי הווב.

מה עשינו בשלב הזה ולמה
-----------------------
ארבעה דפים שמראים את התהליך כפי שהוא נחווה – המפה, המבחן הסטטי, המנוע
האדפטיבי והמסע משאלת בגרות ובחזרה. כל דף הוא קובץ HTML יחיד שנפתח מהדיסק,
בלי רשת ובלי ספריות: הנתונים מוטמעים בתוכו כ־JSON, והמנוע (engine/diagnostic.js)
מוטמע כמו שהוא – אותו קובץ שנבדק מול מנוע ה־Python ב־tests/test_parity.py.

פריסת המפה מחושבת כאן ולא בדפדפן: שורה לכל שכבה מחושבת, ובתוך שורה סדר שנקבע
בכמה מעברי barycenter (כל צומת נמשך לממוצע המיקומים של שכניו) כדי לצמצם
הצטלבויות. הפריסה דטרמיניסטית – אותו קלט, אותו ציור.

קלט:  data/*.json, build/static_test_algebra.json, engine/diagnostic.js,
      web/templates/*
פלט:  web/map.html, web/diagnostic_static.html, web/diagnostic_adaptive.html,
      web/journey.html, web/guided.html
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader, StrictUndefined  # noqa: E402

from engine.graph import (  # noqa: E402
    BAGRUT_FILE, BUILD, QUESTIONS_FILE, ROOT, KnowledgeMap, load_json,
)
from engine.diagnostic import scope_from_map  # noqa: E402
from engine.scenarios import algebra_scope, journey_scope  # noqa: E402

WEB = ROOT / "web"
TEMPLATES = WEB / "templates"
ENGINE_JS = ROOT / "engine" / "diagnostic.js"

DOMAIN_COLORS = {
    "ar": "#9a6b3f", "al": "#2563a8", "fn": "#0e8a7e", "ge": "#7b4fa0",
    "tr": "#b8327a", "an": "#5d7a1f", "sq": "#c0831a", "pr": "#5a67d8",
    "gd": "#2c8fbf", "md": "#d0543b", "ca": "#23345e", "bx": "#8a8a8a",
}

COMPACT = {"nodeW": 58, "nodeH": 26, "gapX": 8, "gapY": 46, "pad": 18}
LABELED = {"nodeW": 118, "nodeH": 44, "gapX": 12, "gapY": 44, "pad": 20}


def wrap_label(label: str, width: int = 17, max_lines: int = 2) -> list[str]:
    words, lines, cur = label.split(), [], ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: width - 1].rstrip() + "…"
    return [ln if len(ln) <= width + 2 else ln[: width].rstrip() + "…" for ln in lines]


def layout(km: KnowledgeMap, ids, dims: dict, passes: int = 6) -> dict:
    """Rows = computed layers (0 at the top). Within a row: barycenter ordering."""
    inside = set(ids)
    dom_rank = {d: i for i, d in enumerate(km.domains)}
    layers = sorted({km.layers[s] for s in ids})
    rows = {
        L: sorted((s for s in ids if km.layers[s] == L), key=lambda s: (dom_rank[km.domain(s)], km.order.index(s)))
        for L in layers
    }
    pre = {s: [p for p in km.prereqs(s) if p in inside] for s in ids}
    kids = {s: [c for c in km.children[s] if c in inside] for s in ids}

    def xs() -> dict[str, float]:
        out = {}
        for row in rows.values():
            for i, s in enumerate(row):
                out[s] = i - (len(row) - 1) / 2
        return out

    for _ in range(passes):
        for L in layers[1:]:
            x = xs()
            rows[L].sort(key=lambda s: sum(x[p] for p in pre[s]) / len(pre[s]) if pre[s] else x[s])
        for L in reversed(layers[:-1]):
            x = xs()
            rows[L].sort(key=lambda s: sum(x[c] for c in kids[s]) / len(kids[s]) if kids[s] else x[s])

    W, H, gx, gy, pad = dims["nodeW"], dims["nodeH"], dims["gapX"], dims["gapY"], dims["pad"]
    max_cols = max(len(r) for r in rows.values())
    width = pad * 2 + max_cols * W + (max_cols - 1) * gx + 40  # 40: room for row labels
    center = 40 + pad + (max_cols * W + (max_cols - 1) * gx) / 2
    nodes = {}
    for ri, L in enumerate(layers):
        row = rows[L]
        for i, s in enumerate(row):
            off = i - (len(row) - 1) / 2
            # RTL: first in row on the right
            nodes[s] = {"x": round(center - off * (W + gx), 1), "y": pad + ri * (H + gy) + H / 2}
    height = pad * 2 + len(layers) * H + (len(layers) - 1) * gy
    return {
        **dims,
        "width": round(width),
        "height": round(height),
        "rows": [{"layer": L, "y": pad + ri * (H + gy) + H / 2} for ri, L in enumerate(layers)],
        "nodes": nodes,
        "edges": [[p, s] for s in ids for p in pre[s]],
    }


def skill_payload(km: KnowledgeMap, ids) -> dict:
    return {
        s: {
            "id": s,
            "label": km.label(s),
            "domain": km.domain(s),
            "layer": km.layers[s],
            "prerequisites": km.prereqs(s),
            "note": km.skills[s]["note"],
            "lines": wrap_label(km.label(s)),
        }
        for s in ids
    }


def dumps(obj) -> str:
    # Safe inside <script type="application/json">
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def main() -> int:
    km = KnowledgeMap.load()
    questions = {q["skill"]: q for q in load_json(QUESTIONS_FILE)["questions"]}
    bagrut = load_json(BAGRUT_FILE)
    static = load_json(BUILD / "static_test_algebra.json")
    domains = {d: {"name": n, "color": DOMAIN_COLORS[d]} for d, n in km.domains.items()}

    env = Environment(loader=FileSystemLoader(TEMPLATES), undefined=StrictUndefined, autoescape=False)
    shared = {
        "css": (TEMPLATES / "_style.css").read_text(encoding="utf-8"),
        "ui_js": (TEMPLATES / "_ui.js").read_text(encoding="utf-8"),
        "engine_js": ENGINE_JS.read_text(encoding="utf-8"),
    }

    all_ids = km.order
    qt = []
    for q in km.question_types:
        closure = km.closure(q["skills"])
        qt.append({"id": q["id"], "label": q["label"], "direct": q["skills"], "closure": km.sorted(closure)})
    map_data = {
        "title": km.meta["title"],
        "domains": domains,
        "skills": skill_payload(km, all_ids),
        "order": all_ids,
        "ancestors": {s: km.sorted(km.ancestors[s]) for s in all_ids},
        "descendants": {s: km.sorted(km.descendants[s]) for s in all_ids},
        "children": km.children,
        "questionTypes": qt,
        "layout": layout(km, all_ids, COMPACT),
        "layerCount": max(km.layers.values()) + 1,
    }

    alg = algebra_scope(km)
    alg_ids = [s["id"] for s in alg["skills"]]
    alg_layout = layout(km, alg_ids, LABELED)
    static_data = {
        "domains": domains,
        "skills": skill_payload(km, alg_ids),
        "scope": alg,
        "layout": alg_layout,
        "test": static["used"],
        "questions": {s: questions[s] for s in static["used"]},
    }
    adaptive_data = {
        "domains": domains,
        "skills": skill_payload(km, alg_ids),
        "scope": alg,
        "layout": alg_layout,
        "questions": {s: questions[s] for s in alg_ids},
    }

    jrn = journey_scope(km, bagrut["questionType"])
    jrn_ids = [s["id"] for s in jrn["skills"]]
    tags: dict[str, list[str]] = {}
    for sec in bagrut["sections"]:
        for s in sec["skills"]:
            tags.setdefault(s, []).append(sec["id"])
    journey_data = {
        "domains": domains,
        "skills": skill_payload(km, jrn_ids),
        "scope": jrn,
        "layout": layout(km, jrn_ids, LABELED),
        "questions": {s: questions[s] for s in jrn_ids},
        "bagrut": bagrut,
        "questionType": {"id": bagrut["questionType"], "label": km.question_type(bagrut["questionType"])["label"]},
        "sectionTags": tags,
    }

    q_ids = [s for s in km.order if s in questions]
    guided_scope = {"skills": [x for x in scope_from_map(km, q_ids)["skills"]]}
    guided_data = {
        "domains": domains,
        "skills": skill_payload(km, q_ids),
        "scope": guided_scope,
        "layout": layout(km, q_ids, LABELED),
        "questions": {s: questions[s] for s in q_ids},
        "bagrut": bagrut,
        "sectionTags": tags,
    }
    map_data["withQuestion"] = q_ids

    pages = [
        ("map.html", map_data),
        ("diagnostic_static.html", static_data),
        ("diagnostic_adaptive.html", adaptive_data),
        ("journey.html", journey_data),
        ("guided.html", guided_data),
    ]
    for name, data in pages:
        html = env.get_template(name).render(page=name, data_json=dumps(data), **shared)
        (WEB / name).write_text(html, encoding="utf-8")
        print(f"→ web/{name}  ({len(html.encode('utf-8')) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
