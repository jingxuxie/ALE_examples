import argparse
import collections
import copy
import datetime
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tarfile
import time

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import eigh


HERE = Path(__file__).resolve().parent
PACKET = HERE.parent.parent
CONCEPT = PACKET.parent.parent
ORBITAL_COUNT = 10
PAIR_COUNT = 3
FULL_MASK = 127
PAIRS = list(itertools.combinations(range(ORBITAL_COUNT), 2))
LOW_MASKS = [mask for mask in range(128) if mask.bit_count() <= 3]
TRIPLE_MASKS = [mask for mask in LOW_MASKS if mask.bit_count() == 3]
CONTROLS = ([dict(kind="pair_energy", orbitals=[orbital]) for orbital in range(10)]
            + [dict(kind="hopping", orbitals=list(pair)) for pair in PAIRS]
            + [dict(kind="density", orbitals=list(pair)) for pair in PAIRS])
FAMILIES = ["original_vv", "ov_transfer", "diagonal_energy", "all_density",
            "fixed_density", "all_pair_transfer", "previously_fixed", "full_coefficients"]
RADII = [0.001, 0.002, 0.003, 0.005, 0.01]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory):
    return {str(path.relative_to(directory)): digest(path)
            for path in sorted(directory.rglob("*")) if path.is_file()}


def finite_tree(value):
    if isinstance(value, dict):
        return all(finite_tree(entry) for entry in value.values())
    if isinstance(value, list):
        return all(finite_tree(entry) for entry in value)
    return not isinstance(value, (int, float)) or math.isfinite(value)


def initialize():
    inputs = HERE / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    if not (inputs / "target.json").exists():
        shutil.copy2(PACKET / "participant/input/target.json", inputs / "target.json")
        shutil.copy2(CONCEPT / "attempts/v_2/witness.json", inputs / "champion_witness.json")
        shutil.copy2(CONCEPT / "attempts/v_2.score.json", inputs / "main_official_report.json")
        shutil.copy2(PACKET / "evaluator/hidden/freeze.json", inputs / "generation2_freeze.json")
    main_report = json.loads((inputs / "main_official_report.json").read_text())
    if not main_report["passed"] or main_report["perturbed_assay"]["successes"] != 128:
        raise ValueError("expected actual officially passing fresh B2 champion")
    archive_path = HERE / "archive/portfolio_evidence.tar.gz"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if not archive_path.exists():
        portfolio = HERE.parent / "portfolio"
        before = inventory(portfolio)
        report_hash = digest(HERE.parent / "portfolio_report.json")
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(portfolio, arcname="portfolio", recursive=True)
            archive.add(HERE.parent / "portfolio_report.json", arcname="portfolio_report.json")
        if before != inventory(portfolio) or report_hash != digest(HERE.parent / "portfolio_report.json"):
            raise AssertionError("portfolio changed during archival")
        write_json(HERE / "archive/manifest.json", {
            "archived_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "portfolio_stopped": True, "portfolio_files": before,
            "portfolio_report_sha256": report_hash, "archive_sha256": digest(archive_path),
            "archive_bytes": archive_path.stat().st_size,
        })
    return json.loads((inputs / "target.json").read_text())


def frozen_audit():
    freeze = json.loads((HERE / "inputs/generation2_freeze.json").read_text())
    mismatches = [name for name, expected in freeze["files"].items()
                  if digest(PACKET / name) != expected]
    manifest_matches = digest(PACKET / "evaluator/hidden/freeze.json") == digest(HERE / "inputs/generation2_freeze.json")
    archive = json.loads((HERE / "archive/manifest.json").read_text())
    portfolio_matches = inventory(HERE.parent / "portfolio") == archive["portfolio_files"]
    report_matches = digest(HERE.parent / "portfolio_report.json") == archive["portfolio_report_sha256"]
    result = dict(frozen_file_count=len(freeze["files"]), mismatches=mismatches,
                  frozen_manifest_unchanged=manifest_matches, portfolio_unchanged=portfolio_matches,
                  portfolio_report_unchanged=report_matches,
                  actual_champion_unchanged=digest(CONCEPT / "attempts/v_2/witness.json") == digest(HERE / "inputs/champion_witness.json"))
    if mismatches or not all((manifest_matches, portfolio_matches, report_matches, result["actual_champion_unchanged"])):
        raise AssertionError(result)
    return result


