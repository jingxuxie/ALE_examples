import argparse
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import mock

sys.dont_write_bytecode = True
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS"):
    os.environ[variable] = "1"

import numpy as np
import scipy
from scipy.linalg import eigh
from threadpoolctl import threadpool_limits


ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 2e-10


def load_module(relative, name, aliases=None):
    specification = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(specification)
    with mock.patch.dict(sys.modules, aliases or {}):
        specification.loader.exec_module(module)
    return module


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def difference(actual, expected):
    error = float(np.max(np.abs(np.asarray(actual) - np.asarray(expected))))
    require(np.isfinite(error) and error <= TOLERANCE, f"Absolute error {error} exceeds {TOLERANCE}")
    return error


def tensor_operator(length, factors):
    result = np.ones((1, 1), dtype=complex)
    for site in reversed(range(length)):
        result = np.kron(result, factors.get(site, np.eye(2)))
    return result


def independent_operators(fields):
    length = len(fields)
    spin_x = np.array([[0, 1], [1, 0]], dtype=complex) / 2
    spin_y = np.array([[0, 1j], [-1j, 0]], dtype=complex) / 2
    spin_z = np.diag([-0.5, 0.5]).astype(complex)
    full_exchange = np.zeros((2 ** length, 2 ** length), dtype=complex)
    full_field = np.zeros_like(full_exchange)
    magnetization = np.zeros_like(full_exchange)
    full_mode = np.zeros_like(full_exchange)
    for site in range(length):
        neighbour = (site + 1) % length
        for operator in (spin_x, spin_y, spin_z):
            full_exchange += tensor_operator(length, {site: operator, neighbour: operator})
        local_z = tensor_operator(length, {site: spin_z})
        full_field += fields[site] * local_z
        magnetization += local_z
        full_mode += np.exp(2j * np.pi * site / length) * local_z
    indices = np.flatnonzero(np.abs(np.diag(magnetization)) < 1e-14)
    selection = np.ix_(indices, indices)
    return {
        "indices": indices,
        "hamiltonian": (full_exchange + full_field)[selection],
        "exchange": full_exchange[selection],
        "mode": full_mode[selection],
        "mode_squared": (full_mode.conj().T @ full_mode)[selection],
    }


def independent_fraction(eigenvectors, mode, mode_squared, lower, upper):
    fractions = []
    denominators = []
    for index in range(lower, upper):
        vector = eigenvectors[:, index]
        expectation = np.vdot(vector, mode @ vector)
        denominator = float(np.vdot(vector, mode_squared @ vector).real)
        require(denominator > 1e-12, "Undefined Eq. (6) denominator")
        fractions.append(1 - abs(expectation) ** 2 / denominator)
        denominators.append(denominator)
    require(min(fractions) >= -TOLERANCE and max(fractions) <= 1 + TOLERANCE, "Eq. (6) outside [0,1]")
    matrix_elements = eigenvectors.conj().T @ mode @ eigenvectors
    off_diagonal = []
    for index in range(lower, upper):
        weights = np.abs(matrix_elements[:, index]) ** 2
        off_diagonal.append((weights.sum() - weights[index]) / weights.sum())
    difference(fractions, off_diagonal)
    return float(np.mean(fractions)), float(min(denominators))


def independent_ratio(energies, lower, upper):
    values = []
    for index in range(lower + 1, upper - 1):
        left_gap = energies[index] - energies[index - 1]
        right_gap = energies[index + 1] - energies[index]
        require(left_gap > 1e-12 and right_gap > 1e-12, "Unresolved reference gap")
        values.append(min(left_gap, right_gap) / max(left_gap, right_gap))
    require(bool(values), "No internal adjacent-gap pairs")
    return float(sum(values) / len(values))


def production_observables(module, fields, **options):
    if len(fields) == 4:
        with mock.patch.object(module, "gap_ratio", return_value=0.0):
            return module.observables(fields, **options)
    return module.observables(fields, **options)


