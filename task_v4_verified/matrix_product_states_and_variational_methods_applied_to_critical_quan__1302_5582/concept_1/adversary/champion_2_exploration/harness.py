import os
import sys

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import resource
import signal
import subprocess
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "snapshots/trusted"))
sys.path.insert(0, str(ROOT / "snapshots/teacher"))
from trusted_contractor import load_mps, measure
from observables import diagnostics


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    sources = {}
    for path in sorted((ROOT / "snapshots").rglob("*")):
        if path.is_file():
            sources[str(path.relative_to(ROOT))] = sha256(path)
    for path in sorted(ROOT.glob("*.py")):
        sources[path.name] = sha256(path)
    write_json(ROOT / "SOURCE_HASHES.json", sources)


def base_request(label, mass, sector, length=64):
    return {
        "version": 1, "case_id": label, "seed": 1302558202,
        "n_sites": length, "local_dim": 14, "bond_cap": 24,
        "sector": sector, "omega": [0.55] * length,
        "mass2": [mass] * length, "lambda4": [0.05] * length,
        "field": [0.0] * length, "coupling": [1.5] * (length - 1),
        "budget_seconds": 40.0, "wall_seconds": 120.0,
    }


def preserve_request(request, family, motivation, domain="advertised_contract_v2"):
    case = request["case_id"]
    path = ROOT / "requests" / (case + ".json")
    if path.exists() and json.loads(path.read_text()) != request:
        raise ValueError("Refusing to overwrite a different request")
    write_json(path, request)
    write_json(ROOT / "requests" / (case + ".provenance.json"), {
        "family": family, "motivation": motivation, "domain": domain,
        "critical_mass_certified": False, "request_sha256": sha256(path),
        "finite_hamiltonian": "P q^k P from padded d+4 oscillator; no continuum energy reference",
    })


def initial_requests():
    for label, mass in (("m020", -0.020), ("m034", -0.034)):
        for sector in ("even", "odd"):
            request = base_request("uniform_" + label + "_" + sector, mass, sector)
            preserve_request(request, "finite_basis_mass_scan",
                             "Measure attained parity splitting and entanglement at low omega; masses are search coordinates only")


def structured_requests(center):
    generator = np.random.default_rng(1302558202)
    length = 64
    coordinate = np.linspace(0, 1, length)
    request = base_request("disordered_weaklink_odd", center, "odd")
    request["mass2"] = (center + 0.006 * np.sin(6 * np.pi * coordinate)
                        + generator.uniform(-0.003, 0.003, length)).tolist()
    request["coupling"] = generator.uniform(0.8, 1.5, length - 1).tolist()
    for bond in (15, 32, 47):
        request["coupling"][bond] = 0.05
    preserve_request(request, "disordered_parity_transfer", "Four weakly connected, inequivalent regions; odd parity must allocate globally")
    request = base_request("soft_islands_odd", center, "odd")
    request["mass2"] = (0.005 - 0.047 * np.exp(-((coordinate - 0.19) / 0.10) ** 4)
                        - 0.049 * np.exp(-((coordinate - 0.80) / 0.11) ** 4)).tolist()
    request["coupling"][31] = 0.05
    preserve_request(request, "separated_soft_islands", "Two near-degenerate soft islands separated by a positive-mass bridge; potential odd-excitation localization trap")
    request = base_request("multiregion_tilt_any", center - 0.012, "any")
    request["mass2"] = (center - 0.012 + 0.004 * np.cos(8 * np.pi * coordinate)).tolist()
    request["field"] = np.repeat([0.0011, -0.0015, 0.0013, -0.0009], 16).tolist()
    for bond in (15, 31, 47):
        request["coupling"][bond] = 0.05
    preserve_request(request, "competing_field_regions", "Four sign-competing weakly connected domains with full nonzero-field objective")
    request = base_request("random_crossover_any", center, "any")
    request["mass2"] = (center + generator.uniform(-0.009, 0.009, length)).tolist()
    request["omega"] = generator.uniform(0.55, 0.75, length).tolist()
    request["coupling"] = generator.uniform(0.7, 1.5, length - 1).tolist()
    request["field"] = (0.001 * np.cos(4 * np.pi * coordinate) + generator.uniform(-0.0002, 0.0002, length)).tolist()
    preserve_request(request, "random_finite_crossover", "Spatial mass, basis, spring disorder and competing weak fields")
    request = base_request("quartic_regions_odd", center - 0.017, "odd", 48)
    request["lambda4"] = np.repeat([0.05, 0.10, 0.07, 0.14], 12).tolist()
    request["mass2"] = np.repeat([center - 0.001, center - 0.028, center - 0.014, center - 0.051], 12).tolist()
    request["coupling"] = [1.0] * 47
    for bond in (11, 23, 35):
        request["coupling"][bond] = 0.05
    preserve_request(request, "heterogeneous_quartic_parity", "Different quartic regions at distinct finite-basis crossover offsets")
    request = base_request("cutoff_control_odd", center, "odd")
    request["local_dim"] = 12
    request["bond_cap"] = 20
    request["mass2"] = (center + 0.006 * np.cos(2 * np.pi * coordinate)).tolist()
    request["coupling"][20] = 0.05
    request["coupling"][42] = 0.08
    preserve_request(request, "lower_cap_parity_allocation", "Three inequivalent weakly connected regions at a smaller bond cap; no large-size extension")


