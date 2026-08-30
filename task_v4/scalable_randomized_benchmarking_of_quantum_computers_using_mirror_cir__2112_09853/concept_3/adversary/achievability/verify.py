import hashlib
import importlib.util
import json
import multiprocessing
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(WORK))
import search


def main():
    summary = json.loads((WORK / "latest_summary.json").read_text())
    config_path = ROOT / summary["config"]
    config = json.loads(config_path.read_text())
    snapshot = json.loads((config_path.parent / "input_snapshot.json").read_text())
    if hashlib.sha256((WORK / "search.py").read_bytes()).hexdigest() != config["search_sha256"]:
        raise RuntimeError("search source changed")
    for path, digest in config["frozen_file_sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise RuntimeError("frozen source/specification changed")
    seed_hashes = [hashlib.sha256(seed.encode()).hexdigest() for seed in config["seeds"]]
    if seed_hashes != config["seed_sha256"]:
        raise RuntimeError("seed commitments do not match")
    replay_directory = config_path.parent / "deterministic_replay"
    replay_directory.mkdir(exist_ok=True)
    primary = next(circuit["layers"] for circuit in snapshot["template"]["circuits"] if circuit["family"] == "grid20")
    warmstarts = [primary, primary, search.inverse_representative(primary), snapshot["alternative"]["layers"]]
    selected_worker = summary["selected_worker"]
    stop = multiprocessing.get_context("fork").Event()
    search.worker(selected_worker, config["family"], [int(seed) for seed in config["seeds"]], warmstarts,
                  time.monotonic() + 60, stop, str(replay_directory))
    replayed = json.loads((replay_directory / f"worker_{selected_worker}_best.json").read_text())
    original = json.loads((config_path.parent / f"worker_{selected_worker}_best.json").read_text())
    if replayed != original:
        raise RuntimeError("winning worker did not deterministically reproduce its circuit")
    artifact_path = ROOT / "champions/private_achievability.json"
    artifact = json.loads(artifact_path.read_text())
    spec = json.loads((ROOT / "evaluator/hidden/frozen_spec.json").read_text())
    reference_spec = importlib.util.spec_from_file_location("reference", ROOT / "participant/baseline/solve.py")
    reference = importlib.util.module_from_spec(reference_spec)
    reference_spec.loader.exec_module(reference)
    exact_comparison = {}
    for family in spec["families"]:
        circuit = next(circuit for circuit in artifact["circuits"] if circuit["family"] == family["id"])
        independent = reference.measurements(family, circuit)
        official_kernel = [values.tolist() for strata in search.circuit_weights(family["n"], circuit["layers"]) for values in strata]
        if independent != official_kernel:
            raise RuntimeError("independent full-support integer arithmetic disagrees")
        exact_comparison[family["id"]] = {"equal": True, "checked_paulis": sum(map(len, independent))}
    report_path = ROOT / "champions/private_achievability_recheck.json"
    completed = subprocess.run([sys.executable, "-B", str(ROOT / "evaluator/evaluate.py"),
                                "--submission", str(artifact_path), "--output", str(report_path)],
                               check=True, text=True, capture_output=True)
    report = json.loads(completed.stdout)
    if not report["valid"] or not report["passed"] or report["core_score"] != 1.0:
        raise RuntimeError("frozen official evaluator did not pass the artifact")
    validation = {"valid": True, "passed": True, "core_score": report["core_score"],
                  "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                  "official_report": str(report_path.relative_to(ROOT)),
                  "deterministic_replay_exact": True, "seed_commitments_verified": True,
                  "source_hashes_verified": True, "independent_full_support_comparison": exact_comparison,
                  "fresh_artifacts_read": False, "frozen_files_modified": False,
                  "config": str(config_path.relative_to(ROOT)),
                  "selected_worker": selected_worker,
                  "selected_worker_iterations": summary["workers"][selected_worker]["iterations"],
                  "search_runtime_seconds": summary["runtime_seconds"],
                  "search_cpu_seconds": sum(record["cpu_seconds"] for record in summary["workers"])}
    (WORK / "validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))
    for family, value in report["families"].items():
        print(family, {direction: {kind: (metrics["minimum"], metrics["mean"])
                                 for kind, metrics in strata.items()}
                       for direction, strata in value["metrics"].items()})


if __name__ == "__main__":
    main()
