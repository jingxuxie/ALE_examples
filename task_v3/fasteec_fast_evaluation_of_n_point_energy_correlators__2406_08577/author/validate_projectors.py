"""Independent, deliberately low-multiplicity validation of the private projectors."""

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from functools import lru_cache
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import time
import traceback


ROOT = Path(__file__).resolve().parent.parent
BINARIES = (
    "eec_fast", "eec_fast_weight", "eec_fast_kt", "eec_fast_kt_weight",
    "eec_fast_nu_point",
)
HEADERS = ("eec_compute.h", "eec_higher_weight.h", "eec_nu_point.h",
           "read_events.h", "banner.h")
PRECISION = 70
EXACT_RESOLUTION = 1e30
LOG_MIN = -4.5
BINS = 73
ABS_TOL = 2e-11
L1_TOL = 1e-10
ZERO = Decimal(0)
ONE = Decimal(1)
FIXTURES = {
    "singleton": ((13.0, 0.31, 2.94),),
    "seam_pair": ((2.0, -0.2, 3.02), (1.0, 0.27, -3.03)),
    "triangle": ((9.0, 0.05, 0.12), (3.0, 0.23, -0.08), (1.0, -0.27, 0.21)),
    "square": ((8.0, -0.16, -0.16), (8.0, -0.16, 0.16),
               (8.0, 0.16, -0.16), (8.0, 0.16, 0.16)),
    "five": ((7.0, -0.33, -0.12), (2.5, -0.11, 0.23),
             (4.0, 0.29, 0.06), (0.7, 0.14, -0.32), (1.3, 0.03, 0.1)),
    "hierarchical": ((2.3, -0.27, -0.24), (1.1, -0.252, -0.218),
                     (0.4, -0.1, -0.04), (3.2, 0.25, 0.22),
                     (0.7, 0.294, 0.271)),
    "underflow": ((2.0, 0.0, 0.0), (1.0, 3e-7, 4e-7)),
    "overflow": ((3.0, -0.57, -0.22), (1.0, 0.57, 0.22)),
}


GEOMETRY_DRIVER = r"""
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include "fastjet/ClusterSequence.hh"

void emit_jet(const fastjet::PseudoJet &jet) {
    std::vector<int> members;
    for (const auto &constituent : jet.constituents())
        members.push_back(constituent.user_index());
    std::sort(members.begin(), members.end());
    std::cout << "{\"pt\":" << jet.pt() << ",\"rapidity\":" << jet.rap()
              << ",\"phi\":" << jet.phi_std() << ",\"members\":[";
    for (std::size_t index = 0; index < members.size(); ++index) {
        if (index) std::cout << ',';
        std::cout << members[index];
    }
    std::cout << "]}";
}

void emit_node(const fastjet::PseudoJet &jet, const std::string &mode,
               double resolution, int cap, bool wrong_kt_cut) {
    fastjet::PseudoJet first, second;
    if (!jet.has_parents(first, second)) {
        std::cout << "{\"leaf\":";
        emit_jet(jet);
        std::cout << '}';
        return;
    }
    const double theta_squared = first.squared_distance(second);
    double cut = theta_squared / (1.5 * 1.5 * resolution);
    if (wrong_kt_cut) cut *= std::min(first.perp2(), second.perp2());
    auto left = mode == "fractional" ? first.exclusive_subjets_up_to(cap / 2)
                                     : first.exclusive_subjets(cut);
    auto right = mode == "fractional" ? second.exclusive_subjets_up_to(cap / 2)
                                      : second.exclusive_subjets(cut);
    std::cout << "{\"theta_squared\":" << theta_squared << ",\"cut\":" << cut
              << ",\"left_count\":" << left.size() << ",\"subjets\":[";
    left.insert(left.end(), right.begin(), right.end());
    for (std::size_t index = 0; index < left.size(); ++index) {
        if (index) std::cout << ',';
        emit_jet(left[index]);
    }
    std::cout << "],\"children\":[";
    emit_node(first, mode, resolution, cap, wrong_kt_cut);
    std::cout << ',';
    emit_node(second, mode, resolution, cap, wrong_kt_cut);
    std::cout << "]}";
}

int main(int argc, char **argv) {
    try {
        if (argc != 8) throw std::runtime_error("geometry driver arguments");
        const int event_count = std::stoi(argv[2]);
        const std::string mode = argv[3];
        const double resolution = std::stod(argv[4]);
        const int cap = std::stoi(argv[5]);
        const auto scheme = std::string(argv[6]) == "pt" ? fastjet::pt_scheme
                                                        : fastjet::E_scheme;
        const bool wrong_kt_cut = std::string(argv[7]) == "wrong_kt_cut";
        std::vector<std::vector<fastjet::PseudoJet>> events(event_count);
        std::ifstream input(argv[1]);
        int event_id;
        double transverse, rapidity, phi;
        while (input >> event_id >> transverse >> rapidity >> phi) {
            if (event_id < 0 || event_id >= event_count)
                throw std::runtime_error("event ID out of range");
            const double momentum_x = transverse * std::cos(phi);
            const double momentum_y = transverse * std::sin(phi);
            const double momentum_z = transverse * std::sinh(rapidity);
            const double energy = std::sqrt(momentum_x * momentum_x
                + momentum_y * momentum_y + momentum_z * momentum_z);
            fastjet::PseudoJet particle(momentum_x, momentum_y, momentum_z, energy);
            particle.set_user_index(events[event_id].size());
            events[event_id].push_back(particle);
        }
        fastjet::ClusterSequence::set_fastjet_banner_stream(nullptr);
        std::cout << std::setprecision(17) << "{\"events\":[";
        for (int index = 0; index < event_count; ++index) {
            if (events[index].empty() || events[index].size() > 5)
                throw std::runtime_error("only 1..5 particles are permitted");
            fastjet::JetDefinition definition(fastjet::genkt_algorithm, 1.5,
                                              mode == "kt" ? 1.0 : 0.0, scheme);
            fastjet::ClusterSequence sequence(events[index], definition);
            const auto jets = sequence.inclusive_jets(0);
            if (jets.size() != 1) throw std::runtime_error("fixture is not one jet");
            double scalar = 0;
            for (const auto &particle : events[index]) scalar += particle.pt();
            if (index) std::cout << ',';
            std::cout << "{\"scalar_pt\":" << scalar << ",\"root_pt\":"
                      << jets[0].pt() << ",\"tree\":";
            emit_node(jets[0], mode, resolution, cap, wrong_kt_cut);
            std::cout << '}';
        }
        std::cout << "]}\n";
    } catch (const std::exception &error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
"""