def limits(cpu):
    resource.setrlimit(resource.RLIMIT_CPU, (int(cpu + 5), int(cpu + 8)))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def launch(case, solver, budget, seed=None, run_label=None):
    original_path = ROOT / "requests" / (case + ".json")
    original = json.loads(original_path.read_text())
    label = run_label or solver + "_" + str(int(budget))
    directory = ROOT / "runs" / case / label
    directory.mkdir(parents=True, exist_ok=True)
    result_path = directory / "result.json"
    if result_path.exists():
        return json.loads(result_path.read_text())
    request = dict(original, budget_seconds=budget,
                   wall_seconds=120.0 if budget <= 40 else max(300.0, 4 * budget))
    request_path = directory / "request.json"
    state_path = directory / "state.npz"
    write_json(request_path, request)
    if solver == "teacher":
        if seed is None:
            raise ValueError("Teacher needs a measured seed")
        command = [sys.executable, "-B", str(ROOT / "teacher.py"), "--request", str(request_path),
                   "--output", str(state_path), "--seed", str(Path(seed).resolve())]
    else:
        command = [sys.executable, "-B", str(ROOT / "snapshots" / solver / "solve.py"),
                   "--request", str(request_path), "--output", str(state_path)]
    environment = dict(os.environ, MPS_DEBUG="1")
    started = time.monotonic()
    timed_out = False
    with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=stdout,
                                   stderr=stderr, env=environment, start_new_session=True,
                                   preexec_fn=lambda: limits(budget))
        while True:
            waited, status, usage = os.wait4(process.pid, os.WNOHANG)
            if waited:
                break
            if time.monotonic() - started > request["wall_seconds"] + 30:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                _, status, usage = os.wait4(process.pid, 0)
                break
            time.sleep(0.05)
        process.returncode = os.waitstatus_to_exitcode(status)
    result = {
        "case_id": case, "solver": solver, "budget_seconds": budget,
        "mode": "private source-native direct child, not frozen evaluator certification",
        "command": command, "returncode": process.returncode,
        "cpu_seconds": usage.ru_utime + usage.ru_stime,
        "wall_seconds": time.monotonic() - started,
        "peak_rss_kib": usage.ru_maxrss, "outer_wall_timeout": timed_out,
        "source_hash_manifest_sha256": sha256(ROOT / "SOURCE_HASHES.json"),
        "harness_sha256": sha256(Path(__file__)),
        "run_label": label,
        "request_sha256": sha256(request_path), "original_request_sha256": sha256(original_path),
        "ground_energy_certified": False,
    }
    if seed is not None:
        result["seed_path"] = str(Path(seed).resolve())
        result["seed_sha256"] = sha256(Path(seed))
    if state_path.exists():
        try:
            tensors = load_mps(state_path, original)
            result["measurement"] = measure(tensors, original)
            result["physical_validity"] = True
            result["state_sha256"] = sha256(state_path)
            result["state_bytes"] = state_path.stat().st_size
            result["diagnostics"] = diagnostics(tensors, original, result["measurement"]["energy"])
        except Exception as error:
            result["physical_validity"] = False
            result["measurement_error"] = repr(error)
    else:
        result["physical_validity"] = False
    result["resource_observation_valid"] = (process.returncode == 0 and not timed_out
        and result["cpu_seconds"] <= budget and result["wall_seconds"] <= request["wall_seconds"])
    write_json(result_path, result)
    summary = {key: result[key] for key in ("case_id", "solver", "cpu_seconds", "wall_seconds", "returncode", "physical_validity")}
    if "measurement" in result:
        summary.update(result["measurement"])
        summary["entropy"] = result["diagnostics"]["center_entropy"]
        summary["cutoff"] = result["diagnostics"]["max_cutoff_edge_population"]
    print(json.dumps(summary), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("initial", "structured", "run", "manifest"))
    parser.add_argument("--center", type=float, default=-0.026)
    parser.add_argument("--cases", nargs="+")
    parser.add_argument("--solvers", nargs="+", default=["v3", "v4"])
    parser.add_argument("--budget", type=float, default=40)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed")
    parser.add_argument("--run-label")
    args = parser.parse_args()
    if args.action == "initial":
        initial_requests()
    elif args.action == "structured":
        structured_requests(args.center)
    elif args.action == "run":
        jobs = [(case, solver) for case in args.cases for solver in args.solvers]
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(launch, case, solver, args.budget, args.seed, args.run_label) for case, solver in jobs]
            for future in concurrent.futures.as_completed(futures):
                future.result()
    else:
        manifest()


if __name__ == "__main__":
    main()
