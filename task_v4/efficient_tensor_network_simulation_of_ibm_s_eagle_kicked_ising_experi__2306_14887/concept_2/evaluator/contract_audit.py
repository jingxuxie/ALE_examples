"""Generation-one contract, archive, isolation, and reference-score audits."""

import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import ast
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "attempts" / "ratchet_generation_1"
ARCHIVE = ROOT / "generations" / "generation_0"


def load(name, path):
    specification = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def functions(path):
    return {node.name: ast.dump(node) for node in ast.parse(path.read_text()).body if isinstance(node, ast.FunctionDef)}


def main():
    checks = []
    def check(name, passed, detail=None):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    protocol = load("contract_public_protocol", ROOT / "participant" / "workspace" / "protocol.py")
    trusted = load("contract_trusted_protocol", ROOT / "evaluator" / "resources" / "protocol.py")
    checker = load("contract_checker", ROOT / "evaluator" / "evaluate.py")
    spec = json.loads((ROOT / "participant" / "input" / "target.json").read_text())
    old_spec = json.loads((ARCHIVE / "participant" / "input" / "target.json").read_text())
    unchanged = ("n_sites", "initial_state", "edges", "zz_angle", "chis", "observable", "depth_min", "depth_max", "knot_count", "knot_min", "knot_max", "max_slew", "perturbation", "error_min", "spread_max", "confidence_floor", "algorithm", "cutoff_relative", "degeneracy_relative", "pivot_tie_absolute")
    check("physical_and_score_constants_unchanged", all(spec[key] == old_spec[key] for key in unchanged))
    old_functions = functions(ARCHIVE / "evaluator" / "resources" / "simulator.py")
    new_functions = functions(ROOT / "evaluator" / "resources" / "simulator.py")
    check("every_original_simulator_function_AST_unchanged", all(new_functions.get(name) == value for name, value in old_functions.items()))
    check("exact_oracle_bytes_unchanged", (ROOT / "evaluator" / "resources" / "reference.py").read_bytes() == (ARCHIVE / "evaluator" / "resources" / "reference.py").read_bytes())
    check("scoring_function_AST_unchanged", functions(ROOT / "participant" / "workspace" / "protocol.py")["metrics"] == functions(ARCHIVE / "participant" / "workspace" / "protocol.py")["metrics"])
    witness = {"schema_version": 1, "depth": 24, "knots": [0.41,0.56,0.83,0.74,1.05,1.16], "observable": "zz1"}
    actual = protocol.waveforms(witness, spec)
    check("exactly_325_labels", len(actual) == 325)
    check("exactly_65_drifts", len(protocol.drift_vectors(spec)) == 65)
    grid = np.arange(witness["depth"]) / (witness["depth"] - 1)
    positions = grid * 5
    left = np.minimum(np.floor(positions).astype(int), 4)
    fraction = positions - left
    expected = {}
    directions = [None] + list(itertools.product((-1.0, 1.0), repeat=6))
    for index, direction in enumerate(directions):
        knots = np.array(witness["knots"]) + (0 if direction is None else 0.002 * np.array(direction))
        interpolated = (1 - fraction) * knots[left] + fraction * knots[left + 1]
        for family, perturbation in (("nominal", 0), ("offset_minus", -0.002), ("offset_plus", 0.002),
                                      ("tilt_minus", -0.002 * (2 * grid - 1)), ("tilt_plus", 0.002 * (2 * grid - 1))):
            label = family if index == 0 else f"corner_{index - 1:02d}/" + family
            expected[label] = interpolated + perturbation
    interpolation_error = max(float(np.max(np.abs(actual[label] - expected[label]))) for label in expected)
    check("independent_corner_cross_product_and_interpolation", actual.keys() == expected.keys() and interpolation_error < 2e-15, interpolation_error)
    check("public_trusted_waveforms_identical", all(np.array_equal(actual[label], value) for label, value in trusted.waveforms(witness, spec).items()))
    for boundary in (0.12, 1.45):
        check("nominal_knot_boundary_" + str(boundary), len(protocol.waveforms(dict(witness, knots=[boundary] * 6), spec)) == 325)
    unsafe = dict(witness, depth=12, knots=[0.12,0.38,0.38,0.38,0.38,0.38])
    check("corner_slew_fixture_passes_original_five", len(protocol.waveforms(unsafe, spec, include_corners=False)) == 5)
    try:
        protocol.waveforms(unsafe, spec)
        rejected = False
    except ValueError:
        rejected = True
    check("corner_slew_fixture_rejected_on_actual_pulses", rejected)
    artifact = OUTPUT / "budget_fixture"
    artifact.mkdir(exist_ok=True)
    (artifact / "witness.json").write_text(json.dumps(witness))
    original_clock = checker.time
    clock = iter((0.0, 601.0, 602.0))
    try:
        checker.time = SimpleNamespace(monotonic=lambda: next(clock))
        timed_out = checker.evaluate(artifact, workers=1)
    finally:
        checker.time = original_clock
    check("timeout_returns_bounded_failure_JSON", timed_out["valid"] and not timed_out["passed"] and not timed_out["evaluation_complete"] and timed_out["core_score"] == 0 and "time budget" in timed_out["reason"])
    check("worker_count_cannot_exceed_four", not checker.evaluate(artifact, workers=5)["valid"])
    archive_manifest = json.loads((ARCHIVE / "archive_manifest.json").read_text())
    check("generation_zero_archive_byte_hashes_preserved", all(hashlib.sha256((ARCHIVE / name).read_bytes()).hexdigest() == digest for name, digest in archive_manifest["files"].items()))
    for name in ("simulator.py", "protocol.py"):
        check("hidden_public_copy_" + name, (ROOT / "participant" / "workspace" / name).read_bytes() == (ROOT / "evaluator" / "resources" / name).read_bytes())
    check("hidden_public_target_identical", (ROOT / "participant" / "input" / "target.json").read_bytes() == (ROOT / "evaluator" / "resources" / "target.json").read_bytes())
    text = "\n".join(path.read_text() for path in (ROOT / "participant").rglob("*") if path.is_file() and path.suffix in (".py", ".json", ".md"))
    private_witnesses = list((ROOT / "champions").glob("*/witness.json"))
    check("no_private_witness_parameters_in_participant", all(str(value) not in text for path in private_witnesses for value in json.loads(path.read_text())["knots"]))
    private_hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in (ROOT / "champions" / "generation_1").rglob("*") if path.is_file()}
    check("no_fresh_submission_file_copied_to_participant", all(hashlib.sha256(path.read_bytes()).hexdigest() not in private_hashes for path in (ROOT / "participant").rglob("*") if path.is_file() and "__pycache__" not in path.parts))
    proposal_loop = lambda path: next(ast.dump(node) for node in ast.walk(ast.parse(path.read_text())) if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == "trial")
    check("original_weak_baseline_proposal_loop_unchanged", proposal_loop(ROOT / "participant" / "baseline" / "search.py") == proposal_loop(ARCHIVE / "participant" / "baseline" / "search.py"))
    subprocess.run([sys.executable, "-I", str(ARCHIVE / "evaluator" / "evaluate.py"), "--submission", str(ROOT / "champions" / "generation_1"), "--output", str(OUTPUT / "original_replay.json")], check=True)
    original = json.loads((OUTPUT / "original_replay.json").read_text())
    check("archived_original_still_scores_fresh_100", original["passed"] and original["core_score"] == 100 and original["worst_family_score"] == 100 and original["resource_score"] == 50)
    check("original_first_attempt_score_unchanged", (ROOT / "attempts" / "v_1_score.json").read_bytes() == (ARCHIVE / "attempts" / "v_1_score.json").read_bytes())
    report = {"passed": all(item["passed"] for item in checks), "checks": checks}
    (OUTPUT / "contract_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "checks": len(checks)}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
