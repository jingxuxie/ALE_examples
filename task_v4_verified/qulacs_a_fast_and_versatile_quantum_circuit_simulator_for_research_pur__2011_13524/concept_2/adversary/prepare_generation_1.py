import os
import sys


sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "adversary/pool_generation_1"
sys.path.insert(0, str(ROOT / "evaluator"))
sys.path.insert(0, str(ROOT / "authoring"))
from dense_reference import dense_unitary
from kernel import MAX_JSON_BYTES, circuit_unitary, score_payload, target_matrix, unitary_metrics
from ratchet_pool import qualifies, spectral_statistics


def encode(value):
    return (json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(contents):
    return hashlib.sha256(contents).hexdigest()


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError("expected exactly one migration anchor: " + old[:100])
    return source.replace(old, new, 1)


def parameterized_tests(source):
    declaration = '        cls.witness = read_json(ROOT / "evaluator/hidden/witness.json")'
    revised = replace_once(
        source, declaration,
        declaration + '\n        cls.primary_target = cls.specification["targets"][0]'
        + '\n        cls.primary_id = cls.primary_target["id"]',
    )
    if revised.count('"unitary_4q"') != 3:
        raise RuntimeError("unexpected target-specific test layout; review before migration")
    revised = revised.replace('"unitary_4q"', 'self.primary_id')
    revised = revised.replace('seconds=20)', 'seconds=60)')
    revised = replace_once(revised, '{**rotation, "qubit": 4}',
                           '{**rotation, "qubit": self.primary_target["n_qubits"]}')
    revised = replace_once(
        revised, 'for kind, count in (("CNOT", 13), ("U3", 81)):',
        'for kind, count in (("CNOT", self.primary_target["max_cnot"] + 1), '
        '("U3", self.primary_target["max_u3"] + 1)):',
    )
    ast.parse(revised)
    return revised


def test_patch(before, after):
    removed = "".join("-" + line + "\n" for line in before.splitlines())
    added = "".join("+" + line + "\n" for line in after.splitlines())
    return "*** Begin Patch\n*** Update File: evaluator/test_evaluator.py\n@@\n" + removed + added + "*** End Patch\n"


def task_text(targets):
    budgets = "\n".join(
        f'- `{target["id"]}`: {target["n_qubits"]} qubits, at most '
        f'**{target["max_cnot"]} CNOTs** and **{target["max_u3"]} U3 gates**.'
        for target in targets
    )
    return f"""# Compact circuits for public unitary operators

## Mission

Recover a compact circuit for each complete operator in `input/targets.json`.
Use arbitrary one-qubit U3 rotations and nearest-neighbor CNOTs on the supplied
line connectivity, in either CNOT direction. No ancillas, measurements, other
gates, or qubit relabeling are allowed.

{budgets}

Match the **entire unitary**, not its action on one initial state. Global phase
is irrelevant. Every target requires operator infidelity at most `1e-8` and
phase-aligned normalized Frobenius discrepancy at most `2e-4`. All operator
entries, connectivity, gate budgets, and numerical conditions are public.
Any legal equivalent circuit is accepted.

## Assets and interface

- `input/targets.json`: scored operators and exact constraints.
- `input/demo.json` and `input/demo_witness.json`: unscored two-qubit example.
- `workspace/PROTOCOL.md`: complete gate, matrix, JSON, and scoring conventions.
- `workspace/check.py`: public full-operator checker, taking input and witness paths.
- `baseline/solution.py`: runnable identity baseline.

Submit a directory containing `solution.py` and any supporting files. It runs
as `python solution.py INPUT_JSON OUTPUT_JSON`. Write a JSON object mapping
every input target ID to its ordered gate list at `OUTPUT_JSON`; stdout is not
the answer. The baseline uses the same interface:
`python baseline/solution.py input/targets.json answer.json`.

## Objective and resources

The score is the fraction of targets whose circuits are legal and meet both
error thresholds. The objective is **1.0, passing both targets**; approximation
errors are diagnostic only. Use any construction strategy.

Development time is one hour. Evaluation has a 300-second wall limit and 4-GiB
memory limit, on one CPU thread with Python, NumPy, and SciPy available, without
network or accelerator access. Supporting precomputed artifacts are permitted.
"""


def protocol_text(source, targets):
    identifiers = " and ".join('`' + target["id"] + '`' for target in targets)
    budgets = "\n".join(
        f'- `{target["id"]}`: `n_qubits={target["n_qubits"]}`, '
        f'`max_cnot={target["max_cnot"]}`, `max_u3={target["max_u3"]}`.'
        for target in targets
    )
    replacement = f"The scored IDs are {identifiers}.\n\nExact gate budgets:\n{budgets}\n\nThe separate demo uses"
    revised, count = re.subn(r"The scored IDs are .*?The separate demo uses", replacement, source, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError("cannot find protocol target-ID paragraph")
    return revised


def validate_selection(case_ids):
    audit = load(POOL / "audit.json")
    pool_bytes = (POOL / "pool.json").read_bytes()
    if digest(pool_bytes) != audit["pool_sha256"]:
        raise RuntimeError("pool no longer matches its independent audit")
    cases = {entry["id"]: entry for entry in json.loads(pool_bytes)["cases"]}
    certificates = {entry["id"]: entry for entry in load(POOL / "metadata.json")["certificates"]}
    if len(set(case_ids)) != 2 or any(identifier not in cases for identifier in case_ids):
        raise ValueError("select two distinct IDs present in the audited pool")
    selected = sorted((cases[identifier] for identifier in case_ids), key=lambda entry: entry["suite"]["targets"][0]["n_qubits"])
    families = [(entry["suite"]["targets"][0]["n_qubits"], entry["suite"]["targets"][0]["max_cnot"]) for entry in selected]
    if families != [(6, 36), (7, 42)]:
        raise ValueError("select exactly one n6_m36 case and one n7_m42 case")
    verifications = []
    for entry in selected:
        certificate = certificates[entry["id"]]
        input_path = POOL / certificate["input"]
        witness_path = POOL / certificate["witness"]
        if digest(input_path.read_bytes()) != certificate["input_sha256"] or digest(witness_path.read_bytes()) != certificate["witness_sha256"]:
            raise RuntimeError("selected case does not match its private certificate")
        if load(input_path) != entry["suite"] or load(witness_path) != entry["witness"]:
            raise RuntimeError("pool entry disagrees with individual case files")
        if not certificate["target_met"] or certificate["core_score"] != 1.0:
            raise RuntimeError("selected case lacks a passing private certificate")
        target = entry["suite"]["targets"][0]
        if target["id"] != "unitary_" + str(target["n_qubits"]) + "q":
            raise RuntimeError("unexpected target ID")
        if entry["suite"]["tolerances"] != {"infidelity": 1e-8, "normalized_frobenius": 2e-4}:
            raise RuntimeError("selection would change numerical acceptance semantics")
        report = score_payload(entry["suite"], entry["witness"])
        gates = entry["witness"][target["id"]]
        dense = dense_unitary(target["n_qubits"], gates)
        efficient = circuit_unitary(target["n_qubits"], gates)
        maximum_error = float(np.max(np.abs(dense - efficient)))
        metrics = unitary_metrics(target_matrix(target), dense)
        statistics = spectral_statistics(target_matrix(target), target["n_qubits"])
        if not report["target_met"] or maximum_error > 1e-12 or not qualifies(statistics):
            raise RuntimeError("selected target failed independent feasibility or spectral validation")
        if any(metrics[name] > entry["suite"]["tolerances"][name] for name in metrics):
            raise RuntimeError("independent dense witness failed full-unitary acceptance")
        verifications.append({"id": entry["id"], "input_sha256": certificate["input_sha256"],
                              "report": report, "dense_metrics": metrics,
                              "independent_kernel_max_error": maximum_error,
                              "statistics": statistics})
    specification = copy.deepcopy(selected[0]["suite"])
    specification["targets"] = [copy.deepcopy(entry["suite"]["targets"][0]) for entry in selected]
    witness = {identifier: gates for entry in selected for identifier, gates in entry["witness"].items()}
    if len(encode(specification)) > MAX_JSON_BYTES or len(encode(witness)) > MAX_JSON_BYTES:
        raise RuntimeError("combined generation exceeds the unchanged evaluator JSON limit")
    if not score_payload(specification, witness)["target_met"]:
        raise RuntimeError("combined generation failed achievability")
    return selected, specification, witness, verifications


def main():
    parser = argparse.ArgumentParser(description="Prepare generation 1 from two privately screened pool cases; does not freeze, test, or launch an agent")
    parser.add_argument("case_ids", nargs=2, metavar="CASE_ID")
    parser.add_argument("--apply-patch", default=shutil.which("apply_patch"), help="path to the required apply_patch executable")
    arguments = parser.parse_args()
    if not arguments.apply_patch or not os.access(arguments.apply_patch, os.X_OK):
        raise RuntimeError("apply_patch must be available before preparation")
    archive = ROOT / "generations/generation_0"
    freeze = ROOT / "adversary/target_freeze.json"
    old_status = load(ROOT / "status.json")
    if old_status.get("generation") != 0 or archive.exists():
        raise RuntimeError("generation 0 is not active or is already archived; refusing overwrite")
    if not freeze.is_file() or not (ROOT / "champions/generation_0").is_dir():
        raise RuntimeError("generation-0 freeze and champion must exist before ratcheting")
    prior_evaluation_path = ROOT / "attempts/v1_evaluation.json"
    if not prior_evaluation_path.exists():
        prior_evaluation_path = ROOT / "attempts/v_1_evaluation.json"
    prior_evaluation = load(prior_evaluation_path)
    prior_passed = prior_evaluation.get("passed", prior_evaluation.get("target_met", prior_evaluation.get("success", False)))
    if prior_evaluation.get("core_score") != 1.0 or not prior_evaluation.get("valid") or not prior_passed:
        raise RuntimeError("generation-0 evaluation does not certify a solved first attempt")
    selected, specification, witness, verifications = validate_selection(arguments.case_ids)
    targets = specification["targets"]
    tests_path = ROOT / "evaluator/test_evaluator.py"
    original_tests = tests_path.read_text(encoding="utf-8")
    revised_tests = parameterized_tests(original_tests)
    revised_protocol = protocol_text((ROOT / "participant/workspace/PROTOCOL.md").read_text(encoding="utf-8"), targets)
    manifest = load(ROOT / "evaluator/hidden/manifest.json")
    if digest((ROOT / "participant/input/targets.json").read_bytes()) != manifest["targets_sha256"]:
        raise RuntimeError("active generation-0 targets disagree with the manifest")
    if digest((ROOT / "participant/input/demo.json").read_bytes()) != manifest["demo_sha256"]:
        raise RuntimeError("demo input disagrees with the manifest")
    timestamp = datetime.now(timezone.utc).isoformat()
    target_bytes = encode(specification)
    manifest.update(generation=1, targets_sha256=digest(target_bytes), frozen_utc=timestamp, fresh_agent_started=False)
    report_path = "evaluator/hidden/achievability_generation_1.json"
    report = score_payload(specification, witness)
    report.update(generation=1, independent_reconstruction=True, verification=verifications)
    status = copy.deepcopy(old_status)
    status.update(
        generation=1, ratchet_generations=1, state="prepared_pending_tests_and_freeze",
        selected_pool_cases=[entry["id"] for entry in selected],
        target_sha256=manifest["targets_sha256"],
        baseline={"state": "isolated rerun pending"},
        privileged_witness={"core_score": 1.0, "report": report_path, "independent_reconstruction": True},
        evaluator_validation={"state": "pending after target-dependent test parameterization"},
        previous_generation_archive="generations/generation_0", previous_champion="champions/generation_0",
        fresh_attempts=[], target_frozen=False, requires_target_freeze=True,
        ratchet_reason="Same mode-C concept: prior generation solved; increase interior-cut coupling and robust operator-Schmidt content under compact gate budgets.",
        solvability="selected private witnesses independently verified against both full public operators",
    )
    status["fixed_target"] = {"core_score": 1.0, "every_target_infidelity_max": 1e-8, "normalized_frobenius_max": 2e-4}
    status["selection_evidence"] = {
        "report": "adversary/ratchet_search_generation_1.json",
        "kind": "bounded recovered-champion method probe, not a full one-hour generation attempt",
    }
    updates = {
        "participant/input/targets.json": target_bytes,
        "participant/TASK.md": task_text(targets).encode("utf-8"),
        "participant/workspace/PROTOCOL.md": revised_protocol.encode("utf-8"),
        "evaluator/hidden/witness.json": encode(witness),
        "evaluator/hidden/manifest.json": encode(manifest),
        "evaluator/hidden/generation_metadata.json": encode({"generation": 1, "private": True, "prepared_utc": timestamp,
                                                            "selected_pool_cases": [entry["id"] for entry in selected],
                                                            "verification": verifications}),
        report_path: encode(report),
    }
    unchanged = {name: digest((ROOT / name).read_bytes()) for name in
                 ("evaluator/evaluate.py", "evaluator/kernel.py", "participant/baseline/solution.py")}
    archive.mkdir(parents=True)
    for directory in ("participant", "evaluator"):
        shutil.copytree(ROOT / directory, archive / directory,
                        ignore=shutil.ignore_patterns(".git", ".agents", ".codex", "__pycache__"))
    shutil.copy2(ROOT / "status.json", archive / "status_before_reclassification.json")
    shutil.copy2(prior_evaluation_path, archive / "v1_evaluation.json")
    archived_status = copy.deepcopy(old_status)
    archived_status.update(
        state="solved", status="solved", generation=0,
        solved_evaluation="v1_evaluation.json", champion="../../champions/generation_0",
        fresh_attempts=[{"attempt": "v1", "core_score": 1.0, "valid": True, "passed": True,
                         "evaluation": "v1_evaluation.json"}],
        evaluation_sha256=digest(prior_evaluation_path.read_bytes()),
        evaluation_original_path=str(prior_evaluation_path.relative_to(ROOT)),
    )
    (archive / "status.json").write_bytes(encode(archived_status))
    (archive / "target_freeze.json").write_bytes(freeze.read_bytes())
    subprocess.run([arguments.apply_patch], input=test_patch(original_tests, revised_tests),
                   text=True, cwd=ROOT, check=True)
    for name, contents in updates.items():
        (ROOT / name).write_bytes(contents)
    if any(digest((ROOT / name).read_bytes()) != previous for name, previous in unchanged.items()):
        raise RuntimeError("evaluator semantics or identity baseline changed concurrently; do not launch")
    shutil.move(str(freeze), str(archive / "target_freeze.json"))
    (ROOT / "status.json").write_bytes(encode(status))
    print(json.dumps({"prepared": True, "generation": 1, "selected_cases": status["selected_pool_cases"],
                      "targets_sha256": manifest["targets_sha256"], "private_score": 1.0,
                      "old_freeze_archived": True, "tests_run": False, "fresh_agent_launched": False,
                      "next": "Run baseline and evaluator tests, then rerun the common freeze tool before the next fresh attempt."}, indent=2))


if __name__ == "__main__":
    main()
