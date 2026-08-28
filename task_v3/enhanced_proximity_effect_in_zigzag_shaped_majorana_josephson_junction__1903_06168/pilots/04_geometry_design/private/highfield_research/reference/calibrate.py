"""Private fixed-reference calibration for the explicit high-field request."""

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import pickle
import resource
import signal
import subprocess
import sys
import time
import traceback
import zipfile


HERE = Path(__file__).resolve().parent
INPUT = HERE.parent
PRIVATE = HERE.parents[1]
PHYSICS = PRIVATE / "reference" / "physics.py"
CPUS = [40, 42, 44, 46, 48, 50]
CONTROLLER_CPU = 51
EXPECTED_MEMBER_SHA256 = "a4c1a00cf91599bc822b9a7e7a15de9b8693045be6c09b262350478ad3ed548a"
SCOPE = "private narrowed-high-field adaptation diagnostic; no initial score, acceptance change, or demonstrated solver capability gap"
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    if not path.resolve().is_relative_to(HERE):
        raise ValueError("Writes must remain within highfield_research/reference")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def physics_module():
    specification = importlib.util.spec_from_file_location("highfield_audit_physics", PHYSICS)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def usage():
    measured = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "affinity": sorted(os.sched_getaffinity(0)),
        "cpu_seconds": measured.ru_utime + measured.ru_stime,
        "peak_rss_kib": measured.ru_maxrss,
        "address_space_limit_bytes": resource.getrlimit(resource.RLIMIT_AS)[0],
    }


def source_fingerprint(physics, request, masks):
    import numpy as np

    class ArrayUnpickler(pickle.Unpickler):
        def find_class(self, module, name):
            allowed = {
                ("numpy.core.multiarray", "_reconstruct"): np.core.multiarray._reconstruct,
                ("numpy.core.multiarray", "scalar"): np.core.multiarray.scalar,
                ("numpy", "ndarray"): np.ndarray, ("numpy", "dtype"): np.dtype,
            }
            if (module, name) not in allowed:
                raise pickle.UnpicklingError(f"Disallowed pickle global: {module}.{name}")
            return allowed[module, name]

    provenance = read(INPUT / "provenance.json")
    archive = PRIVATE / "reference" / "author_code.zip"
    with zipfile.ZipFile(archive) as handle:
        payload = handle.read(provenance["source_member"])
    source_digest = hashlib.sha256(payload).hexdigest()
    history = ArrayUnpickler(io.BytesIO(payload)).load()
    source_masks = history["masks_by_epoch"][provenance["epoch"]]
    archived = {"sc_top": source_masks["sc_top"], "sc_bottom": source_masks["sc_bot"]}
    shape = (request["grid"]["ny"], request["grid"]["nx"])
    original = physics.original_zigzag(request)
    checks = {
        "source_member_is_homogeneous_filtered": provenance["source_member"] == "code/data/homogeneous_filtered.p",
        "source_member_sha256_matches_prior_verified_inventory": source_digest == EXPECTED_MEMBER_SHA256,
        "source_epoch_is_800": provenance["epoch"] == 800,
        "source_shapes_match_request": all(np.shape(value) == shape for value in archived.values()),
        "strong_equals_unmodified_source_epoch": all(np.array_equal(masks["strong"][name], archived[name]) for name in archived),
        "weak_equals_original_zigzag": all(np.array_equal(masks["weak"][name], original[name]) for name in original),
        "dimension_matches_source": 4 * int(np.size(archived["sc_top"])) == 4 * shape[0] * shape[1],
    }
    record = {
        "supplied_provenance": provenance, "source_shape": list(np.shape(archived["sc_top"])),
        "dimension": 4 * shape[0] * shape[1], "source_epoch_count": len(history["masks_by_epoch"]),
        "archive_path": str(archive), "archive_sha256": sha256(archive),
        "source_member_sha256": source_digest,
        "expected_source_member_sha256": EXPECTED_MEMBER_SHA256,
        "expected_hash_provenance": "../../counterexample_research/manifest.json existing_reference; same previously verified author archive member",
        "input_sha256": {name: sha256(INPUT / name) for name in ("request.json", "strong.json", "scenarios.json", "provenance.json")},
        "physics_path": str(PHYSICS), "physics_sha256": sha256(PHYSICS),
        "calibration_script_sha256": sha256(Path(__file__)),
        "geometry_sha256": {label: physics.geometry_digest(value) for label, value in masks.items()},
        "checks": checks, "verified": all(checks.values()),
    }
    record["fingerprint_sha256"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
    return record


def worker(arguments):
    os.sched_setaffinity(0, {arguments.cpu})
    resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (600, 601))
    import numpy as np
    import scipy
    from threadpoolctl import threadpool_info, threadpool_limits

    threadpool_limits(limits=1)
    physics = physics_module()
    request = read(INPUT / "request.json")
    scenarios = read(INPUT / "scenarios.json")
    geometry = request["baseline_geometry"] if arguments.worker == "weak" else read(INPUT / "strong.json")["geometry"]
    masks = physics.geometry_arrays(request, geometry)
    runtime = read(HERE / "runtime.json")
    output = HERE / "measurements" / f"{arguments.worker}_scenario_{arguments.scenario}.json"
    started = time.monotonic()
    record = {
        "label": arguments.worker, "scenario_index": arguments.scenario, "scenario": scenarios[arguments.scenario],
        "status": "starting", "complete": False, "started_utc": stamp(),
        "manufacturing": physics.feasibility(request, masks), "physical_feasibility": None,
        "geometry_sha256": physics.geometry_digest(masks), "physics_sha256": sha256(PHYSICS),
        "numpy_version": np.__version__, "scipy_version": scipy.__version__, "threadpools": threadpool_info(),
        "momenta_rad": [], "gaps_mev": [], "low_energy_mev": [], "low_energy_seconds": [], **usage(),
    }
    save(output, record)
    try:
        model = physics.ForwardModel(request, masks, scenarios[arguments.scenario])
        record.update(dimension=model.dimension, construction_seconds=time.monotonic() - started)
        topology_started = time.monotonic()
        record["class_d_invariant"] = model.topological_invariant()
        record["topology_seconds"] = time.monotonic() - topology_started
        record["topology_method"] = "unchanged independent Pfaffian at k=0 and pi; not inferred from sampled gaps"
        record["status"] = "sampling"
        save(output, record)
        for momentum in np.linspace(0.0, math.pi, 51):
            if time.monotonic() >= runtime["deadline_monotonic"]:
                raise TimeoutError("Shared 600-second numeric wall budget exhausted")
            solve_started = time.monotonic()
            energies, states = model.low_energy(float(momentum))
            del states
            record["momenta_rad"].append(float(momentum))
            record["gaps_mev"].append(float(np.min(np.abs(energies))))
            record["low_energy_mev"].append(energies.tolist())
            record["low_energy_seconds"].append(time.monotonic() - solve_started)
            record.update(wall_seconds=time.monotonic() - started, **usage())
            save(output, record)
        minimum = int(np.argmin(record["gaps_mev"]))
        record.update(status="complete", complete=True, gap_mev=record["gaps_mev"][minimum], momentum_rad=record["momenta_rad"][minimum])
        record["physical_feasibility"] = bool(record["manufacturing"]["valid"] and record["class_d_invariant"] == -1 and record["gap_mev"] > 1e-5)
    except TimeoutError as error:
        record.update(status="incomplete_timeout", error=str(error))
    except Exception as error:
        record.update(status="measurement_error", error=repr(error), traceback=traceback.format_exc())
    finally:
        record.update(finished_utc=stamp(), wall_seconds=time.monotonic() - started, **usage())
        save(output, record)


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()


