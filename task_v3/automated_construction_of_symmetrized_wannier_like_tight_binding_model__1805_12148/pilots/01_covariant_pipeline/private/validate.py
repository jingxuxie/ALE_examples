"""Author-side acceptance checks; never required in participant execution."""

import json
import os
from pathlib import Path
import tempfile

import numpy as np

import evaluator
from metrics import aggregate, numerical_error, score, track_metrics


PRIVATE = Path(__file__).resolve().parent
PILOT = PRIVATE.parent


def expect_exception(function, exception):
    try:
        function()
    except exception:
        return
    raise AssertionError(f"Expected {exception.__name__}")


def main():
    checks = {}
    errors = [0.0, 0.01, 0.1, 1.0, 10.0, 1000000.0]
    values = [score(error, 1.0) for error in errors]
    assert values[0] == 1.0 and abs(values[3] - 0.1) < 1e-15
    assert all(first > second > 0 for first, second in zip(values, values[1:]))
    checks["continuous_monotone_score"] = values
    expect_exception(lambda: numerical_error(np.zeros((2, 2)), np.zeros((3, 3))), ValueError)
    expect_exception(lambda: numerical_error(np.array([np.nan]), np.array([1.0])), ValueError)
    expect_exception(lambda: numerical_error(np.array([np.inf]), np.array([1.0])), ValueError)
    checks["shape_and_finiteness_rejection"] = True
    seeds = set()
    input_digests = set()
    maximum_invariant = 0.0
    case_count = 0
    minimum_orbitals = 1000
    wsvec_errors = []
    fractional_wrong = 0
    ablation_cases = {name: [] for name in ("import_repaired_only", "mapping_repaired_only", "bands_only")}
    strong_cases = []
    for split in ("test", "challenge", "confirmation"):
        manifest = json.loads((PRIVATE / "reference" / f"manifest_{split}.json").read_text())
        strong_report = json.loads((PRIVATE / "validation" / f"strong_{split}.json").read_text())
        weak_report = json.loads((PRIVATE / "validation" / f"weak_{split}.json").read_text())
        strong_cases.extend(strong_report["per_case"])
        assert strong_report["core_score"] > 0.9
        assert strong_report["worst_family_score"] > 0.9
        assert abs(weak_report["core_score"] - 0.1) < 1e-10
        assert abs(weak_report["worst_family_score"] - 0.1) < 1e-10
        checks[f"{split}_strong"] = {key: strong_report[key] for key in ("core_score", "worst_family_score", "family_scores")}
        checks[f"{split}_weak"] = {key: weak_report[key] for key in ("core_score", "worst_family_score", "family_scores")}
        for record in manifest["cases"]:
            case_count += 1
            seed = record["provenance"]["seed"]
            assert seed not in seeds
            seeds.add(seed)
            input_digest = record["input_sha256"]["case.json"]
            assert input_digest not in input_digests
            input_digests.add(input_digest)
            maximum_invariant = max(maximum_invariant, *record["invariants"].values())
            minimum_orbitals = min(minimum_orbitals, record["provenance"]["import"]["output_orbitals"], record["provenance"]["mapping"]["output_orbitals"])
            assert record["provenance"]["mapping"]["historical_matrix_difference"] > 1e-3
            if "ignore_wsvec" in record["ablations"]:
                wsvec_errors.append(record["ablations"]["ignore_wsvec"]["error"])
            if "fractional_metric" in record["ablations"]:
                fractional_wrong += record["ablations"]["fractional_metric"]["wrong_assignments"]
            for name, cases in ablation_cases.items():
                values = record["ablations"][name]
                cases.append({"families": {record["import_family"]: {"score": values["import"]}, "cell_gauge": {"score": values["map"]}}})
    assert maximum_invariant < 2e-7
    assert minimum_orbitals >= 16
    assert max(wsvec_errors) > 1e-4
    assert fractional_wrong > 0
    checks["independent_invariants"] = {"case_count": case_count, "maximum_absolute_residual": maximum_invariant,
                                        "minimum_output_orbitals": minimum_orbitals,
                                        "disjoint_seeds_and_inputs": True, "wsvec_ablation_errors": wsvec_errors,
                                        "fractional_metric_wrong_assignments": fractional_wrong}
    checks["anti_compression_ablations"] = {name: aggregate(cases) for name, cases in ablation_cases.items()}
    assert checks["anti_compression_ablations"]["import_repaired_only"]["worst_family_score"] < 0.11
    assert checks["anti_compression_ablations"]["mapping_repaired_only"]["worst_family_score"] < 0.11
    assert checks["anti_compression_ablations"]["bands_only"]["core_score"] < 0.2
    first_manifest = json.loads((PRIVATE / "reference/manifest_test.json").read_text())
    expected = evaluator.read_arrays(PRIVATE / first_manifest["cases"][0]["reference"])
    damaged = dict(expected)
    damaged["map_h1"] = np.array([np.nan])
    assert track_metrics(damaged, expected, "import")[0] == 0
    expect_exception(lambda: track_metrics(damaged, expected, "map"), ValueError)
    checks["independent_partial_output_scoring"] = True
    public = PILOT / "participant"
    public_npz = list(public.rglob("*.npz"))
    assert len(public_npz) == 1 and public_npz[0].name == "mapping_model.npz"
    with np.load(public_npz[0], allow_pickle=False) as arrays:
        assert set(arrays.files) == {"R", "hop", "pos", "uc"}
    assert not list(public.rglob("*reference*"))
    assert len(list((public / "input").glob("*/case.json"))) == 1
    checks["public_package_has_no_labels"] = True
    with tempfile.TemporaryDirectory(prefix="pilot01-validation-", dir=PRIVATE) as temporary:
        temporary = Path(temporary)
        submission = temporary / "submission"
        submission.mkdir()
        (submission / "solve.py").write_text(
            'import argparse,os,numpy as np\n'
            'parser=argparse.ArgumentParser()\n'
            'parser.add_argument("--input")\n'
            'parser.add_argument("--output")\n'
            'args=parser.parse_args()\n'
            'np.savez(args.output, leaked=np.array(["PYTHONPATH" in os.environ, "PYTHONHOME" in os.environ]))\n'
        )
        scratch = temporary / "run"
        scratch.mkdir()
        saved = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = "/author-only/should/not/leak"
        try:
            execution, output = evaluator.execute(submission, public / "input/smoke", scratch)
        finally:
            if saved is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = saved
        assert execution["status"] == "ok", execution
        assert not np.any(evaluator.read_arrays(output)["leaked"])
        checks["submitted_process_has_no_author_pythonpath"] = True
        object_output = temporary / "object.npz"
        np.savez(object_output, invalid=np.array([{}], dtype=object))
        expect_exception(lambda: evaluator.read_arrays(object_output), ValueError)
        checks["pickle_rejected"] = True
        (submission / "solve.py").write_text("import time\ntime.sleep(10)\n")
        scratch = temporary / "timeout"
        scratch.mkdir()
        original_timeout = evaluator.TIMEOUT_SECONDS
        evaluator.TIMEOUT_SECONDS = 0.1
        try:
            execution, _ = evaluator.execute(submission, public / "input/smoke", scratch)
        finally:
            evaluator.TIMEOUT_SECONDS = original_timeout
        assert execution["status"] == "timeout", execution
        checks["timeout_and_process_group_cleanup"] = True
    report = {"status": "passed", "checks": checks, "per_case": strong_cases}
    report.update(aggregate(strong_cases))
    output = PRIVATE / "validation/reference_validation_report.json"
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "per_case"}, indent=2))


if __name__ == "__main__":
    main()
