"""Private generation sweep; submitted policies see public assets only."""

import argparse
import collections
import difflib
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor


HERE = Path(__file__).resolve().parent
TASK = HERE.parents[1]
ARCHIVE = TASK / "champions" / "generation_1"
EVALUATOR = None
POLICY_MODULE = None
LAST_DEVICE = None


def asset(path, text):
    path = Path(path)
    if path.exists():
        if path.read_text() != text:
            raise ValueError(f"refusing to overwrite existing asset: {path}")
        return
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
    patch += "".join("+" + line + "\n" for line in text.splitlines())
    patch += "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True, stdout=subprocess.DEVNULL)


def encoded(value):
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def parameterize(source):
    replacements = [
        ("CORE_SIZE = 6", "CORE_SIZE = 6\nCONTRACT = json.loads(open('/task/contract.json').read())\nFRAME_LIMIT = CONTRACT['frames']\nQUERY_LIMIT = CONTRACT['parity_queries']\nFRAME_QUERY_LIMIT = CONTRACT['queries_per_frame']\nNOISE_GRID = tuple(1 / denominator if denominator else 0.00001 for denominator in CONTRACT['contamination_denominators'])\nNOISE_COUNT = len(NOISE_GRID)"),
        ("for epsilon in (0.00001, 1 / 32, 1 / 16):", "for epsilon in NOISE_GRID:"),
        ("-math.log(30 if family == 0 else 180)", "-math.log((10 if family == 0 else 60) * NOISE_COUNT)"),
        ("deepest > 8 - self.frame_queries", "deepest > FRAME_QUERY_LIMIT - self.frame_queries"),
        ("self.frames < 153", "self.frames < FRAME_LIMIT - 7"),
        ("self.queries < 470", "self.queries < QUERY_LIMIT - 10"),
        ("self.frames < 160", "self.frames < FRAME_LIMIT"),
        ("self.queries < (472 if full else 477)", "self.queries < (QUERY_LIMIT - 8 if full else QUERY_LIMIT - 3)"),
        ("[0.0] * 3 for unused in range(2)", "[0.0] * NOISE_COUNT for unused in range(2)"),
        ("index % 3", "index % NOISE_COUNT"),
        ("for noise in range(3)", "for noise in range(NOISE_COUNT)"),
        ("self.frames < 110", "self.frames < FRAME_LIMIT - 50"),
        ("self.queries < 370", "self.queries < QUERY_LIMIT - 110"),
        ("120 - self.frames", "FRAME_LIMIT - 40 - self.frames"),
        ("self.queries < 477", "self.queries < QUERY_LIMIT - 3"),
    ]
    for old, new in replacements:
        if old not in source:
            raise ValueError(f"missing exact replacement: {old}")
        source = source.replace(old, new)
    return source, replacements


def prepare(name, denominators, queries):
    profile = HERE / "profiles" / name
    contract = json.loads((ARCHIVE / "participant/input/contract.json").read_text())
    contract["contamination_denominators"] = denominators
    contract["parity_queries"] = queries
    if denominators != [0, 32, 16] or queries != 480:
        contract["version"] = "cascade-correlated-echo-v2-" + name
    original = (ARCHIVE / "submission/policy.py").read_text()
    adapted, replacements = parameterize(original)
    asset(HERE / "policies/champion_parameterized.py", adapted)
    asset(HERE / "policies/champion_original.py", original)
    asset(HERE / "policies/baseline.py", (ARCHIVE / "participant/baseline/policy.py").read_text())
    asset(HERE / "champion_parameterization.patch", "".join(difflib.unified_diff(original.splitlines(True), adapted.splitlines(True), fromfile="generation_1/submission/policy.py", tofile="private/champion_parameterized.py")))
    asset(HERE / "parameterization.json", encoded({"replacements": replacements, "zero_noise_floor_preserved": 0.00001, "allocation_policy": "Preserve absolute remaining-frame and remaining-query reserves, source selection, likelihoods, confidence thresholds, discovery counts, and decoding. Noise-count prior normalization is unchanged for three-level contracts."}))
    asset(profile / "participant/input/contract.json", encoded(contract))
    for name in ("simulator.py", "dev_cases.json"):
        asset(profile / "participant/input" / name, (ARCHIVE / "participant/input" / name).read_text())
    asset(profile / "evaluator/evaluate.py", (TASK / "evaluator/evaluate.py").read_text())
    manifest_path = profile / "evaluator/hidden/manifest.json"
    if not manifest_path.exists():
        asset(manifest_path, encoded({"version": "cascade-correlated-echo-hidden-v2", "root_seed": secrets.token_hex(32), "episodes_per_cell": 20, "target_frozen_date": "2026-08-28", "generation_only": True}))
    asset(profile / "profile.json", encoded({"name": profile.name, "denominators": denominators, "queries": queries, "frames": 160, "mounted_dev": "unchanged generation_1 public development cases; no private labels/seeds mounted", "private_evaluator": "byte-identical to current evaluator/evaluate.py; only root relocation changes public contract"}))
    return profile


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def initialize(profile, policy):
    global EVALUATOR, POLICY_MODULE
    sys.dont_write_bytecode = True
    sys.modules.pop("simulator", None)
    EVALUATOR = load_module("private_evaluator", Path(profile) / "evaluator/evaluate.py")
    base_device = EVALUATOR.Device

    class RecordingDevice(base_device):
        def __init__(self, *arguments):
            global LAST_DEVICE
            super().__init__(*arguments)
            self.transcript = []
            self.starts = []
            LAST_DEVICE = self

        def handle(self, request):
            response = super().handle(request)
            self.transcript.append((request, response))
            if request["op"] == "start":
                source = request["source"]
                echo = next(site for site in range(32) if site != source and (self.residual >> (8 * site)) & 255)
                self.starts.append({"source": source, "echo": echo, "off_graph": echo not in self.neighbors[source], "queries": 0})
            elif request["op"] == "parity":
                self.starts[-1]["queries"] += 1
            return response

    EVALUATOR.Device = RecordingDevice
    POLICY_MODULE = None
    if Path(policy).name.startswith("champion"):
        import types
        POLICY_MODULE = types.ModuleType("private_diagnostic_replay")
        source = Path(policy).read_text().replace("json.loads(open('/task/contract.json').read())", repr(EVALUATOR.CONTRACT))
        exec(compile(source, str(policy), "exec"), POLICY_MODULE.__dict__)