def champion_parameters(target):
    witness = json.loads((HERE / "inputs/champion_witness.json").read_text())
    hopping = np.zeros((10, 10))
    hopping[:3, 3:] = target["occupied_virtual_hopping"]
    hopping[3:, :3] = hopping[:3, 3:].T
    hopping[3:, 3:] = witness["virtual_hopping"]
    density = np.array(target["background_density"], dtype=float)
    density[3:, 3:] = witness["virtual_density"]
    return dict(pair_energy_eh=target["pair_energy_eh"], hopping=hopping.tolist(), density=density.tolist())


def validate_parameters(parameters, target):
    if not isinstance(parameters, dict) or set(parameters) != {"pair_energy_eh", "hopping", "density"}:
        raise ValueError("invalid full-parameter fields")
    for field, shape in (("pair_energy_eh", (10,)), ("hopping", (10, 10)), ("density", (10, 10))):
        entries = parameters[field]
        flat = entries if len(shape) == 1 else [entry for row in entries for entry in row]
        if any(type(entry) not in (int, float) for entry in flat):
            raise ValueError("non-numeric or boolean coefficient")
        matrix = np.asarray(entries, dtype=float)
        if matrix.shape != shape or not np.all(np.isfinite(matrix)):
            raise ValueError("invalid shape or nonfinite coefficients")
        if len(shape) == 2:
            bound = target["hopping_bound_eh" if field == "hopping" else "density_bound_eh"]
            if not np.array_equal(matrix, matrix.T) or np.any(np.diag(matrix)):
                raise ValueError("matrix must be exactly symmetric with zero diagonal")
            if np.max(np.abs(matrix)) > bound:
                raise ValueError("coefficient outside bound")
    return tuple(np.array(parameters[field], dtype=float) for field in ("pair_energy_eh", "hopping", "density"))


def family_indices(family):
    selected = []
    for index, control in enumerate(CONTROLS):
        kind = control["kind"]
        orbitals = control["orbitals"]
        virtual_pair = len(orbitals) == 2 and min(orbitals) >= 3
        occupied_virtual = len(orbitals) == 2 and min(orbitals) < 3 <= max(orbitals)
        choices = {
            "original_vv": virtual_pair,
            "ov_transfer": kind == "hopping" and occupied_virtual,
            "diagonal_energy": kind == "pair_energy",
            "all_density": kind == "density",
            "fixed_density": kind == "density" and not virtual_pair,
            "all_pair_transfer": kind == "hopping",
            "previously_fixed": not virtual_pair,
            "full_coefficients": True,
        }
        if choices[family]:
            selected.append(index)
    return selected


def perturb(center, family, radius, uniforms, target):
    if radius < 0 or not math.isfinite(radius) or np.shape(uniforms) != (100,):
        raise ValueError("invalid noise specification")
    if not np.all(np.isfinite(uniforms)) or np.min(uniforms) < 0 or np.max(uniforms) > 1:
        raise ValueError("uniform coordinates must be finite in [0,1]")
    result = copy.deepcopy(center)
    for index in family_indices(family):
        control = CONTROLS[index]
        orbitals = control["orbitals"]
        kind = control["kind"]
        if kind == "pair_energy":
            original = center["pair_energy_eh"][orbitals[0]]
            result["pair_energy_eh"][orbitals[0]] = float(original + radius * (2 * uniforms[index] - 1))
        else:
            source, destination = orbitals
            bound = target["hopping_bound_eh" if kind == "hopping" else "density_bound_eh"]
            original = center[kind][source][destination]
            lower = max(-bound, original - radius)
            upper = min(bound, original + radius)
            value = float(lower + (upper - lower) * uniforms[index])
            result[kind][source][destination] = result[kind][destination][source] = value
    return result


