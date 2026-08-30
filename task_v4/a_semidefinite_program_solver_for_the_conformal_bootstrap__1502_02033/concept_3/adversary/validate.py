import copy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("checker", ROOT / "evaluator" / "hidden" / "checker.py")
CHECKER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKER)


def evaluate_matrix(polynomial, point):
    rows = len(polynomial[0])
    columns = len(polynomial[0][0])
    result = [[Fraction(0) for column in range(columns)] for row in range(rows)]
    for matrix in reversed(polynomial):
        for row in range(rows):
            for column in range(columns):
                result[row][column] = result[row][column] * point + Fraction(matrix[row][column])
    return result


def main():
    hidden = ROOT / "evaluator" / "hidden"
    inputs = json.loads((hidden / "instances.json").read_text())
    witness = json.loads((hidden / "planted_certificate.json").read_text())
    witness_report = CHECKER.verify(hidden / "instances.json", hidden / "planted_certificate.json")
    assert witness_report["passed"]
    point_count = 0
    for instance, certificate in zip(inputs["instances"], witness["certificates"]):
        for integer in range(-2, len(instance["coefficients"]) + 1):
            point = Fraction(integer, 7)
            matrix = evaluate_matrix(instance["coefficients"], point)
            first = evaluate_matrix(certificate["A"], point)
            second = evaluate_matrix(certificate["B"], point)
            for row in range(instance["dimension"]):
                for column in range(instance["dimension"]):
                    product = sum(vector[row] * vector[column] for vector in first)
                    product += point * sum(vector[row] * vector[column] for vector in second)
                    assert matrix[row][column] == product
            point_count += 1
    rejected = []
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
        path = Path(temporary) / "candidate.json"
        for mutation in ["coefficient", "nan", "float", "duplicate", "degree", "bits", "negative_denominator", "empty"]:
            modified = copy.deepcopy(witness)
            first = modified["certificates"][0]["A"]
            if mutation == "coefficient":
                first[2][0][0] = str(Fraction(first[2][0][0]) + Fraction(1, 10 ** 80))
            elif mutation == "nan":
                first[0][0][0] = "NaN"
            elif mutation == "float":
                first[0][0][0] = 0.5
            elif mutation == "duplicate":
                modified["certificates"][1]["id"] = modified["certificates"][0]["id"]
            elif mutation == "degree":
                first.pop()
            elif mutation == "bits":
                first[0][0][0] = str(2 ** 2100)
            elif mutation == "negative_denominator":
                first[0][0][0] = "1/-2"
            else:
                modified["certificates"] = []
            path.write_text(json.dumps(modified))
            report = CHECKER.verify(hidden / "instances.json", path)
            assert not report["passed"], mutation
            rejected.append({"mutation": mutation, "reason": report["reason"]})
    baseline = ROOT / "adversary" / "baseline_certificate.json"
    subprocess.run(["python", str(ROOT / "participant" / "baseline" / "solve.py"),
                    str(ROOT / "participant" / "input" / "instances.json"), str(baseline)], check=True)
    baseline_report = CHECKER.verify(hidden / "instances.json", baseline)
    report = {"valid": True, "independent_exact_sample_points": point_count,
              "mutation_tests": rejected, "planted_witness": witness_report, "baseline": baseline_report}
    (ROOT / "adversary" / "validation.json").write_text(json.dumps(report, indent=2) + "\n")
    status = json.loads((ROOT / "status.json").read_text())
    status.update({"status": "ready_for_tournament", "baseline_score": baseline_report,
                   "privileged_witness_score": witness_report,
                   "solvability": "demonstrated_by_exact_private_witness", "evaluator_valid": True})
    (ROOT / "status.json").write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
