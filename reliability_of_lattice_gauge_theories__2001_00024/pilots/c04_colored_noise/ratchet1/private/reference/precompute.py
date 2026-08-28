import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

RATCHET = Path(__file__).resolve().parents[2]
PILOT = RATCHET.parent
TASK_ROOT = RATCHET.parents[2]
sys.path.insert(0, str(RATCHET / "private/reference"))
sys.path.insert(1, str(RATCHET / "private"))

import numpy as np

import engine
from accelerated import solve_detailed
from cases import all_cases, make_case
from scoring import FLOORS, raw_errors, score_result, prediction_array
from weak_baseline.solver import solve as weak_solve


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def original_hashes():
    manifest = json.loads((PILOT / "private/freeze.json").read_text())
    paths = [PILOT / name for name in manifest["hashes"]]
    paths += list((PILOT / "attempt").glob("*.py"))
    paths += list((PILOT / "private/reference/longtime").rglob("*"))
    paths += list((TASK_ROOT / "authoring/c04_longtime_probe").rglob("*"))
    return {str(path.relative_to(TASK_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file() and "__pycache__" not in path.parts}


def max_prediction_error(case, actual, expected):
    return float(max(np.max(np.abs(prediction_array(actual["predictions"][identifier], len(case["times"]))
                                   - prediction_array(expected["predictions"][identifier], len(case["times"]))))
                     for identifier in expected["predictions"]))


def closed_drift(case):
    operators = engine.build_model(case)
    action = max(engine.feasible_actions(case), key=engine.action_cost)
    energies, basis = np.linalg.eigh(engine.hamiltonian(case, operators, action))
    initial = operators["initial"]
    states = basis @ (np.exp(-1j * np.outer(energies, case["times"])) * (basis.conj().T @ initial)[:, None])
    ideal_energies, ideal_basis = np.linalg.eigh(operators["hzero"])
    ideal = ideal_basis @ (np.exp(-1j * np.outer(ideal_energies, case["times"])) * (ideal_basis.conj().T @ initial)[:, None])
    return dict(action=action["id"], gauge=np.einsum("it,ij,jt->t", states.conj(), operators["gauge"], states).real.tolist(),
                fidelity=(np.abs(np.sum(ideal.conj() * states, axis=0))**2).tolist())


def validate_audit(case, seed):
    operators = engine.build_model(case)
    audit = case["audit"]
    hsystem = engine.hamiltonian(case, operators, audit["action"])
    bath_channels = engine.channels(case, operators, audit["bath"]["eta"])
    compiled = engine.secular_generator(hsystem, bath_channels, audit["bath"])
    random = np.random.default_rng(seed + 701)
    rotated = compiled["vectors"].astype(complex).copy()
    for group in compiled["energy_groups"]:
        unitary, _ = np.linalg.qr(random.normal(size=(len(group), len(group)))
                                  + 1j * random.normal(size=(len(group), len(group))))
        rotated[:, group] = rotated[:, group] @ unitary
    changed = engine.secular_generator(hsystem, bath_channels, audit["bath"],
                                      eigensystem=(compiled["energies"], rotated))
    first = engine.audit_response(compiled, audit["states"])
    second = engine.audit_response(changed, audit["states"])
    error = float(max(np.linalg.norm(np.asarray(actual[part]) - np.asarray(expected[part]))
                      for actual, expected in zip(first, second) for part in ("real", "imag", "activity")))
    identity = np.eye(64).ravel(order="F")
    trace_error = float(np.linalg.norm(identity @ compiled["generator"]))
    unital_error = float(np.linalg.norm(compiled["dissipator"] @ identity))
    gauss_error = float(max(np.linalg.norm(operators["hzero"] @ charge - charge @ operators["hzero"])
                           for charge in operators["charges"]))
    initial_error = float(np.linalg.norm(operators["gauge"] @ operators["initial"]))
    if max(error, trace_error, unital_error, gauss_error, initial_error) > 1e-9:
        raise ArithmeticError("independent invariant or degenerate-rotation check failed")
    return dict(rotation_error=error, trace_generator_error=trace_error, unital_error=unital_error,
                gauss_commutator_error=gauss_error, initial_sector_error=initial_error,
                largest_energy_degeneracy=max(map(len, compiled["energy_groups"])),
                multiple_transition_frequency_groups=compiled["degeneracy_count"])


def build():
    before = original_hashes()
    write_json(RATCHET / "private/original_hashes_before.json", before)
    records = all_cases()
    all_checks, short_checks = {}, []
    for split, cases in records.items():
        for reserved in cases:
            case = reserved["case"]
            name = case["case_id"] + ".json"
            assert 8000 <= case["times"][-1] <= 20000
            assert len(case["times"]) == 7 and np.allclose(np.diff(case["times"]), case["times"][-1] / 6)
            write_json(RATCHET / "private/challenge_pool" / split / name, reserved)
            timer = time.perf_counter()
            reference, exact_diagnostics, exact_states = solve_detailed(case, method="centered_expm")
            exact_seconds = time.perf_counter() - timer
            timer = time.perf_counter()
            commuting, commuting_diagnostics, commuting_states = solve_detailed(case, method="commuting_eigh")
            commuting_seconds = time.perf_counter() - timer
            maximum_error = max_prediction_error(case, commuting, reference)
            density_error = float(max(np.max(np.abs(commuting_states[identifier] - exact_states[identifier]))
                                      for identifier in exact_states))
            if max(maximum_error, density_error) > 2e-8:
                raise ArithmeticError("independent late-time methods disagree")
            timer = time.perf_counter()
            weak = weak_solve(case)
            weak_seconds = time.perf_counter() - timer
            errors, messages = raw_errors(case, weak, reference)
            if messages:
                raise ArithmeticError(messages)
            label = dict(case_sha256=checksum(case), reference=reference, weak=weak,
                         anchors={component: max(FLOORS[component], error) for component, error in errors.items()},
                         weak_errors=errors, reference_seconds=exact_seconds, weak_seconds=weak_seconds,
                         risks={identifier: engine.risk(case, prediction) for identifier, prediction in reference["predictions"].items()},
                         provenance="Ratchet author secular reimplementation; not official code; measured weak anchors")
            write_json(RATCHET / "private/reference/outputs" / split / name, label)
            audit_check = validate_audit(case, reserved["seed"])
            if reserved["family"] == "brown_degenerate" and audit_check["largest_energy_degeneracy"] < 2:
                raise ArithmeticError("brown audit did not retain genuine energy degeneracy")
            if split == "screening":
                short = json.loads(json.dumps(case))
                short["times"] = np.linspace(0, 4.0, 7).tolist()
                original_short = engine.solve(short)
                short_result = solve_detailed(short, method="centered_expm")[0]
                short_error = max_prediction_error(short, short_result, original_short)
                if short_error > 2e-8:
                    raise ArithmeticError("original short-time reference mismatch")
                short_checks.append(dict(case_id=case["case_id"], maximum_scored_observable_error=short_error))
            all_checks[case["case_id"]] = dict(split=split, family=reserved["family"],
                reference_seconds=exact_seconds, commuting_seconds=commuting_seconds, weak_seconds=weak_seconds,
                maximum_scored_observable_error=maximum_error, maximum_density_entry_error=density_error,
                centered_diagnostics=exact_diagnostics, commuting_diagnostics=commuting_diagnostics,
                audit=audit_check, closed_system=closed_drift(case),
                reference_consistency=score_result(case, commuting, label), weak_consistency=score_result(case, weak, label))
            print(split, reserved["family"], case["case_id"], "T", case["times"][-1],
                  "best", reference["selected_action"], "ref_s", round(exact_seconds, 3),
                  "weak", round(all_checks[case["case_id"]]["weak_consistency"]["core"], 6),
                  "deg", audit_check["largest_energy_degeneracy"], flush=True)
    example = make_case("pink_correlated", 0, 941001, 8500)["case"]
    write_json(RATCHET / "participant/input/example_case.json", example)
    write_json(RATCHET / "private/validation/scientific_checks.json", dict(
        passed=True, cases=all_checks, short_time_checks=short_checks,
        scope="Independent exponential algorithms, unchanged short-time engine, invariants and rotations; not empirical validation"))
    after = original_hashes()
    write_json(RATCHET / "private/original_integrity.json", dict(unchanged=before == after, checked_files=len(before), hashes=after))
    if before != after:
        raise RuntimeError("original artifacts changed")


def freeze():
    if any((RATCHET / "attempt").iterdir()):
        raise RuntimeError("attempt must remain strictly empty before launch")
    checks = json.loads((RATCHET / "private/validation/scientific_checks.json").read_text())
    if not checks["passed"] or len(checks["cases"]) != 9:
        raise RuntimeError("scientific checks incomplete")
    if json.loads((RATCHET / "private/original_hashes_before.json").read_text()) != original_hashes():
        raise RuntimeError("original artifacts changed before freeze")
    for split, count in (("screening", 6), ("confirmation", 3)):
        assert len(list((RATCHET / "private/challenge_pool" / split).glob("*.json"))) == count
        for role in ("reference", "weak"):
            report = json.loads((RATCHET / "private/validation" / f"{role}_{split}.json").read_text())
            if len(report["cases"]) != count or not all(case["ok"] for case in report["cases"]):
                raise RuntimeError("isolated validation incomplete")
            if role == "reference" and not all(case["core"] > 0.9 for case in report["cases"]):
                raise RuntimeError("reference below required score")
    files = [path for path in RATCHET.rglob("*") if path.is_file() and path.name != "freeze.json"
             and "__pycache__" not in path.parts and "attempt" not in path.parts
             and not any(part.startswith(".evaluation-") for part in path.parts)]
    hashes = {str(path.relative_to(RATCHET)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}
    write_json(RATCHET / "private/freeze.json", dict(
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), hashes=hashes,
        case_counts=dict(screening=6, confirmation=3), fresh_agent_runs=0,
        scoring_weights=dict(calibration=0.25, audit=0.30, dynamics=0.30, decision=0.15),
        source_snapshot_manifest="private/snapshot_manifest.json", weak_anchor_status="actually executed and fixed",
        author_audit_sha256=hashlib.sha256((TASK_ROOT / "authoring/c04_ratchet1_audit.md").read_bytes()).hexdigest(),
        confirmation_status="Reserved; author reference/weak checks only, never participant tuning",
        rejection_rule="If the second fresh agent solves screening and confirmation, reject rather than tighten again"))
    print("Frozen", len(hashes), "files", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-only", action="store_true")
    arguments = parser.parse_args()
    if arguments.freeze_only:
        freeze()
    else:
        build()
