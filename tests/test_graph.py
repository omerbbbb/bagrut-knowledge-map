import importlib.util
from pathlib import Path

from engine.graph import KnowledgeMap, load_json, MAP_FILE

KM = KnowledgeMap.load()


def _load(name):
    path = Path(__file__).resolve().parent.parent / "pipeline" / name
    spec = importlib.util.spec_from_file_location(name[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_map_is_valid():
    assert _load("01_validate_graph.py").validate(load_json(MAP_FILE)) == []


def test_validator_catches_cycle():
    raw = load_json(MAP_FILE)
    ar1 = next(s for s in raw["skills"] if s["id"] == "ar1")
    ar1["prerequisites"] = ["al1"]
    assert any("מעגל" in e for e in _load("01_validate_graph.py").validate(raw))


def test_validator_catches_missing_and_duplicate():
    raw = load_json(MAP_FILE)
    raw["skills"][1]["prerequisites"] = ["ar1", "ar1", "zz9"]
    errs = _load("01_validate_graph.py").validate(raw)
    assert any("zz9" in e for e in errs) and any("כפול" in e for e in errs)


def test_layers():
    assert max(KM.layers.values()) + 1 == 15
    for p, s in KM.edges:
        assert KM.layers[p] < KM.layers[s]


def test_same_layer_independent():
    assert _load("02_compute_layers.py").check_same_layer_independent(KM) == []


def test_counts():
    assert len(KM.order) == 156 and len(KM.edges) == 305 and len(KM.question_types) == 16