def physics_case(module, length):
    fields = np.random.default_rng(81000 + length).uniform(-3.7, 3.7, length)
    reference = independent_operators(fields)
    states, _, exchange, _ = module.sector(length)
    require(np.array_equal(states, reference["indices"]), "Sector basis differs from full-space Sz=0 slicing")
    matrix_error = difference(module.hamiltonian(fields), reference["hamiltonian"])
    exchange_error = difference(exchange, reference["exchange"])
    energies, eigenvectors = eigh(reference["hamiltonian"], driver="evd")
    dimension = len(energies)
    lower, upper = dimension // 3, 2 * dimension // 3
    fraction, minimum_denominator = independent_fraction(
        eigenvectors, reference["mode"], reference["mode_squared"], lower, upper)
    ratio = independent_ratio(energies, lower, upper) if length > 4 else None
    driver_errors = []
    for driver, full in (("evr", False), ("evr", True), ("evd", False), ("evd", True)):
        actual = production_observables(module, fields, driver=driver, full=full)
        driver_errors.append(difference(actual["f"], fraction))
        if ratio is not None:
            driver_errors.append(difference(actual["r"], ratio))
            without_vectors = module.observables(fields, vectors=False, driver=driver, full=full)
            driver_errors.append(difference(without_vectors["r"], ratio))
        if full:
            driver_errors.append(difference(actual["energies"], energies))
            residual = module.hamiltonian(fields) @ actual["eigenvectors"] - actual["eigenvectors"] * actual["energies"]
            driver_errors.append(difference(residual, np.zeros_like(residual)))
    invariances = {}
    transforms = {"cyclic": np.roll(fields, 1), "reflection": fields[::-1],
                  "global_field_sign": -fields, "uniform_field_gauge": fields + 2.75}
    for name, transformed in transforms.items():
        actual = production_observables(module, transformed, full=True, driver="evd")
        errors = [difference(actual["energies"], energies), difference(actual["f"], fraction)]
        if ratio is not None:
            errors.append(difference(actual["r"], ratio))
        invariances[name] = max(errors)
    if length == 4:
        try:
            module.observables(fields)
        except ValueError as error:
            require("insufficient" in str(error).lower(), "Unexpected L4 rejection")
        else:
            raise AssertionError("L4 should reject its two-level middle slice for gap ratios")
    return {"length": length, "sector_dimension": dimension, "rank_slice": [lower, upper],
            "internal_ratio_count": max(0, upper - lower - 2), "hamiltonian_max_error": matrix_error,
            "exchange_max_error": exchange_error, "f": fraction, "r": ratio,
            "minimum_eq6_denominator": minimum_denominator, "driver_max_error": max(driver_errors),
            "invariance_errors": invariances, "l4_gap_ratio_stubbed_for_f_only": length == 4}


def gap_boundary_case(module):
    dimension = 20
    lower, upper = dimension // 3, 2 * dimension // 3
    gaps = np.array([0.03, 8, 0.4, 2, 5, 0.001, 1, 3, 2, 7, 4, 11, 0.002, 9, 0.1, 8, 0.2, 3, 1])
    energies = np.concatenate(([0.0], np.cumsum(gaps)))
    expected = independent_ratio(energies, lower, upper)
    calls = []

    def fake_eigh(matrix, eigvals_only, **options):
        require(eigvals_only, "Boundary test requests energies only")
        subset = options.get("subset_by_index")
        calls.append(subset)
        if subset is None:
            return energies.copy()
        require(subset == [lower, upper - 1], "Off-by-one LAPACK subset")
        return energies[subset[0]:subset[1] + 1]

    with mock.patch.object(module, "eigh", side_effect=fake_eigh):
        for driver, full in (("evr", False), ("evr", True), ("evd", False), ("evd", True)):
            actual = module.observables(np.arange(6), vectors=False, driver=driver, full=full)
            difference(actual["r"], expected)
    rejected = 0
    for values in ([], [0], [0, 1], [0, 1, 1], [0, 2, 1], [0, 1e-13, 1]):
        try:
            module.gap_ratio(values)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError(f"Invalid gap sequence accepted: {values}")
    difference(module.gap_ratio([0, 1, 3, 4]), 0.5)
    return {"rank_slice": [lower, upper], "internal_ratio_count": upper - lower - 2,
            "expected_r": expected, "lapack_subsets": calls, "invalid_sequences_rejected": rejected}