def decimal_input(value):
    return Decimal(format(value, ".17g"))


def sha256_bytes(contents):
    return hashlib.sha256(contents).hexdigest()


def sha256_file(path):
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bin_index(distance):
    if distance <= 10 ** LOG_MIN:
        return 0
    return min(BINS - 1, max(0, math.floor((math.log10(distance) - LOG_MIN)
                                         * BINS / -LOG_MIN)))


def support_bins(axes):
    if not 1 <= len(axes) <= 5:
        raise ValueError("The independent oracle is restricted to 1..5 particles")
    pair_bins = {}
    for first in range(len(axes)):
        for second in range(first):
            distance = math.hypot(axes[first][0] - axes[second][0],
                                  math.remainder(axes[first][1] - axes[second][1],
                                                 math.tau))
            pair_bins[first, second] = bin_index(distance)
    return [max((position for (first, second), position in pair_bins.items()
                 if mask & (1 << first) and mask & (1 << second)), default=0)
            for mask in range(1 << len(axes))]


@lru_cache(maxsize=None)
def ordered_occupancies(particle_count, order):
    """Count actual ordered tuples, not the official unordered-tuple algorithm."""
    if not 1 <= particle_count <= 5 or not 1 <= order <= 8:
        raise ValueError("ordered tuple oracle limits exceeded")
    counts = Counter()
    for ordered_tuple in product(range(particle_count), repeat=order):
        exponents = [0] * particle_count
        for particle_index in ordered_tuple:
            exponents[particle_index] += 1
        counts[tuple(exponents)] += 1
    if sum(counts.values()) != particle_count ** order:
        raise AssertionError("ordered enumeration lost tuples")
    return tuple((exponents, multiplicity,
                  sum(1 << index for index, exponent in enumerate(exponents) if exponent))
                 for exponents, multiplicity in counts.items())


def crosses_split(mask, left_count):
    return left_count is None or (mask & ((1 << left_count) - 1)
                                  and mask >> left_count)


def ordered_histogram(axes, weights, order, left_count=None):
    positions = support_bins(axes)
    histogram = [ZERO] * BINS
    powers = [[weight ** exponent for exponent in range(order + 1)]
              for weight in weights]
    for exponents, multiplicity, mask in ordered_occupancies(len(weights), order):
        if not crosses_split(mask, left_count):
            continue
        contribution = Decimal(multiplicity)
        for index, exponent in enumerate(exponents):
            contribution *= powers[index][exponent]
        histogram[positions[mask]] += contribution
    return histogram


def subset_histogram(axes, fractions, nu, left_count=None):
    """Direct alternating subset sums; never subtract previously computed W(T)."""
    positions = support_bins(axes)
    powers = [ZERO] + [sum((fraction for index, fraction in enumerate(fractions)
                           if mask & (1 << index)), ZERO) ** nu
                        for mask in range(1, 1 << len(fractions))]
    histogram = [ZERO] * BINS
    signed_measures = []
    for mask in range(1, 1 << len(fractions)):
        if not crosses_split(mask, left_count):
            continue
        contribution = ZERO
        submask = mask
        while submask:
            sign = -1 if (mask.bit_count() - submask.bit_count()) % 2 else 1
            contribution += sign * powers[submask]
            submask = (submask - 1) & mask
        histogram[positions[mask]] += contribution
        signed_measures.append(contribution)
    return histogram, signed_measures


def fractions_for(event):
    momenta = [decimal_input(particle[0]) for particle in event]
    total = sum(momenta, ZERO)
    return [momentum / total for momentum in momenta]


def exact_histogram(event, query):
    axes = [(particle[1], particle[2]) for particle in event]
    fractions = fractions_for(event)
    if "nu" in query:
        return subset_histogram(axes, fractions, decimal_input(query["nu"]))[0]
    weights = [fraction ** decimal_input(query["kappa"]) for fraction in fractions]
    return ordered_histogram(axes, weights, query["order"])


def mean_histograms(histograms):
    return [sum(column, ZERO) / len(histograms) for column in zip(*histograms)]


