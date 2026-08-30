import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
sys.path.insert(0, str(ROOT / "evaluator"))

import numpy as np
import scipy
import exact
import evaluate


def run_evaluator(path, output, cwd=None):
    environment = os.environ.copy()
    if cwd is not None:
        environment["PYTHONPATH"] = str(cwd)
    process = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "evaluator" / "evaluate.py"), str(path), "--output", str(output)],
                             capture_output=True, text=True, timeout=195, cwd=cwd, env=environment)
    if process.returncode:
        raise AssertionError(process.stderr)
    report = json.loads(process.stdout)
    assert report == json.loads(output.read_text())
    assert {"core", "worst_family", "resource", "pass", "valid", "reason"} <= set(report)
    return report


def main():
    started = time.monotonic()
    controls = ROOT / "adversary" / "controls"
    outputs = controls / "reports"
    outputs.mkdir(exist_ok=True)
    champion_path = ROOT / "adversary" / "champions" / "witness.json"
    witness = json.loads(champion_path.read_text())
    protocol = json.loads((ROOT / "participant" / "input" / "protocol.json").read_text())
    public_bytes = (ROOT / "participant" / "workspace" / "exact.py").read_bytes()
    hidden_bytes = (ROOT / "evaluator" / "hidden" / "exact.py").read_bytes()
    assert public_bytes == hidden_bytes
    assert (ROOT / "participant" / "input" / "protocol.json").read_bytes() == (ROOT / "evaluator" / "hidden" / "protocol.json").read_bytes()
    for source in list((ROOT / "participant").rglob("*.py")) + list((ROOT / "evaluator").rglob("*.py")):
        ast.parse(source.read_text(), filename=str(source))
    champion = run_evaluator(champion_path, ROOT / "adversary" / "champions" / "evaluation.json")
    assert champion["valid"] and champion["pass"], champion["reason"]
    assert champion["resource"]["diagonalizations"] == 33
    repeated = run_evaluator(champion_path, outputs / "repeated_champion.json")
    for key in ("core", "worst_family", "base", "families", "members"):
        assert champion[key] == repeated[key], key
    baseline = run_evaluator(ROOT / "adversary" / "baseline_witness.json", ROOT / "adversary" / "baseline_evaluation.json")
    assert baseline["valid"] and not baseline["pass"]
    assert baseline["resource"]["diagonalizations"] == 33
    sidecar_witness = controls / "sidecars" / "witness.json"
    sidecar_witness.write_text(json.dumps(witness))
    sidecar = run_evaluator(sidecar_witness, outputs / "sidecars_ignored.json", cwd=sidecar_witness.parent)
    assert sidecar["pass"] and sidecar["core"] == champion["core"]
    reversed_witness = {**witness, "orientation": -witness["orientation"]}
    reverse_path = controls / "opposite_orientation.json"
    reverse_path.write_text(json.dumps(reversed_witness))
    opposite = run_evaluator(reverse_path, outputs / "opposite_orientation.json")
    assert opposite["valid"] and not opposite["pass"]
    assert abs(opposite["core"] + champion["core"]) < 1e-14
    invalid_objects = {
        "empty_object": {}, "list_root": [witness], "missing_field": {"schema_version": 1, "orientation": -1},
        "extra_score": {**witness, "core": 1.0},
        "code_payload": {**witness, "code": "__import__('os').system('false')"},
        "path_payload": {**witness, "fields": "../../authoring/physics.py"},
        "short_fields": {**witness, "fields": witness["fields"][:10]},
        "long_fields": {**witness, "fields": witness["fields"] + [0]},
        "bool_field": {**witness, "fields": [True] + witness["fields"][1:]},
        "string_field": {**witness, "fields": ["0.0"] + witness["fields"][1:]},
        "nested_field": {**witness, "fields": [[0.0]] + witness["fields"][1:]},
        "null_field": {**witness, "fields": [None] + witness["fields"][1:]},
        "bool_orientation": {**witness, "orientation": True},
        "float_orientation": {**witness, "orientation": -1.0},
        "zero_orientation": {**witness, "orientation": 0},
        "bool_version": {**witness, "schema_version": True},
        "float_version": {**witness, "schema_version": 1.0},
        "wrong_version": {**witness, "schema_version": 2},
        "zero_field": {**witness, "fields": [0.0] * 12},
        "uniform_field": {**witness, "fields": [1.0] * 12},
        "symmetry": {**witness, "fields": np.linspace(-5.5, 5.5, 12).tolist()},
        "nonzero_mean": {**witness, "fields": [value + 0.01 for value in witness["fields"]]},
        "out_of_bound": {**witness, "fields": [value * 10 for value in witness["fields"]]},
        "low_rms": {**witness, "fields": [value * 0.001 for value in witness["fields"]]},
        "duplicate_fields": {**witness, "fields": [-1.0, -1.0, -2.0, -3.0, -4.0, -5.0, 1.0, 1.0, 2.0, 3.0, 4.0, 5.0]}
    }
    raw = {name: json.dumps(value) for name, value in invalid_objects.items()}
    raw.update({"duplicate_key": '{"schema_version":1,"schema_version":1,"fields":[],"orientation":-1}',
                "nan": '{"schema_version":1,"fields":[NaN],"orientation":-1}',
                "infinity": '{"schema_version":1,"fields":[Infinity],"orientation":-1}',
                "overflow_float": json.dumps(witness).replace(str(witness["fields"][0]), "1e999", 1),
                "huge_integer": json.dumps(witness).replace(str(witness["fields"][0]), "9" * 1000, 1),
                "trailing_code": json.dumps(witness) + "\n__import__('os').system('false')",
                "malformed": "{not json", "empty_file": "", "oversized": " " * 16385,
                "deep_nesting": "[" * 2000 + "0" + "]" * 2000})
    rejected = []
    for name, contents in raw.items():
        path = controls / (name + ".json")
        path.write_text(contents)
        report = run_evaluator(path, outputs / (name + ".json"))
        assert not report["valid"] and not report["pass"], name
        assert report["resource"]["diagonalizations"] == 0, name
        rejected.append({"case": name, "reason": report["reason"]})
    invalid_utf8 = controls / "invalid_utf8.json"
    invalid_utf8.write_bytes(b"\xff\xfe\x00")
    special_paths = {"invalid_utf8": invalid_utf8, "directory": controls, "missing": controls / "not_present.json"}
    link = controls / "linked_witness.json"
    if not link.is_symlink():
        link.symlink_to(champion_path)
    special_paths["symlink"] = link
    fifo = controls / "witness.fifo"
    if not fifo.exists():
        os.mkfifo(fifo)
    special_paths["fifo"] = fifo
    for name, path in special_paths.items():
        report = run_evaluator(path, outputs / (name + ".json"))
        assert not report["valid"] and not report["pass"], name
        assert report["resource"]["diagonalizations"] == 0, name
        rejected.append({"case": name, "reason": report["reason"]})
    fifo.unlink()
    link.unlink()
    hidden_protocol_before = (ROOT / "evaluator" / "hidden" / "protocol.json").read_bytes()
    (controls / "sidecars" / "protocol.json").write_text('{"targets":{"core":-999}}')
    unchanged = run_evaluator(sidecar_witness, outputs / "sidecar_protocol_ignored.json", cwd=sidecar_witness.parent)
    assert unchanged["core"] == champion["core"] and unchanged["targets"] == protocol["targets"]
    assert hidden_protocol_before == (ROOT / "evaluator" / "hidden" / "protocol.json").read_bytes()
    ladder = exact.proxy_statistics(np.arange(924, dtype=float))
    assert ladder["rank_r"] == 1.0 and ladder["proxy_r"] == 1.0
    assert ladder["rank_ratio_count"] == 306
    assert [window["nearest_rank"] for window in ladder["windows"]] == [452, 461, 471]
    assert [window["start"] for window in ladder["windows"]] == [388, 397, 407]
    assert all(window["ratio_count"] == 126 for window in ladder["windows"])
    for spectrum in (np.concatenate(([-1e8], np.arange(923))), np.concatenate((np.arange(923), [1e8]))):
        boundary = exact.proxy_statistics(spectrum)
        assert all(window["start"] in (0, 796) for window in boundary["windows"])
    root_source = ROOT.parent / "authoring" / "physics.py"
    specification = importlib.util.spec_from_file_location("independent_root_physics", root_source)
    root_physics = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(root_physics)
    fields = np.array(witness["fields"])
    matrix = exact.hamiltonian(fields)
    assert np.max(np.abs(matrix - root_physics.hamiltonian(fields))) == 0.0
    assert np.max(np.abs(matrix - matrix.T)) == 0.0
    assert abs(float(np.trace(matrix)) + 252) < 1e-9
    root_result = root_physics.observables(fields, vectors=False, full=True, driver="evd")
    public_result = exact.proxy_statistics(root_result["energies"])
    assert abs(public_result["rank_r"] - root_result["r"]) < 1e-12
    alternative = exact.assess(witness, protocol, driver="evd")
    core_error = abs(alternative["core"] - champion["core"])
    member_error = max(abs(reference["difference"] - tested["difference"])
                       for reference, tested in zip(champion["members"], alternative["members"]))
    assert core_error < 1e-9 and member_error < 1e-8
    assert alternative["pass"]
    base_energies = exact.spectrum(fields)
    symmetry_errors = [float(np.max(np.abs(base_energies - exact.spectrum(profile))))
                       for profile in (np.roll(fields, 3), fields[::-1], -fields)]
    assert max(symmetry_errors) < 1e-10
    (ROOT / "adversary" / "champions" / "evd_evaluation.json").write_text(json.dumps(alternative, indent=2) + "\n")
    summary = {"passed": True, "seconds": time.monotonic() - started, "malformed_controls": rejected,
               "malformed_control_count": len(rejected), "repeat_exact": True, "sidecars_ignored": True,
               "isolated_runner_with_hostile_pythonpath": True,
               "opposite_orientation_rejected": True, "uniform_ladder_and_boundary_tests": True,
               "root_hamiltonian_max_error": 0.0, "root_r_error": abs(public_result["rank_r"] - root_result["r"]),
               "evr_evd_core_error": core_error, "evr_evd_max_member_error": member_error,
               "physical_spectrum_symmetry_errors": symmetry_errors,
               "python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__,
               "root_physics_sha256": hashlib.sha256(root_source.read_bytes()).hexdigest(),
               "public_helper_sha256": hashlib.sha256(public_bytes).hexdigest(),
               "champion": {key: champion[key] for key in ("core", "worst_family", "valid", "pass", "resource")},
               "baseline": {key: baseline[key] for key in ("core", "worst_family", "valid", "pass", "resource")}}
    (ROOT / "adversary" / "validation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key != "malformed_controls"}, indent=2))


if __name__ == "__main__":
    main()
