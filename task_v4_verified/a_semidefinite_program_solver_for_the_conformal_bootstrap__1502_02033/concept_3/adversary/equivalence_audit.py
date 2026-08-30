import copy
from fractions import Fraction
import importlib.util
import json
from pathlib import Path
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def main():
    hidden = ROOT / "evaluator" / "hidden"
    spec = importlib.util.spec_from_file_location("trusted", hidden / "checker.py")
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    witness = json.loads((hidden / "planted_certificate.json").read_text())
    rotated = copy.deepcopy(witness)
    changed = 0
    for certificate in rotated["certificates"]:
        for label in ["A", "B"]:
            for matrix in certificate[label]:
                first = [Fraction(value) for value in matrix[0]]
                second = [Fraction(value) for value in matrix[1]]
                matrix[0] = [str(Fraction(3, 5) * left + Fraction(4, 5) * right)
                             for left, right in zip(first, second)]
                matrix[1] = [str(-Fraction(4, 5) * left + Fraction(3, 5) * right)
                             for left, right in zip(first, second)]
                changed += 2 * len(first)
    with tempfile.TemporaryDirectory(dir=ROOT / "adversary") as temporary:
        path = Path(temporary) / "rotated.json"
        path.write_text(json.dumps(rotated))
        report = checker.verify(hidden / "instances.json", path)
        assert report["passed"]
    result = {"passed": True, "equivalent_factor_entries_transformed": changed,
              "method": "rational orthogonal row rotation; checker never compares with planted factors",
              "score": report}
    (ROOT / "adversary" / "equivalence_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
