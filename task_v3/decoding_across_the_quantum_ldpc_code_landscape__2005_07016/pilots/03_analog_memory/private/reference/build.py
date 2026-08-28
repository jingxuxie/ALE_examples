from __future__ import annotations

import argparse
import hashlib
import json
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

from runtime import PAPER, PILOT, SOURCE

import ldpc
import numpy as np
import scipy

from codes import construct
from official import decode_case

sys.path.insert(0, str(PILOT / "private"))
from metrics import CORE, measure

CONFIGURATIONS = (
    ("toric3d", 3, 4, 0.045, 0.80),
    ("toric3d", 4, 6, 0.040, 0.85),
    ("lifted_product", 16, 3, 0.020, 0.55),
    ("lifted_product", 16, 5, 0.016, 0.55),
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stage_prestate():
    source = PAPER / "pilots/01_local_recovery/participant/workspace"
    destination = PILOT / "participant/workspace"
    legacy = destination / "legacy_2020"
    if not legacy.exists():
        shutil.copytree(source / "legacy_2020", legacy)
    baseline = destination / "binary_bp.py"
    if not baseline.exists():
        shutil.copyfile(source / "baseline.py", baseline)
    files = [baseline, *(path for path in legacy.rglob("*") if path.is_file())]
    record = {
        "prestate_commit": "74f86d3ef00f04bbb90a043dfef52e92a091f4d3",
        "provenance_owner": "main agent / pilot01 prestate research; no independent history reconstruction",
        "scope": "original binary BP+global OSD sources, plus a generic minimum-sum Python helper",
        "files": {str(path.relative_to(destination)): digest(path) for path in files},
    }
    (PILOT / "private/reference/prestate.json").write_text(json.dumps(record, indent=2) + "\n")


def make_case(configuration, shots, seed, identity):
    family, size, rounds, probability, noise = configuration
    checks, stabilizers, metachecks, logical_checks, source_paths = construct(family, size)
    generator = np.random.default_rng(seed)
    num_checks, num_qubits = checks.shape
    probabilities = probability * generator.uniform(0.75, 1.25, (rounds, num_qubits))
    offset = generator.uniform(-0.45, 0.45, (rounds, num_checks))
    gain = generator.uniform(0.8, 1.2, (rounds, num_checks))
    sigma = noise * generator.uniform(0.8, 1.2, (rounds, num_checks))
    increments = (generator.random((shots, rounds, num_qubits)) < probabilities).astype(np.uint8)
    cumulative = np.cumsum(increments, axis=1, dtype=np.int32) % 2
    syndrome_history = (cumulative @ checks.T % 2).astype(np.uint8)
    readout = offset + gain * (1 - 2 * syndrome_history.astype(float))
    readout += sigma * generator.normal(size=readout.shape)
    case = {
        "schema_version": np.array(1, dtype=np.int64),
        "case_id": np.array(identity),
        "checks": checks,
        "stabilizers": stabilizers,
        "metachecks": metachecks,
        "readout": readout,
        "mean0": offset + gain,
        "mean1": offset - gain,
        "sigma": sigma,
        "data_error_prob": probabilities,
        "terminal_syndrome": syndrome_history[:, -1].copy(),
    }
    truth = {
        "increments": increments,
        "syndrome_history": syndrome_history,
        "final_error": cumulative[:, -1].astype(np.uint8),
        "logical_checks": logical_checks,
    }
    return case, truth, source_paths


def provenance(source_paths):
    files = [
        SOURCE / "src/mqt/qecc/mod2.py",
        SOURCE / "src/mqt/qecc/analog_information_decoding/simulators/memory_experiment_v2.py",
        SOURCE / "src/mqt/qecc/analog_information_decoding/utils/simulation_utils.py",
        SOURCE / "src/mqt/qecc/analog_information_decoding/utils/data_utils.py",
        SOURCE / "LICENSE",
        *source_paths,
    ]
    return {
        "upstream_git_sha": subprocess.check_output(
            ["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True
        ).strip(),
        "upstream_files": {str(path.relative_to(SOURCE)): digest(path) for path in sorted(set(files))},
        "author_files": {name: digest(Path(__file__).parent / name) for name in (
            "build.py", "codes.py", "official.py", "runtime.py", "design.md"
        )},
        "metrics_sha256": digest(PILOT / "private/metrics.py"),
        "prestate_manifest_sha256": digest(PILOT / "private/reference/prestate.json"),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "ldpc_import_version": ldpc.__version__,
        "timing": "source-native time.process_time, seconds; not replay or host wall time",
        "reference": "MQT build_multiround_pcm and decode_multiround, terminal whole-window call",
        "adapter": "Gaussian calibration mapped to unit sigma; exact elimination of terminal fixed-zero columns; capture and verify full decoding",
        "weak": "hard ideal-terminal syndrome only; all inferred increments placed in last interval",
        "hard_window": "same official temporal decoder and search budget, sign-only observation likelihoods",
    }


def build_split(split, shots, root_seed, replace=False, post_attempt_fresh=False):
    destination = PILOT / "private/challenge_pool" / split
    manifest_path = destination / "manifest.json"
    if manifest_path.exists() and not replace:
        raise FileExistsError(f"{manifest_path} exists; use --replace explicitly")
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    source_paths = []
    for index, configuration in enumerate(CONFIGURATIONS):
        identity_digest = hashlib.sha256(f"{root_seed}:{split}:{index}".encode()).digest()
        seed = int.from_bytes(identity_digest[:8], "little")
        identity = identity_digest.hex()[:20]
        case, truth, paths = make_case(configuration, shots, seed, identity)
        source_paths.extend(paths)
        input_path = destination / f"{identity}.input.npz"
        truth_path = destination / f"{identity}.truth.npz"
        np.savez_compressed(input_path, **case)
        np.savez_compressed(truth_path, **truth)
        metrics = {}
        timings = {}
        outputs = {}
        for mode in ("weak", "hard_window", "reference"):
            prediction, elapsed = decode_case(case, mode)
            output_path = destination / f"{identity}.{mode}.npz"
            np.savez_compressed(output_path, **prediction)
            metrics[mode] = measure(case, truth, prediction)
            timings[mode] = elapsed
            outputs[mode] = output_path.name
            if mode in ("weak", "reference"):
                replay = PILOT / "private/reference" / f"replay_{mode}" / "answers"
                replay.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(output_path, replay / f"{identity}.npz")
            print(json.dumps({
                "split": split, "case": index, "family": configuration[0], "mode": mode,
                "logical": metrics[mode]["logical_accuracy"],
                "history": metrics[mode]["history_balanced_accuracy"], "seconds": elapsed,
            }), flush=True)
        records.append({
            "case_id": identity,
            "family": configuration[0],
            "configuration": list(configuration),
            "seed": seed,
            "shots": shots,
            "shape": list(case["readout"].shape),
            "qubits": case["checks"].shape[1],
            "metachecks": case["metachecks"].shape[0],
            "input": input_path.name,
            "truth": truth_path.name,
            "input_sha256": digest(input_path),
            "truth_sha256": digest(truth_path),
            "outputs": outputs,
            "metrics": metrics,
            "build_seconds": timings,
        })
    anchors = {}
    for family in sorted({record["family"] for record in records}):
        selected = [record for record in records if record["family"] == family]
        anchors[family] = {
            metric: {
                mode: float(np.mean([record["metrics"][mode][metric] for record in selected]))
                for mode in ("weak", "reference")
            } for metric in CORE
        }
    ready = all(
        values["reference"] - values["weak"] > 0.01
        for family in anchors.values() for values in family.values()
    )
    ready = ready and shots >= 128 and all(
        record["metrics"]["reference"]["logical_accuracy"] > 0.9 for record in records
    )
    manifest = {
        "schema_version": 1, "split": split, "root_seed": root_seed, "ready": ready,
        "cases": records, "anchors": anchors, "provenance": provenance(source_paths),
        "selection": "all generated shots retained; no truth-based filtering",
        "generation_phase": "post_attempt_fresh" if post_attempt_fresh else "initial",
        "readiness_gate": "128 independent shots per case, reference raw logical accuracy >0.9 in every case, positive family headroom",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"split": split, "ready": ready, "anchors": anchors}), flush=True)
    if not ready:
        raise RuntimeError("Insufficient reference headroom; inspect pilot before generating later splits")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=("pilot", "challenge", "holdout"), default="pilot")
    parser.add_argument("--shots", type=int)
    parser.add_argument("--seed", type=int, default=731926401)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--replace", action="store_true")
    arguments = parser.parse_args()
    if arguments.split == "holdout" and not arguments.fresh:
        parser.error("Holdout is reserved; use --fresh only after inspecting the initial attempt")
    stage_prestate()
    root_seed = secrets.randbits(63) if arguments.fresh else arguments.seed
    if arguments.shots is not None and not 4 <= arguments.shots <= 128:
        parser.error("--shots must be in [4, 128]")
    public = PILOT / "participant/input/example.npz"
    if not public.exists():
        public.parent.mkdir(parents=True, exist_ok=True)
        example, _, _ = make_case(CONFIGURATIONS[0], 2, 91283517, "schema-example")
        np.savez_compressed(public, **example)
    build_split(
        arguments.split, arguments.shots or 128, root_seed, arguments.replace,
        post_attempt_fresh=arguments.split == "holdout" and arguments.fresh,
    )


if __name__ == "__main__":
    main()