def diagnose(device, result):
    if POLICY_MODULE is None or result["failure"]:
        return {"replay": "not applicable"}
    transcript = iter(device.transcript)

    def exchange(request):
        expected, response = next(transcript)
        if expected != request:
            raise AssertionError((expected, request))
        return response

    policy = POLICY_MODULE.Policy(exchange)
    prediction = policy.run()
    expected, response = next(transcript)
    assert expected == {"op": "guess", "family": prediction}
    assert prediction == result["prediction"]
    components = []
    for origin in range(32):
        if any(origin in sites for sites in components):
            continue
        sites = {origin}
        pending = [origin]
        while pending:
            source = pending.pop()
            for adjacent in device.neighbors[source]:
                if adjacent not in sites:
                    sites.add(adjacent)
                    pending.append(adjacent)
        components.append(sites)
    component_families = []
    import itertools
    for sites in components:
        origin = min(sites)
        adjacent = device.neighbors[origin]
        triangle = any(all(second in device.neighbors[first] for first, second in itertools.combinations(triple, 2)) for triple in itertools.combinations(adjacent, 3))
        component_families.append("R" if triangle else "S")
    discoveries = [entry for entry in policy.trace if entry[0] == "discover"]
    models = []
    for name in ("first", "second"):
        model = getattr(policy, name, None)
        if model is None:
            continue
        discovery = discoveries[len(models)]
        center = discovery[1]
        component = next(index for index, sites in enumerate(components) if center in sites)
        models.append({"name": name, "center": center, "core": model.core, "core_all_true_neighbors": all(site in device.neighbors[center] for site in model.core), "component": component, "true_component_family": component_families[component], "posterior_S": model.probability(), "observations": model.observations, "hits": model.hits})
    probabilities = policy.joint(policy.first, policy.second)[0] if hasattr(policy, "second") else None
    clusters = []
    if not result["correct"]:
        if len(models) < 2:
            clusters.append("second_component_not_acquired")
        if any(not model["core_all_true_neighbors"] for model in models):
            clusters.append("contaminated_or_incomplete_neighborhood_model")
        if len(models) == 2 and models[0]["component"] == models[1]["component"]:
            clusters.append("both_models_from_same_component")
        if len(models) == 2 and all(model["core_all_true_neighbors"] for model in models) and models[0]["component"] != models[1]["component"]:
            clusters.append("inference_failure_on_valid_neighborhoods")
        if result["frames"] >= EVALUATOR.CONTRACT["frames"]:
            clusters.append("frame_budget_saturated")
        if result["queries"] >= EVALUATOR.CONTRACT["parity_queries"] - 4:
            clusters.append("query_budget_saturated")
        if probabilities and max(probabilities) > 0.99:
            clusters.append("confident_wrong_posterior")
    return {"replay": "exact scored transcript reproduced; diagnostics never supplied to child", "models": models, "posterior_families": probabilities, "trace": policy.trace, "off_graph_echoes": sum(frame["off_graph"] for frame in device.starts), "clusters": clusters}


def run_payload(payload):
    policy, case = payload
    result = EVALUATOR.run_case(policy, case)
    try:
        diagnostic = diagnose(LAST_DEVICE, result)
    except Exception as error:
        diagnostic = {"replay_error": repr(error)}
    return {"case": case, "result": result, "diagnostic": diagnostic}