def aggregate(label, manufacturing):
    measurements = []
    for scenario in range(3):
        path = HERE / "measurements" / f"{label}_scenario_{scenario}.json"
        measurements.append(read(path) if path.exists() else {"scenario_index": scenario, "status": "incomplete_no_output", "complete": False})
    complete = all(row.get("complete") and len(row.get("gaps_mev", [])) == 51 for row in measurements)
    record = {
        "complete": bool(complete), "manufacturing": manufacturing, "physical_feasibility": None,
        "robust_gap_mev": None, "mean_gap_mev": None, "worst_gap_mev": None, "measurements": measurements,
    }
    if complete:
        gaps = [row["gap_mev"] for row in measurements]
        record.update(
            physical_feasibility=bool(manufacturing["valid"] and all(row["physical_feasibility"] for row in measurements)),
            mean_gap_mev=sum(gaps) / 3, worst_gap_mev=min(gaps), robust_gap_mev=0.5 * sum(gaps) / 3 + 0.5 * min(gaps),
        )
    return record


def controller(arguments):
    if not set(CPUS + [CONTROLLER_CPU]).issubset(os.sched_getaffinity(0)):
        raise RuntimeError("Requested CPUs 40–51 are unavailable; no alternative affinity is allowed")
    os.sched_setaffinity(0, {CONTROLLER_CPU})
    physics = physics_module()
    request = read(INPUT / "request.json")
    scenarios = read(INPUT / "scenarios.json")
    if len(scenarios) != 3:
        raise ValueError("Exactly three supplied scenarios are required")
    masks = {"weak": physics.geometry_arrays(request, request["baseline_geometry"]), "strong": physics.load_result(request, INPUT / "strong.json")}
    fingerprint = source_fingerprint(physics, request, masks)
    save(HERE / "fingerprint.json", fingerprint)
    if not fingerprint["verified"]:
        raise ValueError("The supplied masks did not verify against the archived source and original zigzag")
    manufacturing = {label: physics.feasibility(request, value) for label, value in masks.items()}
    for label, value in masks.items():
        save(HERE / f"{label}.json", {"schema_version": 1, "request_id": request["request_id"], "geometry": physics.geometry_json(value)})
    started = time.monotonic()
    runtime = {
        "started_utc": stamp(), "started_monotonic": started, "deadline_monotonic": started + arguments.wall_seconds,
        "numeric_wall_budget_seconds": arguments.wall_seconds, "worker_cpus": CPUS,
        "controller_affinity": sorted(os.sched_getaffinity(0)), "max_workers": 6, "blas_threads_per_worker": 1,
        "worker_address_space_limit_gib": 3, "momentum_points": 51, "scenario_count": 3, "dimension": fingerprint["dimension"],
        "command": [sys.executable, "-B", str(Path(__file__).resolve()), "--wall-seconds", str(arguments.wall_seconds)],
    }
    save(HERE / "runtime.json", runtime)
    active = []
    jobs = [(label, scenario) for label in ("weak", "strong") for scenario in range(3)]
    try:
        for (label, scenario), cpu in zip(jobs, CPUS):
            output = HERE / "measurements" / f"{label}_scenario_{scenario}.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            log = open(output.with_suffix(".log"), "w", encoding="utf-8")
            command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", label, "--scenario", str(scenario), "--cpu", str(cpu)]
            process = subprocess.Popen(command, cwd=HERE, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            active.append((process, output, log))
            print(json.dumps({"event": "worker_started", "label": label, "scenario": scenario, "cpu": cpu, "pid": process.pid}), flush=True)
        while any(process.poll() is None for process, _, _ in active) and time.monotonic() < runtime["deadline_monotonic"]:
            time.sleep(0.5)
    finally:
        for process, output, log in active:
            timed_out = process.poll() is None
            stop(process)
            log.close()
            row = read(output) if output.exists() else {"complete": False, "physical_feasibility": None}
            if not row.get("complete"):
                row.update(status="incomplete_timeout" if timed_out else row.get("status", "worker_exit_without_output"), physical_feasibility=None)
            row["worker_returncode"] = process.returncode
            save(output, row)
    records = {label: aggregate(label, manufacturing[label]) for label in masks}
    complete = all(record["complete"] for record in records.values())
    delta = records["strong"]["robust_gap_mev"] - records["weak"]["robust_gap_mev"] if complete else None
    unchanged = sha256(PHYSICS) == fingerprint["physics_sha256"] and all(sha256(INPUT / name) == digest for name, digest in fingerprint["input_sha256"].items())
    ready = bool(complete and unchanged and all(record["physical_feasibility"] for record in records.values()) and delta > 1e-4)
    calibration = {
        "schema_version": 1, "request_id": request["request_id"], "scope": SCOPE,
        "finished": True, "complete": complete, "ready": ready, "finished_utc": stamp(),
        "numeric_wall_seconds": time.monotonic() - started, "momentum_points": 51, "scenario_count": 3,
        "dimension": runtime["dimension"], "fingerprint_sha256": fingerprint["fingerprint_sha256"], "source_and_inputs_unchanged": unchanged,
        "robust_gap_definition": "0.5 * mean(scenario gaps) + 0.5 * min(scenario gaps)",
        "physical_feasibility_definition": "unchanged manufacturing valid AND all three independent Q=-1 AND each full-51 gap > 1e-5 meV",
        "incomplete_is_failure": False,
        "normalization": {
            "ready": ready, "formula": "(robust_gap_mev - weak.robust_gap_mev) / (strong.robust_gap_mev - weak.robust_gap_mev)",
            "clipped": False, "weak_anchor": 0.0 if ready else None, "strong_anchor": 1.0 if ready else None,
            "strong_minus_weak_mev": delta, "minimum_anchor_separation_mev": 1e-4,
        }, **records,
    }
    save(HERE / "calibration.json", calibration)
    print(json.dumps({key: value for key, value in calibration.items() if key not in ("weak", "strong")}, indent=2), flush=True)
    for label, record in records.items():
        print(json.dumps({"label": label, "complete": record["complete"], "physical_feasibility": record["physical_feasibility"], "robust_gap_mev": record["robust_gap_mev"]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wall-seconds", type=float, default=600.0)
    parser.add_argument("--worker", choices=("weak", "strong"))
    parser.add_argument("--scenario", type=int, choices=range(3))
    parser.add_argument("--cpu", type=int, choices=CPUS)
    arguments = parser.parse_args()
    if not 0 < arguments.wall_seconds <= 600:
        parser.error("The numeric wall budget must be at most 600 seconds")
    if arguments.worker:
        worker(arguments)
        return
    if (HERE / "calibration.json").exists() or (HERE / "runtime.json").exists():
        parser.error("Existing calibration run detected; refusing to overwrite measurements")
    try:
        controller(arguments)
    except Exception as error:
        save(HERE / "calibration.json", {
            "scope": SCOPE, "finished": True, "complete": False, "ready": False, "incomplete_is_failure": False,
            "error": repr(error), "traceback": traceback.format_exc(),
            "weak": {"robust_gap_mev": None, "physical_feasibility": None, "complete": False},
            "strong": {"robust_gap_mev": None, "physical_feasibility": None, "complete": False},
        })
        raise


if __name__ == "__main__":
    main()
