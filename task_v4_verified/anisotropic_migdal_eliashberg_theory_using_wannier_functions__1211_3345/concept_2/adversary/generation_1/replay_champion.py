import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import ast
import difflib
import hashlib
import json
import re
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path


PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parents[1]
POOL = ROOT / "adversary" / "ratchet_pool"
sys.path.insert(0, str(POOL))

from pool_common import audit_pair, json_write, load_instance, read_artifact
from reporting import add_reporting_fields


def prepare_adapter():
    source = ROOT / "champions" / "generation_1" / "frozen_submission" / "search.py"
    original = source.read_text()
    adapted, replacements = re.subn(r'^PARTICIPANT\s*=\s*Path\([^\n]+\)$', 'PARTICIPANT = Path("/participant")', original, flags=re.MULTILINE)
    if replacements != 1:
        raise ValueError("expected exactly one hardcoded PARTICIPANT assignment")
    tree = ast.parse(original)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "PARTICIPANT" for target in node.targets):
            node.value.args[0].value = "/participant"
    if ast.dump(tree, include_attributes=False) != ast.dump(ast.parse(adapted), include_attributes=False):
        raise ValueError("adapter changed more than the participant path")
    folder = PENDING / "champion_adapter"
    folder.mkdir(exist_ok=True)
    destination = folder / "search.py"
    if destination.exists():
        if destination.read_text() != adapted:
            raise ValueError("existing adapter differs")
    else:
        patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n" + "".join("+" + line + "\n" for line in adapted.splitlines()) + "*** End Patch\n"
        subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    (folder / "path_only.diff").write_text("".join(difflib.unified_diff(original.splitlines(True), adapted.splitlines(True), fromfile="frozen_submission/search.py", tofile="champion_adapter/search.py")))
    json_write(folder / "manifest.json", {
        "original_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "adapted_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "algorithm_unchanged": True, "ast_equivalent_except_participant_path": True,
        "original_search_arguments": ["--count", "48", "--starts", "24"],
        "recorded_refinement_arguments": ["--count", "192", "--starts", "0", "--resume", "witness.npz"],
        "selection": "Audit both the original coarse search and its recorded refinement; retain the better score. This favors the champion rather than discarding a successful refinement.",
    })
    return destination


def evaluate_artifact(artifact, instance, search_resources):
    started_wall = time.monotonic()
    started_cpu = time.process_time()
    result = {"admissible": False, "valid": False, "score": 0., "target_ratio": instance["config"]["target_ratio"]}
    try:
        kernels, digest = read_artifact(artifact, instance["config"], with_digest=True)
        result = audit_pair(kernels, instance)
        result["artifact_sha256"] = digest
    except Exception as error:
        result["error"] = type(error).__name__ + ": " + str(error)
    measurements = {
        "evaluation_wall_seconds": time.monotonic() - started_wall,
        "evaluation_cpu_seconds": time.process_time() - started_cpu,
        "evaluator_process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "search": search_resources,
        "scope": "Evaluation times exclude search; evaluator peak RSS is process-lifetime Linux KiB. Search resource files measure the isolated Python search process through GNU time.",
    }
    return add_reporting_fields(result, measurements)


def read_resource_record(path):
    raw = path.read_text() if path.exists() else ""
    for line in reversed(raw.splitlines()):
        try:
            record = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(record, dict) and "wall_seconds" in record:
            return record
    return {
        "wall_seconds": None, "user_cpu_seconds": None, "system_cpu_seconds": None,
        "peak_rss_kib": None, "resource_measurement_available": False,
        "resource_measurement_reason": "GNU time produced no complete JSON record; CPU and peak RSS are unknown, not zero.",
        "resource_record_raw": raw[:4096],
    }


def run_stage(participant, output, arguments, stage):
    resource_file = "/output/" + stage + ".resource.json"
    command = [
        "/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-all",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
        "--ro-bind", "/etc", "/etc", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(participant), "/participant", "--bind", str(output), "/output", "--chdir", "/output",
        "--setenv", "HOME", "/tmp", "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "OMP_NUM_THREADS", "1",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--",
        "/usr/bin/time", "-f", '{"wall_seconds":%e,"user_cpu_seconds":%U,"system_cpu_seconds":%S,"peak_rss_kib":%M,"exit_status":%x}',
        "-o", resource_file, "/usr/bin/python3", "-B", "/output/search.py", *arguments,
    ]
    started = time.monotonic()
    with (output / (stage + ".log")).open("w") as stream:
        try:
            completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
            code = completed.returncode
        except subprocess.TimeoutExpired:
            code = -999
    resource_path = output / (stage + ".resource.json")
    measurements = read_resource_record(resource_path)
    measurements.update(host_wall_seconds=time.monotonic() - started, returncode=code, command=command,
                        stage_wall_limit_seconds=600,
                        execution_status="timeout" if code == -999 else "completed" if code == 0 else "failed")
    return measurements