def design_fixture(spec):
    return {"layouts": [{"id": bank["id"], "high": list(range(len(bank["fields"]))),
                         "low": list(reversed(range(len(bank["fields"]))))} for bank in spec["banks"]]}


def invalid_designs(spec):
    template = design_fixture(spec)
    cases = {"null": None, "boolean": True, "number": 4, "array": [], "string": "layouts",
             "missing_layouts": {}, "layouts_object": {"layouts": {}}, "empty_layouts": {"layouts": []},
             "extra_top_key": dict(template, score=100)}
    for name, value in (("null_layout", None), ("array_layout", []), ("empty_layout", {})):
        document = copy.deepcopy(template)
        document["layouts"][0] = value
        cases[name] = document
    for name, value in (("unknown_id", "not-a-bank"), ("integer_id", 0), ("list_id", []), ("null_id", None)):
        document = copy.deepcopy(template)
        document["layouts"][0]["id"] = value
        cases[name] = document
    document = copy.deepcopy(template)
    document["layouts"][0]["extra"] = 100
    cases["extra_layout_key"] = document
    if len(template["layouts"]) > 1:
        document = copy.deepcopy(template)
        document["layouts"][1]["id"] = document["layouts"][0]["id"]
        cases["repeated_id"] = document
    for key in ("high", "low"):
        length = len(template["layouts"][0][key])
        for name, value in (("null", None), ("string", "012345"), ("object", {}),
                            ("short", list(range(length - 1))), ("long", list(range(length + 1)))):
            document = copy.deepcopy(template)
            document["layouts"][0][key] = value
            cases[key + "_" + name] = document
        for name, value in (("boolean", False), ("float", 0.0), ("string_index", "0"),
                            ("negative", -1), ("out_of_range", length), ("huge_integer", 2 ** 200),
                            ("null_index", None), ("nested", []), ("nan", float("nan")),
                            ("infinity", float("inf")), ("duplicate", 1)):
            document = copy.deepcopy(template)
            document["layouts"][0][key] = list(range(length))
            document["layouts"][0][key][0] = value
            cases[key + "_" + name] = document
    return cases


def validator_case(module, spec):
    require(len(module.validate_design(design_fixture(spec), spec)) == len(spec["banks"]),
            "Valid permutations rejected")
    cases = invalid_designs(spec)
    for name, document in cases.items():
        try:
            module.validate_design(document, spec)
        except (ValueError, TypeError):
            continue
        raise AssertionError("Malformed design accepted: " + name)
    return {"valid_format_accepted": True, "malformed_cases_rejected": len(cases), "case_names": list(cases)}


