import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import difflib
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GENERATION = ROOT / "adversary" / "generation_1"
RUNS = ROOT.parent / "authoring" / "runs" / "concept_2"
CHAMPION = ROOT / "champions" / "generation_2"
EXPECTED_SOURCE = "ff3be413ac50296f29a0a63e6383759d30d2ea3696f4323d130195b1e69baba2"
EXPECTED_INPUT = "bf5b6cc4e1027989d4672ab890d19d9556e96ab07eb8e309246daa85a134b486"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def manifest(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError("symlink in frozen directory: " + str(path))
        if path.is_file():
            result[str(path.relative_to(directory))] = digest(path)
    return result


def copy_file(source, destination):
    if source.is_symlink() or not source.is_file():
        raise ValueError("not a regular source file: " + str(source))
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.is_symlink() or digest(source) != digest(destination):
            raise ValueError("refusing to replace an existing archive: " + str(destination))
    else:
        shutil.copyfile(source, destination)


def copy_tree(source, destination):
    expected = manifest(source)
    for relative in expected:
        copy_file(source / relative, destination / relative)
    if manifest(destination) != expected:
        raise ValueError("archive mismatch: " + str(destination))
    return expected


def archive_champion():
    evaluations = {name: read_json(RUNS / name / "evaluation.json") for name in ("v_3", "v_4")}
    selected = max((name for name in evaluations if evaluations[name]["valid"]), key=lambda name: evaluations[name]["score"])
    if selected != "v_4":
        raise ValueError("the selected fresh champion changed")
    source = RUNS / selected
    recorded = read_json(source / "result.json")
    launch = read_json(source / "launch.json")
    actual = copy_tree(source / "frozen_submission", CHAMPION / "frozen_submission")
    if actual != recorded["submission_manifest"] or actual["search.py"] != EXPECTED_SOURCE:
        raise ValueError("fresh submission hash/provenance mismatch")
    if evaluations[selected]["input_sha256"] != EXPECTED_INPUT:
        raise ValueError("unexpected generation input")
    ignored_bytecode = {}
    for kind in ("participant", "evaluator"):
        present = manifest(ROOT / kind)
        expected = launch[kind + "_manifest"]
        ignored_bytecode[kind] = [name for name in present if name not in expected and "__pycache__" in Path(name).parts and name.endswith(".pyc")]
        checked = {name: value for name, value in present.items() if name not in ignored_bytecode[kind]}
        if checked != expected:
            raise ValueError("active " + kind + " differs from the fresh launch")
    for filename in ("evaluation.json", "evaluation_audit.json", "evaluation_complete.json", "evaluation.log", "launch.json", "result.json", "prompt.txt", "transcript.log"):
        copy_file(source / filename, CHAMPION / filename)
    metadata = {
        "selected_fresh_attempt": selected, "winning_task_generation": 1,
        "archive_generation": 2, "selection_rule": "highest unrounded independently valid fresh score",
        "source": str(source), "score": evaluations[selected]["score"],
        "all_generation_1_results": evaluations, "frozen_submission_manifest": actual,
        "submission_manifest_matches_result": True, "active_package_matches_launch": True,
        "excluded_runtime_bytecode_from_launch_comparison": ignored_bytecode,
        "recorded_search_arguments": ["--starts", "1"],
        "effective_search_configuration": {"count": 32, "starts": 1, "maxiter": 300, "seed": 1729, "initial": None},
        "transcript_search_invocation_line": 1055,
    }
    write_json(CHAMPION / "archive_manifest.json", metadata)
    copy_file(ROOT / "status.json", HERE / "archive" / "status_before_replay.json")
    write_json(HERE / "protected_manifest.json", {kind: manifest(ROOT / kind) for kind in ("participant", "evaluator")})
    return metadata


def prepare_adapter():
    source = CHAMPION / "frozen_submission" / "search.py"
    original = source.read_text()
    participant_line = next(line for line in original.splitlines() if line.startswith("PARTICIPANT = "))
    replacements = [
        (participant_line, 'PARTICIPANT = Path("/participant")'),
        ("np.triu_indices(8, 1)", "np.triu_indices(self.reference.shape[1], 1)"),
        ("np.zeros((8, len(self.edges[0])))", "np.zeros((self.reference.shape[1], len(self.edges[0])))"),
        ("np.zeros(168)", "np.zeros(2 * self.reference_edges.size)"),
    ]
    adapted = original
    for before, after in replacements:
        if adapted.count(before) != 1:
            raise ValueError("adapter substitution is not unique: " + before)
        adapted = adapted.replace(before, after)
    reversed_source = adapted
    for before, after in reversed(replacements):
        reversed_source = reversed_source.replace(after, before)
    if reversed_source != original:
        raise ValueError("adapter reversibility failed")
    destination = HERE / "adapter" / "search.py"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.read_text() != adapted:
            raise ValueError("existing adapter differs")
    else:
        patch = "*** Begin Patch\n*** Add File: " + str(destination) + "\n" + "".join("+" + line + "\n" for line in adapted.splitlines()) + "*** End Patch\n"
        subprocess.run(["apply_patch"], input=patch, text=True, check=True)
    (HERE / "adapter" / "config_only.diff").write_text("".join(difflib.unified_diff(original.splitlines(True), adapted.splitlines(True), fromfile="v4_frozen/search.py", tofile="adapter/search.py")))
    write_json(HERE / "adapter" / "manifest.json", {
        "original_sha256": digest(source), "adapted_sha256": digest(destination),
        "reversible_exact_substitutions": replacements, "algorithm_unchanged": True,
        "families": "Already iterates over config['families']; no four-family literal exists.",
        "target": "No literal target or target stop exists. Each frozen config's target is enforced by the exact checker.",
        "initialization": "Zero null coordinates, both reference kernels; no private or frozen winning pair seeded.",
        "search_arguments": ["--starts", "1"],
        "unchanged": ["M32", "SLSQP", "epigraph minimax objective", "implicit gradients", "seed 1729", "ftol 1e-11", "maxiter 300", "one start", "incumbent artifact selection"],
    })
    return destination


def pool_specifications():
    candidates = GENERATION / "robustness_exploration" / "candidates"
    ordinary = ROOT / "adversary" / "ratchet_pool" / "instances"
    return [
        ("control_middle_cross_45", GENERATION / "participant" / "input", GENERATION / "evaluator" / "hidden" / "witness.npz", 1.09),
        ("original_reference", GENERATION / "archived_originals" / "participant" / "input", GENERATION / "archived_originals" / "evaluator" / "hidden" / "witness.npz", 1.12),
        ("rough_broad", ordinary / "rough_broad" / "input", ordinary / "rough_broad" / "witness.npz", 1.12),
        ("rough_assortative", ordinary / "rough_assortative" / "input", ordinary / "rough_assortative" / "witness.npz", 1.12),
        ("anti_constant_1p0", candidates / "anti_constant_1p0" / "input", candidates / "anti_constant_1p0" / "witness.npz", 1.08),
        ("middle_below_soft", candidates / "middle_below_soft" / "input", candidates / "middle_below_soft" / "witness.npz", 1.08),
        ("middle_cross_35", candidates / "middle_cross_35" / "input", candidates / "middle_cross_35" / "witness.npz", 1.09),
        ("middle_cross_60", candidates / "middle_cross_60" / "input", candidates / "middle_cross_60" / "witness.npz", 1.08),
    ]


def evaluate(case, artifact, label):
    output = case / (label + ".json")
    command = ["/usr/bin/python3", "-B", str(case / "evaluator" / "evaluate.py"), "--artifact", str(artifact), "--output", str(output), "--audit-output", str(case / (label + ".audit.json"))]
    with (case / (label + ".log")).open("w") as stream:
        subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=120)
    return read_json(output)


