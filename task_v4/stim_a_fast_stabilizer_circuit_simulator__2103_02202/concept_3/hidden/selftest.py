import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hidden"))
sys.path.insert(0, str(ROOT / "evaluator"))
from generate import native_rows, operation, save, stim, to_stim
from checker import Invalid, apply_gate, check, load, pauli_text, parse_pauli, tableau
from evaluate import evaluate


def main():
    checks = []
    rng = random.Random(73491)
    for width in (1, 2, 3, 6, 36):
        for trial in range(30):
            layers = []
            for step in range(80):
                gate = rng.choice(("H", "S", "CX") if width > 1 else ("H", "S"))
                targets = rng.sample(range(width), 2 if gate == "CX" else 1)
                layers.append([operation(gate, *targets)])
            artifact = dict(schema_version=1, num_qubits=width, layers=layers)
            assert [pauli_text(row, width) for row in tableau(artifact)] == native_rows(artifact)
    checks.append("150 random signed-tableau comparisons against private Stim")
    for gate, targets in (("H", [0]), ("S", [0]), ("CX", [0, 1]), ("CX", [1, 0])):
        circuit = stim.Circuit()
        circuit.append(gate, targets)
        for letters in itertools.product("IXYZ", repeat=2):
            for sign in "+-":
                text = sign + "".join(letters)
                rows = [parse_pauli(text, 2)]
                apply_gate(rows, gate, targets)
                assert pauli_text(rows[0], 2) == str(stim.PauliString(text).after(circuit)).replace("_", "I")
    checks.append("128 exhaustive signed Pauli gate-conjugation comparisons")
    instance = json.loads((ROOT / "evaluator" / "hidden" / "instance.json").read_text())
    witness = json.loads((ROOT / "evaluator" / "hidden" / "witness" / "circuit.json").read_text())
    witness_report = evaluate(ROOT / "evaluator" / "hidden" / "witness")
    baseline_report = evaluate(ROOT / "participant" / "baseline")
    assert witness_report["passed"] and witness_report["score"] == 100
    assert baseline_report["semantic_valid"] and not baseline_report["passed"]
    save(ROOT / "attempts" / "generation_validation" / "witness_report.json", witness_report)
    save(ROOT / "attempts" / "generation_validation" / "baseline_report.json", baseline_report)
    checks.append("Trusted resource-limited witness and baseline evaluation")
    signed = copy.deepcopy(witness)
    signed["layers"].extend([[operation("S", 0)], [operation("S", 0)]])
    assert not check(signed, instance)["semantic_valid"]
    assert [row[:2] for row in tableau(signed)] == [row[:2] for row in tableau(witness)]
    checks.append("Reject phase-only error with identical unsigned tableau")
    malformed = []
    for bad_gate in (operation("CX", 0, 35), operation("CX", 0, 0), operation("T", 0),
                     operation("H", True), operation("H", 36), operation("H", -1), operation("H", 0, 1)):
        artifact = copy.deepcopy(witness)
        artifact["layers"].append([bad_gate])
        malformed.append(json.dumps(artifact).encode())
    collision = copy.deepcopy(witness)
    collision["layers"].append([operation("H", 0), operation("S", 0)])
    malformed.append(json.dumps(collision).encode())
    for raw in (b'{"layers":[],"layers":[]}', b'{"num_qubits":NaN}', b'{"num_qubits":36.0}',
                b'[' * 2000, b'not-json', b'\xff'):
        malformed.append(raw)
    with tempfile.TemporaryDirectory(prefix="clifford-check-") as directory:
        path = Path(directory) / "circuit.json"
        for raw in malformed:
            path.write_bytes(raw)
            assert not evaluate(path)["valid"]
        path.unlink()
        path.symlink_to(ROOT / "evaluator" / "hidden" / "witness" / "circuit.json")
        assert not evaluate(path)["valid"]
        path.unlink()
        with path.open("wb") as destination:
            destination.truncate(64 * 1024 * 1024 + 1)
        assert not evaluate(path)["valid"]
    checks.append("14 malformed/topology cases, symlink, and 64MiB overflow rejection")
    with tempfile.TemporaryDirectory(prefix="clifford-output-") as directory:
        output = Path(directory)
        writer = ROOT / "participant" / "baseline" / "solve.py"
        for arguments, expected in (([], output / "circuit.json"),
                                    (["--output", str(output / "nested")], output / "nested" / "circuit.json"),
                                    (["--output", str(output / "explicit" / "circuit.json")], output / "explicit" / "circuit.json")):
            subprocess.run([sys.executable, "-B", str(writer)] + arguments, cwd=output,
                           check=True, capture_output=True, timeout=15)
            assert expected.read_bytes() == (ROOT / "participant" / "baseline" / "circuit.json").read_bytes()
        (output / "solve.py").write_text("raise AssertionError('submitted code executed')\n")
        (output / "checker.py").write_text("raise AssertionError('untrusted checker imported')\n")
        (output / "sitecustomize.py").write_text("raise AssertionError('untrusted site customization imported')\n")
        report = evaluate(output)
        assert report["semantic_valid"] and report["score"] == baseline_report["score"]
        preview = subprocess.run([sys.executable, "-B", str(ROOT / "participant" / "input" / "check_circuit.py"),
                                  str(output / "circuit.json")], check=True, capture_output=True, timeout=15)
        assert json.loads(preview.stdout)["score"] == baseline_report["score"]
    checks.append("Baseline writer default/directory/file outputs; directory evaluation; public preview; no submission imports")
    public = ROOT / "participant"
    for path in public.rglob("*"):
        assert not path.is_symlink()
        if path.is_file():
            assert "stim" not in path.name.lower()
            assert path.suffix not in (".so", ".whl")
    assert (public / "input" / "checker.py").read_bytes() == (ROOT / "evaluator" / "checker.py").read_bytes()
    checks.append("Public assets contain no vendor, seed, generator, or witness files")
    hashes = {str(path.relative_to(public)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(public.rglob("*")) if path.is_file()}
    save(ROOT / "adversary" / "public_manifest.json", hashes)
    status = json.loads((ROOT / "status.json").read_text())
    status.update(status="generation_validated_not_agent_tested", selftests=checks,
                  baseline=baseline_report, private_witness=witness_report, fresh_agent_tested=False,
                  submission="OUTPUT_DIRECTORY/circuit.json", participant_assets_read_only=True,
                  baseline_entrypoint="participant/baseline/solve.py", score_scale=[0, 100],
                  private_witness_artifact="evaluator/hidden/witness/circuit.json",
                  trusted_instance="evaluator/hidden/instance.json")
    save(ROOT / "status.json", status)
    save(ROOT / "adversary" / "selftest_report.json", dict(passed=True, checks=checks))
    print(json.dumps(dict(passed=True, checks=checks, witness=witness_report, baseline=baseline_report), indent=2))


if __name__ == "__main__":
    main()