class IndependentEngine:
    def __init__(self, target):
        self.target = target
        self.states = [state for state in range(1 << 10) if state.bit_count() == 3]
        self.orbitals = [[orbital for orbital in range(10) if state & (1 << orbital)] for state in self.states]
        self.occupation = np.array([[int(orbital in occupied) for orbital in range(10)] for occupied in self.orbitals])
        self.reference = self.states.index(7)
        self.subsets = {mask: np.array([index for index, state in enumerate(self.states)
                                       if not state & ~(7 | (mask << 3))]) for mask in range(128)}
        rows, columns, sources, destinations, phases = [], [], [], [], []
        for row, left_state in enumerate(self.states):
            for column, right_state in enumerate(self.states[:row]):
                if (left_state ^ right_state).bit_count() == 2:
                    source = (right_state & ~left_state).bit_length() - 1
                    destination = (left_state & ~right_state).bit_length() - 1
                    spin_state = sum(3 << (2 * orbital) for orbital in self.orbitals[column])
                    phase = 1
                    for spin_orbital in (2 * source, 2 * source + 1, 2 * destination + 1, 2 * destination):
                        if (spin_state & ((1 << spin_orbital) - 1)).bit_count() % 2:
                            phase = -phase
                        spin_state ^= 1 << spin_orbital
                    rows.append(row)
                    columns.append(column)
                    sources.append(source)
                    destinations.append(destination)
                    phases.append(phase)
        self.edges = tuple(np.array(values, dtype=int) for values in (rows, columns, sources, destinations, phases))
        self.combo_basis = list(itertools.combinations(range(10), 3))
        combo_index = {state: index for index, state in enumerate(self.combo_basis)}
        self.permutation = np.array([combo_index[tuple(occupied)] for occupied in self.orbitals])
        combo_rows, combo_columns, combo_sources, combo_destinations = [], [], [], []
        for row, state in enumerate(self.combo_basis):
            for source in state:
                for destination in range(10):
                    if destination not in state:
                        child = tuple(sorted((set(state) - {source}) | {destination}))
                        column = combo_index[child]
                        if column < row:
                            combo_rows.append(row)
                            combo_columns.append(column)
                            combo_sources.append(source)
                            combo_destinations.append(destination)
        self.combo_edges = tuple(np.array(values, dtype=int) for values in (combo_rows, combo_columns, combo_sources, combo_destinations))
        self.evaluations = 0
        self.diagonalizations = 0

    def matrices(self, parameters):
        energies, hopping, density = validate_parameters(parameters, self.target)
        first = np.diag(self.occupation @ energies + 0.5 * np.sum((self.occupation @ density) * self.occupation, axis=1))
        rows, columns, sources, destinations, phases = self.edges
        first[rows, columns] = first[columns, rows] = hopping[sources, destinations] * phases
        second = np.diag([math.fsum([energies[orbital] for orbital in state]
                                   + [density[source, destination] for source, destination in itertools.combinations(state, 2)])
                          for state in self.combo_basis])
        rows, columns, sources, destinations = self.combo_edges
        second[rows, columns] = second[columns, rows] = hopping[sources, destinations]
        return first, second[np.ix_(self.permutation, self.permutation)]

    def evaluate(self, parameters, complete=False):
        started = time.perf_counter()
        first, second = self.matrices(parameters)
        matrix_error = float(np.max(np.abs(first - second)))
        values, vectors = eigh(first, subset_by_index=(0, 1), driver="evr", check_finite=True)
        alternate_values, alternate_vectors = eigh(second, driver="evd", check_finite=True)
        self.diagonalizations += 2
        residual = max(float(np.max(np.abs(first @ vectors - vectors * values))),
                       float(np.max(np.abs(second @ alternate_vectors[:, :2] - alternate_vectors[:, :2] * alternate_values[:2]))))
        reference = float(first[self.reference, self.reference])
        alternate_reference = float(second[self.reference, self.reference])
        energy_map = {0: reference, 127: float(values[0])}
        alternate_map = {0: alternate_reference, 127: float(alternate_values[0])}
        selected_masks = list(range(128)) if complete else LOW_MASKS
        for mask in selected_masks:
            if mask in (0, 127):
                continue
            selection = self.subsets[mask]
            energy_map[mask] = float(eigh(first[np.ix_(selection, selection)], subset_by_index=(0, 0), driver="evr", eigvals_only=True, check_finite=True)[0])
            alternate_map[mask] = float(eigh(second[np.ix_(selection, selection)], subset_by_index=(0, 0), driver="evx", eigvals_only=True, check_finite=True)[0])
            self.diagonalizations += 2
        increments, alternate_increments = {0: 0.0}, {0: 0.0}
        for mask in selected_masks:
            if not mask:
                continue
            subset, terms, previous = mask, [], []
            while subset:
                sign = -1 if (mask.bit_count() - subset.bit_count()) % 2 else 1
                terms.append(sign * (energy_map[subset] - reference))
                if subset != mask:
                    previous.append(alternate_increments[subset])
                subset = (subset - 1) & mask
            increments[mask] = math.fsum(terms)
            alternate_increments[mask] = alternate_map[mask] - alternate_reference - math.fsum(previous)
        truncation = reference + math.fsum(increments[mask] for mask in LOW_MASKS)
        alternate_truncation = alternate_reference + math.fsum(alternate_increments[mask] for mask in LOW_MASKS)
        triples = np.array([increments[mask] for mask in TRIPLE_MASKS])
        triple_maximum = float(np.max(np.abs(triples)))
        tail = abs(float(values[0]) - truncation)
        numerical_errors = {
            "matrix_agreement_eh": matrix_error,
            "energy_agreement_eh": max(abs(energy_map[mask] - alternate_map[mask]) for mask in energy_map),
            "increment_agreement_eh": max(abs(increments[mask] - alternate_increments[mask]) for mask in increments),
            "truncation_agreement_eh": abs(truncation - alternate_truncation),
            "eigen_residual_eh": residual,
            "variational_violation_eh": max([0.0] + [energy_map[mask | (1 << index)] - energy_map[mask]
                for mask in energy_map for index in range(7)
                if not mask & (1 << index) and (mask | (1 << index)) in energy_map]),
        }
        if complete:
            numerical_errors["closure_error_eh"] = abs(reference + math.fsum(increments.values()) - values[0])
        numerical_valid = max(numerical_errors.values()) <= self.target["numerical_check_eh"]
        metrics = {
            "reference_energy_eh": reference, "full_energy_eh": float(values[0]),
            "third_order_energy_eh": truncation, "signed_tail_eh": float(values[0]) - truncation,
            "tail_eh": tail, "max_abs_triple_eh": triple_maximum,
            "tail_to_parent_ratio": tail / max(triple_maximum, self.target["ratio_floor_eh"]),
            "hf_weight": float(vectors[self.reference, 0] ** 2),
            "spectral_gap_eh": float(values[1] - values[0]),
            "diagonal_margin_eh": min(float(first[index, index] - reference) for index in range(120) if index != self.reference),
            "max_abs_single_eh": max(abs(increments[mask]) for mask in LOW_MASKS if mask.bit_count() == 1),
            "max_abs_pair_eh": max(abs(increments[mask]) for mask in LOW_MASKS if mask.bit_count() == 2),
            "max_numerical_error_eh": max(numerical_errors.values()),
        }
        physical = {
            "hf_weight": metrics["hf_weight"] >= self.target["min_hf_weight"],
            "spectral_gap": metrics["spectral_gap_eh"] >= self.target["min_spectral_gap_eh"],
            "diagonal_margin": metrics["diagonal_margin_eh"] >= self.target["min_diagonal_margin_eh"],
        }
        checks = {
            "material_tail": tail >= self.target["min_tail_eh"],
            "parents": triple_maximum <= self.target["parent_threshold_eh"],
            "ratio": metrics["tail_to_parent_ratio"] >= self.target["min_tail_to_parent_ratio"],
        }
        failures = (["numerical"] if not numerical_valid else []) + (["physical"] if not all(physical.values()) else [])
        failures += [name for name, passed in checks.items() if not passed]
        score = min(1.0, self.target["parent_threshold_eh"] / max(triple_maximum, self.target["ratio_floor_eh"]),
                    tail / self.target["min_tail_eh"], metrics["tail_to_parent_ratio"] / self.target["min_tail_to_parent_ratio"])
        if not numerical_valid or not all(physical.values()):
            score = 0.0
        self.evaluations += 1
        result = dict(valid=numerical_valid and all(physical.values()), passed=not failures,
                      numerical_valid=numerical_valid, physical=physical, checks=checks, failures=failures,
                      cluster="+".join(failures) if failures else "pass", core_score=score,
                      metrics=metrics, numerical_errors=numerical_errors,
                      worst_triple_virtual_indices=[index for index in range(7) if TRIPLE_MASKS[int(np.argmax(np.abs(triples)))] & (1 << index)],
                      elapsed_seconds=time.perf_counter() - started)
        if complete:
            result["order_sums_eh"] = {str(order): math.fsum(value for mask, value in increments.items() if mask.bit_count() == order) for order in range(1, 8)}
        if not finite_tree(result):
            raise ValueError("nonfinite recomputed result")
        return result


