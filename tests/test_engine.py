"""Engine behaviour on the scenarios documented in the README."""
from engine.diagnostic import Diagnostic, guided_ladder, interpret_static
from engine.graph import KnowledgeMap
from engine.scenarios import algebra_scope, journey_scope, run, section_results, unknown_set

KM = KnowledgeMap.load()
ALG = algebra_scope(KM)


def sim(gaps):
    return run(ALG, unknown_set(KM, gaps))


def roots(res):
    return [r["skill"] for r in res["summary"]["rootGaps"]]


def test_scopes():
    assert len(ALG["skills"]) == 37
    assert len(journey_scope(KM)["skills"]) == 55


def test_all_known():
    res = sim([])
    assert 18 <= res["summary"]["asked"] <= 22
    assert roots(res) == [] and res["summary"]["counts"]["na"] == 0


def test_gap_al7():
    res = sim(["al7"])
    assert 13 <= res["summary"]["asked"] <= 17
    assert roots(res) == ["al7"]


def test_gap_ar4_descends():
    res = sim(["ar4"])
    assert 9 <= res["summary"]["asked"] <= 13
    failed_seq = [s["skill"] for s in res["steps"] if not s["correct"]]
    assert failed_seq == ["al7", "al5", "al4", "al3", "al1", "ar4"]
    assert roots(res) == ["ar4"]


def test_two_roots_no_symptoms():
    res = sim(["al15", "al13"])
    assert sorted(roots(res)) == ["al13", "al15"]
    assert all(r["confirmed"] for r in res["summary"]["rootGaps"])


def test_every_single_gap_is_found():
    for s in [x["id"] for x in ALG["skills"]]:
        res = sim([s])
        assert roots(res) == [s], s
        assert res["summary"]["contradictions"] == []


def test_journey_ca4():
    unknown = unknown_set(KM, ["ca4"])
    sections = section_results(unknown)
    assert [s["id"] for s in sections if not s["correct"]] == ["ד", "ז"]
    res = run(journey_scope(KM), unknown, sections)
    assert roots(res) == ["ca4"]
    assert res["summary"]["integration"] == []
    assert res["summary"]["sectionCauses"] == {"ד": ["ca6"], "ז": ["ca6"]}


def test_integration_difficulty():
    # All skills known, yet the student fails section ד: a combination difficulty.
    scope = journey_scope(KM)
    sections = [{**s, "correct": s["id"] != "ד"} for s in section_results([])]
    res = run(scope, [], sections)
    assert res["summary"]["integration"] == ["ד"]
    assert roots(res) == []


def test_contradiction_reported():
    out = interpret_static(ALG, {"ar4": False, "al7": True})
    assert out["summary"]["contradictions"] == [{"skill": "al7", "failedAncestors": ["ar4"]}]


def test_static_interpretation():
    out = interpret_static(ALG, {"al3": True, "al7": False, "al5": False})
    st = out["status"]
    assert st["al1"] == "inferred" and st["al17"] == "risk"
    assert [r["skill"] for r in out["summary"]["rootGaps"]] == ["al5"]


def test_finish_closes_stack():
    d = Diagnostic(ALG)
    q = d.next_question()
    d.answer(q["skill"], False)
    d.finish()
    assert d.stack == []


def test_guided_ladder_section_d():
    scope = journey_scope(KM)
    assert guided_ladder(scope, ["ca6", "ca12"], 1) == ["al26", "ca2", "al27", "ca4", "ca5", "ca6", "ca12"]


def test_guided_ladder_personal_skips_known():
    scope = journey_scope(KM)
    unknown = unknown_set(KM, ["ca4"])
    status = run(scope, unknown, section_results(unknown))["status"]
    assert guided_ladder(scope, ["ca6", "ca12"], 1, status) == ["ca4", "ca6"]