def finite_histogram(event, tree, query, wrong_subjet_power=False):
    """Enumerate the public prescription on FastJet-only geometry, not EEC code."""
    fractions = fractions_for(event)
    total = sum((decimal_input(particle[0]) for particle in event), ZERO)

    def visit(node):
        if "leaf" in node:
            particle_index = node["leaf"]["members"][0]
            exponent = (decimal_input(query["nu"]) if "nu" in query else
                        decimal_input(query["kappa"]) * query["order"])
            result = [ZERO] * BINS
            result[0] = fractions[particle_index] ** exponent
            return result
        axes = [(subjet["rapidity"], subjet["phi"]) for subjet in node["subjets"]]
        if "nu" in query:
            weights = [decimal_input(subjet["pt"]) / total for subjet in node["subjets"]]
            result = subset_histogram(axes, weights, decimal_input(query["nu"]),
                                      node["left_count"])[0]
        else:
            kappa = decimal_input(query["kappa"])
            if kappa == ONE or wrong_subjet_power:
                weights = [(decimal_input(subjet["pt"]) / total) ** kappa
                           for subjet in node["subjets"]]
            else:
                weights = [sum((fractions[index] ** kappa for index in subjet["members"]),
                               ZERO) for subjet in node["subjets"]]
            result = ordered_histogram(axes, weights, query["order"], node["left_count"])
        children = [visit(child) for child in node["children"]]
        return [sum(column, ZERO) for column in zip(result, *children)]

    return visit(tree)


def tree_nodes(tree):
    if "leaf" not in tree:
        yield tree
        for child in tree["children"]:
            yield from tree_nodes(child)


def metrics(observed, expected):
    if len(observed) != len(expected):
        raise ValueError("histogram lengths differ")
    observed = list(map(float, observed))
    expected = list(map(float, expected))
    if not all(math.isfinite(value) for value in observed + expected):
        raise ValueError("nonfinite histogram")
    errors = [abs(actual - target) for actual, target in zip(observed, expected)]
    worst = max(range(len(errors)), key=errors.__getitem__)
    return {"max_absolute_error": errors[worst], "l1_error": math.fsum(errors),
            "worst_bin": worst, "observed_at_worst_bin": observed[worst],
            "expected_at_worst_bin": expected[worst],
            "observed_total": math.fsum(observed), "expected_total": math.fsum(expected)}


def contract_strings(contents):
    module = ast.parse(contents)
    strings = {}
    for statement in module.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id in ("COMMON", "WEIGHTED", "FRACTIONAL"):
                    strings[target.id] = ast.literal_eval(statement.value)
    return strings, module


