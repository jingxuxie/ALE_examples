import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import secrets
import shutil
import tempfile
import time

from common import PARTICIPANT, ROOT, SIDE, digest_file, private_path, tree_inventory, write_json

import numpy as np
from scipy.sparse import csc_matrix
from baseline.decoder import Decoder
from evaluate import read_predictions, run_isolated, sandbox_command, snapshot_submission
from models import load_model, save_model
from diagnostics import extract_features, residual_report, summarize_pair
from regimes import catalog, make_stress_model


def checked_name(name):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ValueError("Names may contain only letters, digits, underscores, and hyphens")
    return name


def aggregate(case_records):
    baseline = np.concatenate([entry["baseline_wrong"] for entry in case_records])
    candidate = np.concatenate([entry["candidate_wrong"] for entry in case_records])
    groups = {}
    for group in sorted({entry["stress_group"] for entry in case_records}):
        selected = [entry for entry in case_records if entry["stress_group"] == group]
        groups[group] = summarize_pair(np.concatenate([entry["baseline_wrong"] for entry in selected]),
                                       np.concatenate([entry["candidate_wrong"] for entry in selected]))
    return dict(pooled=summarize_pair(baseline, candidate), stress_groups=groups)


def sample_sparse(model, shots, seed):
    generator = np.random.Generator(np.random.PCG64DXSM(seed))
    faults = (generator.random((shots, model["num_mechanisms"])) < model["probabilities"]).astype(np.uint8)
    syndromes = ((csc_matrix(model["detector_matrix"]) @ faults.T).T % 2).astype(np.uint8)
    labels = ((csc_matrix(model["observable_matrix"]) @ faults.T).T % 2).astype(np.uint8)
    return np.ascontiguousarray(syndromes), labels, faults


def build(args):
    suite = private_path(SIDE / "corpora" / checked_name(args.name))
    if suite.exists():
        raise ValueError("Corpus already exists; use a new independent discovery/confirmation name")
    suite.mkdir(parents=True)
    specs = json.loads(private_path(args.catalog_file).read_text())["specs"] if args.catalog_file else catalog()
    if args.cases:
        selected = set(args.cases.split(","))
        specs = [spec for spec in specs if spec["case_id"] in selected]
        if selected != {spec["case_id"] for spec in specs}:
            raise ValueError("Unknown case ID")
    if not specs or args.shots < 2:
        raise ValueError("Need cases and at least two shots")
    write_json(suite / "catalog_before_sampling.json", dict(exploratory=True, frozen=False, specs=specs))
    metadata = dict(name=args.name, role=args.role, exploratory=True, official_score=False, frozen=False,
                    created_utc=datetime.now(timezone.utc).isoformat(), shots_per_case=args.shots,
                    sampling="Unconditional independent Bernoulli mechanisms; sparse H/L parity; independent 128-bit streams", cases=[])
    baseline_cases = []
    records = []
    for spec in specs:
        case_id = spec["case_id"]
        model = make_stress_model(spec)
        save_model(model, suite / "models" / case_id)
        seed = secrets.randbits(128)
        syndromes, labels, faults = sample_sparse(model, args.shots, seed)
        started = time.process_time()
        decoder = Decoder(model)
        initialization = time.process_time() - started
        started = time.process_time()
        predictions = decoder.decode(syndromes)
        decoding = time.process_time() - started
        features = extract_features(model, syndromes, faults)
        destination = suite / "private" / (case_id + ".npz")
        destination.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(destination, syndromes=syndromes, labels=labels, faults=faults, baseline=predictions)
        np.savez_compressed(suite / "private" / (case_id + "_features.npz"), **features)
        diagnosis = residual_report(model, syndromes, labels, predictions, predictions, features)
        write_json(suite / "baseline_diagnostics" / (case_id + ".json"), diagnosis)
        wrong = np.any(predictions != labels, axis=1)
        record = dict(case_id=case_id, stress_group=spec["stress_group"], detectors=model["num_detectors"],
                      mechanisms=model["num_mechanisms"], shots=args.shots, failures=int(wrong.sum()),
                      init_cpu_seconds=initialization, decode_cpu_seconds=decoding,
                      diagnostics=str(suite / "baseline_diagnostics" / (case_id + ".json")))
        baseline_cases.append(record)
        records.append(dict(case_id=case_id, stress_group=spec["stress_group"], baseline_wrong=wrong, candidate_wrong=wrong))
        model_files = {name: digest_file(suite / "models" / case_id / name) for name in ["case.json", "model.npz", "model.dem"]}
        metadata["cases"].append(dict(spec=spec, seed=str(seed), data_sha256=digest_file(destination), model_sha256=model_files))
        write_json(suite / "progress.json", dict(complete=False, cases_done=len(records), cases_total=len(specs)))
        print(json.dumps(record), flush=True)
    write_json(suite / "manifest.json", metadata)
    report = dict(exploratory=True, official_score=False, source="trusted two-pass correlated PyMatching baseline",
                  cpu_measurement="time.process_time around trusted in-process construction/decode; imports excluded; not comparable to isolated total without an isolated reference",
                  manifest_sha256=digest_file(suite / "manifest.json"), cases=baseline_cases, **aggregate(records))
    write_json(suite / "baseline_report.json", report)
    write_json(suite / "progress.json", dict(complete=True, cases_done=len(records), cases_total=len(specs)))
    initial_report = ROOT / "attempts/baseline_isolated.json"
    original = json.loads(initial_report.read_text())
    write_json(SIDE / "reports/initial_baseline_reference.json", dict(source=str(initial_report), source_sha256=digest_file(initial_report),
               freeze_sha256=original["freeze_sha256"], pooled=original["pooled"], families=original["families"],
               execution=original["execution"], note="Known original baseline only; no claim about the active fresh attempt"))
    return report