def specification():
    return {
        "status": "private exploratory challenge, not a frozen target", "source": "actual fresh B2 final witness",
        "grid_seed": 202608281207, "confirmation_seed": 202608281208,
        "grid_draws_per_cell": 128, "confirmation_draws": 512, "radii_eh": RADII,
        "generator": "numpy.random.Generator(numpy.random.PCG64(seed)).random((count,100))",
        "control_order": CONTROLS,
        "families": {family: family_indices(family) for family in FAMILIES},
        "distribution": "independent uniform coefficients; for hopping and density, uniform on intersection of nominal +/- radius with original symmetric coefficient bound; mirror exactly; diagonal pair energies uniform nominal +/- radius",
        "centering": "all draws independently centered on unchanged actual champion; never accumulated",
        "pairing": "same iid 100-coordinate uniform rows reused across grid families and radii to isolate direction effects; cells must not be pooled as independent samples",
        "constraints": "unchanged original weak-reference, spectral-gap, diagonal-margin, material-tail, all-triples and ratio conditions; no conditioning away physical failures",
        "confirmation": "512 additional independent rows for original_vv, previously_fixed and full_coefficients at the original 0.001 Eh radius",
        "scope": "effective real pair-conserving electronic model only, not arbitrary ab initio integral tensors, not universal robustness, not a population success guarantee",
    }