def replay(name, input_path, private_score, adapter, family="compressed_spectrum"):
    directory = PENDING / "champion_replays" / name
    result_path = directory / "result.json"
    if result_path.exists():
        previous = json.loads(result_path.read_text())
        if previous.get("admissible"):
            return previous
        shutil.copyfile(result_path, directory / "prior_execution_failure.json")
    participant = directory / "participant"
    output = directory / "output"
    directory.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=True)
    if not participant.exists():
        shutil.copytree(PENDING / "archived_originals" / "participant", participant)
    for filename in ("config.json", "reference.npz"):
        shutil.copyfile(input_path / filename, participant / "input" / filename)
    shutil.copyfile(adapter, output / "search.py")
    instance = load_instance(participant / "input")
    coarse_resources = run_stage(participant, output, ["--count", "48", "--starts", "24", "--family", family, "--output", "/output/witness.npz"], "coarse")
    phases = []
    if coarse_resources["returncode"] == 0 and (output / "witness.npz").exists():
        coarse = evaluate_artifact(output / "witness.npz", instance, coarse_resources)
        phases.append(("coarse", coarse))
        json_write(directory / "coarse.audit.json", coarse)
        refinement_resources = run_stage(participant, output, ["--count", "192", "--starts", "0", "--family", family, "--resume", "/output/witness.npz", "--output", "/output/refined.npz"], "refinement")
        if refinement_resources["returncode"] == 0 and (output / "refined.npz").exists():
            refined = evaluate_artifact(output / "refined.npz", instance, refinement_resources)
            phases.append(("refinement", refined))
            json_write(directory / "refinement.audit.json", refined)
    if phases:
        phase, best = max(phases, key=lambda item: (item[1].get("admissible", False), item[1]["score"]))
        score = best["score"]
        genuine = bool(best["admissible"] and not best["valid"] and private_score is not None and private_score >= instance["config"]["target_ratio"])
        result = {"name": name, "selected_phase": phase, "score": score, "core_score": score, "worst_family_score": score,
                  "valid": best["valid"], "admissible": best["admissible"], "reason": best["reason"], "resources": best["resources"],
                  "private_passing_score": private_score, "private_minus_champion": private_score - score if private_score is not None else None,
                  "genuine_admissible_failure_observed": genuine, "algorithm_unchanged": True,
                  "search_not_static_artifact_replay": True, "input_sha256": instance["input_sha256"]}
    else:
        result = {"name": name, "score": 0., "core_score": 0., "worst_family_score": 0., "valid": False, "admissible": False,
                  "reason": "Search execution did not complete; this is NOT counted as an optimization or robustness failure.",
                  "resources": coarse_resources, "genuine_admissible_failure_observed": False,
                  "algorithm_unchanged": True, "search_not_static_artifact_replay": True}
    json_write(result_path, result)
    print(json.dumps({key: result.get(key) for key in ("name", "score", "valid", "admissible", "private_minus_champion", "genuine_admissible_failure_observed", "reason")}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-seconds", type=float, default=1800.)
    arguments = parser.parse_args()
    adapter = prepare_adapter()
    selected = json.loads((PENDING / "champion_selection.json").read_text())
    results = [replay("original_control", PENDING / "archived_originals" / "participant" / "input", selected["score"], adapter)]
    control = results[0]
    if not control["valid"] or abs(control["score"] - selected["score"]) > 2e-6:
        json_write(PENDING / "champion_replay_summary.json", {"control_passed": False, "results": results, "reason": "Original control failed; alternative failures cannot support a ratchet."})
        raise RuntimeError("original control did not reproduce the fresh champion")
    seen = {"original_control"}
    started = time.monotonic()
    while True:
        for audit_path in sorted((POOL / "instances").glob("*/audit.json")):
            name = audit_path.parent.name
            if name in seen:
                continue
            private = json.loads(audit_path.read_text())
            if private.get("valid"):
                results.append(replay(name, audit_path.parent / "input", private["score"], adapter))
                seen.add(name)
        if (POOL / "pool_summary.json").exists() or time.monotonic() - started > arguments.wait_seconds:
            break
        time.sleep(10)
    summary = {"control_passed": True, "results": results, "actual_search_replays": len(results),
               "genuine_admissible_failures": [result["name"] for result in results[1:] if result["genuine_admissible_failure_observed"]],
               "active_package_unchanged": True, "new_fresh_launches": 0}
    json_write(PENDING / "champion_replay_summary.json", summary)
    print(json.dumps({"finished": True, "actual_search_replays": len(results), "genuine_admissible_failures": summary["genuine_admissible_failures"]}), flush=True)


if __name__ == "__main__":
    main()
