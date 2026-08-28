import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np

import build


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
evaluator = build.evaluator
oracle = build.oracle
strong = build.strong
weak = build.weak


def maximum_error(case, observed, expected):
    return max(evaluator.errors_for(case, observed, expected).values())


def invariants():
    checks = {}
    one_band = build.make_afm(79, 5.0, 1, 8, 64)
    checks["one_band_legacy_control"] = maximum_error(one_band, weak.solve(one_band), oracle.solve(one_band))
    repeated = build.make_afm(101, 9.0, 2, 12, 80, duplicate=True)
    output = oracle.solve(repeated)
    checks["afm_duplicate_band_symmetry"] = float(np.max(np.abs(oracle.unpack(output["weiss_iw"])[0:2] - oracle.unpack(output["weiss_iw"])[2:4])))
    case = build.make_afm(307, 11.0, 5, 18, 128)
    permutation = [3, 0, 4, 1, 2]
    flavor_order = [flavor for band in permutation for flavor in (2 * band, 2 * band + 1)]
    reordered = copy.deepcopy(case)
    reordered["dos"] = [case["dos"][band] for band in permutation]
    for key in ("g0_iw", "g_iw"):
        reordered[key] = [case[key][flavor] for flavor in flavor_order]
    original, permuted = oracle.solve(case), strong.solve(reordered)
    target = {key: [value[flavor] for flavor in flavor_order] for key, value in original.items()}
    checks["afm_band_permutation"] = maximum_error(reordered, permuted, target)
    measurements = build.make_legendre(229, 4.0, 12, 10, 9)
    for config in measurements["configurations"]:
        config["sign"] = 1
    checks["sign_free_legacy_control"] = maximum_error(measurements, weak.solve(measurements), oracle.solve(measurements))
    measurements = build.make_legendre(401, 7.0, 16, 12, 12)
    rescaled = copy.deepcopy(measurements)
    for config in rescaled["configurations"]:
        config["weight"] *= 7.5
    checks["signed_weight_normalization"] = maximum_error(rescaled, strong.solve(rescaled), oracle.solve(measurements))
    split = copy.deepcopy(measurements)
    first = split["configurations"].pop(0)
    first["weight"] /= 2
    split["configurations"].extend([first, copy.deepcopy(first)])
    checks["configuration_split_invariance"] = maximum_error(split, oracle.solve(split), oracle.solve(measurements))
    matrix_case = build.make_fourier(617, 9.0, 18, 128)
    matrix_output = oracle.solve(matrix_case)
    zero_channel = matrix_case["channels"][4]
    assert zero_channel["moments"] == [0.0, 0.0, 0.0]
    assert np.max(np.abs(oracle.unpack(zero_channel["iw"]))) > 1e-4
    assert np.max(np.abs(matrix_output["g_tau"][4])) > 1e-4
    checks["zero_moments_active_channel"] = 0.0
    checks["fermionic_endpoint_jump"] = max(abs(values[0] + values[-1] + channel["moments"][0]) for channel, values in zip(matrix_case["channels"], matrix_output["g_tau"]))
    nodes, weights = np.polynomial.legendre.leggauss(256)
    times = matrix_case["beta"] * (nodes + 1) / 2
    frequencies = 1j * (2 * np.arange(18) + 1) * np.pi / matrix_case["beta"]
    phase = np.exp(frequencies[:, None] * times)
    integration_errors = []
    for channel in matrix_case["channels"]:
        first, second, third = channel["moments"]
        polynomial = -first / 2 + second * (2 * times - matrix_case["beta"]) / 4
        polynomial += third * times * (matrix_case["beta"] - times) / 4
        numeric = matrix_case["beta"] / 2 * phase @ (weights * polynomial)
        analytic = first / frequencies + second / frequencies**2 + third / frequencies**3
        integration_errors.append(float(np.max(np.abs(numeric - analytic))))
    checks["tail_polynomial_independent_quadrature"] = max(integration_errors)
    assert max(checks.values()) < 2e-9, checks
    return checks


def malformed_checks():
    record = evaluator.read_json(HERE / "manifest.json")["core"][0]
    cases = {
        "missing_file": "pass\n",
        "missing_fields": "from pathlib import Path\nPath('output.json').write_text('{}')\n",
        "malformed_json": "from pathlib import Path\nPath('output.json').write_text('{')\n",
        "nonfinite_json": "from pathlib import Path\nPath('output.json').write_text('{\"g_tau\":NaN}')\n",
        "nonzero_exit": "raise SystemExit(7)\n",
        "wrong_top_level": "from pathlib import Path\nPath('output.json').write_text('[]')\n",
        "duplicate_keys": "from pathlib import Path\nPath('output.json').write_text('{\"g_tau\":[],\"g_tau\":[]}')\n",
        "malformed_resource": "from pathlib import Path\nPath('_resource.json').write_text('null')\nPath('output.json').write_text('{}')\n",
        "timeout": "import time\ntime.sleep(3)\n",
    }
    outcomes = {}
    with tempfile.TemporaryDirectory(prefix="author-check-", dir=ROOT) as directory:
        submission = Path(directory) / "solve.py"
        for name, source in cases.items():
            submission.write_text(source)
            result = evaluator.run_case(submission, record, timeout=0.15 if name == "timeout" else 5)
            assert result["score"] == 0 and result["status"] == "error", (name, result)
            assert all(score == 0 for score in result["component_scores"].values())
            outcomes[name] = result["failure"]
        result = evaluator.run_case(Path(directory) / "absent.py", record)
        assert result["score"] == 0
        outcomes["absent_submission"] = result["failure"]
    expected = evaluator.read_json(HERE.parent / record["reference"])
    for name, replacement in (("wrong_shape", []), ("mixed_boolean", True), ("numeric_string", "0.0")):
        output = copy.deepcopy(expected)
        if name == "wrong_shape":
            output["g_tau"] = replacement
        else:
            output["g_tau"][0][0] = replacement
        try:
            evaluator.validate_output(output, expected)
        except ValueError:
            outcomes[name] = "rejected"
        else:
            raise AssertionError(name)
    return outcomes


def main():
    os.environ.pop("ALPS_EVAL_WRAPPER", None)
    files = sorted(path for path in (ROOT / "participant").rglob("*") if path.is_file())
    frozen = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
    build.save(HERE / "participant_frozen_sha256.json", frozen)
    summary = {"invariants": invariants(), "malformed_outputs": malformed_checks(), "reports": {}}
    for name, submission in (("weak", ROOT / "participant/workspace/solve.py"), ("strong", HERE / "strong.py")):
        for split in ("core", "challenge"):
            report = evaluator.evaluate(submission, split)
            assert all(case["status"] == "ok" for case in report["cases"]), report
            if name == "strong":
                assert report["mean_core_score"] > 0.995, report
                assert report["worst_family_score"] > 0.99, report
            build.save(HERE / (name + "_" + split + "_report.json"), report)
            summary["reports"][name + "_" + split] = {
                "mean_core_score": report["mean_core_score"], "worst_family_score": report["worst_family_score"],
                "total_wall_seconds": report["times"]["total_wall_seconds"],
            }
    for relative, digest in frozen.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
    build.save(HERE / "validation_summary.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