def prepare_pool(adapter):
    ledger = []
    for name, inputs, witness, target in pool_specifications():
        case = HERE / "cases" / name
        config = read_json(inputs / "config.json")
        if config["target_ratio"] != target:
            raise ValueError("frozen pool target changed: " + name)
        copy_tree(ROOT / "participant" / "workspace", case / "participant" / "workspace")
        for filename in ("config.json", "reference.npz"):
            copy_file(inputs / filename, case / "participant" / "input" / filename)
            copy_file(inputs / filename, case / "evaluator" / "hidden" / "frozen_input" / filename)
        for filename in ("evaluate.py", "_physics.py", "_audit.py", "reporting.py"):
            copy_file(ROOT / "evaluator" / filename, case / "evaluator" / filename)
        copy_file(witness, case / "private_witness.npz")
        copy_file(adapter, case / "output" / "search.py")
        private = evaluate(case, case / "private_witness.npz", "private_evaluation")
        if not private["valid"]:
            raise ValueError("known private witness no longer passes: " + name)
        record = {
            "name": name, "target_ratio": target, "source_input": str(inputs), "source_witness": str(witness),
            "private_score": private["score"], "private_valid": private["valid"],
            "input_sha256": private["input_sha256"], "private_artifact_sha256": digest(witness),
            "shape": config["artifact_shape"], "families": config["families"],
            "public_manifest": manifest(case / "participant"), "evaluator_manifest": manifest(case / "evaluator"),
            "search_adapter_sha256": digest(adapter),
        }
        write_json(case / "provenance.json", record)
        ledger.append(record)
        print(json.dumps({"prepared": name, "private_score": private["score"], "target": target}), flush=True)
    write_json(HERE / "pool_manifest.json", {"cases": ledger, "targets_unchanged": True, "new_instances": 0, "n24_excluded": "The prior 600-second truncated replay is inconclusive; it is not a one-hour failure."})


