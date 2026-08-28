import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

from generate import moment, operation, public_example, reference_difference, write_json
from independent import solve


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
import evaluator


def native(data, directory):
    input_path = directory / "check_input.json"
    output_path = directory / "check_output.json"
    write_json(input_path, data)
    subprocess.run([str(ROOT / "alea_oracle"), "--input", str(input_path),
                    "--output", str(output_path)], check=True)
    return json.loads(output_path.read_text())


def main():
    checks = {}
    with tempfile.TemporaryDirectory(prefix="checks_", dir=ROOT) as temporary:
        directory = Path(temporary)
        data = public_example()
        expected = native(data, directory)
        independent = solve(data)
        difference = reference_difference(expected, independent)
        assert difference[0] < 2e-9 and difference[1] < 2e-7, difference
        checks["native_vs_independent_partial_batches"] = list(difference)
        reversed_signs = copy.deepcopy(data)
        for replica in reversed_signs["replicas"]:
            replica["signs"] = [-sign for sign in replica["signs"]]
        difference = reference_difference(expected, native(reversed_signs, directory))
        assert max(difference) < 2e-7, difference
        checks["global_sign_reversal"] = list(difference)
        linear = copy.deepcopy(data)
        linear["block_sizes"] = [1]
        linear["expressions"] = [moment(0), moment(2)]
        for replica in linear["replicas"]:
            replica["signs"] = [1] * len(replica["signs"])
        result = native(linear, directory)["analyses"][0]["pooled"]
        samples = np.concatenate([replica["measurements"] for replica in linear["replicas"]])[:, [0, 2]]
        np.testing.assert_allclose(result["mean"], samples.mean(axis=0), rtol=1e-10, atol=1e-12)
        np.testing.assert_allclose(result["covariance"], np.cov(samples, rowvar=False, ddof=1) / len(samples),
                                   rtol=1e-8, atol=1e-12)
        checks["analytic_iid_linear_covariance"] = True
        equal_blocks = copy.deepcopy(linear)
        equal_blocks["block_sizes"] = [2]
        equal_blocks["replicas"] = [{"signs": [1] * 12,
                                     "measurements": samples[:12].tolist()}]
        equal_blocks["expressions"] = [moment(0), operation("div", moment(0), moment(1))]
        result = native(equal_blocks, directory)["analyses"][0]["pooled"]
        blocks = samples[:12].reshape(6, 2, 2).sum(axis=1)
        leaveout = (blocks.sum(axis=0) - blocks) / 10
        transformed = np.column_stack((leaveout[:, 0], leaveout[:, 0] / leaveout[:, 1]))
        centered = transformed - transformed.mean(axis=0)
        hand_covariance = 5.0 / 6.0 * centered.T @ centered
        np.testing.assert_allclose(result["covariance"], hand_covariance, rtol=1e-7, atol=1e-12)
        checks["ordinary_equal_block_jackknife"] = True
        errors = evaluator.measure_errors(independent, expected)
        calibration = [{name: max(error[name], evaluator.FLOORS[name]) for name in evaluator.COMPONENTS}
                       for error in errors]
        assert evaluator.score_answer(expected, expected, calibration)["score"] == 1.0
        diagonal_only = copy.deepcopy(expected)
        for block in diagonal_only["analyses"]:
            for statistics in [block["pooled"]] + block["replicas"]:
                statistics["covariance"] = np.diag(np.diag(statistics["covariance"])).tolist()
        diagonal_score = evaluator.score_answer(diagonal_only, expected, calibration)["score"]
        assert diagonal_score < 0.2, diagonal_score
        checks["exact_means_cannot_hide_missing_covariance"] = diagonal_score
        for invalid in ({}, {"schema_version": 1, "analyses": []}):
            try:
                evaluator.measure_errors(invalid, expected)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid answer accepted")
        checks["invalid_shapes_rejected"] = True
        for invalid_value in (float("nan"), "1.0", True):
            invalid = copy.deepcopy(expected)
            if isinstance(invalid_value, bool):
                invalid["analyses"][0]["pooled"]["mean"] = [True] * len(expected["analyses"][0]["pooled"]["mean"])
            else:
                invalid["analyses"][0]["pooled"]["mean"][0] = invalid_value
            try:
                evaluator.measure_errors(invalid, expected)
            except ValueError:
                pass
            else:
                raise AssertionError("malformed numeric statistics accepted")
        checks["nonfinite_and_nonnumeric_rejected"] = True
        manifest = json.loads((ROOT.parent / "manifest.json").read_text())
        assert len(manifest["core"]) == 8 and len(manifest["challenge"]) >= 9
        for entry in manifest["core"] + manifest["challenge"]:
            data_path = ROOT.parent / entry["input"]
            assert data_path.is_file() and (ROOT.parent / entry["reference"]).is_file()
            document = json.loads(data_path.read_text())
            assert set(document) == {"schema_version", "block_sizes", "expressions", "replicas"}
        checks["stored_unlabeled_cases"] = {"core": 8, "challenge": len(manifest["challenge"])}
        for mode, source in (("missing", "pass\n"), ("malformed", "import sys\nfrom pathlib import Path\nPath(sys.argv[-1]).write_text('{bad')\n")):
            candidate = directory / (mode + ".py")
            candidate.write_text(source)
            report = evaluator.evaluate(candidate, "core")
            assert report["mean_core_score"] == 0 and len(report["errors"]) == 8, report
            checks[mode + "_output_scores_zero"] = True
        wrapper = directory / "wrapper_probe.py"
        wrapper.write_text("import json,subprocess,sys\nfrom pathlib import Path\n"
                           "arguments=sys.argv[1:]\nwork=Path(arguments[arguments.index('--work')+1])\n"
                           "command=arguments[arguments.index('--')+1:]\n"
                           "status=subprocess.run(command).returncode\n"
                           "staged=all(str(work) in value for value in (command[1],command[3],command[5]))\n"
                           "(work/'_resource.json').write_text(json.dumps({'seconds':0.125,'max_rss_kib':1234,"
                           "'child_paths_staged':staged}))\nsys.exit(status)\n")
        prior_wrapper = os.environ.get("ALPS_EVAL_WRAPPER")
        os.environ["ALPS_EVAL_WRAPPER"] = str(wrapper)
        try:
            answer, times = evaluator.run_submission(ROOT.parent.parent / "participant" / "workspace",
                                                     ROOT.parent.parent / "participant" / "input" / "example.json")
            assert answer["schema_version"] == 1
            assert times["seconds"] == 0.125 and times["max_rss_kib"] == 1234
            assert times["child_paths_staged"] is True
            try:
                evaluator.run_submission(directory / "missing.py",
                                         ROOT.parent.parent / "participant" / "input" / "example.json")
            except evaluator.SubmissionFailure as error:
                assert error.times["max_rss_kib"] == 1234
            else:
                raise AssertionError("missing wrapped output accepted")
        finally:
            if prior_wrapper is None:
                os.environ.pop("ALPS_EVAL_WRAPPER", None)
            else:
                os.environ["ALPS_EVAL_WRAPPER"] = prior_wrapper
        checks["wrapper_argv_and_resource_collection_success_and_failure"] = True
    write_json(ROOT / "verification.json", checks)
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
