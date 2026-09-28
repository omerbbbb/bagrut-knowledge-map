"""Built pages are self-contained: inline data, the tested engine, no network."""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["map.html", "diagnostic_static.html", "diagnostic_adaptive.html", "journey.html", "guided.html"]
ENGINE = (ROOT / "engine" / "diagnostic.js").read_text(encoding="utf-8")


@pytest.mark.parametrize("page", PAGES)
def test_page_is_self_contained(page):
    html = (ROOT / "web" / page).read_text(encoding="utf-8")
    assert '<html lang="he" dir="rtl">' in html
    assert not re.search(r"""(src|href)=["']https?://""", html), "no network resources"
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)
    data = json.loads(m.group(1))
    assert data["skills"] and data["layout"]["nodes"]
    if page != "map.html":
        assert ENGINE in html, "the embedded engine must be the tested one"


def test_page_scopes():
    def data(page):
        html = (ROOT / "web" / page).read_text(encoding="utf-8")
        return json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert len(data("map.html")["skills"]) == 156
    assert len(data("diagnostic_static.html")["test"]) == 15
    assert len(data("diagnostic_adaptive.html")["scope"]["skills"]) == 37
    assert len(data("journey.html")["scope"]["skills"]) == 55


def test_guided_page_scope():
    html = (ROOT / "web" / "guided.html").read_text(encoding="utf-8")
    data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1))
    assert len(data["scope"]["skills"]) == 64 and len(data["questions"]) == 64
