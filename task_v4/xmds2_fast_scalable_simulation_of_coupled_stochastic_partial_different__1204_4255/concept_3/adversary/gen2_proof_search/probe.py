import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TRUSTED = ROOT / "evaluator/hidden"
sys.path.insert(0, str(TRUSTED))
import field_control as fc


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", nargs="+", required=True)
    parser.add_argument("--official", action="store_true")
    parser.add_argument("--reuse-probe", action="store_true")
    parser.add_argument("--nx", type=int, default=64)
    parser.add_argument("--dt", type=float, default=0.02)
    arguments = parser.parse_args()
    protocol = fc.read_json(TRUSTED / "protocol.json")
    cases = fc.read_json(TRUSTED / "cases.json")
    shape = (arguments.nx, arguments.nx // 2)
    initial, target, residual = fc.references(cases, shape, HERE / "probe_cache")
    records = []
    for source_name in arguments.artifact:
        source = Path(source_name).resolve()
        payload = source.read_bytes()
        snapshot = HERE / (source.stem + ".probed_control.json")
        snapshot.write_bytes(payload)
        artifact = fc.read_json(snapshot)
        splines, diagnostics = fc.validate_artifact(artifact, protocol)
        if arguments.reuse_probe:
            record = fc.read_json(HERE / (source.stem + ".probe.json"), 1024 * 1024)
            if record["artifact_sha256"] != hashlib.sha256(payload).hexdigest():
                raise RuntimeError("Cached probe artifact hash mismatch")
            if record["grid"] != list(shape) or record["dt"] != arguments.dt:
                raise RuntimeError("Cached probe resolution mismatch")
            records.append((record, snapshot))
            print("REUSED_HASH_VERIFIED_PROBE", str(source), flush=True)
            continue
        started = time.monotonic()
        state, numerical = fc.evolve(splines, cases, shape, arguments.dt, initial)
        fidelities = fc.fidelities(state, target, shape)
        scores = fc.summarize(fidelities, cases, protocol)
        guard = {key: float(np.max(value)) for key, value in numerical.items()}
        record = dict(scores, source=str(source), artifact_sha256=hashlib.sha256(payload).hexdigest(), grid=list(shape), dt=arguments.dt, reference_residual=residual, diagnostics=guard, seconds=time.monotonic() - started, valid_control=True, official=False, cases=[dict(id=case["id"], family=case["family"], fidelity=float(score)) for case, score in zip(cases, fidelities)])
        dump(HERE / (source.stem + ".probe.json"), record)
        records.append((record, snapshot))
        print("PROBE", json.dumps({key: value for key, value in record.items() if key != "cases"}, allow_nan=False), flush=True)
    if not arguments.official:
        return
    eligible = [(record, snapshot) for record, snapshot in records if record["passed"] and record["diagnostics"]["boundary_mass"] < 6e-9]
    if not eligible:
        print("NO_NUMERICALLY_PROMISING_SURROGATE", flush=True)
        return
    record, snapshot = max(eligible, key=lambda pair: min(pair[0]["core_score"] - 0.99, pair[0]["worst_family_score"] - 0.985, pair[0]["worst_case_score"] - 0.98))
    lock_stream = (HERE / "official.lock").open("a")
    fcntl.flock(lock_stream, fcntl.LOCK_EX)
    if (HERE / "proof.json").is_file():
        prior = fc.read_json(HERE / "proof.json", 1024 * 1024)
        if prior["passed"] and prior["valid"] and prior["frozen_unchanged"]:
            print("EXISTING_OFFICIAL_PASS_PRESERVED", flush=True)
            return
        if prior["control_sha256"] == hashlib.sha256(snapshot.read_bytes()).hexdigest() and prior["frozen_unchanged"]:
            print("EXISTING_OFFICIAL_RESULT_PRESERVED", flush=True)
            return
    for reference_shape in (tuple(protocol["audit"]["spatial_grid"]), tuple(protocol["audit"]["refined_grid"])):
        reference_path = TRUSTED / "references" / (fc.reference_key(cases, reference_shape) + ".npz")
        if not reference_path.is_file():
            raise RuntimeError("Frozen evaluator reference cache missing; do not permit root writes")
    protected = [path for path in (ROOT / "evaluator").rglob("*") if path.is_file()]
    before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    control = HERE / "control.json"
    control.write_bytes(snapshot.read_bytes())
    command = [sys.executable, "-I", "-B", str(ROOT / "evaluator/evaluate.py"), "--artifact", str(control), "--output", str(HERE / "evaluation.json")]
    print("OFFICIAL_START", json.dumps(command), flush=True)
    with (HERE / "evaluation.log").open("w") as output:
        completed = subprocess.run(command, stdout=output, stderr=subprocess.STDOUT, cwd=HERE, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1"))
    result = fc.read_json(HERE / "evaluation.json", 1024 * 1024)
    dump(HERE / (snapshot.stem + ".evaluation.json"), result)
    after = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
    proof = {"role": "privileged_postdeadline_generation_only", "generation": 2, "fresh_success": False, "control_sha256": hashlib.sha256(control.read_bytes()).hexdigest(), "selected_snapshot": str(snapshot), "frozen_sha256": before, "frozen_unchanged": before == after, "command": command, "returncode": completed.returncode, "valid": result["valid"], "passed": result["passed"], "reason": result["reason"], "core_score": result["core_score"], "worst_family_score": result["worst_family_score"], "worst_case_score": result["worst_case_score"], "runtime_score": result["runtime_score"], "resource_score": result["resource_score"], "audits": result.get("audits"), "source_probe": record}
    dump(HERE / "proof.json", proof)
    dump(HERE / (snapshot.stem + ".proof.json"), proof)
    print("OFFICIAL_COMPLETE", json.dumps({key: value for key, value in proof.items() if key not in ["frozen_sha256", "source_probe"]}, allow_nan=False), flush=True)
    assert before == after


if __name__ == "__main__":
    main()