def register_champion(args):
    if not args.confirm_promoted:
        raise ValueError("Main must explicitly confirm completed official evaluation and promotion")
    submission = args.submission.resolve()
    if not submission.is_relative_to(ROOT / "champions"):
        raise ValueError("Only promoted champions are accepted; active attempts/v_1 is never read or copied")
    official = json.loads(args.official_report.read_text())
    if not official.get("valid") or not official.get("passed"):
        raise ValueError("The independently scored original-task report must be valid and passed")
    destination = private_path(SIDE / "snapshots" / checked_name(args.name))
    if destination.exists():
        raise ValueError("Snapshot name already exists")
    before = tree_inventory(submission.parent)
    destination.mkdir(parents=True)
    snapshot_submission(submission, destination / "code")
    after = tree_inventory(submission.parent)
    copied = tree_inventory(destination / "code")
    if before["sha256"] != after["sha256"] or copied["sha256"] != before["sha256"]:
        raise RuntimeError("Source changed during snapshot; registration refused")
    manifest = dict(kind="main_confirmed_champion", main_confirmed=True, official_score=False,
                    source_submission=str(submission), entrypoint=submission.name, inventory=copied,
                    official_report=str(args.official_report.resolve()), official_report_sha256=digest_file(args.official_report),
                    note="Main's explicit promotion attests correspondence between source and official score; original evaluator report does not itself authenticate source hashes")
    write_json(destination / "manifest.json", manifest)
    print(str(destination / "manifest.json"), flush=True)
    return manifest


def load_suite(suite):
    suite = private_path(suite)
    manifest = json.loads((suite / "manifest.json").read_text())
    for case in manifest["cases"]:
        case_id = case["spec"]["case_id"]
        if digest_file(suite / "private" / (case_id + ".npz")) != case["data_sha256"]:
            raise ValueError("Private corpus changed")
        for filename, expected in case["model_sha256"].items():
            if digest_file(suite / "models" / case_id / filename) != expected:
                raise ValueError("Public stress model changed")
    return suite, manifest