def virtual_cli(module, payload, evaluator=False, seed_bytes=None, symlink=False, oversized=False):
    submission = Path("/__physics_audit__/design.json")
    output = Path("/__physics_audit__/report.json")
    texts = {submission: payload,
             ROOT / "concept_2/participant/input/spec.json": (ROOT / "concept_2/participant/input/spec.json").read_text(),
             ROOT / "concept_2/evaluator/hidden/spec.json": (ROOT / "concept_2/evaluator/hidden/spec.json").read_text()}
    seed_path = ROOT / "concept_2/evaluator/hidden/seeds.json"
    committed_bytes = seed_path.read_bytes() if seed_bytes is None else seed_bytes
    texts[seed_path] = committed_bytes.decode()
    captured = {}
    reads = []

    def read_text(path, *arguments, **keywords):
        reads.append(str(path))
        require(path in texts, "Unexpected file read: " + str(path))
        return texts[path]

    def read_bytes(path):
        reads.append(str(path))
        require(path == seed_path, "Unexpected bytes read: " + str(path))
        return committed_bytes

    def write_text(path, text, *arguments, **keywords):
        require(path == output, "Unexpected output path: " + str(path))
        captured["report"] = json.loads(text)
        return len(text)

    arguments = [str(module.__file__), "--submission", str(submission), "--output", str(output)] if evaluator else [str(module.__file__), str(submission), "--output", str(output)]
    with contextlib.ExitStack() as stack:
        stack.enter_context(mock.patch.object(Path, "read_text", read_text))
        stack.enter_context(mock.patch.object(Path, "read_bytes", read_bytes))
        stack.enter_context(mock.patch.object(Path, "write_text", write_text))
        stack.enter_context(mock.patch.object(Path, "mkdir", return_value=None))
        stack.enter_context(mock.patch.object(Path, "is_dir", return_value=False))
        stack.enter_context(mock.patch.object(Path, "is_symlink", return_value=symlink))
        stack.enter_context(mock.patch.object(Path, "stat", return_value=SimpleNamespace(st_size=100001 if oversized else len(payload.encode()))))
        stack.enter_context(mock.patch.object(sys, "argv", arguments))
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        if evaluator:
            stack.enter_context(mock.patch.object(module.signal, "signal"))
            stack.enter_context(mock.patch.object(module.signal, "alarm"))
            stack.enter_context(mock.patch.object(module.resource, "getrusage", return_value=SimpleNamespace(ru_maxrss=1024)))
        try:
            module.main()
        except Exception as error:
            captured["exception"] = error
    captured["reads"] = reads
    return captured


def cli_case(evaluator, private_check, participant_check, spec):
    malformed = {"empty_json": "", "truncated_json": '{"layouts":',
                 "trailing_comma": '{"layouts":[],}', "trailing_document": '{} {}',
                 "single_quotes": "{'layouts': []}"}
    malformed.update({name: json.dumps(document) for name, document in invalid_designs(spec).items()})
    with mock.patch.object(private_check, "observables", return_value={"r": 0.47, "f": 0.5}), \
            mock.patch.object(participant_check, "observables", return_value={"r": 0.47, "f": 0.5}):
        for name, payload in malformed.items():
            result = virtual_cli(evaluator, payload, evaluator=True)
            require("exception" not in result and "report" in result, "Evaluator crashes on " + name)
            report = result["report"]
            require(not report["valid"] and not report["passed"] and report["evaluator_valid"],
                    "Evaluator does not cleanly reject " + name)
            participant = virtual_cli(participant_check, payload)
            require(isinstance(participant.get("exception"), (ValueError, TypeError)),
                    "Participant CLI does not reject " + name)
        valid_payload = json.dumps(design_fixture(spec))
        for name, flags in (("symlink", {"symlink": True}), ("oversized", {"oversized": True})):
            result = virtual_cli(evaluator, valid_payload, evaluator=True, **flags)
            require(not result["report"]["valid"] and result["report"]["evaluator_valid"], "File guard failed: " + name)
        tampered = (ROOT / "concept_2/evaluator/hidden/seeds.json").read_bytes() + b" "
        result = virtual_cli(evaluator, valid_payload, evaluator=True, seed_bytes=tampered)
        require(not result["report"]["evaluator_valid"] and "commitment" in result["report"]["reason"].lower(),
                "Tampered seed bytes were not rejected")
        duplicate = '{"layouts":null,"layouts":' + json.dumps(design_fixture(spec)["layouts"]) + '}'
        duplicate_result = virtual_cli(evaluator, duplicate, evaluator=True)
        require("report" in duplicate_result, "Duplicate-key test did not return a report")
        result = virtual_cli(evaluator, valid_payload, evaluator=True)
        require(result["report"]["valid"] and not result["report"]["passed"], "Zero-separation CLI guard failed")
        require(not any("participant" in path for path in result["reads"]), "Evaluator reads participant files")
    return {"malformed_cli_cases_rejected_per_entrypoint": len(malformed), "symlink_and_size_guards": True,
            "seed_commitment_tamper_rejected": True, "evaluator_reads_no_participant_files": True,
            "duplicate_json_keys_accepted_last_value_wins": duplicate_result["report"]["valid"],
            "io_mode": "In-memory Path mocks; parser/checker/main execute, output and signal/resource operations are intercepted"}


