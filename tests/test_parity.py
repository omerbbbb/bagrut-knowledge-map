"""Python ↔ JS parity: both engines must produce the same questions, reasons, log and summary."""
import json
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from engine.diagnostic import guided_ladder, interpret_static
from engine.graph import KnowledgeMap
from engine.scenarios import (
    ALGEBRA, JOURNEY, algebra_scope, journey_scope, run, section_results, unknown_set,
)

RUNNER = Path(__file__).with_name("js_runner.js")
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is required for the parity test")

KM = KnowledgeMap.load()
ALG = algebra_scope(KM)
JRN = journey_scope(KM)


def js(job: dict) -> dict:
    out = subprocess.run([NODE, str(RUNNER)], input=json.dumps(job), capture_output=True,
                         text=True, check=True)
    return json.loads(out.stdout)


def normalize(obj):
    # JSON round-trip so tuples/lists and int/float compare the same way
    return json.loads(json.dumps(obj))


def algebra_cases():
    cases = [(c["id"], c["gaps"]) for c in ALGEBRA]
    cases += [(f"single_{s}", [s]) for s in [x["id"] for x in ALG["skills"]]]
    rng = random.Random(571)
    ids = [x["id"] for x in ALG["skills"]]
    cases += [(f"random_{i}", rng.sample(ids, rng.randint(2, 4))) for i in range(20)]
    return cases


@pytest.mark.parametrize("name,gaps", algebra_cases(), ids=lambda v: v if isinstance(v, str) else None)
def test_adaptive_parity(name, gaps):
    unknown = unknown_set(KM, gaps)
    py = normalize(run(ALG, unknown))
    assert py == js({"scope": ALG, "unknown": unknown})


def journey_cases():
    cases = [(c["id"], c["gaps"]) for c in JOURNEY]
    ids = [x["id"] for x in JRN["skills"]]
    cases += [(f"journey_{s}", [s]) for s in ids]
    return cases


@pytest.mark.parametrize("name,gaps", journey_cases(), ids=lambda v: v if isinstance(v, str) else None)
def test_journey_parity(name, gaps):
    unknown = unknown_set(KM, gaps)
    sections = section_results(unknown)
    py = normalize(run(JRN, unknown, sections))
    assert py == js({"scope": JRN, "unknown": unknown, "sections": sections})


@pytest.mark.parametrize("seed", range(10))
def test_static_parity(seed):
    rng = random.Random(seed)
    skills = rng.sample([x["id"] for x in ALG["skills"]], 15)
    answers = {s: rng.random() < 0.6 for s in skills}
    py = normalize(interpret_static(ALG, answers))
    assert py == js({"scope": ALG, "static": answers})


@pytest.mark.parametrize("depth", [1, 2])
def test_ladder_parity(depth):
    from engine.graph import BAGRUT_FILE, load_json
    for sec in load_json(BAGRUT_FILE)["sections"]:
        py = guided_ladder(JRN, sec["skills"], depth)
        assert py == js({"scope": JRN, "ladder": {"targets": sec["skills"], "depth": depth}})
    # personal mode: after a journey run
    unknown = unknown_set(KM, ["ca4"])
    status = run(JRN, unknown, section_results(unknown))["status"]
    py = guided_ladder(JRN, ["ca6", "ca12"], depth, status)
    assert py == js({"scope": JRN, "ladder": {"targets": ["ca6", "ca12"], "depth": depth, "status": status}})