def run_tests(engine, center):
    nominal = engine.evaluate(center, complete=True)
    official = json.loads((HERE / "inputs/main_official_report.json").read_text())["nominal"]["metrics"]
    energy_fields = ("full_energy_eh", "third_order_energy_eh", "tail_eh", "max_abs_triple_eh", "spectral_gap_eh", "diagonal_margin_eh")
    official_error = max(abs(nominal["metrics"][field] - official[field]) for field in energy_fields)
    if not nominal["passed"] or official_error > 5e-10:
        raise AssertionError("independent nominal calculation disagrees")
    repeated = engine.evaluate(center)
    deterministic_error = max(abs(repeated["metrics"][field] - nominal["metrics"][field]) for field in nominal["metrics"])
    shifted = copy.deepcopy(center)
    shifted["pair_energy_eh"] = [entry + 0.001 for entry in shifted["pair_energy_eh"]]
    energy_shift = engine.evaluate(shifted, complete=True)
    density_center = copy.deepcopy(center)
    density_center["density"] = (0.99 * np.array(density_center["density"])).tolist()
    density_reference = engine.evaluate(density_center, complete=True)
    shifted_density = copy.deepcopy(density_center)
    for source, destination in PAIRS:
        shifted_density["density"][source][destination] += 0.001
        shifted_density["density"][destination][source] += 0.001
    density_shift = engine.evaluate(shifted_density, complete=True)
    gauge_pairs = ((energy_shift, nominal), (density_shift, density_reference))
    gauge_error = max(abs(report["metrics"][field] - reference_report["metrics"][field])
                      for report, reference_report in gauge_pairs
                      for field in ("tail_eh", "max_abs_triple_eh", "hf_weight", "spectral_gap_eh", "diagonal_margin_eh"))
    gauge_error = max(gauge_error, *(abs(report["metrics"]["full_energy_eh"] - reference_report["metrics"]["full_energy_eh"] - 0.003)
                                     for report, reference_report in gauge_pairs))
    malformed = []
    for label, field, value in (("nan", "pair_energy_eh", float("nan")), ("infinity", "pair_energy_eh", float("inf")), ("boolean", "pair_energy_eh", True)):
        invalid = copy.deepcopy(center)
        invalid[field][0] = value
        malformed.append((label, invalid))
    invalid = copy.deepcopy(center)
    invalid["hopping"][0][3] += 0.01
    malformed.append(("asymmetric", invalid))
    invalid = copy.deepcopy(center)
    invalid["density"][0][0] = 1.0
    malformed.append(("nonzero_diagonal", invalid))
    invalid = copy.deepcopy(center)
    invalid["hopping"][0][1] = invalid["hopping"][1][0] = 0.451
    malformed.append(("bound", invalid))
    invalid = copy.deepcopy(center)
    invalid["pair_energy_eh"] = invalid["pair_energy_eh"][:-1]
    malformed.append(("shape", invalid))
    rejected = []
    for label, invalid in malformed:
        try:
            validate_parameters(invalid, engine.target)
        except (ValueError, TypeError):
            rejected.append(label)
        else:
            raise AssertionError("malformed input accepted: " + label)
    generator = np.random.Generator(np.random.PCG64(202608281206))
    random_checks = []
    for radius in RADII:
        parameters = perturb(center, "full_coefficients", radius, generator.random(100), engine.target)
        report = engine.evaluate(parameters, complete=True)
        if not report["numerical_valid"]:
            raise AssertionError("independent random spectrum check failed")
        random_checks.append(dict(radius_eh=radius, max_numerical_error_eh=report["metrics"]["max_numerical_error_eh"]))
    if max(official_error, deterministic_error, gauge_error) > 5e-10:
        raise AssertionError("energy/gauge/repeat validation failed")
    report = dict(passed=True, official_nominal_energy_error_eh=official_error,
                  deterministic_error=deterministic_error, gauge_invariance_error_eh=gauge_error,
                  malformed_rejected=rejected, full_closure_random_checks=random_checks,
                  pair_operator_phases=sorted(set(engine.edges[-1].tolist())),
                  independent_builders="explicit spin-fermion pair action in bitmask order vs unordered spatial-pair combinations",
                  independent_energies="evr vs evx/evd; direct alternating sums vs recursive subtraction")
    write_json(HERE / "tests.json", report)
    write_json(HERE / "nominal_report.json", nominal)
    return report