def run(profile, policy, output, replicates, seed_tag, jobs, original_hidden=False, use_manifest=False, paired_from=None):
    contract = json.loads((profile / "participant/input/contract.json").read_text())
    manifest = json.loads((profile / "evaluator/hidden/manifest.json").read_text())
    if original_hidden:
        manifest = json.loads((ARCHIVE / "evaluator/hidden/manifest.json").read_text())
    root_seed = manifest["root_seed"] if original_hidden or use_manifest else hashlib.sha256((manifest["root_seed"] + ":" + seed_tag).encode()).hexdigest()
    cases = []
    for replicate in range(replicates):
        for family in contract["families"]:
            for denominator in contract["contamination_denominators"]:
                material = f"{root_seed}:{family}:{denominator}:{replicate}".encode()
                cases.append({"family": family, "contamination_denominator": denominator, "seed": int.from_bytes(hashlib.sha256(material).digest(), "big")})
    if paired_from is not None:
        cases = json.loads((paired_from / "private_cases.json").read_text())
        paired_score = json.loads((paired_from / "score.json").read_text())
        root_seed = paired_score["case_root_seed"]
        assert len(cases) == replicates * len(contract["families"]) * len(contract["contamination_denominators"])
        assert all(case["contamination_denominator"] in contract["contamination_denominators"] for case in cases)
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=True)
    (output / "private_cases.json").write_text(encoded(cases))
    results = []
    with ProcessPoolExecutor(max_workers=jobs, initializer=initialize, initargs=(str(profile), str(policy))) as executor:
        for record in executor.map(run_payload, [(str(policy), case) for case in cases]):
            results.append(record)
            if len(results) % 30 == 0:
                print(f"{profile.name}/{policy.name}: {len(results)}/{len(cases)} correct={sum(row['result']['correct'] for row in results)}", flush=True)
    counts = collections.defaultdict(lambda: {"correct": 0, "total": 0})
    failures = collections.Counter()
    clusters = collections.Counter()
    for record in results:
        case, result = record["case"], record["result"]
        cell = counts[f"{case['family']}@{case['contamination_denominator']}"]
        cell["correct"] += int(result["correct"])
        cell["total"] += 1
        if result["failure"]:
            failures[result["failure"]] += 1
        clusters.update(record["diagnostic"].get("clusters", []))
    total = len(results)
    correct = sum(record["result"]["correct"] for record in results)
    complete = replicates == 20 and len(counts) == 9
    passed = complete and correct >= 171 and all(cell["correct"] >= 18 for cell in counts.values())
    report = {"mode": "E", "suite": "private_hidden_confirmation" if complete else "private_stratified_screen", "episodes": total, "correct": correct, "accuracy": correct / total, "core_score": correct / total, "worst_family_score": min(cell["correct"] / cell["total"] for cell in counts.values()), "runtime_resource_score": 1 - sum(failures.values()) / total, "cells": dict(counts), "protocol_failures": dict(failures), "mean_queries": sum(record["result"]["queries"] for record in results) / total, "mean_frames": sum(record["result"]["frames"] for record in results) / total, "max_queries": max(record["result"]["queries"] for record in results), "max_frames": max(record["result"]["frames"] for record in results), "passed": passed, "target_passed": passed, "complete_hidden_suite": complete, "valid": True, "reason": "fixed target met" if passed else "accuracy, worst-cell target, or complete-suite requirement not met", "root_cause_clusters_nonexclusive": dict(clusters), "replay_errors": sum("replay_error" in record["diagnostic"] for record in results), "elapsed_seconds": time.monotonic() - started, "profile": profile.name, "seed_tag": seed_tag, "case_root_seed": root_seed, "contract_sha256": hashlib.sha256((profile / "participant/input/contract.json").read_bytes()).hexdigest(), "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(), "evaluator_sha256": hashlib.sha256((profile / "evaluator/evaluate.py").read_bytes()).hexdigest(), "private_cases_sha256": hashlib.sha256((output / "private_cases.json").read_bytes()).hexdigest(), "scoring": "unmodified evaluator.run_case in bwrap; parent-only recording and post-score deterministic replay; no diagnostic used to score"}
    (output / "episodes.json").write_text(encoded(results))
    (output / "score.json").write_text(encoded(report))
    print(json.dumps(report, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--denominators", default="0,32,16")
    parser.add_argument("--queries", type=int, default=480)
    parser.add_argument("--replicates", type=int, default=3)
    parser.add_argument("--seed-tag", default="screen-v1")
    parser.add_argument("--jobs", type=int, default=16)
    parser.add_argument("--policy", choices=("champion_parameterized", "champion_original", "baseline"), default="champion_parameterized")
    parser.add_argument("--original-hidden", action="store_true")
    parser.add_argument("--use-manifest", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--paired-from", type=Path)
    args = parser.parse_args()
    profile = prepare(args.profile, [int(value) for value in args.denominators.split(",")], args.queries)
    if not args.prepare_only:
        run(profile, HERE / "policies" / (args.policy + ".py"), HERE / "reports" / (args.profile + "_" + args.seed_tag + "_" + args.policy), args.replicates, args.seed_tag, args.jobs, args.original_hidden, args.use_manifest, args.paired_from)


if __name__ == "__main__":
    main()
