import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

import copy
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
from simulator import DEFAULT, Dynamics, field_distance, independent, initial, integrate, modes
from search_api import parse_submission


def main():
    started = time.monotonic()
    folder = ROOT / "adversary" / "controls"
    folder.mkdir(exist_ok=True)
    payload = json.loads((ROOT / "attempts" / "baseline.json").read_text())
    controls = {"empty": "", "array": "[]", "nan": '{"schema_version":1,"parameters":NaN}', "duplicate": '{"schema_version":1,"schema_version":1,"parameters":{}}', "oversize": " " * 16385, "deep": "[" * 1200 + "]" * 1200}
    for name, field, value in (
        ("boolean", "dispersion", True), ("negative", "duration", -1),
        ("zero", "nonlinearity", 0), ("overflow", "dispersion", 1e300),
        ("nested", "cross", {}),
    ):
        modified = copy.deepcopy(payload)
        modified["parameters"][field] = value
        controls[name] = json.dumps(modified)
    modified = copy.deepcopy(payload)
    modified["claimed_score"] = 1
    controls["spoof_score"] = json.dumps(modified)
    modified = copy.deepcopy(payload)
    modified["parameters"]["grid"] = 64
    controls["extra_parameter"] = json.dumps(modified)
    controls["infinity"] = json.dumps(payload).replace(str(payload["parameters"]["dispersion"]), "1e309", 1)
    results = []
    for name, content in controls.items():
        destination = folder / (name + ".json")
        destination.write_text(content)
        process = subprocess.run(["/usr/bin/python3", "-B", str(ROOT / "evaluator" / "evaluate.py"), "--submission", str(destination)], capture_output=True, text=True, timeout=15)
        result = json.loads(process.stdout)
        assert not result["valid"] and not result["passed"] and result["core_score"] == 0, name
        results.append({"control": name, "reason": result["reason"], "passed": True})
    for name, target in (("missing", folder / "does_not_exist.json"), ("directory", folder)):
        process = subprocess.run(["/usr/bin/python3", "-B", str(ROOT / "evaluator" / "evaluate.py"), "--submission", str(target)], capture_output=True, text=True, timeout=15)
        result = json.loads(process.stdout)
        assert not result["valid"] and result["core_score"] == 0, name
        results.append({"control": name, "reason": result["reason"], "passed": True})
    invalid_utf = folder / "invalid_utf.json"
    invalid_utf.write_bytes(bytes([255, 254]))
    symbolic = folder / "symbolic.json"
    if not symbolic.is_symlink():
        symbolic.symlink_to(ROOT / "attempts" / "baseline.json")
    pipe = folder / "pipe.json"
    if not pipe.exists():
        os.mkfifo(pipe)
    for name, target in (("invalid_utf", invalid_utf), ("symlink", symbolic), ("fifo", pipe)):
        process = subprocess.run(["/usr/bin/python3", "-B", str(ROOT / "evaluator" / "evaluate.py"), "--submission", str(target)], capture_output=True, text=True, timeout=15)
        result = json.loads(process.stdout)
        assert not result["valid"] and result["core_score"] == 0, name
        results.append({"control": name, "reason": result["reason"], "passed": True})
    linear = dict(DEFAULT, nonlinearity=0.0)
    dynamics = Dynamics(linear, 32)
    simulated = integrate(linear)
    exact = np.array([dynamics.linear(initial(linear, 32), dynamics.propagator(fraction * linear["duration"])) for fraction in np.arange(1, 9) / 8])
    linear_error = float(np.max(field_distance(simulated, exact)))
    assert linear_error < 1e-11
    initial_state = initial(DEFAULT, 32)
    initial_leakage = float(np.sum(abs(initial_state[:, abs(modes(32)) > 3]) ** 2))
    assert initial_leakage < 1e-26
    dynamics = Dynamics(DEFAULT, 32)
    shifted = np.fft.fftshift(initial_state, axes=-1)
    density = [np.convolve(component, component[::-1].conj()) for component in shifted]
    direct = np.array([1j * DEFAULT["nonlinearity"] * np.convolve(density[component] + DEFAULT["cross"] * density[1 - component], shifted[component])[31:63] for component in (0, 1)])
    convolution_error = float(np.max(abs(direct - np.fft.fftshift(dynamics.nonlinear(initial_state), axes=-1))))
    assert convolution_error < 1e-12
    mild = dict(DEFAULT, nonlinearity=3.0, duration=0.3)
    truth, evaluations = independent(mild, 64, tolerance=1e-12)
    errors = [float(np.max(field_distance(integrate(mild, 64, steps), truth))) for steps in (32, 64, 128)]
    ratios = [errors[index] / errors[index + 1] for index in (0, 1)]
    assert min(ratios) > 12
    results.extend([
        {"control": "exact_linear_flow", "error": linear_error, "passed": True},
        {"control": "initial_band_limit", "leakage": initial_leakage, "passed": True},
        {"control": "dealiased_cubic_direct_convolution", "error": convolution_error, "passed": True},
        {"control": "fourth_order_against_DOP853", "errors": errors, "refinement_ratios": ratios, "passed": True},
    ])
    for source, destination in (("participant/workspace/simulator.py", "evaluator/hidden/simulator.py"), ("participant/workspace/search_api.py", "evaluator/hidden/search_api.py"), ("participant/input/protocol.json", "evaluator/hidden/protocol.json")):
        assert (ROOT / source).read_bytes() == (ROOT / destination).read_bytes()
    report = {"passed": True, "checks": results, "runtime_seconds": time.monotonic() - started}
    (ROOT / "adversary" / "validity_controls.json").write_text(json.dumps(report, indent=2) + "\n")
    for name in controls:
        (folder / (name + ".json")).unlink()
    invalid_utf.unlink()
    symbolic.unlink()
    pipe.unlink()
    folder.rmdir()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
