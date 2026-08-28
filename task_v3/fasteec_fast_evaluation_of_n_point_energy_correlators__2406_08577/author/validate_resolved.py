import argparse
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import shlex
import subprocess
import tempfile
import time


UPSTREAM_COMMIT = "0736fc3c24d00f1ea7d08b8ea3c62ccd84f7b10e"
SEED = 682431
TOLERANCE = 2e-12
DIMENSIONS = ((9, 5, 7), (7, 1, 1), (8, 4, 8))
WEIGHT_FAMILIES = {
    3: ((1.0, 1.0), (0.6, 1.4), (2.0, 1.0), (1.0, 2.5), (1.7, 0.35)),
    4: ((1.0, 1.0, 1.0), (0.65, 1.4, 2.1), (2.0, 1.0, 1.0),
        (1.0, 2.0, 0.5), (1.0, 1.0, 2.0)),
}
LOG_MIN = -3.0
AUTHOR = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def command(arguments, **kwargs):
    result = subprocess.run(arguments, capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {shlex.join(map(str, arguments))}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def wrap(angle):
    angle = math.fmod(angle, 2.0 * math.pi)
    if angle > math.pi:
        angle -= 2.0 * math.pi
    if angle <= -math.pi:
        angle += 2.0 * math.pi
    return angle


def displacement(particle, special):
    return particle[0] - special[0], wrap(particle[1] - special[1])


def signed_angle(reference, target):
    first_norm = math.sqrt(reference[0] ** 2 + reference[1] ** 2)
    second_norm = math.sqrt(target[0] ** 2 + target[1] ** 2)
    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0
    first_x, first_y = reference[0] / first_norm, reference[1] / first_norm
    second_x, second_y = target[0] / second_norm, target[1] / second_norm
    return wrap(math.atan2(first_x * second_y - first_y * second_x,
                           first_x * second_x + first_y * second_y))


def extract_function(source, declaration):
    beginning = source.index(declaration)
    opening = source.index("{", beginning)
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[beginning:position + 1]
    raise AssertionError(f"Incomplete upstream function: {declaration}")


def verify_provenance():
    repository = AUTHOR / "ResolvedEnergyCorrelators"
    revision = command(["git", "-C", str(repository), "rev-parse", "HEAD"]).stdout.strip()
    require(revision == UPSTREAM_COMMIT, f"Unexpected upstream revision: {revision}")
    files = {}
    functions = {}
    for order in (3, 4):
        relative = f"write/src/new_enc_{order}particle.cc"
        content = (repository / relative).read_bytes()
        committed = subprocess.run(
            ["git", "-C", str(repository), "show", f"{UPSTREAM_COMMIT}:{relative}"],
            check=True, capture_output=True,
        ).stdout
        require(content == committed, f"Upstream source differs from its pinned blob: {relative}")
        source = content.decode()
        functions[order] = "\n\n".join(
            extract_function(source, declaration)
            for declaration in ("inline double mod2pi(", "double enc_azimuth(")
        )
        files[relative] = {"sha256": sha256(content), "matches_pinned_blob": True,
                           "geometry_sha256": sha256(functions[order].encode())}
        compact = " ".join(source.split())
        contact_default = "true" if order == 3 else "false"
        require(f'cmdln_bool("contact_terms", argc, argv, {contact_default})' in compact,
                f"Unexpected order-{order} contact default")
        if order == 4:
            require('"No support for contact terms yet."' in source,
                    "Upstream four-particle contact restriction changed")
            require('cmdln_bool("recursive_phi", argc, argv, true)' in compact,
                    "Upstream recursive azimuth default changed")
    return {"repository": "samcaf/ResolvedEnergyCorrelators", "commit": revision,
            "passed": True, "files": files}, functions


def verify_upstream_geometry(compiler, directory, functions):
    executable = directory / "upstream_geometry"
    program = """
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
constexpr double PI = 3.14159265358979323846;
constexpr double TWOPI = 2.0 * PI;
struct PseudoJet {
    double rapidity_value;
    double phi_value;
    double rap() const { return rapidity_value; }
    double phi() const { return phi_value; }
};
"""
    for order in (3, 4):
        program += f"\nnamespace upstream_{order} {{\n{functions[order]}\n}}\n"
    program += """
int main() {
    PseudoJet reference, special, target;
    std::cout << std::setprecision(17);
    while (std::cin >> reference.rapidity_value >> reference.phi_value
                   >> special.rapidity_value >> special.phi_value
                   >> target.rapidity_value >> target.phi_value) {
        std::cout << upstream_3::enc_azimuth(reference, special, target) << ' '
                  << upstream_4::enc_azimuth(reference, special, target) << '\\n';
    }
}
"""
    command(compiler + ["-std=c++17", "-O2", "-x", "c++", "-", "-o", str(executable)],
            input=program)
    probes = [
        ("positive_quarter_turn", (0.3, 0.0), (0.0, 0.0), (0.0, 0.2), math.pi / 2),
        ("negative_quarter_turn", (0.0, 0.3), (0.0, 0.0), (0.2, 0.0), -math.pi / 2),
        ("opposite_positive_pi", (0.3, 0.0), (0.0, 0.0), (-0.4, 0.0), math.pi),
        ("zero_reference", (0.0, 0.0), (0.0, 0.0), (0.1, 0.2), 0.0),
        ("zero_target", (0.1, 0.2), (0.0, 0.0), (0.0, 0.0), 0.0),
        ("phi_seam", (0.3, math.pi - 0.01), (0.0, math.pi - 0.01),
         (0.0, -math.pi + 0.02), math.pi / 2),
        ("general_positive", (0.2, 0.1), (-0.1, 0.0), (0.15, 0.4), None),
        ("general_negative", (0.15, 0.4), (-0.1, 0.0), (0.2, 0.1), None),
    ]
    content = "\n".join(" ".join(f"{value:.17g}" for point in probe[1:4] for value in point)
                        for probe in probes) + "\n"
    rows = command([str(executable)], input=content).stdout.splitlines()
    require(len(rows) == len(probes), "Incomplete upstream geometry output")
    cases = []
    for probe, row in zip(probes, rows):
        name, reference, special, target, analytic = probe
        expected = signed_angle(displacement(reference, special), displacement(target, special))
        values = list(map(float, row.split()))
        require(len(values) == 2 and all(math.isfinite(value) for value in values),
                f"Invalid upstream geometry output: {name}")
        errors = [abs(value - expected) for value in values]
        if analytic is not None:
            errors.append(abs(expected - analytic))
        cases.append({"name": name, "expected": expected, "analytic_expected": analytic,
                      "upstream_order3": values[0], "upstream_order4": values[1],
                      "max_abs_error": max(errors), "passed": max(errors) < TOLERANCE})
    return {"scope": "Unmodified upstream mod2pi/enc_azimuth with a rap/phi-only particle stub",
            "cases": cases, "max_abs_error": max(case["max_abs_error"] for case in cases),
            "passed": all(case["passed"] for case in cases)}


def fixtures():
    cases = {
        "singleton": [[(1.0, 0.0, 0.0)]],
        "two_unequal_weights": [[(2.0, 0.0, 0.0), (3.0, 0.4, 0.1)]],
        "equal_radii": [[(1.0, 0.0, 0.0), (1.0, 0.3, 0.0),
                          (1.0, -0.3, 0.0), (1.0, 0.0, 0.3)]],
        "coincident_and_zero_weight": [[(1.0, 0.0, 0.0), (2.0, 0.0, 0.0),
                                         (3.0, 0.4, 0.2), (0.0, 0.1, 0.1)]],
        "phi_seam": [[(1.0, 0.0, math.pi - 0.001), (4.0, 0.1, -math.pi + 0.003),
                      (2.0, -0.2, math.pi - 0.3), (3.0, 0.35, -math.pi + 0.2)]],
        "radial_overflow": [[(1.0, 0.0, 0.0), (2.0, 1.0, 0.0),
                             (3.0, -1.5, 0.0), (4.0, 0.0, math.pi)]],
    }
    randomizer = random.Random(SEED)
    for count in range(2, 8):
        cases[f"random_{count}"] = [[
            (10 ** randomizer.uniform(-3, 2), randomizer.uniform(-0.8, 0.8),
             randomizer.uniform(-math.pi, math.pi)) for _ in range(count)
        ]]
    cases["multiple_jets"] = (cases["two_unequal_weights"] + cases["phi_seam"]
                              + cases["radial_overflow"])
    return cases


def enumerate_histogram(jets, order, dimensions):
    bins, ratio_bins, phi_bins = dimensions
    histogram = [0.0] * (bins * (ratio_bins * phi_bins) ** (order - 2))

    def radius_cell(radius):
        if radius < 10 ** LOG_MIN:
            return 0
        if radius >= 1.0:
            return bins - 1
        return min(bins - 1, int(1 + (bins - 2) * (math.log10(radius) - LOG_MIN) / -LOG_MIN))

    def ratio_cell(ratio):
        return min(ratio_bins - 1, int(ratio * ratio_bins))

    def phi_cell(angle):
        return min(phi_bins - 1, int(phi_bins * (angle + math.pi) / (2 * math.pi)))

    for jet in jets:
        total = math.fsum(particle[0] for particle in jet)
        weights = [particle[0] / total for particle in jet]
        coordinates = [(particle[1], wrap(particle[2])) for particle in jet]
        for indices in itertools.product(range(len(jet)), repeat=order):
            if order == 4 and len(set(indices)) != 4:
                continue
            special = indices[0]
            vectors = [displacement(particle, coordinates[special]) for particle in coordinates]
            radii = [math.sqrt(vector[0] ** 2 + vector[1] ** 2) for vector in vectors]
            ordered = sorted(indices[1:], key=lambda index: (radii[index], index), reverse=True)
            if order == 3 and indices[1] == special and indices[2] == special:
                cells = [0, 0, phi_cell(0)]
            elif order == 3 and special in indices[1:]:
                other = next(index for index in indices[1:] if index != special)
                cells = [radius_cell(radii[other]), 0, phi_cell(0)]
            elif order == 3 and indices[1] == indices[2]:
                cells = [radius_cell(radii[indices[1]]), ratio_bins - 1, phi_cell(0)]
            else:
                outer, middle = ordered[:2]
                cells = [radius_cell(radii[outer]),
                         ratio_cell(radii[middle] / radii[outer] if radii[outer] else 0),
                         phi_cell(signed_angle(vectors[outer], vectors[middle]))]
                if order == 4:
                    inner = ordered[2]
                    cells += [ratio_cell(radii[inner] / radii[middle] if radii[middle] else 0),
                              phi_cell(signed_angle(vectors[middle], vectors[inner]))]
            flat_index = cells[0]
            for cell, dimension in zip(cells[1:], [ratio_bins, phi_bins, ratio_bins, phi_bins]):
                flat_index = flat_index * dimension + cell
            histogram[flat_index] += math.prod(weights[index] for index in indices) / len(jets)
    return histogram


def expected_mass(jets, order):
    if order == 3:
        return 1.0
    masses = []
    for jet in jets:
        total = math.fsum(particle[0] for particle in jet)
        masses.append(24 * math.fsum(
            math.prod(jet[index][0] / total for index in indices)
            for indices in itertools.combinations(range(len(jet)), 4)
        ))
    return math.fsum(masses) / len(jets)


def transcribe_weighted_histogram(jets, order, dimensions, exponents):
    bins, ratio_bins, phi_bins = dimensions
    angular_size = ratio_bins * phi_bins
    histogram = [0.0] * (bins * angular_size ** (order - 2))

    def radius_cell(radius):
        if radius < 10 ** LOG_MIN:
            return 0
        if radius >= 1.0:
            return bins - 1
        return min(bins - 1, int(1 + (bins - 2) * (math.log10(radius) - LOG_MIN) / -LOG_MIN))

    def ratio_cell(inner_radius, outer_radius):
        ratio = inner_radius / outer_radius if outer_radius else 0.0
        return min(ratio_bins - 1, int(ratio * ratio_bins))

    def phi_cell(angle):
        return min(phi_bins - 1, int(phi_bins * (angle + math.pi) / (2 * math.pi)))

    def difference(prefix, weight, exponent):
        return math.pow(prefix + weight, exponent) - math.pow(prefix, exponent)

    zero_phi = phi_cell(0.0)
    for jet in jets:
        total = math.fsum(particle[0] for particle in jet)
        weights = [particle[0] / total for particle in jet]
        coordinates = [(particle[1], wrap(particle[2])) for particle in jet]
        for special in range(len(jet)):
            special_weight = weights[special]
            vectors = [displacement(particle, coordinates[special]) for particle in coordinates]
            radii = [math.sqrt(vector[0] ** 2 + vector[1] ** 2) for vector in vectors]
            ranked = sorted((index for index in range(len(jet)) if index != special),
                            key=lambda index: (radii[index], index))
            sum_weight1 = special_weight
            if order == 3:
                histogram[zero_phi] += math.pow(special_weight, 1.0 + sum(exponents))
            for outer_rank, outer in enumerate(ranked):
                first_weight = weights[outer]
                first_cell = radius_cell(radii[outer])
                sum_weight2 = [0.0] * phi_bins
                sum_weight2[zero_phi] = special_weight
                if order == 3:
                    histogram[first_cell * angular_size + zero_phi] += (
                        2.0 * math.pow(special_weight, 1.0 + exponents[1])
                        * math.pow(first_weight, exponents[0])
                    )
                    histogram[first_cell * angular_size + (ratio_bins - 1) * phi_bins
                              + zero_phi] += special_weight * math.pow(first_weight, sum(exponents))
                for middle_rank in range(outer_rank):
                    middle = ranked[middle_rank]
                    second_weight = weights[middle]
                    second_cell = ratio_cell(radii[middle], radii[outer])
                    second_phi = phi_cell(signed_angle(vectors[outer], vectors[middle]))
                    first_delta = difference(sum_weight1, first_weight, exponents[0])
                    second_delta = difference(sum_weight2[second_phi], second_weight, exponents[1])
                    prefix = (first_cell * ratio_bins + second_cell) * phi_bins + second_phi
                    if order == 3:
                        histogram[prefix] += 2.0 * special_weight * first_delta * second_delta
                    else:
                        sum_weight3 = [0.0] * phi_bins
                        sum_weight3[zero_phi] = special_weight
                        for inner_rank in range(middle_rank):
                            inner = ranked[inner_rank]
                            third_weight = weights[inner]
                            third_cell = ratio_cell(radii[inner], radii[middle])
                            third_phi = phi_cell(signed_angle(vectors[middle], vectors[inner]))
                            third_delta = difference(sum_weight3[third_phi], third_weight, exponents[2])
                            flat_index = (prefix * ratio_bins + third_cell) * phi_bins + third_phi
                            histogram[flat_index] += (6.0 * special_weight * first_delta
                                                      * second_delta * third_delta)
                            sum_weight3[third_phi] += third_weight
                    sum_weight2[second_phi] += second_weight
                sum_weight1 += first_weight
    return [value / len(jets) for value in histogram]


def serialize_events(jets):
    return "\n".join(
        f"{event_id} {pt:.17g} {rapidity:.17g} {phi:.17g}"
        for event_id, jet in enumerate(jets) for pt, rapidity, phi in jet
    ) + "\n"


def check_case(executable, directory, name, jets, order, dimensions, exponents=None):
    input_file, output_file = directory / "events.txt", directory / "histogram.txt"
    content = serialize_events(jets)
    input_file.write_text(content)
    arguments = [str(executable), str(input_file), str(len(jets)), str(order), str(LOG_MIN),
                 *map(str, dimensions), str(output_file)]
    if exponents is not None:
        arguments.extend(map(str, exponents))
    started = time.perf_counter()
    command(arguments)
    elapsed = time.perf_counter() - started
    actual = [float(value) for value in output_file.read_text().split()]
    expected = (enumerate_histogram(jets, order, dimensions) if exponents is None
                else transcribe_weighted_histogram(jets, order, dimensions, exponents))
    require(len(actual) == len(expected), f"Wrong output length for {name}, order {order}")
    require(all(math.isfinite(value) for value in actual), f"Nonfinite output for {name}")
    errors = [abs(left - right) for left, right in zip(actual, expected)]
    worst = max(range(len(errors)), key=errors.__getitem__)
    total_mass = math.fsum(actual)
    unit_exponents = exponents is None or all(exponent == 1.0 for exponent in exponents)
    target_mass = expected_mass(jets, order) if unit_exponents else math.fsum(expected)
    mass_error = abs(total_mass - target_mass)
    return {"fixture": name, "order": order, "dimensions": list(dimensions),
            "exponents": list(exponents) if exponents is not None else [1.0] * (order - 1),
            "default_cli": exponents is None,
            "oracle": ("independent_ordered_tuple_enumeration" if exponents is None
                       else "slow_literal_upstream_cumulative_transcription"),
            "analytic_mass_identity_checked": unit_exponents,
            "jet_count": len(jets), "multiplicities": list(map(len, jets)),
            "input_sha256": sha256(content.encode()), "cells": len(actual),
            "max_abs_bin_error": errors[worst], "l1_error": math.fsum(errors),
            "worst_cell": worst, "worst_actual": actual[worst],
            "worst_expected": expected[worst], "actual_mass": total_mass,
            "expected_mass": target_mass, "mass_error": mass_error,
            "oracle_mass_error": abs(math.fsum(expected) - target_mass),
            "runtime_seconds": elapsed,
            "passed": (errors[worst] < TOLERANCE and mass_error < TOLERANCE
                       and abs(math.fsum(expected) - target_mass) < TOLERANCE)}


def main():
    parser = argparse.ArgumentParser(description="Independent unit and generalized resolved-correlator validation.")
    parser.add_argument("--cxx", default=os.environ.get("CXX", "g++"))
    parser.add_argument("--reuse-binary", action="store_true",
                        help="Use the existing author/bin/resolved_reference instead of rebuilding it.")
    arguments = parser.parse_args()
    compiler = shlex.split(arguments.cxx)
    executable = AUTHOR / "bin" / "resolved_reference"
    source = AUTHOR / "adapters" / "resolved_reference.cpp"
    report_path = AUTHOR / "resolved_validation.json"
    report = {"schema_version": 2, "passed": False, "seed": SEED,
              "expected_case_count": 78, "tolerance": TOLERANCE, "log_min": LOG_MIN,
              "expected_weighted_case_count": 390,
              "weight_families": WEIGHT_FAMILIES,
              "radial_convention": "Dedicated underflow/overflow; bins-2 finite log cells ending at R=1",
              "output_convention": "Arithmetic-mean bin mass, not density",
              "contact_convention": {"3": "Unit-inclusive; literal source contact formula otherwise",
                                     "4": "pairwise-distinct only"},
              "semantic_warnings": [
                  "Non-unit contact terms are not a verified normalized inclusive continuation.",
                  "Phi-local non-unit finite differences can depend on azimuth binning.",
                  "The adapter evaluates finite differences stably; the slow oracle uses direct subtraction.",
              ],
              "tie_convention": "Input-row order for equal radii", "cases": [], "weighted_cases": []}
    try:
        require(bool(compiler), "Empty compiler command")
        report["provenance"], functions = verify_provenance()
        original_source = source.read_bytes()
        original_contract = (AUTHOR / "specs" / "resolved_contract.md").read_bytes()
        report["adapter_sha256"] = sha256(original_source)
        report["contract_sha256"] = sha256(original_contract)
        if not arguments.reuse_binary:
            executable.parent.mkdir(parents=True, exist_ok=True)
            build_command = compiler + ["-std=c++17", "-O3", "-Wall", "-Wextra", "-Wpedantic",
                                        "-pipe", str(source), "-o", str(executable)]
            report["build"] = {"command": build_command,
                               "diagnostics": command(build_command).stderr, "reused": False}
        else:
            require(executable.is_file(), f"Missing existing binary: {executable}")
            report["build"] = {"reused": True}
        report["binary_sha256"] = sha256(executable.read_bytes())
        report["fixtures"] = fixtures()
        with tempfile.TemporaryDirectory(prefix="resolved-validation-") as scratch:
            directory = Path(scratch)
            report["upstream_geometry"] = verify_upstream_geometry(compiler, directory, functions)
            require(report["upstream_geometry"]["passed"], "Upstream signed-angle checks failed")
            for order in (3, 4):
                for dimensions in DIMENSIONS:
                    for name, jets in report["fixtures"].items():
                        report["cases"].append(check_case(executable, directory, name, jets,
                                                          order, dimensions))
                    for exponents in WEIGHT_FAMILIES[order]:
                        for name, jets in report["fixtures"].items():
                            report["weighted_cases"].append(check_case(
                                executable, directory, name, jets, order, dimensions, exponents,
                            ))
            contact_caveat = check_case(
                executable, directory, "two_equal_nonunit_contacts",
                [[(1.0, 0.0, 0.0), (1.0, 0.4, 0.1)]], 3, (9, 5, 7), (2.0, 1.0),
            )
            contact_caveat["analytic_source_mass"] = 0.5
            contact_caveat["passed"] = (contact_caveat["passed"]
                                         and abs(contact_caveat["actual_mass"] - 0.5) < TOLERANCE)
            report["source_contact_caveat"] = contact_caveat
            input_file, output_file = directory / "short.txt", directory / "must_not_exist.txt"
            input_file.write_text(serialize_events(report["fixtures"]["singleton"]))
            failure = subprocess.run(
                [str(executable), str(input_file), "2", "3", str(LOG_MIN), "9", "5", "7",
                 str(output_file)], capture_output=True, text=True,
            )
            report["too_few_events"] = {"returncode": failure.returncode, "stderr": failure.stderr,
                                        "passed": failure.returncode != 0 and not output_file.exists()}
            report["invalid_exponent_checks"] = []
            invalid_exponents = (
                (3, ("1",)), (3, ("0", "1")), (3, ("nan", "1")),
                (3, ("1", "1", "1")), (4, ("1", "1")), (4, ("1", "-1", "1")),
                (4, ("1", "1", "inf")), (4, ("1", "1", "1", "1")),
            )
            for index, (order, exponents) in enumerate(invalid_exponents):
                rejected_output = directory / f"invalid_exponents_{index}.txt"
                rejected = subprocess.run(
                    [str(executable), str(input_file), "1", str(order), str(LOG_MIN),
                     "9", "5", "7", str(rejected_output), *exponents],
                    capture_output=True, text=True,
                )
                report["invalid_exponent_checks"].append({
                    "order": order, "arguments": exponents, "returncode": rejected.returncode,
                    "stderr": rejected.stderr,
                    "passed": rejected.returncode != 0 and not rejected_output.exists(),
                })
        require(source.read_bytes() == original_source, "Adapter changed during validation")
        require((AUTHOR / "specs" / "resolved_contract.md").read_bytes() == original_contract,
                "Contract changed during validation")
        report["passed"] = (len(report["cases"]) == 78
                            and all(case["passed"] for case in report["cases"])
                            and len(report["weighted_cases"]) == 390
                            and all(case["passed"] for case in report["weighted_cases"])
                            and report["source_contact_caveat"]["passed"]
                            and all(case["passed"] for case in report["invalid_exponent_checks"])
                            and report["too_few_events"]["passed"])
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    report["case_count"] = len(report["cases"])
    report["passed_case_count"] = sum(case["passed"] for case in report["cases"])
    report["weighted_case_count"] = len(report["weighted_cases"])
    report["passed_weighted_case_count"] = sum(case["passed"] for case in report["weighted_cases"])
    all_cases = report["cases"] + report["weighted_cases"]
    report["total_case_count"] = len(all_cases)
    report["max_abs_bin_error"] = max((case["max_abs_bin_error"] for case in all_cases),
                                       default=None)
    report["max_mass_error"] = max((case["mass_error"] for case in all_cases), default=None)
    report["max_l1_error"] = max((case["l1_error"] for case in all_cases), default=None)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("passed", "case_count", "passed_case_count", "weighted_case_count",
                       "passed_weighted_case_count", "max_abs_bin_error",
                       "max_mass_error")}, sort_keys=True))
    print(f"Report: {report_path}")
    if "error" in report:
        print(report["error"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
