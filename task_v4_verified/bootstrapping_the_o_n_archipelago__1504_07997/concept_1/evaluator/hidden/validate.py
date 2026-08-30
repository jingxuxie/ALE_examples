import copy
import importlib.util
import json
import time
from pathlib import Path

import mpmath as mp


ROOT = Path(__file__).resolve().parents[2]
HIDDEN = ROOT / "evaluator" / "hidden"
SPEC = importlib.util.spec_from_file_location("objective", ROOT / "evaluator" / "evaluate.py")
objective = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(objective)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def witness_output(witness):
    return {"version": 1, "atoms": [{key: value for key, value in feature.items() if key != "t"}
                                    for feature in witness["features"]]}


def conditioned_fit(case, witness):
    with mp.workdps(270):
        blocks = {block["id"]: block for block in case["blocks"]}
        features = witness["features"]
        design = mp.matrix(len(case["rhs"]), len(features))
        target = mp.matrix(len(case["rhs"]), 1)
        for row, value in enumerate(case["rhs"]):
            scale = max(1, abs(mp.mpf(value)))
            target[row] = mp.mpf(value) / scale
            for column, feature in enumerate(features):
                packed = objective.chebyshev_value(blocks[feature["block"]]["moments"][row], mp.mpf(feature["t"]))
                design[row, column] = objective.trace_product(packed, list(map(mp.mpf, feature["projector"]))) / scale
        recovered, residual = mp.qr_solve(design, target)
        errors = [abs(recovered[column] / mp.mpf(feature["weight"]) - 1) for column, feature in enumerate(features)]
        singular = mp.svd(design, compute_uv=False)
        condition = singular[0] / singular[len(singular) - 1]
        assert max(errors) < mp.mpf("1e-60")
        assert condition < mp.mpf("1e100")
        minimum_gap = mp.inf
        maximum_degree = 0
        for block in case["blocks"]:
            maximum_degree = max(maximum_degree, len(block["matrix"]) - 1)
            local = sorted(mp.mpf(feature["t"]) for feature in features if feature["block"] == block["id"])
            if len(local) > 1:
                minimum_gap = min(minimum_gap, min(right - left for left, right in zip(local, local[1:])))
            positions = [mp.mpf(0)] if block["kind"] == "point" else [mp.mpf(index) / 16 for index in range(-16, 17)]
            for position in positions:
                matrix = objective.chebyshev_value(block["matrix"], position)
                determinant = matrix[0] * matrix[2] - matrix[1] ** 2
                assert matrix[0] + matrix[2] > 0
                assert determinant >= -mp.mpf("1e-220") * objective.packed_norm(matrix) ** 2
        assert maximum_degree <= 64 and len(features) <= 32
        assert minimum_gap > mp.mpf("1e-12")
        return {"condition_2_row_equilibrated": mp.nstr(condition, 12),
                "max_relative_recovered_weight_error": mp.nstr(max(errors), 12),
                "qr_residual": mp.nstr(residual, 12), "minimum_local_gap": mp.nstr(minimum_gap, 12),
                "maximum_matrix_degree": maximum_degree, "atom_count": len(features)}


def parser_controls(case, witness):
    controls = {}
    base = witness_output(witness)
    mutations = {
        "missing_atoms": lambda value: value.pop("atoms"),
        "missing_projector": lambda value: value["atoms"][0].pop("projector"),
        "unknown_block": lambda value: value["atoms"][0].update(block="not_a_block"),
        "nan_string": lambda value: value["atoms"][0].update(x="NaN"),
        "inf_string": lambda value: value["atoms"][0].update(weight="Infinity"),
        "numeric_nan": lambda value: value["atoms"][0].update(weight=float("nan")),
        "boolean_number": lambda value: value["atoms"][0].update(x=True),
        "boolean_version": lambda value: value.update(version=True),
        "zero_weight": lambda value: value["atoms"][0].update(weight="0"),
        "negative_weight": lambda value: value["atoms"][0].update(weight="-1"),
        "zero_projector": lambda value: value["atoms"][0].update(projector=["0", "0", "0"]),
        "full_rank_projector": lambda value: value["atoms"][0].update(projector=["0.5", "0", "0.5"]),
        "indefinite_projector": lambda value: value["atoms"][0].update(projector=["2", "0", "-1"]),
        "wrong_projector_shape": lambda value: value["atoms"][0].update(projector=["1", "0"]),
        "coordinate_outside": lambda value: value["atoms"][0].update(x="-1e50"),
        "huge_exponent": lambda value: value["atoms"][0].update(weight="1e9999999999"),
        "too_many_atoms": lambda value: value.update(atoms=value["atoms"] * 256),
        "extra_key": lambda value: value.update(witness=True),
        "atoms_not_list": lambda value: value.update(atoms={}),
    }
    for name, mutate in mutations.items():
        value = copy.deepcopy(base)
        mutate(value)
        result = objective.score_case(case, witness, value)
        assert not result["protocol_valid"] and result["score"] == 0, name
        controls[name] = result["reason"]
    malformed = {"invalid_json": b"{", "multiple_documents": b'{"version":1,"atoms":[]} {}',
                 "duplicate_key": b'{"version":1,"atoms":[],"atoms":[]}',
                 "json_nan": b'{"version":1,"atoms":[NaN]}',
                 "oversized": b" " * (objective.OUTPUT_BYTES + 1), "bad_utf8": bytes([255])}
    for name, raw in malformed.items():
        try:
            objective.load_output(raw)
        except objective.InvalidOutput as error:
            controls[name] = str(error)
        else:
            raise AssertionError(name)
    return controls