def run(args):
    suite, manifest = load_suite(args.suite)
    if args.trusted_baseline:
        submission = PARTICIPANT / "baseline/decoder.py"
        identity = dict(kind="trusted_baseline_smoke", inventory=tree_inventory(submission.parent))
    elif args.isolation_probe:
        submission = SIDE / "probes/isolation/submission.py"
        identity = dict(kind="trusted_isolation_probe", inventory=tree_inventory(submission.parent))
    else:
        snapshot = private_path(args.champion_manifest)
        identity = json.loads(snapshot.read_text())
        confirmed = identity.get("kind") == "main_confirmed_champion" and identity.get("main_confirmed") is True
        portfolio = identity.get("kind") == "main_approved_portfolio_variant" and identity.get("main_approved_experiment") is True
        if not confirmed and not portfolio:
            raise ValueError("Confirmed champion manifest required")
        submission = snapshot.parent / "code" / identity["entrypoint"]
        if tree_inventory(submission.parent)["sha256"] != identity["inventory"]["sha256"]:
            raise ValueError("Champion snapshot changed")
    selected_cases = manifest["cases"]
    if args.cases:
        selected = set(args.cases.split(","))
        selected_cases = [case for case in selected_cases if case["spec"]["case_id"] in selected]
        if selected != {case["spec"]["case_id"] for case in selected_cases}:
            raise ValueError("Unknown selected case")
    output = private_path(SIDE / "runs" / checked_name(args.name))
    if output.exists():
        raise ValueError("Run already exists; use a new name for a repeat")
    output.mkdir(parents=True)
    scratch = SIDE / "scratch"
    scratch.mkdir(exist_ok=True)
    tempfile.tempdir = str(scratch)
    with tempfile.TemporaryDirectory(prefix="isolated-", dir=scratch) as temporary:
        temporary = Path(temporary)
        request_dir, response_dir = temporary / "request", temporary / "out"
        request_dir.mkdir()
        response_dir.mkdir()
        snapshot_submission(submission, temporary / "submission")
        limits = dict(cpu_seconds=args.cpu_budget, wall_watchdog_seconds=args.wall_watchdog,
                      address_bytes=6 * 1024 ** 3, cpu_cores=1)
        items = []
        for case in selected_cases:
            case_id = case["spec"]["case_id"]
            with np.load(suite / "private" / (case_id + ".npz"), allow_pickle=False) as data:
                np.savez_compressed(request_dir / (case_id + ".npz"), syndromes=data["syndromes"])
            items.append(dict(case_id=case_id, syndromes=f"/request/{case_id}.npz", predictions=f"/out/{case_id}.npz"))
        request = dict(submission="/submission/" + submission.name, participant_root="/participant", items=items, limits=limits)
        write_json(request_dir / "request.json", request)
        command = sandbox_command(PARTICIPANT, temporary / "submission", request_dir, response_dir)
        insertion = command.index("/usr/bin/python3")
        command[insertion:insertion] = ["--ro-bind", str(suite / "models"), "/participant/input/cases"]
        execution = run_isolated(command, output / "worker.log", args.wall_watchdog)
        report = dict(exploratory=True, official_score=False, new_generation_frozen=False, valid=False,
                      identity=identity, suite=str(suite), manifest_sha256=digest_file(suite / "manifest.json"),
                      case_ids=[case["spec"]["case_id"] for case in selected_cases], execution=execution,
                      exploratory_cpu_budget=args.cpu_budget, future_target=None)
        if execution["returncode"] or execution["watchdog_timeout"]:
            report["reason"] = "Isolated exploration interrupted/invalid; inspect worker.log. This is not a new-task failure verdict."
            write_json(output / "report.json", report)
            return report
        records, summaries = [], []
        for case in selected_cases:
            spec = case["spec"]
            case_id = spec["case_id"]
            model = load_model(suite / "models" / case_id)
            with np.load(suite / "private" / (case_id + ".npz"), allow_pickle=False) as data:
                syndromes, labels, baseline = data["syndromes"], data["labels"], data["baseline"]
            with np.load(suite / "private" / (case_id + "_features.npz"), allow_pickle=False) as data:
                features = {name: data[name] for name in data.files}
            predictions = read_predictions(response_dir / (case_id + ".npz"), len(labels))
            (output / "predictions").mkdir(exist_ok=True)
            np.savez_compressed(output / "predictions" / (case_id + ".npz"), predictions=predictions)
            diagnosis = residual_report(model, syndromes, labels, baseline, predictions, features)
            write_json(output / "diagnostics" / (case_id + ".json"), diagnosis)
            summaries.append(dict(case_id=case_id, stress_group=spec["stress_group"], **diagnosis["summary"]))
            records.append(dict(case_id=case_id, stress_group=spec["stress_group"],
                                baseline_wrong=np.any(baseline != labels, axis=1), candidate_wrong=np.any(predictions != labels, axis=1)))
        report.update(valid=True, reason="Exploratory measurements only; await main's adjudication before any ratchet", cases=summaries, **aggregate(records))
        write_json(output / "report.json", report)
        return report


def compare(args):
    reference_path = private_path(args.reference)
    candidate_path = private_path(args.candidate)
    reference = json.loads(reference_path.read_text())
    candidate = json.loads(candidate_path.read_text())
    if not reference.get("valid") or not candidate.get("valid"):
        raise ValueError("Both isolated runs must be valid")
    if reference["manifest_sha256"] != candidate["manifest_sha256"] or reference["case_ids"] != candidate["case_ids"]:
        raise ValueError("Pareto comparisons require exactly the same corpus and case order")
    suite, manifest = load_suite(Path(reference["suite"]))
    groups = {case["spec"]["case_id"]: case["spec"]["stress_group"] for case in manifest["cases"]}
    records = []
    for case_id in reference["case_ids"]:
        with np.load(suite / "private" / (case_id + ".npz"), allow_pickle=False) as data:
            labels = data["labels"]
        with np.load(reference_path.parent / "predictions" / (case_id + ".npz"), allow_pickle=False) as data:
            reference_wrong = np.any(data["predictions"] != labels, axis=1)
        with np.load(candidate_path.parent / "predictions" / (case_id + ".npz"), allow_pickle=False) as data:
            candidate_wrong = np.any(data["predictions"] != labels, axis=1)
        records.append(dict(case_id=case_id, stress_group=groups[case_id], baseline_wrong=reference_wrong, candidate_wrong=candidate_wrong))
    paired = aggregate(records)
    reference_cpu = reference["execution"]["cpu_seconds"]
    candidate_cpu = candidate["execution"]["cpu_seconds"]
    corrected = paired["pooled"]["baseline_failures"] - paired["pooled"]["candidate_failures"]
    result = dict(exploratory=True, official_score=False, future_target=None, reference=str(reference_path), candidate=str(candidate_path),
                  trusted_total_cpu_ratio=candidate_cpu / reference_cpu, reference_cpu_seconds=reference_cpu,
                  candidate_cpu_seconds=candidate_cpu, net_failures_removed=corrected,
                  reference_weakly_dominated=corrected >= 0 and candidate_cpu <= reference_cpu,
                  gain_per_extra_cpu_second=corrected / (candidate_cpu - reference_cpu) if candidate_cpu > reference_cpu else None,
                  caveat="A quality gain bought only with more ensemble work is not evidence for a meaningful new scientific task; establish a compute-matched frontier and independent confirmation first.", **paired)
    write_json(args.output, result)
    return result