def aggregate(records):
    metric_names = records[0]["metrics"]
    return dict(case_count=len(records), successes=sum(record["passed"] for record in records),
                physically_valid_cases=sum(all(record["physical"].values()) for record in records),
                numerically_valid_cases=sum(record["numerical_valid"] for record in records),
                failure_clusters=dict(collections.Counter(record["cluster"] for record in records)),
                failures_nonexclusive=dict(collections.Counter(failure for record in records for failure in record["failures"])),
                physical_failures_nonexclusive=dict(collections.Counter(name for record in records for name, passed in record["physical"].items() if not passed)),
                metric_ranges={field: dict(min=min(record["metrics"][field] for record in records),
                                           max=max(record["metrics"][field] for record in records)) for field in metric_names},
                minimum_case_score=min(record["core_score"] for record in records))


def run_cell(engine, center, family, radius, uniforms, seed, phase):
    identifier = phase + "_" + family + "_" + format(radius, ".3f").replace(".", "p")
    destination = HERE / "results" / (identifier + ".json")
    if destination.exists():
        return json.loads(destination.read_text())
    records, examples = [], {}
    for sample_index, row in enumerate(uniforms):
        parameters = perturb(center, family, radius, row, engine.target)
        record = engine.evaluate(parameters)
        record["sample_index"] = sample_index
        records.append(record)
        cluster = record["cluster"]
        if cluster not in examples:
            example_path = HERE / "examples" / (identifier + "_" + cluster.replace("+", "_") + ".json")
            checked = engine.evaluate(parameters, complete=True)
            if checked["cluster"] != cluster or not checked["numerical_valid"]:
                raise AssertionError("complete verification disagrees with screening diagnostic")
            write_json(example_path, dict(family=family, radius_eh=radius, seed=seed, sample_index=sample_index,
                                         uniform_coordinates=row.tolist(), parameters=parameters, report=checked,
                                         source_witness_sha256=digest(HERE / "inputs/champion_witness.json")))
            examples[cluster] = str(example_path.relative_to(HERE))
    summary = aggregate(records)
    result = dict(phase=phase, family=family, radius_eh=radius, seed=seed,
                  control_count=len(family_indices(family)), summary=summary, examples=examples, cases=records)
    write_json(destination, result)
    print(json.dumps(dict(cell=identifier, successes=summary["successes"], count=len(records),
                          clusters=summary["failure_clusters"])), flush=True)
    return result


