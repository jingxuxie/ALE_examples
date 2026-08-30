"""Admit eight privately proposed cases using cold, sandboxed production baselines.

Run with --proposal PATH, optionally --root CONCEPT_ROOT. Nothing runs at import.
Reports and immutable stage checkpoints live alongside this script. Identical
failed or interrupted stage checkpoints are never automatically retried.
"""

import argparse
from collections import Counter
import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import uuid


ROOT = Path(__file__).resolve().parents[2]
WORK = Path("adversary/ratchet_2_admission")
INFRASTRUCTURE_REVISION = 5
TARGET = {"score_min": 80.0, "core_min": 0.8, "worst_family_min": 0.7,
          "each_long_quality_min": 0.55, "all_16_outputs_valid": True}
STAGES = {"short": {"cpu_seconds": 6.0, "wall_seconds": 30.0},
          "long": {"cpu_seconds": 40.0, "wall_seconds": 120.0}}
PRODUCTION = ("solve.py", "fast.py", "optimizer.py", "contractor.py")
RUNTIME_SOURCES = ("evaluator/evaluate.py", "evaluator/trusted_contractor.py",
                   "evaluator/sandbox_runner.py", "evaluator/worker.py",
                   "evaluator/hidden/suite.py", "adversary/validate_calibration.py",
                   "adversary/ratchet_2_admission/admit.py",
                   "adversary/ratchet_2_admission/prepare_public.py",
                   "adversary/ratchet_2_admission/public_preparation.json",
                   "adversary/wall_guard_repair/freeze_manifest_v5.json")
BOUNDS = {"omega": (0.55, 1.85), "mass2": (-0.20, 0.03),
          "lambda4": (0.05, 0.30), "coupling": (0.05, 1.50),
          "field": (0.0, 0.0)}
REQUEST_KEYS = {"version", "case_id", "seed", "n_sites", "local_dim", "bond_cap",
                "sector", *BOUNDS}
IGNORED_IDENTITY_KEYS = {"case_id", "seed", "budget_seconds", "wall_seconds"}
WALL_ACCOUNTING = "protected supervisor elapsed time on direct solver child"