def commitments_case(spec):
    private = json.loads((ROOT / "concept_2/evaluator/hidden/spec.json").read_text())
    require(private == spec, "Public/private specifications differ")
    seed_bytes = (ROOT / "concept_2/evaluator/hidden/seeds.json").read_bytes()
    require(hashlib.sha256(seed_bytes).hexdigest() == spec["hidden_seeds_sha256"], "Hidden seed SHA256 mismatch")
    seeds = json.loads(seed_bytes)["seeds"]
    require(len(seeds) == spec["hidden_draws_per_scale"], "Hidden draw count differs from spec")
    require(all(seed is None or type(seed) is int and seed >= 0 for seed in seeds), "Malformed committed seed")
    require(len(set(seeds)) == len(seeds), "Repeated hidden seeds")
    require(not (set(seeds) - {None}) & (set(spec["public_seeds"]) - {None}), "Public/private random seed overlap")
    for bank in spec["banks"]:
        fields = np.asarray(bank["fields"])
        require(fields.ndim == 1 and len(fields) >= 6 and len(fields) % 2 == 0 and np.isfinite(fields).all(),
                "Invalid field bank")
    require(len({bank["id"] for bank in spec["banks"]}) == len(spec["banks"]), "Duplicate spec bank IDs")
    require(all(np.isfinite(value) and value > 0 for value in spec["targets"].values()), "Invalid thresholds")
    return {"public_private_specs_identical": True, "committed_seed_digest": spec["hidden_seeds_sha256"],
            "hidden_draw_count": len(seeds), "nominal_no_jitter_draw_count": seeds.count(None),
            "non_nominal_seed_overlap": 0, "generation": spec["generation"]}


def sampling_case(module, spec):
    design = design_fixture(spec)
    seen = []

    def observe(fields):
        seen.append(np.asarray(fields).copy())
        return {"r": 0.47, "f": 0.5}

    with mock.patch.object(module, "observables", side_effect=observe):
        result = module.evaluate_design(design, spec, spec["public_seeds"])
    position = 0
    for bank, layout in zip(spec["banks"], design["layouts"]):
        fields = np.asarray(bank["fields"])
        for scale in spec["scales"]:
            for seed in spec["public_seeds"]:
                generator = np.random.Generator(np.random.PCG64(seed)) if seed is not None else None
                jitter = generator.uniform(-spec["jitter"], spec["jitter"], len(fields)) if generator is not None else np.zeros(len(fields))
                expected = scale * fields + jitter
                for key in ("high", "low"):
                    difference(seen[position], expected[layout[key]])
                    position += 1
                difference(np.sort(seen[position - 2]), np.sort(seen[position - 1]))
    require(position == len(seen), "Wrong physics-call count")
    require(len(result["families"]) == len(spec["banks"]) * len(spec["scales"]), "Missing family")
    return {"physics_calls_checked": position, "families_checked": len(result["families"]),
            "same_perturbed_multiset": True, "labelwise_noise_before_permutation": True,
            "noise_reused_across_scales": True, "no_mean_subtraction": True}