def paired_comparison(results, phase, radius, family):
    baseline = next(result for result in results if result["phase"] == phase and result["radius_eh"] == radius and result["family"] == "original_vv")
    expanded = next(result for result in results if result["phase"] == phase and result["radius_eh"] == radius and result["family"] == family)
    labels = collections.Counter()
    for baseline_case, expanded_case in zip(baseline["cases"], expanded["cases"]):
        labels[("vv_pass" if baseline_case["passed"] else "vv_fail") + "+" + ("expanded_pass" if expanded_case["passed"] else "expanded_fail")] += 1
    return dict(phase=phase, radius_eh=radius, expanded_family=family, counts=dict(labels))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests-only", action="store_true")
    parser.add_argument("--reproduce", type=Path)
    options = parser.parse_args()
    started = time.perf_counter()
    target = initialize()
    audit_before = frozen_audit()
    engine = IndependentEngine(target)
    center = champion_parameters(target)
    if options.reproduce:
        example = json.loads(options.reproduce.read_text())
        generated = perturb(center, example["family"], example["radius_eh"], np.array(example["uniform_coordinates"]), target)
        if generated != example["parameters"]:
            raise AssertionError("saved full Hamiltonian does not reproduce from coordinates")
        report = engine.evaluate(generated, complete=True)
        print(json.dumps(report, indent=2, allow_nan=False))
        return
    spec = specification()
    spec_path = HERE / "challenge_spec.json"
    if spec_path.exists() and json.loads(spec_path.read_text()) != spec:
        raise AssertionError("private predeclared challenge specification changed")
    write_json(spec_path, spec)
    tests = run_tests(engine, center)
    if options.tests_only:
        print(json.dumps(tests, indent=2))
        return
    results = []
    for phase, seed, count, families, radii in (
        ("grid", spec["grid_seed"], 128, FAMILIES, RADII),
        ("confirmation", spec["confirmation_seed"], 512, ["original_vv", "previously_fixed", "full_coefficients"], [0.001]),
    ):
        uniforms = np.random.Generator(np.random.PCG64(seed)).random((count, 100))
        write_json(HERE / (phase + "_uniforms.json"), dict(seed=seed, uniforms=uniforms.tolist()))
        for radius in radii:
            for family in families:
                results.append(run_cell(engine, center, family, radius, uniforms, seed, phase))
    compact = [{field: result[field] for field in ("phase", "family", "radius_eh", "seed", "control_count", "summary", "examples")} for result in results]
    comparisons = [paired_comparison(results, "grid", radius, family) for radius in RADII
                   for family in ("previously_fixed", "full_coefficients")]
    comparisons += [paired_comparison(results, "confirmation", 0.001, family) for family in ("previously_fixed", "full_coefficients")]
    summary = dict(status="completed private champion challenge; generation 3 not built or frozen", source_witness_sha256=digest(HERE / "inputs/champion_witness.json"),
                   started_at_utc=datetime.datetime.fromtimestamp(time.time() - (time.perf_counter() - started), datetime.timezone.utc).isoformat(),
                   elapsed_seconds=time.perf_counter() - started, assay_cases=sum(result["summary"]["case_count"] for result in results),
                   current_process_engine_evaluations=engine.evaluations, current_process_diagonalizations=engine.diagonalizations,
                   tests=tests, cells=compact, paired_comparisons=comparisons,
                   audit_before=audit_before, audit_after=frozen_audit(),
                   official_generation2_result_unchanged=True, original_portfolio_stopped=True, fresh_agents_launched=0,
                   claim_limits=spec["scope"])
    write_json(HERE / "summary.json", summary)
    print(json.dumps(dict(complete=True, seconds=summary["elapsed_seconds"], cases=summary["assay_cases"])), flush=True)


if __name__ == "__main__":
    main()