def register_portfolio(args):
    if not args.main_approved_experiment:
        raise ValueError("Main must explicitly authorize the nonofficial portfolio experiment")
    parent_manifest = private_path(args.parent_manifest)
    parent = json.loads(parent_manifest.read_text())
    if parent.get("kind") != "main_confirmed_champion" or parent.get("main_confirmed") is not True:
        raise ValueError("A confirmed champion must exist before portfolio variants")
    parent_code = parent_manifest.parent / "code"
    if tree_inventory(parent_code)["sha256"] != parent["inventory"]["sha256"]:
        raise ValueError("Parent champion snapshot changed")
    submission = args.submission.resolve()
    if not submission.is_relative_to(SIDE / "portfolio_sources") or submission.parent == SIDE / "portfolio_sources":
        raise ValueError("Use a code-only subdirectory under stress_harness/portfolio_sources; never an active attempt")
    destination = private_path(SIDE / "snapshots" / checked_name(args.name))
    if destination.exists():
        raise ValueError("Snapshot already exists")
    before = tree_inventory(submission.parent)
    destination.mkdir(parents=True)
    snapshot_submission(submission, destination / "code")
    copied = tree_inventory(destination / "code")
    if copied["sha256"] != before["sha256"] or tree_inventory(submission.parent)["sha256"] != before["sha256"]:
        raise ValueError("Portfolio source changed while copying")
    manifest = dict(kind="main_approved_portfolio_variant", main_approved_experiment=True, official_score=False,
                    original_task_passed=None, parent_champion_sha256=parent["inventory"]["sha256"],
                    change_note=args.change_note, entrypoint=submission.name, inventory=copied,
                    note="Unvalidated experimental variant, not a promoted champion or a passing solution")
    write_json(destination / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    builder = subparsers.add_parser("build")
    builder.add_argument("--name", required=True)
    builder.add_argument("--shots", type=int, default=256)
    builder.add_argument("--role", choices=["discovery", "independent_confirmation"], default="discovery")
    builder.add_argument("--cases")
    builder.add_argument("--catalog-file", type=Path)
    registration = subparsers.add_parser("register-champion")
    registration.add_argument("--name", required=True)
    registration.add_argument("--submission", type=Path, required=True)
    registration.add_argument("--official-report", type=Path, required=True)
    registration.add_argument("--confirm-promoted", action="store_true")
    portfolio = subparsers.add_parser("register-portfolio")
    portfolio.add_argument("--name", required=True)
    portfolio.add_argument("--submission", type=Path, required=True)
    portfolio.add_argument("--parent-manifest", type=Path, required=True)
    portfolio.add_argument("--change-note", required=True)
    portfolio.add_argument("--main-approved-experiment", action="store_true")
    runner = subparsers.add_parser("run")
    runner.add_argument("--name", required=True)
    runner.add_argument("--suite", type=Path, required=True)
    runner.add_argument("--cases")
    runner.add_argument("--cpu-budget", type=int, default=180)
    runner.add_argument("--wall-watchdog", type=int, default=1800)
    sources = runner.add_mutually_exclusive_group(required=True)
    sources.add_argument("--champion-manifest", type=Path)
    sources.add_argument("--trusted-baseline", action="store_true")
    sources.add_argument("--isolation-probe", action="store_true")
    comparison = subparsers.add_parser("compare")
    comparison.add_argument("--reference", type=Path, required=True)
    comparison.add_argument("--candidate", type=Path, required=True)
    comparison.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"build": build, "register-champion": register_champion, "register-portfolio": register_portfolio,
              "run": run, "compare": compare}[args.command](args)
    print(json.dumps({key: value for key, value in result.items() if key not in ["cases", "stress_groups", "identity", "inventory"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