class AdmissionError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AdmissionError(message)


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def fingerprint(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid_constant(value):
        raise AdmissionError("nonfinite JSON constant: " + value)

    path = Path(path)
    require(path.stat().st_size <= 4 * 1024 ** 2, "JSON exceeds 4 MiB: " + str(path))
    result = json.loads(path.read_text(), object_pairs_hook=unique,
                        parse_constant=invalid_constant)
    encoded(result)
    return result


def number(value, name, lower=-math.inf, upper=math.inf):
    require(type(value) in (int, float), name + " must be a non-boolean number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    require(finite and lower <= value <= upper, name + " is nonfinite or outside bounds")
    return value


def contained(root, relative, must_exist=True, regular=False):
    root = Path(root).resolve()
    relative = Path(relative)
    require(not relative.is_absolute() and ".." not in relative.parts,
            "path must be concept-relative without '..': " + str(relative))
    path = root
    for component in relative.parts:
        path = path / component
        require(not path.is_symlink(), "symlink forbidden: " + str(path))
    require(path.resolve().is_relative_to(root), "path escapes concept root")
    if must_exist:
        require(path.exists(), "missing path: " + str(path))
    if regular:
        require(stat.S_ISREG(path.stat().st_mode), "not a regular file: " + str(path))
    return path


def write_atomic(root, relative, value):
    path = contained(root, relative, must_exist=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value if isinstance(value, bytes) else encoded(value)
    descriptor, temporary = tempfile.mkstemp(prefix=".admission-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_request(request, allow_budgets=False):
    require(type(request) is dict, "request must be an object")
    optional = {"budget_seconds", "wall_seconds"} if allow_budgets else set()
    require(REQUEST_KEYS <= set(request) <= REQUEST_KEYS | optional,
            "request fields missing, unknown, or contain prohibited budgets")
    require(type(request["version"]) is int and request["version"] == 1, "request version must be 1")
    require(isinstance(request["case_id"], str) and bool(request["case_id"].strip()), "invalid case_id")
    require(type(request["seed"]) is int and request["seed"] >= 0, "seed must be a nonnegative integer")
    for key, lower, upper in (("n_sites", 32, 64), ("local_dim", 8, 14), ("bond_cap", 12, 24)):
        require(type(request[key]) is int and lower <= request[key] <= upper, "invalid " + key)
    require(request["sector"] in ("even", "odd"), "invalid sector")
    for key, (lower, upper) in BOUNDS.items():
        values = request[key]
        length = request["n_sites"] - (key == "coupling")
        require(type(values) is list and len(values) == length, "incorrect length for " + key)
        for value in values:
            number(value, key, lower, upper)
    require(request["sector"] == "any" or all(value == 0 for value in request["field"]),
            "non-any sector requires exactly zero fields")
    for key in optional & set(request):
        require(number(request[key], key) > 0, "nonpositive example budget")
    return copy.deepcopy(request)


def objective_identity(request):
    validated = validate_request(request, allow_budgets=True)
    objective = {key: value for key, value in validated.items() if key not in IGNORED_IDENTITY_KEYS}
    for key in BOUNDS:
        objective[key] = [float(value) if value != 0 else 0.0 for value in objective[key]]
    return fingerprint(objective)


def validate_proposal(proposal, public_examples, root):
    require(type(proposal) is dict and type(proposal.get("cases")) is list, "proposal needs cases")
    require(len(proposal["cases"]) == 8, "proposal must have exactly eight cases")
    public_identities = {objective_identity(request) for request in public_examples}
    identities = set()
    records = []
    for entry in proposal["cases"]:
        require(type(entry) is dict and {"family", "request", "reference_state", "reference_energy",
                                       "source_case_id"} <= set(entry), "incomplete proposal entry")
        for key in ("family", "source_case_id", "reference_state"):
            require(isinstance(entry[key], str) and bool(entry[key].strip()), "invalid " + key)
        request = validate_request(entry["request"])
        identity = objective_identity(request)
        require(identity not in identities, "duplicate optimization objective")
        require(identity not in public_identities, "optimization objective overlaps a public example")
        identities.add(identity)
        contained(root, entry["reference_state"], regular=True)
        number(entry["reference_energy"], "reference_energy")
        request["case_id"] = "g2_" + identity[:32]
        records.append({"family": entry["family"], "request": request, "objective_identity": identity,
                        "source_case_id": entry["source_case_id"], "reference_state": entry["reference_state"],
                        "reference_energy": entry["reference_energy"]})
    counts = Counter(record["family"] for record in records)
    require(len(counts) == 4 and set(counts.values()) == {2}, "need four families with two cases each")
    require(len({record["request"]["case_id"] for record in records}) == 8, "opaque ID collision")
    return sorted(records, key=lambda record: record["request"]["case_id"])


def immutable_inputs(root):
    preparation = read_json(contained(root, WORK / "public_preparation.json", regular=True))
    scoring = read_json(contained(root, "participant/input/scoring.json", regular=True))
    require(preparation.get("generation") == 2, "public preparation is not generation 2")
    require(preparation.get("private_development_artifacts_released") is False, "private public-surface artifacts")
    require(type(preparation.get("fresh_attempts_for_this_generation_launched")) is int
            and preparation["fresh_attempts_for_this_generation_launched"] == 0, "generation already launched")
    for value in (preparation.get("target_predeclared"), scoring.get("target")):
        require(value == TARGET and value.get("all_16_outputs_valid") is True, "predeclared target changed")
        for key in TARGET.keys() - {"all_16_outputs_valid"}:
            number(value[key], key)
    require(preparation.get("stages") == STAGES and scoring.get("stages") == STAGES, "fixed budgets changed")
    for budgets in (preparation["stages"], scoring["stages"]):
        for stage in budgets.values():
            for value in stage.values():
                number(value, "stage budget")
    require(scoring.get("version") == 2 and scoring.get("case_count") == 8
            and scoring.get("family_count") == 4, "scoring schema/count mismatch")
    require(scoring.get("frozen_before_generation_fresh_agent_launch") is True, "target is not predeclared")
    hashes = preparation.get("production_sha256")
    require(type(hashes) is dict and set(hashes) == set(PRODUCTION), "expected four production source hashes")
    source = preparation.get("production_source")
    require(isinstance(source, str), "missing production source")
    for name in PRODUCTION:
        expected = hashes[name]
        for relative in (Path(source) / name, Path("participant/baseline") / name,
                         Path("participant/workspace") / name):
            require(sha256(contained(root, relative, regular=True)) == expected,
                    "production/source hash mismatch: " + str(relative))
    certificate = read_json(contained(root, "adversary/wall_guard_repair/freeze_manifest_v5.json", regular=True))
    require(certificate.get("infrastructure_revision") == INFRASTRUCTURE_REVISION
            and certificate.get("checks_passed", 0) >= 14 and certificate.get("fresh_attempts_launched") == 0,
            "prelaunch infrastructure certificate must validate infra5")
    for relative in ("evaluator/sandbox_runner.py", "evaluator/worker.py"):
        require(certificate.get("source_sha256", {}).get(relative) == sha256(contained(root, relative, regular=True)),
                "infra5 runtime pin mismatch: " + relative)
    paths = set(RUNTIME_SOURCES)
    participant = contained(root, "participant")
    for path in participant.rglob("*"):
        require(not path.is_symlink(), "public symlink forbidden")
        if not path.is_dir():
            paths.add(str(path.relative_to(root)))
    return {relative: sha256(contained(root, relative, regular=True)) for relative in sorted(paths)}


def cache_key(request, production_hashes, runtime_hashes, environment=None):
    validate_request(request, allow_budgets=True)
    require({"budget_seconds", "wall_seconds"} <= set(request), "cache request needs both budgets")
    return fingerprint({"cache_version": 1, "request": request, "production": production_hashes,
                        "runtime_sources": runtime_hashes, "environment": environment or {}})


def validate_measurement(measured, request):
    require(type(measured) is dict, "measurement is not an object")
    number(measured.get("energy"), "measured energy")
    number(measured.get("parity"), "measured parity", -1.000001, 1.000001)
    require(type(measured.get("max_bond")) is int and 1 <= measured["max_bond"] <= request["bond_cap"],
            "measured bond exceeds cap")
    require(number(measured.get("norm_after_canonicalization"), "measured norm") > 0, "nonpositive norm")
    if request["sector"] != "any":
        expected = 1 if request["sector"] == "even" else -1
        require(abs(measured["parity"] - expected) <= 1e-6, "measured parity violated")
    encoded(measured)
    return measured


def validate_process(result, request):
    require(type(result) is dict, "runner report is not an object")
    encoded(result)
    require(result.get("process_valid") is True and result.get("cpu_accounted") is True,
            "cold baseline process invalid or unaccounted: " + str(result.get("error", "")))
    require(type(result.get("returncode")) is int and result["returncode"] == 0, "cold baseline exit failure")
    require(result.get("timed_out") is False and result.get("outer_timed_out") is False, "cold baseline timeout")
    require(result.get("wall_accounting") == WALL_ACCOUNTING, "untrusted baseline wall accounting")
    number(result.get("cpu_seconds"), "baseline CPU", 0, request["budget_seconds"])
    number(result.get("wall_seconds"), "baseline worker wall", 0, request["wall_seconds"])


def copy_state(root, source, relative, expected):
    destination = contained(root, relative, must_exist=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    require(sha256(source) == expected, "source state changed")
    if destination.exists():
        require(destination.is_file() and sha256(destination) == expected, "retained state collision")
    else:
        shutil.copyfile(source, destination)
    require(sha256(destination) == expected, "retained state hash mismatch")
    return destination


def measured_state(root, source, request, contractor):
    source = contained(root, Path(source).relative_to(root), regular=True)
    before = sha256(source)
    measured = validate_measurement(contractor.measure(contractor.load_mps(source, request), request), request)
    require(sha256(source) == before, "state mutated while measuring")
    return dict(measured, state=str(source.relative_to(root)), sha256=before)


def cold_stage(root, request, inputs, environment, runner, contractor):
    production = {name: inputs["participant/baseline/" + name] for name in PRODUCTION}
    identity = cache_key(request, production, inputs, environment)
    relative = WORK / "baseline_cache" / identity
    location = contained(root, relative, must_exist=False)
    checkpoint = location / "checkpoint.json"
    if location.exists():
        require(checkpoint.is_file() and not checkpoint.is_symlink(),
                "interrupted stage has no terminal checkpoint; refusing automatic retry: " + identity)
        saved = read_json(checkpoint)
        require(saved.get("fingerprint") == identity and saved.get("request") == request
                and saved.get("inputs") == inputs and saved.get("environment") == environment,
                "cached stage fingerprint/payload mismatch")
        require(saved.get("status") == "complete", "cached failed stage is preserved; no automatic retry: " + identity)
        result_path = contained(root, relative / "process.json", regular=True)
        require(sha256(result_path) == saved.get("process_sha256"), "cached full process report changed")
        result = read_json(result_path)
        validate_process(result, request)
        state = measured_state(root, location / "scratch/state.npz", request, contractor)
        require(state["sha256"] == saved["state"]["sha256"]
                and abs(state["energy"] - saved["state"]["energy"]) <= 1e-9, "cached baseline state changed")
        return dict(state, cpu_seconds=result["cpu_seconds"], wall_seconds=result["wall_seconds"],
                    process_report=str(result_path.relative_to(root)), cache_fingerprint=identity)
    location.mkdir(parents=True)
    saved = {"fingerprint": identity, "request": request, "inputs": inputs, "environment": environment,
             "status": "started", "automatic_retries": 0}
    write_atomic(root, relative / "started.json", saved)
    result = None
    try:
        result = runner.run_submission(root / "participant/baseline", root / "participant",
                                       location / "scratch", request)
        write_atomic(root, relative / "process.json", result)
        validate_process(result, request)
        require(Path(result.get("state_path", "")).absolute() == (location / "scratch/state.npz").absolute(),
                "runner returned an unexpected state path")
        state = measured_state(root, location / "scratch/state.npz", request, contractor)
        saved.update(status="complete", state=state, process_sha256=sha256(location / "process.json"))
        write_atomic(root, relative / "checkpoint.json", saved)
        return dict(state, cpu_seconds=result["cpu_seconds"], wall_seconds=result["wall_seconds"],
                    process_report=str((location / "process.json").relative_to(root)), cache_fingerprint=identity)
    except Exception as error:
        saved.update(status="failed", error_type=type(error).__name__, error=str(error), hardness_evidence=False)
        if result is not None and not (location / "process.json").exists():
            saved["invalid_process_report_repr"] = repr(result)
        write_atomic(root, relative / "checkpoint.json", saved)
        raise AdmissionError("cold baseline failed; retained " + str(checkpoint) + ": " + str(error)) from error


def improvement_gaps(baselines, reference, length):
    require(set(baselines) == set(STAGES), "both baseline stages are required")
    reference_energy = number(reference["energy"], "reference energy")
    gaps = {stage: number(record["energy"], "baseline energy") - reference_energy
            for stage, record in baselines.items()}
    require(all(gap > 1e-7 * length for gap in gaps.values()),
            "insufficient baseline-reference gap: " + json.dumps(gaps, sort_keys=True))
    return gaps


def load_trusted(root):
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS",
                 "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        os.environ[name] = "1"
    modules = []
    for name in ("sandbox_runner", "trusted_contractor"):
        path = contained(root, "evaluator/" + name + ".py", regular=True)
        spec = importlib.util.spec_from_file_location("_admission_" + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules.append(module)
    return modules


def admit(root, proposal_path, report):
    root = Path(root).resolve()
    proposal_path = contained(root, Path(proposal_path).absolute().relative_to(root), regular=True)
    proposal_hash = sha256(proposal_path)
    proposal = read_json(proposal_path)
    inputs = immutable_inputs(root)
    examples = [read_json(path) for path in sorted((root / "participant/input").glob("example_*.json"))]
    require(len(examples) == 3, "expected three prepared public examples")
    records = validate_proposal(proposal, examples, root)
    environment = {"python": sys.version, "executable": sys.executable,
                   "infrastructure_revision": INFRASTRUCTURE_REVISION,
                   "numpy": importlib.metadata.version("numpy"), "scipy": importlib.metadata.version("scipy")}
    identity = fingerprint({"proposal_sha256": proposal_hash, "immutable_inputs": inputs, "environment": environment})
    report.update(proposal=str(proposal_path.relative_to(root)), proposal_sha256=proposal_hash,
                  admission_fingerprint=identity, immutable_inputs=inputs, environment=environment,
                  target=copy.deepcopy(TARGET), stages=copy.deepcopy(STAGES), cases={})
    previous = read_json(root / "evaluator/hidden/calibration.json")
    if previous.get("generation") == 2:
        require(previous.get("admission_fingerprint") == identity,
                "generation 2 is already frozen with a different admission fingerprint")
    runner, contractor = load_trusted(root)
    for record in records:
        request = record["request"]
        case_id = request["case_id"]
        source = contained(root, record["reference_state"], regular=True)
        state = measured_state(root, source, request, contractor)
        require(abs(state["energy"] - record["reference_energy"]) <= 1e-9,
                "reference energy disagrees by more than 1e-9: " + case_id)
        retained = WORK / "reference_cache" / state["sha256"] / "state.npz"
        copy_state(root, source, retained, state["sha256"])
        state["state"] = str(retained)
        report["cases"][case_id] = {"family": record["family"], "request": request,
                                    "source_case_id": record["source_case_id"],
                                    "source_reference": record["reference_state"],
                                    "reference": state, "baseline": {}}
    for record in records:
        case_id = record["request"]["case_id"]
        outcome = report["cases"][case_id]
        for stage, budget in STAGES.items():
            require(immutable_inputs(root) == inputs, "immutable inputs changed before baseline execution")
            request = dict(record["request"], budget_seconds=budget["cpu_seconds"], wall_seconds=budget["wall_seconds"])
            outcome["baseline"][stage] = cold_stage(root, request, inputs, environment, runner, contractor)
            write_atomic(root, WORK / "case_checkpoints" / identity / (case_id + ".json"), outcome)
        outcome["gaps"] = improvement_gaps(outcome["baseline"], outcome["reference"], record["request"]["n_sites"])
        write_atomic(root, WORK / "case_checkpoints" / identity / (case_id + ".json"), outcome)
    require(immutable_inputs(root) == inputs and sha256(proposal_path) == proposal_hash,
            "immutable inputs or proposal changed during admission")
    for outcome in report["cases"].values():
        require(sha256(contained(root, outcome["source_reference"], regular=True)) == outcome["reference"]["sha256"],
                "proposal reference changed during admission")
    destination = Path("evaluator/hidden/states/generation_2") / identity
    frozen_hashes = dict(inputs)
    calibration_cases = copy.deepcopy(report["cases"])
    for case_id, outcome in calibration_cases.items():
        for label, state in [("reference", outcome["reference"]), *outcome["baseline"].items()]:
            relative = destination / (case_id + "_" + label + ".npz")
            copy_state(root, contained(root, state["state"], regular=True), relative, state["sha256"])
            state["state"] = str(relative)
            frozen_hashes[str(relative)] = state["sha256"]
    cases = {"version": 2, "cases": [{"id": record["request"]["case_id"], "family": record["family"],
                                      "request": record["request"]} for record in records]}
    cases_payload = encoded(cases)
    frozen_hashes["evaluator/hidden/cases.json"] = hashlib.sha256(cases_payload).hexdigest()
    calibration = {"version": 2, "generation": 2, "infrastructure_revision": INFRASTRUCTURE_REVISION,
                   "kind": "attainable variational references; not exact ground energies or a resource-feasible solver",
                   "full_passing_algorithm_known_at_admission": False,
                   "target_frozen_before_launch": copy.deepcopy(TARGET),
                   "frozen_hashes": frozen_hashes, "cases": calibration_cases,
                   "admission_fingerprint": identity, "proposal_sha256": proposal_hash}
    calibration_payload = encoded(calibration)
    publication = {"evaluator/hidden/cases.json": cases_payload,
                   "evaluator/hidden/calibration.json": calibration_payload}
    old = {relative: contained(root, relative, regular=True).read_bytes() for relative in publication}
    for relative, content in old.items():
        saved = WORK / "publication_backup" / identity / Path(relative).name
        backup = contained(root, saved, must_exist=False)
        if not backup.exists():
            write_atomic(root, saved, content)
    require(immutable_inputs(root) == inputs, "immutable inputs changed before publication")
    try:
        for relative, content in publication.items():
            write_atomic(root, relative, content)
        for relative, expected in frozen_hashes.items():
            require(sha256(contained(root, relative, regular=True)) == expected, "published frozen hash mismatch: " + relative)
    except Exception:
        for relative, content in old.items():
            write_atomic(root, relative, content)
        raise
    report.update(status="admitted", retained_states=24, baseline_stages=16,
                  calibration_sha256=hashlib.sha256(calibration_payload).hexdigest(),
                  cases_sha256=hashlib.sha256(cases_payload).hexdigest(),
                  full_passing_algorithm_known=False, hardness_evidence=False)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report = {"status": "rejected", "created_utc": datetime.now(timezone.utc).isoformat(),
              "automatic_retries": 0, "hardness_evidence": False}
    code = 0
    try:
        admit(root, args.proposal, report)
    except Exception as error:
        report.update(status="rejected", error_type=type(error).__name__, error=str(error),
                      passing_or_frozen_calibration_written=False)
        code = 1
    historical = WORK / "reports" / (uuid.uuid4().hex + ".json")
    write_atomic(root, historical, report)
    write_atomic(root, WORK / "admission_report.json", report)
    print(json.dumps({"status": report["status"], "report": str(root / historical),
                      "error": report.get("error"), "retained_states": report.get("retained_states", 0)},
                     allow_nan=False, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