def zero_separation_case(module, spec):
    miniature = copy.deepcopy(spec)
    miniature["banks"] = [{"id": "audit_L6", "fields": spec["banks"][0]["fields"][:6]}]
    design = design_fixture(miniature)
    results = {}
    for name, low in (("identical", list(range(6))), ("cyclic", [5, 0, 1, 2, 3, 4]),
                      ("reflection", list(reversed(range(6))))):
        design["layouts"][0]["low"] = low
        result = module.evaluate_design(design, miniature, [None, 88123])
        require(result["valid"] and not result["passed"] and result["core_score"] <= 1e-8,
                "Zero-separation symmetry accepted: " + name)
        results[name] = {"passed": result["passed"], "core_score": result["core_score"]}
    return {"real_physics_length": 6, "results": results}


def scoring_case(module, spec):
    target = spec["targets"]
    cases = {"all_pass": (None, None),
             "mean_r_fail": ([target["mean_abs_r_difference_max"] + 0.0001] * 5, None),
             "max_r_fail": ([target["max_abs_r_difference_max"] + 0.0001] + [0] * 4, None),
             "mean_f_fail": (None, [target["mean_f_separation_min"] - 0.0001] * 5),
             "min_f_fail": (None, [target["min_f_separation_min"] - 0.0001] + [0.5] * 4),
             "negative_separation": (None, [-0.2] * 5)}
    family_count = len(spec["banks"]) * len(spec["scales"])
    scores = {}
    for name, (bad_gaps, bad_separations) in cases.items():
        responses = []
        expected_scores = []
        for family in range(family_count):
            gaps = bad_gaps if family == family_count - 1 and bad_gaps is not None else [0.001] * 5
            separations = bad_separations if family == family_count - 1 and bad_separations is not None else [0.5] * 5
            margins = [target["mean_abs_r_difference_max"] / max(sum(gaps) / 5, 1e-15),
                       target["max_abs_r_difference_max"] / max(max(gaps), 1e-15),
                       sum(separations) / 5 / target["mean_f_separation_min"],
                       min(separations) / target["min_f_separation_min"]]
            expected_scores.append(max(0.0, min(1.0, *margins)))
            for gap, separation in zip(gaps, separations):
                responses.extend([{"r": gap, "f": 0.5 + separation / 2}, {"r": 0.0, "f": 0.5 - separation / 2}])
        with mock.patch.object(module, "observables", side_effect=responses):
            result = module.evaluate_design(design_fixture(spec), spec, [None, 1, 2, 3, 4])
        difference(result["core_score"], 100 * sum(expected_scores) / len(expected_scores))
        difference(result["worst_family_score"], 100 * min(expected_scores))
        require(result["passed"] == (name == "all_pass"), "Incorrect pass threshold: " + name)
        scores[name] = {"passed": result["passed"], "worst_family_score": result["worst_family_score"]}
    return {"synthetic_scoring_only": True, "cases": scores, "last_family_failure_cannot_be_averaged_away": True}


def participant_import_case():
    imports = {}
    suspicious = []
    for path in sorted((ROOT / "concept_2/participant").rglob("*.py")):
        tree = ast.parse(path.read_text())
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
            elif isinstance(node, ast.Call):
                expression = ast.unparse(node.func)
                if "__import__" in expression or "import_module" in expression or "sys.path" in expression:
                    suspicious.append(str(path.relative_to(ROOT)) + ":" + expression)
        require(not any({"hidden", "evaluator", "adversary", "authoring"} & set(name.split(".")) for name in names),
                "Participant imports private modules")
        imports[str(path.relative_to(ROOT))] = sorted(set(names))
    require(not suspicious, "Dynamic import/path mutation requires review: " + str(suspicious))
    return {"static_imports": imports, "private_module_imports": [],
            "limit": "Static source audit plus evaluator I/O tracing; OS isolation is the main session's responsibility"}