def run_case(record):
    name = record["name"]
    case = HERE / "cases" / name
    output = case / "output"
    if (case / "replay_result.json").exists():
        return read_json(case / "replay_result.json")
    if sorted(path.name for path in output.iterdir()) != ["search.py"]:
        raise ValueError("replay output must start empty except the provenance-checked source: " + name)
    if digest(output / "search.py") != record["search_adapter_sha256"]:
        raise ValueError("search source changed")
    command = [
        "/usr/bin/bwrap", "--die-with-parent", "--new-session", "--unshare-all",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
        "--ro-bind", "/etc", "/etc", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--ro-bind", str(case / "participant"), "/participant", "--bind", str(output), "/output", "--chdir", "/output",
        "--setenv", "HOME", "/tmp", "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "OMP_NUM_THREADS", "1",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--",
        "/usr/bin/time", "-f", '{"wall_seconds":%e,"user_cpu_seconds":%U,"system_cpu_seconds":%S,"peak_rss_kib":%M,"exit_status":%x}',
        "-o", "/output/search.resource.json", "/usr/bin/python3", "-B", "/output/search.py", "--starts", "1",
    ]
    write_json(case / "invocation.json", {"command": command, "timeout_seconds": 3600, "timeout_interpretation": "Incomplete search is inconclusive, not an optimization-quality failure.", "private_mounts": [], "input_and_output_only": True})
    started = time.monotonic()
    with (output / "search.log").open("w") as stream:
        try:
            process = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, timeout=3600)
            returncode = process.returncode
        except subprocess.TimeoutExpired:
            returncode = None
    measured = {"controller_wall_seconds": time.monotonic() - started}
    resource_path = output / "search.resource.json"
    measured["search"] = None
    if resource_path.exists():
        for line in reversed(resource_path.read_text().splitlines()):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict) and "wall_seconds" in parsed:
                    measured["search"] = parsed
                    break
            except ValueError:
                continue
    artifact = output / "witness.npz"
    evaluation = evaluate(case, artifact, "champion_evaluation") if artifact.exists() else None
    if manifest(case / "participant") != record["public_manifest"] or digest(output / "search.py") != record["search_adapter_sha256"]:
        raise ValueError("public data or search source changed during replay")
    completed = returncode == 0
    valid = bool(evaluation and evaluation["valid"])
    gap = bool(completed and evaluation and evaluation["admissible"] and not valid)
    result = {
        "name": name, "private_score": record["private_score"], "target_ratio": record["target_ratio"],
        "input_sha256": record["input_sha256"], "search_returncode": returncode,
        "completed_recorded_method": completed, "admissible": bool(evaluation and evaluation["admissible"]),
        "valid": valid, "score": evaluation["score"] if evaluation else None,
        "genuine_admissible_failure_observed": gap, "resources": measured,
        "reason": "PASS: actual fresh search produced an independently valid pair." if valid else ("Completed recorded method emitted an admissible below-contract pair; review required before any ratchet." if gap else "Inconclusive: no completed admissible search result."),
    }
    write_json(case / "replay_result.json", result)
    print(json.dumps(result), flush=True)
    return result


def replay_pool():
    records = read_json(HERE / "pool_manifest.json")["cases"]
    results = []
    control = run_case(records[0])
    results.append(control)
    expected = read_json(CHAMPION / "evaluation.json")["score"]
    if not control["valid"] or abs(control["score"] - expected) > 2e-8:
        write_json(HERE / "summary.json", {"control_passed": False, "results": results, "reason": "Original generation-1 control did not reproduce; no alternative result supports a gap."})
        raise ValueError("original control failed")
    for record in records[1:]:
        results.append(run_case(record))
        save_summary(results)
    return save_summary(results)


def save_summary(results):
    protected = read_json(HERE / "protected_manifest.json")
    unchanged = all(manifest(ROOT / kind) == protected[kind] for kind in protected)
    summary = {
        "control_passed": True, "actual_search_replays": len(results), "results": results,
        "passing_replays": sum(record["valid"] for record in results),
        "genuine_admissible_failures": [record["name"] for record in results if record["genuine_admissible_failure_observed"]],
        "inconclusive_replays": [record["name"] for record in results if not record["valid"] and not record["genuine_admissible_failure_observed"]],
        "active_numerical_package_unchanged": unchanged, "new_fresh_launches": 0,
        "original_23_v2_replays_preserved": True,
        "search_cpu_seconds": sum(record["resources"]["search"]["user_cpu_seconds"] + record["resources"]["search"]["system_cpu_seconds"] for record in results if record["resources"]["search"]),
        "reason": "Bounded replay of the actual v4 minimax search over frozen, independently revalidated cases. No path/shape/target failure is counted.",
    }
    write_json(HERE / "summary.json", summary)
    if not unchanged:
        raise ValueError("active package changed during replay")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("prepare", "replay"))
    arguments = parser.parse_args()
    if arguments.stage == "prepare":
        archive_champion()
        prepare_pool(prepare_adapter())
    else:
        replay_pool()


if __name__ == "__main__":
    main()