class Validator:
    def __init__(self, root, temporary, compiler):
        self.root = root
        self.author = root / "author"
        self.temporary = temporary
        self.compiler = compiler
        self.checks = []
        self.runs = []
        self.run_cache = {}
        self.geometry_cache = {}
        self.fixture_files = {}
        self.builder_bytes = (self.author / "build_pilots.py").read_bytes()
        self.source_bytes = {name: (self.author / "FastEEC" / name).read_bytes()
                             for name in HEADERS + tuple(name + ".cc" for name in BINARIES)}
        monitored = [self.author / "bin" / name for name in BINARIES]
        monitored += [self.author / "FastEEC" / name for name in self.source_bytes]
        monitored += [self.author / "build_pilots.py", Path(__file__).resolve(),
                      self.author / "fastjet" / "lib" / "libfastjet.a"]
        monitored += sorted((self.author / "reference_source").glob("eec*"))
        monitored += sorted((self.root / "pilots").glob("*/participant/input/CONTRACT.md"))
        self.monitored = monitored
        self.hashes_before = {str(path.relative_to(root)): sha256_file(path) for path in monitored}
        self.report = {
            "schema_version": 1,
            "started_utc": datetime.now(timezone.utc).isoformat(),
            "scope": {
                "oracle_max_particles": 5, "decimal_working_digits": PRECISION,
                "integer_oracle": "Enumerate every ordered tuple with replacement, then group identical exponent vectors for Decimal accumulation.",
                "fractional_oracle": "Direct inclusion/exclusion over all nonempty sub-subsets; no official recurrence or projector imports.",
                "finite_resolution_oracle": "FastJet primitives supply pt_scheme trees/axes only; independent tuple/subset enumeration evaluates the public contract.",
                "driver": "Fresh official-source executables with 17-digit double output; these are implementation cross-checks, NOT independent oracles or higher-precision arithmetic.",
                "exact_integer_resolution": EXACT_RESOLUTION,
                "exact_fractional_nsub": 16,
                "near_integer_errors": "Absolute bin and L1 errors only; no relative error on cancelling or vanishing measures.",
                "limitations": [
                    "No accuracy or throughput claim for large-M or 16-subjet double-precision recurrence.",
                    "70 digits describes low-M oracle working precision, not achieved accuracy of the official implementation.",
                    "Finite-resolution geometry intentionally depends on FastJet, but exact particle-level oracles do not.",
                    "No tournament, CMS data, reference data, official source, or public contract is modified.",
                ],
                "persistent_output": "author/projector_validation.json",
                "other_persistent_writes_by_validator": [],
                "temporary_builds": "TemporaryDirectory under /tmp, removed on exit",
            },
            "axis": {"log_min": LOG_MIN, "bins": BINS, "overflow": "last", "contact": "first"},
            "tolerances": {"oracle_max_absolute": ABS_TOL, "oracle_l1": L1_TOL,
                           "binary_driver_max_absolute": 2e-14, "binary_driver_l1": 2e-13},
            "fixtures": FIXTURES,
            "checks": self.checks,
            "runs": self.runs,
            "near_integer": [],
            "square_signed_masses": [],
            "negative_controls": [],
        }

    def assertion(self, name, passed, **details):
        self.checks.append({"name": name, "category": "assertion", "passed": bool(passed),
                            **details})

    def compare(self, name, observed, expected, category, abs_tol=ABS_TOL, l1_tol=L1_TOL):
        result = metrics(observed, expected)
        result.update(name=name, category=category, max_absolute_tolerance=abs_tol,
                      l1_tolerance=l1_tol,
                      passed=result["max_absolute_error"] <= abs_tol and result["l1_error"] <= l1_tol)
        self.checks.append(result)
        return result

    def command(self, arguments, timeout=180):
        process = subprocess.run(list(map(str, arguments)), capture_output=True, text=True,
                                 timeout=timeout, check=True, cwd=self.temporary)
        if "Error:" in process.stdout or "Error:" in process.stderr:
            raise RuntimeError("official program reported an error: " + process.stdout + process.stderr)
        return process

    def compile_drivers(self):
        print("Compiling round-trip-precision drivers and FastJet-only geometry probe", flush=True)
        source_dir = self.temporary / "drivers"
        source_dir.mkdir()
        for name in HEADERS:
            (source_dir / name).write_bytes(self.source_bytes[name])
        common = [self.compiler, "-O3", "-std=c++17",
                  "-I" + str(self.author / "fastjet" / "include")]
        library = self.author / "fastjet" / "lib" / "libfastjet.a"
        build_records = []
        for name in BINARIES:
            original = self.source_bytes[name + ".cc"].decode()
            if original.count("f.open(fname);") != 1:
                raise ValueError("Cannot instrument official output precision safely")
            driver_source = original.replace("f.open(fname);",
                                             "f.open(fname);\n    f.precision(17);")
            source_path = source_dir / (name + ".cc")
            source_path.write_text(driver_source)
            executable = source_dir / name
            command = common + [source_path, library, "-lm", "-o", executable]
            self.command(command)
            build_records.append({"name": name, "source_sha256": sha256_file(source_path),
                                  "binary_sha256": sha256_file(executable),
                                  "flags": ["-O3", "-std=c++17", "-lm"], "output_digits": 17})
            reference = self.author / "reference_source" / (name + ".cc")
            self.assertion("private_source_precision_only/" + name,
                           reference.read_text() == driver_source,
                           evidence="Official source plus f.precision(17), no algorithm edit")
        geometry_source = source_dir / "geometry.cpp"
        geometry_source.write_text(GEOMETRY_DRIVER)
        self.geometry_executable = source_dir / "geometry"
        self.command(common + [geometry_source, library, "-lm", "-o", self.geometry_executable])
        self.drivers = source_dir
        self.report["builds"] = build_records
        self.report["geometry_probe"] = {"source_sha256": sha256_file(geometry_source),
                                         "binary_sha256": sha256_file(self.geometry_executable),
                                         "includes_official_projector": False}
        self.report["environment"] = {
            "python": platform.python_version(),
            "compiler": self.command([self.compiler, "--version"]).stdout.splitlines()[0],
            "fastjet": self.command([self.author / "fastjet" / "bin" / "fastjet-config",
                                      "--version"]).stdout.strip(),
        }

    def events_file(self, events):
        text = "".join(f"{event_index} " + " ".join(format(value, ".17g") for value in particle)
                       + "\n" for event_index, event in enumerate(events) for particle in event)
        digest = sha256_bytes(text.encode())
        if digest not in self.fixture_files:
            path = self.temporary / ("events_" + digest + ".txt")
            path.write_text(text)
            self.fixture_files[digest] = path
        return self.fixture_files[digest], digest

    def geometry(self, events, query, scheme="pt", wrong_kt_cut=False):
        path, digest = self.events_file(events)
        mode = "fractional" if "nu" in query else query["algorithm"]
        options = [mode, query.get("resolution", EXACT_RESOLUTION), query.get("nsub", 16),
                   scheme, "wrong_kt_cut" if wrong_kt_cut else "angular_cut"]
        key = (digest, *options)
        if key not in self.geometry_cache:
            self.geometry_cache[key] = json.loads(self.command(
                [self.geometry_executable, path, len(events), *options]).stdout)["events"]
        return self.geometry_cache[key]

    def evaluate(self, label, events, query, finite=False):
        path, digest = self.events_file(events)
        cache_key = (digest, json.dumps(query, sort_keys=True), finite)
        if cache_key in self.run_cache:
            return self.run_cache[cache_key]
        if "nu" in query:
            name = "eec_fast_nu_point"
            options = [query["nu"], query["nsub"], LOG_MIN, BINS]
        else:
            name = "eec_fast" + ("_kt" if query["algorithm"] == "kt" else "")
            if query["kappa"] != 1:
                name += "_weight"
            options = [query["order"], query["resolution"]]
            if query["kappa"] != 1:
                options += [query["kappa"]]
            options += [LOG_MIN, BINS]
        output_paths = [self.temporary / (f"run_{len(self.runs)}_{kind}.txt")
                        for kind in ("binary", "driver")]
        histograms = []
        for executable, output in zip((self.author / "bin" / name, self.drivers / name), output_paths):
            self.command([executable, path, len(events), *options, output])
            numbers = list(map(float, output.read_text().split()))
            if numbers[:4] != [float(len(events)), float(BINS), LOG_MIN, 0.0]:
                raise ValueError("unexpected official output header")
            if len(numbers) != BINS + 4:
                raise ValueError("unexpected official output length")
            histograms.append([value / len(events) for value in numbers[4:]])
        if finite:
            geometries = self.geometry(events, query)
            expected = mean_histograms([finite_histogram(event, geometry["tree"], query)
                                       for event, geometry in zip(events, geometries)])
            oracle_name = "independent finite-resolution enumeration"
        else:
            expected = mean_histograms([exact_histogram(event, query) for event in events])
            oracle_name = "independent exact low-M enumeration"
        binary, driver = histograms
        comparison = self.compare(label + "/binary_oracle", binary, expected, "binary_oracle")
        self.compare(label + "/driver_oracle", driver, expected, "driver_oracle")
        self.compare(label + "/binary_driver", binary, driver, "binary_driver", 2e-14, 2e-13)
        normalization = ONE if "nu" in query else sum(
            (sum((fraction ** decimal_input(query["kappa"]) for fraction in fractions_for(event)),
                 ZERO) ** query["order"] for event in events), ZERO) / len(events)
        self.compare(label + "/scalar_moment_normalization", [math.fsum(binary)], [normalization],
                     "normalization")
        run = {"id": label, "binary": name, "query": query, "event_count": len(events),
               "particle_counts": list(map(len, events)), "events_sha256": digest,
               "oracle": oracle_name,
               "binary_output_sha256": sha256_file(output_paths[0]),
               "driver_output_sha256": sha256_file(output_paths[1]),
               "max_absolute_error": comparison["max_absolute_error"],
               "l1_error": comparison["l1_error"]}
        self.runs.append(run)
        result = {"binary": binary, "driver": driver, "oracle": expected, "run": run}
        self.run_cache[cache_key] = result
        return result

    def validate_contracts(self):
        strings, module = contract_strings(self.builder_bytes)
        common = " ".join(strings["COMMON"].split())
        weighted = " ".join(strings["WEIGHTED"].split())
        fractional = " ".join(strings["FRACTIONAL"].split())
        clauses = {
            "common_per_jet_mean": (common, "per-jet mean bin"),
            "common_contact_and_overflow": (common, "Clamp underflow (including zero/contact) to bin zero and overflow to the last bin"),
            "weighted_ordered_replacement": (weighted, "ordered order-tuples **with replacement**"),
            "weighted_pt_scheme": (weighted, "R=1.5 and `pt_scheme`"),
            "weighted_kt_angular_cut": (weighted, "exclusive_subjets(theta^2/(1.5^2*resolution))"),
            "weighted_constituent_moment": (weighted, "sum of constituent pt^kappa"),
            "weighted_original_scalar": (weighted, "original scalar total pt^kappa"),
            "fractional_signed_measure": (fractional, "need not be a positive measure"),
            "fractional_inclusion_exclusion": (fractional, "sum_{T proper subset of S} W_nu(T)"),
            "fractional_separate_children": (fractional, "**each child separately**"),
            "fractional_floor_cap": (fractional, "floor(nsub/2)"),
            "fractional_up_to": (fractional, "exclusive_subjets_up_to"),
            "fractional_pt_scheme": (fractional, "FastJet `pt_scheme`"),
            "fractional_original_scalar": (fractional, "jet's scalar sum of constituent pt"),
        }
        for name, (text, clause) in clauses.items():
            self.assertion("contract_text/" + name, clause in text, expected_clause=clause)
        for kind in ("weighted", "fractional"):
            public = self.root / "pilots" / kind / "participant" / "input" / "CONTRACT.md"
            if public.exists():
                self.assertion("generated_contract/" + kind,
                               public.read_text() == strings["COMMON"] + strings[kind.upper()],
                               path=str(public.relative_to(self.root)), sha256=sha256_file(public))
        reference = next(statement for statement in module.body
                         if isinstance(statement, ast.FunctionDef) and statement.name == "reference")
        for kind in ("weighted", "fractional"):
            branch = next(statement for statement in ast.walk(reference)
                          if isinstance(statement, ast.If) and isinstance(statement.test, ast.Compare)
                          and isinstance(statement.test.left, ast.Name) and statement.test.left.id == "kind"
                          and any(isinstance(value, ast.Constant) and value.value == kind
                                  for value in statement.test.comparators))
            queries = ([{"algorithm": algorithm, "kappa": kappa, "order": 4,
                         "resolution": 8, "log_min": LOG_MIN, "bins": BINS}
                        for algorithm in ("ca", "kt") for kappa in (1, 1.5)]
                       if kind == "weighted" else
                       [{"nu": 0.6, "nsub": 16, "log_min": LOG_MIN, "bins": BINS}])
            for query in queries:
                values = {}
                for statement in branch.body:
                    if isinstance(statement, ast.Assign) and isinstance(statement.targets[0], ast.Name):
                        target = statement.targets[0].id
                        if target in ("name", "options"):
                            values[target] = eval(compile(ast.Expression(statement.value),
                                                          "build_pilots.py", "eval"),
                                                  {"__builtins__": {}}, {"query": query})
                if kind == "weighted":
                    expected_name = "eec_fast" + ("_kt" if query["algorithm"] == "kt" else "")
                    expected_options = [4, 8]
                    if query["kappa"] != 1:
                        expected_name += "_weight"
                        expected_options.append(query["kappa"])
                    expected_options += [LOG_MIN, BINS]
                else:
                    expected_name, expected_options = "eec_fast_nu_point", [0.6, 16, LOG_MIN, BINS]
                self.assertion("contract_binary_dispatch/" + expected_name,
                               values == {"name": expected_name, "options": expected_options},
                               observed=values)
        division = "numbers[4:] / job['nevents']"
        self.assertion("contract_reference_mean_conversion", division in ast.unparse(reference),
                       expected_expression=division)
        for name in BINARIES:
            source = self.source_bytes[name + ".cc"].decode()
            definitions = [line.strip() for line in source.splitlines()
                           if "JetDefinition jetdef" in line]
            self.assertion("official_pt_scheme/" + name,
                           len(definitions) == 1 and "fastjet::pt_scheme" in definitions[0],
                           evidence=definitions)
        self.report["contract_validation"] = {
            "source": "author/build_pilots.py", "source_sha256": sha256_bytes(self.builder_bytes),
            "approach": "AST extraction without importing or executing the builder; textual clauses, dispatch expressions, and independent finite-resolution numerical checks.",
            "edits": [],
        }

    def validate_exact(self):
        print("Validating ordered integer tuples, fractional subsets, and exact resolution", flush=True)
        for fixture_name, event in FIXTURES.items():
            orders = range(2, 9) if fixture_name in ("five", "square") else (2, 4, 8)
            for algorithm, kappa, order in product(("ca", "kt"), (1.0, 1.5, 2.0), orders):
                query = {"algorithm": algorithm, "kappa": kappa, "order": order,
                         "resolution": EXACT_RESOLUTION}
                self.evaluate(f"exact/{fixture_name}/{algorithm}/{kappa}/{order}", [event], query)
            for nu in (0.03, 0.15, 0.5, 1.0, 1.7, 2.0, 3.0, 4.5, 8.0):
                query = {"nu": nu, "nsub": 16}
                result = self.evaluate(f"exact/{fixture_name}/nu/{nu}", [event], query)
                if nu.is_integer():
                    collapsed = ordered_histogram([(particle[1], particle[2]) for particle in event],
                                                  fractions_for(event), int(nu))
                    self.compare(f"integer_collapse/{fixture_name}/{nu}", result["binary"],
                                 collapsed, "integer_collapse")
            for mode in ("ca", "kt", "fractional"):
                query = ({"nu": 0.5, "nsub": 16} if mode == "fractional" else
                         {"algorithm": mode, "resolution": EXACT_RESOLUTION})
                geometry = self.geometry([event], query)[0]
                nodes = list(tree_nodes(geometry["tree"]))
                self.assertion(f"exact_resolution/{fixture_name}/{mode}",
                               all(len(subjet["members"]) == 1 for node in nodes
                                   for subjet in node["subjets"]),
                               reason="Every resolved subjet is an original constituent; nsub=16 gives eight slots per child for M<=5")
                self.compare(f"pt_scheme_scalar_pt/{fixture_name}/{mode}",
                             [geometry["root_pt"]], [geometry["scalar_pt"]], "scalar_pt")
        events = list(FIXTURES.values())
        for algorithm, kappa in product(("ca", "kt"), (1.0, 1.5, 2.0)):
            query = {"algorithm": algorithm, "kappa": kappa, "order": 4,
                     "resolution": EXACT_RESOLUTION}
            self.evaluate(f"batch/{algorithm}/{kappa}", events, query)
        for nu in (0.15, 1.0, 2.0, 4.5):
            self.evaluate(f"batch/nu/{nu}", events, {"nu": nu, "nsub": 16})
        for integer, offset in product((1, 2, 3, 4), (-1e-8, -1e-12, 1e-12, 1e-8)):
            nu = integer + offset
            event = FIXTURES["five"]
            query = {"nu": nu, "nsub": 16}
            result = self.evaluate(f"near_integer/{nu:.17g}", [event], query)
            collapsed = exact_histogram(event, {"order": integer, "kappa": 1.0})
            observed_residual = [actual - float(base) for actual, base in zip(result["binary"], collapsed)]
            expected_residual = [target - base for target, base in zip(result["oracle"], collapsed)]
            error = self.compare(f"near_integer_residual/{nu:.17g}", observed_residual,
                                 expected_residual, "near_integer_absolute")
            self.report["near_integer"].append({
                "nu": nu, "integer": integer, "distance_to_integer": abs(nu - integer),
                "expected_departure_l1": math.fsum(abs(float(value)) for value in expected_residual),
                "observed_departure_l1": math.fsum(map(abs, observed_residual)),
                "max_absolute_error": error["max_absolute_error"], "l1_error": error["l1_error"],
                "relative_error": None,
            })

    def validate_square(self):
        event = FIXTURES["square"]
        for nu in (0.03, 0.15, 0.5, 1.0, 1.7, 2.0, 3.0, 4.5):
            exponent = decimal_input(nu)
            contact = 4 * Decimal("0.25") ** exponent
            edge = 4 * (Decimal("0.5") ** exponent - 2 * Decimal("0.25") ** exponent)
            diagonal = ONE - contact - edge
            analytic = [ZERO] * BINS
            positions = [0, bin_index(0.32), bin_index(math.sqrt(2) * 0.32)]
            for position, mass in zip(positions, (contact, edge, diagonal)):
                analytic[position] += mass
            query = {"nu": nu, "nsub": 16}
            result = self.evaluate(f"square/nu/{nu}", [event], query)
            self.compare(f"square_analytic/{nu}/subset", result["oracle"], analytic, "square_analytic")
            self.compare(f"square_analytic/{nu}/binary", result["binary"], analytic, "square_analytic")
            unused, measures = subset_histogram([(particle[1], particle[2]) for particle in event],
                                                fractions_for(event), exponent)
            self.report["square_signed_masses"].append({
                "nu": nu, "bins": positions,
                "contact_mass": float(contact), "edge_mass": float(edge),
                "diagonal_mass": float(diagonal),
                "positive_subset_mass": float(sum((value for value in measures if value > ZERO), ZERO)),
                "negative_subset_mass": float(sum((value for value in measures if value < ZERO), ZERO)),
                "sum_squared_signed_subset_masses": float(sum((value * value for value in measures), ZERO)),
                "squared_mass_note": "Diagnostic sum of individual W(S)^2, not an official output or an event-variance estimator",
            })
            if nu < 1:
                self.assertion(f"square_signs/{nu}", edge < ZERO < diagonal and
                               result["binary"][positions[1]] < 0 < result["binary"][positions[2]])

    def validate_transformations(self):
        print("Checking rotations, scalar rescalings, and finite-resolution contracts", flush=True)
        base = FIXTURES["five"]
        transformations = (("rotation", 1.0, 3.05, 0.0), ("scale_small", 0.025, 0.0, 0.0),
                           ("scale_large", 37.0, 0.0, 0.0), ("combined", 0.2, 3.05, -0.8))
        queries = [{"algorithm": algorithm, "kappa": kappa, "order": order,
                    "resolution": EXACT_RESOLUTION}
                   for algorithm, kappa, order in product(("ca", "kt"), (1.0, 1.5), (4, 8))]
        queries += [{"nu": nu, "nsub": 16} for nu in (0.15, 1.7, 4.5)]
        for query_index, query in enumerate(queries):
            original = self.evaluate(f"transform_base/{query_index}", [base], query)
            for label, scale, rotation, boost in transformations:
                transformed = tuple((particle[0] * scale, particle[1] + boost,
                                     math.remainder(particle[2] + rotation, math.tau))
                                    for particle in base)
                changed = self.evaluate(f"transform/{query_index}/{label}", [transformed], query)
                self.compare(f"invariance/{query_index}/{label}", changed["binary"],
                             original["binary"], "exact_invariance")
        vector_total = math.hypot(math.fsum(particle[0] * math.cos(particle[2]) for particle in base),
                                  math.fsum(particle[0] * math.sin(particle[2]) for particle in base))
        scalar_total = math.fsum(particle[0] for particle in base)
        self.assertion("scalar_vs_vector_normalization_fixture", abs(scalar_total / vector_total - 1) > 1e-3,
                       scalar_pt=scalar_total, vector_pt=vector_total,
                       wrong_vector_normalized_order4_mass=(scalar_total / vector_total) ** 4)

    def validate_finite(self):
        event = FIXTURES["hierarchical"]
        differences = {"subjet_power_not_moment": [], "E_scheme_not_pt_scheme": [],
                       "kt_momentum_times_angular_cut": [], "fixed_f_kt_rescaling": []}
        compressed_count = 0
        for algorithm in ("ca", "kt"):
            resolutions = (2.0, 8.0, 64.0) if algorithm == "ca" else (0.03, 0.3, 3.0, 30.0, 300.0)
            for resolution, kappa in product(resolutions, (1.0, 1.5, 2.0)):
                query = {"algorithm": algorithm, "kappa": kappa, "order": 4,
                         "resolution": resolution}
                label = f"finite/{algorithm}/{resolution}/{kappa}"
                result = self.evaluate(label, [event], query, finite=True)
                geometry = self.geometry([event], query)[0]
                nodes = list(tree_nodes(geometry["tree"]))
                compressed_count += sum(len(subjet["members"]) > 1 for node in nodes
                                        for subjet in node["subjets"])
                self.compare(label + "/angular_cut", [node["cut"] for node in nodes],
                             [node["theta_squared"] / (1.5 ** 2 * resolution) for node in nodes],
                             "angular_cut")
                wrong_geometry = self.geometry([event], query, scheme="E")[0]
                wrong = finite_histogram(event, wrong_geometry["tree"], query)
                differences["E_scheme_not_pt_scheme"].append((label, metrics(wrong, result["oracle"])))
                if kappa != 1:
                    wrong = finite_histogram(event, geometry["tree"], query, wrong_subjet_power=True)
                    differences["subjet_power_not_moment"].append((label, metrics(wrong, result["oracle"])))
                if algorithm == "kt":
                    wrong_geometry = self.geometry([event], query, wrong_kt_cut=True)[0]
                    wrong = finite_histogram(event, wrong_geometry["tree"], query)
                    differences["kt_momentum_times_angular_cut"].append((label, metrics(wrong, result["oracle"])))
                    if kappa == 1.5:
                        scale = 0.125
                        transformed = tuple((particle[0] * scale, particle[1], particle[2]) for particle in event)
                        adjusted = dict(query, resolution=resolution / scale ** 2)
                        changed = self.evaluate(label + "/scale_adjusted", [transformed], adjusted, finite=True)
                        self.compare(label + "/kt_covariance_f_over_scale_squared", changed["binary"],
                                     result["binary"], "finite_kt_covariance")
                        fixed = self.evaluate(label + "/scale_fixed_f", [transformed], query, finite=True)
                        differences["fixed_f_kt_rescaling"].append((label, metrics(fixed["binary"], result["binary"])))
        for cap, nu in product((2, 3, 4, 5, 6, 7, 8, 16), (0.15, 1.7, 3.0)):
            query = {"nu": nu, "nsub": cap}
            label = f"finite/fractional/{cap}/{nu}"
            result = self.evaluate(label, [event], query, finite=True)
            geometry = self.geometry([event], query)[0]
            nodes = list(tree_nodes(geometry["tree"]))
            self.assertion(label + "/per_child_cap",
                           all(node["left_count"] <= cap // 2
                               and len(node["subjets"]) - node["left_count"] <= cap // 2
                               for node in nodes))
            if cap % 2:
                even = self.evaluate(label + "/even_cap", [event], dict(query, nsub=cap - 1), finite=True)
                self.compare(label + "/floor_cap_equivalence", result["binary"], even["binary"], "floor_cap")
        self.assertion("finite_fixtures_actually_compress", compressed_count > 0,
                       compressed_subjet_observations=compressed_count)
        for name, candidates in differences.items():
            label, difference = max(candidates, key=lambda candidate: candidate[1]["l1_error"])
            self.assertion("negative_control_detected/" + name, difference["l1_error"] > 1e-6,
                           witness=label, incorrect_variant_l1=difference["l1_error"])
            self.report["negative_controls"].append({"name": name, "witness": label, **difference})

    def finish(self):
        after = {str(path.relative_to(self.root)): sha256_file(path) for path in self.monitored}
        self.report["hashes"] = {path: {"before": before, "after": after[path],
                                       "unchanged": before == after[path]}
                                 for path, before in self.hashes_before.items()}
        immutable = [path for path in after if path.startswith(("author/bin/", "author/FastEEC/"))
                     or path == "author/fastjet/lib/libfastjet.a"]
        self.assertion("tested_binaries_and_dependencies_unchanged",
                       all(self.hashes_before[path] == after[path] for path in immutable))
        initial_contracts, unused = contract_strings(self.builder_bytes)
        final_contracts, unused = contract_strings((self.author / "build_pilots.py").read_bytes())
        self.assertion("weighted_fractional_contracts_stable_during_validation",
                       initial_contracts == final_contracts)
        categories = {}
        for check in self.checks:
            category = categories.setdefault(check["category"], {"count": 0, "failed": 0,
                                                                  "max_absolute_error": 0.0,
                                                                  "max_l1_error": 0.0})
            category["count"] += 1
            category["failed"] += not check["passed"]
            category["max_absolute_error"] = max(category["max_absolute_error"],
                                                 check.get("max_absolute_error", 0.0))
            category["max_l1_error"] = max(category["max_l1_error"], check.get("l1_error", 0.0))
        self.report["categories"] = categories
        failed = [check["name"] for check in self.checks if not check["passed"]]
        oracle_checks = [check for check in self.checks if check["category"] == "binary_oracle"]
        self.report["summary"] = {
            "passed": not failed, "status": "pass" if not failed else "fail",
            "checks": len(self.checks), "runs": len(self.runs), "failed_checks": failed,
            "binary_vs_oracle_max_absolute_error": max(check["max_absolute_error"] for check in oracle_checks),
            "binary_vs_oracle_max_l1_error": max(check["l1_error"] for check in oracle_checks),
            "binary_vs_oracle_total_l1_error": math.fsum(check["l1_error"] for check in oracle_checks),
            "binary_modes_exercised": sorted({run["binary"] for run in self.runs}),
            "contract_mismatch": any(not check["passed"] and check["name"].startswith(
                ("contract_", "generated_contract/", "official_pt_scheme/")) for check in self.checks),
        }
        self.report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        return self.report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cxx", default="g++")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    output = arguments.output or root / "author" / "projector_validation.json"
    compiler = shutil.which(arguments.cxx)
    if compiler is None:
        raise SystemExit("C++ compiler not found: " + arguments.cxx)
    started = time.monotonic()
    validator = None
    try:
        with tempfile.TemporaryDirectory(prefix="projector_validation_", dir="/tmp") as temporary:
            with localcontext() as context:
                context.prec = PRECISION
                validator = Validator(root, Path(temporary), compiler)
                validator.validate_contracts()
                validator.compile_drivers()
                validator.validate_exact()
                validator.validate_square()
                validator.validate_transformations()
                validator.validate_finite()
                report = validator.finish()
    except Exception as error:
        report = validator.report if validator is not None else {"schema_version": 1}
        report["summary"] = {"passed": False, "status": "error", "error": str(error)}
        report["traceback"] = traceback.format_exc()
    report["wall_seconds"] = time.monotonic() - started
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"report": str(output), **report["summary"]}, sort_keys=True), flush=True)
    return 0 if report["summary"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