def run_audit():
    sources = ["authoring/physics.py", "concept_2/evaluator/physics.py",
               "concept_2/participant/workspace/physics.py", "concept_2/evaluator/check.py",
               "concept_2/participant/workspace/check.py", "concept_2/evaluator/evaluate.py",
               "concept_2/participant/input/spec.json", "concept_2/evaluator/hidden/spec.json",
               "concept_2/evaluator/hidden/seeds.json", "concept_2/participant/TASK.md",
               "concept_2/participant/baseline/solve.py"]
    hashes = {source: hashlib.sha256((ROOT / source).read_bytes()).hexdigest() for source in sources}
    results = []

    def check(name, action):
        try:
            details = action()
            results.append({"name": name, "passed": True, "details": details})
        except Exception as error:
            results.append({"name": name, "passed": False,
                            "error": type(error).__name__ + ": " + str(error)})

    physics = load_module("authoring/physics.py", "audited_root_physics")
    with threadpool_limits(1):
        for length in (4, 6, 8):
            check(f"independent_physics_L{length}", lambda length=length: physics_case(physics, length))
        check("gap_boundaries", lambda: gap_boundary_case(physics))
    check("physics_copies_identical", lambda: require(len({hashes[source] for source in sources[:3]}) == 1,
                                                     "Root/evaluator/participant physics differ"))
    spec = json.loads((ROOT / "concept_2/participant/input/spec.json").read_text())
    private_physics = load_module("concept_2/evaluator/physics.py", "audited_private_physics")
    participant_physics = load_module("concept_2/participant/workspace/physics.py", "audited_participant_physics")
    private_check = load_module("concept_2/evaluator/check.py", "audited_private_check", {"physics": private_physics})
    participant_check = load_module("concept_2/participant/workspace/check.py", "audited_participant_check", {"physics": participant_physics})
    evaluator = load_module("concept_2/evaluator/evaluate.py", "audited_evaluator", {"check": private_check})
    check("checkers_identical", lambda: require(hashes[sources[3]] == hashes[sources[4]], "Checker copies differ"))
    check("spec_and_seed_commitments", lambda: commitments_case(spec))
    with threadpool_limits(1):
        for name, module in (("evaluator", private_check), ("participant", participant_check)):
            check(name + "_validator", lambda module=module: validator_case(module, spec))
            check(name + "_sampling", lambda module=module: sampling_case(module, spec))
            check(name + "_zero_separation", lambda module=module: zero_separation_case(module, spec))
            check(name + "_score_thresholds", lambda module=module: scoring_case(module, spec))
        check("cli_rejections_and_commitment_tamper", lambda: cli_case(evaluator, private_check, participant_check, spec))
    check("participant_imports", participant_import_case)
    changed = [source for source, digest in hashes.items()
               if hashlib.sha256((ROOT / source).read_bytes()).hexdigest() != digest]
    check("audited_sources_unchanged", lambda: require(not changed, f"Concurrent source changes: {changed}"))
    return {"audit_version": 1, "passed": all(result["passed"] for result in results),
            "scope": "Independent physics and concept2 evaluator/participant checks", "absolute_tolerance": TOLERANCE,
            "environment": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__},
            "source_sha256": hashes, "checks": results,
            "notes": ["No changes to physics, concept2, private search, or isolation.",
                      "L4 has only two middle-third levels: production r correctly rejects; f is tested with only the r guard stubbed.",
                      "Gap convention uses only triples entirely inside the rank slice; no neighbouring outside levels.",
                      "Reference Eq. (6) uses full-space Kronecker M1 and M1-dagger M1, plus an independent off-diagonal spectral-weight check.",
                      "Python JSON accepts duplicate object keys with last-key-wins semantics. Resulting designs still receive full validation; this is a non-blocking strict-JSON caveat.",
                      "Jitter is labelwise before permutation, reused across scales and also across equal-length banks for the same seed.",
                      "No L12 witness or hidden/private search was run. Numerical zero-separation integration uses L6 with disclosed thresholds."]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--emit-patch", action="store_true")
    arguments = parser.parse_args()
    report = run_audit()
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.emit_patch:
        print("*** Begin Patch\n*** Add File: authoring/physics_audit.json")
        print("".join("+" + line + "\n" for line in text.splitlines()), end="")
        print("*** End Patch")
    else:
        print(text, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