def main():
    started = time.monotonic()
    suite = objective.load_suite()
    valid, numerical = [], []
    for record, raw, case, witness in suite:
        result = objective.score_case(case, witness, witness_output(witness))
        assert result["protocol_valid"] and result["score"] > 1 - 1e-12, (record["id"], result)
        valid.append(dict(result, id=record["id"], family=record["family"]))
        numerical.append(dict(conditioned_fit(case, witness), id=record["id"], family=record["family"]))
        print(json.dumps({"validated": record["id"], "family": record["family"]}), flush=True)
    record, raw, case, witness = suite[0]
    base = witness_output(witness)
    controls = {}
    for name in ("empty", "one_omitted", "half_omitted", "duplicates", "roots_only", "wrong_weights", "shifted_roots"):
        altered = copy.deepcopy(base)
        if name == "empty":
            altered["atoms"] = []
        elif name == "one_omitted":
            altered["atoms"] = altered["atoms"][1:]
        elif name == "half_omitted":
            altered["atoms"] = altered["atoms"][::2]
        elif name == "duplicates":
            altered["atoms"] *= 2
        elif name == "roots_only":
            for atom in altered["atoms"]:
                atom.update(projector=["1", "0", "0"], weight="1")
        else:
            for atom in altered["atoms"]:
                with mp.workdps(280):
                    if name == "wrong_weights":
                        atom["weight"] = mp.nstr(2 * mp.mpf(atom["weight"]), 260)
                    else:
                        atom["x"] = mp.nstr(mp.mpf(atom["x"]) + mp.mpf("1e-4"), 260)
        controls[name] = objective.score_case(case, witness, altered)
        assert controls[name]["score"] < 1 - 1e-12
    assert controls["empty"]["score"] == 0
    assert controls["roots_only"]["score"] <= 0.31
    assert controls["wrong_weights"]["score"] <= 0.61
    parser_results = parser_controls(case, witness)
    process_results = {}
    for script, timeout in (("emit_nan.py", 3), ("emit_oversized.py", 3), ("emit_timeout.py", 0.15), ("emit_exit.py", 3)):
        output, execution = objective.run_candidate(HIDDEN / "adversary" / script, raw, timeout)
        assert output is None and not execution["protocol_valid"], script
        process_results[script] = execution
    privacy, execution = objective.run_candidate(HIDDEN / "adversary" / "privacy_probe.py", raw, 3)
    assert privacy == {"hidden_read_denied": True, "hidden_write_denied": True, "network_denied": True}, (privacy, execution)
    audit = objective.aggregate(valid)
    assert audit["passed"]
    write(HIDDEN / "validation" / "known_witness_audit.json", audit)
    write(HIDDEN / "validation" / "conditioned_moment_reconstruction.json", numerical)
    write(HIDDEN / "adversary" / "negative_controls.json", controls)
    write(HIDDEN / "adversary" / "protocol_controls.json", {"parser": parser_results, "process": process_results, "privacy": privacy})
    summary = {"state": "validated_provisional", "cases": len(suite), "families": 6,
               "known_witness_audit": {"core": audit["core"], "worst_family": audit["worst_family"], "passed": audit["passed"]},
               "conditioned_moment_reconstruction": "full_rank_all_cases_relative_error_below_1e-60",
               "negative_controls": len(controls) + len(parser_results) + len(process_results) + len(privacy),
               "elapsed_validation_seconds": time.monotonic() - started, "input_only_passing_solver": None,
               "achievability": "not_verified_by_input_only_solver", "hardness": "unassessed_pending_main_tournament",
               "agents_launched": 0, "baseline_report": "attempts/baseline.json"}
    write(HIDDEN / "validation.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
