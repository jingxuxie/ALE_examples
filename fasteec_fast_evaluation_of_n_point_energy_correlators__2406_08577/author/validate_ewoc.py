import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import shlex
import subprocess
import sys
import time


AUTHOR = Path(__file__).resolve().parent
SOURCE = AUTHOR / "adapters/ewoc_reference.cpp"
CONTRACT = AUTHOR / "specs/ewoc_contract.md"
BINARY = AUTHOR / "bin/ewoc_reference"
OUTPUT = AUTHOR / "ewoc_validation.json"
UPSTREAM_COMMIT = "0736fc3c24d00f1ea7d08b8ea3c62ccd84f7b10e"
SEED = 250117218
ABS_TOLERANCE = 2e-12
REL_TOLERANCE = 2e-11
DEFAULTS = dict(nevents=1, geometry="pp", algorithm="ca", radius=0.1,
                observable="angular", kappa=1, log_min=-1, bins=3)
SCIENTIFIC = re.compile(r"-?\d\.\d{17}e[+-]\d{2,}\Z")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def file_hash(path):
    with path.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command(arguments, **kwargs):
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=120, **kwargs)
    if result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {shlex.join(map(str, arguments))}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def frozen_hashes():
    return {str(path.relative_to(AUTHOR.parent)): file_hash(path)
            for path in (SOURCE, CONTRACT, BINARY) if path.exists()}


def verify_provenance():
    repository = AUTHOR / "ResolvedEnergyCorrelators"
    revision = command(["git", "-C", str(repository), "rev-parse", "HEAD"]).stdout.strip()
    require(revision == UPSTREAM_COMMIT, f"Unexpected upstream revision: {revision}")
    files = {}
    for relative in ("write/src/ewocs.cc", "write/src/utils/ewoc_utils.cc",
                     "write/src/utils/jet_utils.cc"):
        content = (repository / relative).read_bytes()
        committed = subprocess.run(
            ["git", "-C", str(repository), "show", f"{UPSTREAM_COMMIT}:{relative}"],
            check=True, capture_output=True, timeout=30,
        ).stdout
        require(content == committed, f"Upstream source differs from pinned blob: {relative}")
        files[relative] = dict(sha256=sha256(content), matches_pinned_blob=True)
    return dict(repository="samcaf/ResolvedEnergyCorrelators", commit=revision,
                passed=True, files=files)


@contextmanager
def memory_file(name, content=b""):
    descriptor = os.memfd_create(name)
    try:
        with os.fdopen(os.dup(descriptor), "wb") as stream:
            stream.write(content)
        yield Path(f"/proc/{os.getpid()}/fd/{descriptor}")
    finally:
        os.close(descriptor)


@contextmanager
def executable(report, rebuild):
    library = AUTHOR / "fastjet/lib/libfastjet.a"
    report["fastjet_version"] = command(
        [str(AUTHOR / "fastjet/bin/fastjet-config"), "--version"]
    ).stdout.strip()
    report["fastjet_library_sha256"] = file_hash(library)
    existing = BINARY.is_file() and os.access(BINARY, os.X_OK)
    stale = existing and BINARY.stat().st_mtime_ns < max(
        SOURCE.stat().st_mtime_ns, library.stat().st_mtime_ns
    )
    if existing:
        report["existing_binary_sha256"] = file_hash(BINARY)
    if existing and not stale and not rebuild:
        report["build"] = dict(mode="existing", path="author/bin/ewoc_reference",
                               source_association="mtime heuristic; --rebuild forces source compilation")
        report["binary_sha256"] = report["existing_binary_sha256"]
        yield BINARY
        return
    compiler = shlex.split(os.environ.get("CXX", "g++"))
    require(bool(compiler), "CXX must name a compiler")
    report["build"] = dict(
        mode="memory_backed_rebuild",
        reason="requested" if rebuild else "stale_binary" if stale else "missing_executable",
        existing_binary_modified=False,
        compiler=command(compiler + ["--version"]).stdout.splitlines()[0],
        commands=[],
    )
    with memory_file("ewoc-validation-object") as object_path, \
            memory_file("ewoc-validation-executable") as binary_path:
        commands = [
            compiler + ["-std=c++17", "-O2", "-pipe", "-Wall", "-Wextra", "-Wpedantic",
                        "-Werror", "-D_GLIBCXX_ASSERTIONS", f"-I{AUTHOR / 'fastjet/include'}",
                        "-c", str(SOURCE), "-o", str(object_path)],
            compiler + [str(object_path), f"-L{AUTHOR / 'fastjet/lib'}", "-lfastjet",
                        "-o", str(binary_path)],
        ]
        for arguments in commands:
            result = command(arguments)
            report["build"]["commands"].append(dict(argv=arguments, stdout=result.stdout,
                                                     stderr=result.stderr, returncode=0))
        report["binary_sha256"] = file_hash(binary_path)
        yield binary_path


def serialize_events(events):
    return "".join(
        f"{event_id} {pt:.17g} {rapidity:.17g} {phi:.17g}\n"
        for event_id, rows in enumerate(events) for pt, rapidity, phi in rows
    ).encode()


def bin_integrals(terms, observable, log_min, bins):
    upper = 10000.0 if observable == "mass" else math.pi
    edges = [10 ** (log_min + (math.log10(upper) - log_min) * edge / (bins - 2))
             for edge in range(bins - 2)] + [upper]
    histogram = [0.0] * bins
    for coordinate, weight in terms:
        histogram[sum(coordinate >= edge for edge in edges)] += weight
    return histogram


def four_momentum(row):
    pt, rapidity, phi = row
    px, py, pz = pt * math.cos(phi), pt * math.sin(phi), pt * math.sinh(rapidity)
    return (px, py, pz, math.sqrt(px * px + py * py + pz * pz))


def scalar_weight(momentum, geometry):
    return math.hypot(momentum[0], momentum[1]) if geometry == "pp" else momentum[3]


def angular_distance(first, second, geometry):
    if geometry == "pp":
        first_y = 0.5 * math.log((first[3] + first[2]) / (first[3] - first[2]))
        second_y = 0.5 * math.log((second[3] + second[2]) / (second[3] - second[2]))
        delta_phi = math.remainder(math.atan2(first[1], first[0]) -
                                   math.atan2(second[1], second[0]), 2 * math.pi)
        return math.hypot(first_y - second_y, delta_phi)
    norm = math.sqrt(sum(value * value for value in first[:3]) *
                     sum(value * value for value in second[:3]))
    require(norm > 0, "Independent oracle encountered a directionless subjet")
    cosine = sum(left * right for left, right in zip(first[:3], second[:3])) / norm
    return math.acos(max(-1.0, min(1.0, cosine)))


def independent_subjets(rows, geometry, algorithm, radius):
    power = {"ca": 0, "kt": 1, "antikt": -1}[algorithm]
    active = [four_momentum(row) for row in rows]
    final = []
    while active:
        beam_scales = [scalar_weight(momentum, geometry) ** (2 * power)
                       for momentum in active]
        candidates = [(scale, index, None) for index, scale in enumerate(beam_scales)]
        for first, second in itertools.combinations(range(len(active)), 2):
            angle = angular_distance(active[first], active[second], geometry)
            metric = ((angle / radius) ** 2 if geometry == "pp" else
                      (1 - math.cos(angle)) / (1 - math.cos(radius)))
            candidates.append((min(beam_scales[first], beam_scales[second]) * metric,
                               first, second))
        _, first, second = min(candidates, key=lambda item: item[0])
        if second is None:
            final.append(active.pop(first))
        else:
            combined = tuple(left + right for left, right in zip(active[first], active[second]))
            active.pop(second)
            active.pop(first)
            active.append(combined)
    return sorted(final, key=lambda momentum: scalar_weight(momentum, geometry), reverse=True)


def independent_histogram(events, geometry, algorithm, radius, observable, kappa, log_min, bins):
    terms = []
    for rows in events:
        denominator = sum(scalar_weight(four_momentum(row), geometry) for row in rows)
        subjets = independent_subjets(rows, geometry, algorithm, radius)
        for first_index, first in enumerate(subjets):
            for second_index, second in enumerate(subjets):
                contact = first_index == second_index
                if observable == "mass":
                    momentum = first if contact else tuple(
                        left + right for left, right in zip(first, second)
                    )
                    mass_squared = momentum[3] ** 2 - sum(value ** 2 for value in momentum[:3])
                    coordinate = math.sqrt(max(0.0, mass_squared))
                else:
                    coordinate = 0.0 if contact else angular_distance(first, second, geometry)
                weight = ((scalar_weight(first, geometry) / denominator) *
                          (scalar_weight(second, geometry) / denominator)) ** kappa
                terms.append((coordinate, weight / len(events)))
    return bin_integrals(terms, observable, log_min, bins)


class Validator:
    def __init__(self, binary, report):
        self.binary = binary
        self.report = report

    def case(self, name, category, data, expected=None, expect_error=False,
             alias=False, invariant=None, **overrides):
        options = dict(DEFAULTS, **overrides)
        data = data.encode() if isinstance(data, str) else data
        entry = dict(name=name, category=category, options=options, input_sha256=sha256(data),
                     input_bytes=len(data), expect_error=expect_error, passed=False)
        self.report["cases"].append(entry)
        try:
            with memory_file("ewoc-validation-input", data) as input_path, \
                    memory_file("ewoc-validation-output", b"untouched") as output_path:
                selected_output = output_path
                if alias:
                    descriptor = os.open(input_path, os.O_RDONLY)
                    selected_output = Path(f"/proc/{os.getpid()}/fd/{descriptor}")
                try:
                    arguments = [str(self.binary), str(input_path)] + [
                        str(options[key]) for key in DEFAULTS
                    ] + [str(selected_output)]
                    result = subprocess.run(arguments, capture_output=True, text=True, timeout=30)
                    output = output_path.read_bytes()
                finally:
                    if alias:
                        os.close(descriptor)
                entry.update(returncode=result.returncode, stderr=result.stderr)
                require(not result.stdout, "Unexpected adapter stdout")
                if expect_error:
                    require(result.returncode != 0 and result.stderr, "Expected diagnostic failure")
                    require(output == b"untouched", "Failure modified existing output")
                    require(input_path.read_bytes() == data, "Failure modified input")
                    entry["output_preserved"] = True
                else:
                    require(result.returncode == 0 and not result.stderr, result.stderr or "Adapter failed")
                    require(output.endswith(b"\n") and output.count(b"\n") == 1,
                            "Output must be exactly one newline-terminated row")
                    tokens = output.decode().split()
                    require(len(tokens) == options["bins"], "Wrong flattened histogram size")
                    require(all(SCIENTIFIC.fullmatch(token) for token in tokens),
                            "Expected scientific notation with 17 decimal places")
                    actual = [float(token) for token in tokens]
                    entry["actual"] = actual
                    require(all(math.isfinite(value) and value >= 0 for value in actual),
                            "Histogram contains a non-finite or negative weight")
                    if expected is not None:
                        require(len(actual) == len(expected), "Oracle histogram size mismatch")
                        errors = [abs(got - wanted) for got, wanted in zip(actual, expected)]
                        ratios = [error / (ABS_TOLERANCE + REL_TOLERANCE * abs(wanted))
                                  for error, wanted in zip(errors, expected)]
                        entry.update(
                            expected=expected, max_abs_bin_error=max(errors), l1_error=sum(errors),
                            total_weight_error=abs(sum(actual) - sum(expected)),
                            max_relative_bin_error=max(error / max(abs(wanted), ABS_TOLERANCE)
                                                       for error, wanted in zip(errors, expected)),
                            max_tolerance_ratio=max(ratios),
                        )
                        require(max(ratios) <= 1, "Histogram differs from independent expectation")
                    else:
                        require(invariant is not None, "Successful case needs an expectation")
                    if invariant is not None:
                        invariant(actual)
                entry["passed"] = True
        except Exception as error:
            entry["error"] = f"{type(error).__name__}: {error}"


def analytic_cases(validator):
    pair = "0 10 0 0\n0 10 0 1\n"
    merged = "0 10 0 -0.2\n0 10 0 0.2\n"
    for geometry, algorithm, observable in itertools.product(
            ("pp", "ee"), ("ca", "kt", "antikt"), ("mass", "angular")):
        suffix = f"{geometry}_{algorithm}_{observable}"
        options = dict(geometry=geometry, algorithm=algorithm, observable=observable)
        validator.case(f"split_ordered_pairs_{suffix}", "analytic", pair,
                       [0.5, 0.5, 0.0], **options)
        validator.case(f"massless_single_contact_{suffix}", "analytic", "0 10 0 0",
                       [1.0, 0.0, 0.0], **options)
        for kappa in (1, 2):
            weight = math.cos(0.2) ** (2 * kappa) if geometry == "pp" else 1.0
            coordinate = 20 * math.sin(0.2) if observable == "mass" else 0.0
            expected = bin_integrals([(coordinate, weight)], observable, -1, 22)
            validator.case(f"massive_E_scheme_contact_kappa{kappa}_{suffix}", "analytic",
                           merged, expected, radius=1, kappa=kappa, bins=22, **options)
    for geometry, observable, kappa in itertools.product(("pp", "ee"), ("mass", "angular"), (1, 1.7)):
        second_weight = 7 if geometry == "pp" else 7 * math.cosh(1)
        first_fraction = 2 / (2 + second_weight)
        second_fraction = second_weight / (2 + second_weight)
        contacts = first_fraction ** (2 * kappa) + second_fraction ** (2 * kappa)
        pairs = 2 * (first_fraction * second_fraction) ** kappa
        coordinate = (math.sqrt(28 * (math.cosh(1) - 1)) if observable == "mass" else
                      1.0 if geometry == "pp" else math.acos(1 / math.cosh(1)))
        expected = bin_integrals([(0, contacts), (coordinate, pairs)], observable, -2, 49)
        validator.case(f"original_denominator_{geometry}_{observable}_{kappa}", "denominator",
                       "0 2 0 0\n0 7 1 0\n", expected, geometry=geometry,
                       observable=observable, kappa=kappa, log_min=-2, bins=49)


def boundary_cases(validator):
    cases = [
        ("average_two_nonconsecutive_ids", "0 1 0 0\n10 10 0 0\n10 10 0 1", [0.75, 0.25, 0], dict(nevents=2)),
        ("prefix_unread_suffix", "0 1 0 0\n10 10 0 0\nmalformed unread suffix\n", [1, 0, 0], {}),
        ("comments_zero_rows_max_id", "# input\n\n  # comment\n18446744073709551615 0 0 0\n18446744073709551615 1 0 0", [1, 0, 0], {}),
        ("mass_upper_edge", "0 5000 0 0\n0 5000 0 3.141592653589793\n", [0.5, 0, 0.5], dict(observable="mass")),
        ("mass_internal_edge", "0 50 0 0\n0 50 0 3.141592653589793\n", [0.5, 0, 0, 0.5, 0, 0], dict(observable="mass", log_min=0, bins=6)),
        ("mass_lower_edge", "0 5 0 0\n0 5 0 3.141592653589793\n", [0.5, 0.5, 0, 0, 0], dict(observable="mass", log_min=1, bins=5)),
        ("ee_back_to_back_overflow", "0 10 0 0\n0 10 0 3.141592653589793\n", [0.5, 0, 0.5], dict(geometry="ee")),
        ("pp_distance_overflow", "0 10 -2 0\n0 10 2 0\n", [0.5, 0, 0.5], {}),
        ("positive_underflow_pairs", "0 10 0 0\n0 10 0 0.0001\n", [1, 0, 0], dict(radius=1e-6, log_min=-3)),
    ]
    for name, data, expected, options in cases:
        validator.case(name, "boundary", data, expected, **options)
    row = b"0 1 0 0"
    for name, ending in (("eof", b""), ("lf", b"\n"), ("crlf", b"\r\n")):
        validator.case(f"line_ending_{name}", "reader", row + ending, [1, 0, 0])
    for ending_name, ending in (("eof", b""), ("lf", b"\n")):
        validator.case(f"maximum_line_{ending_name}", "reader",
                       row + b" " * (4096 - len(row)) + ending, [1, 0, 0])
        validator.case(f"oversize_line_{ending_name}", "rejection",
                       row + b" " * (4097 - len(row)) + ending, expect_error=True)


def random_cases(validator):
    generator = random.Random(SEED)
    events = [[(math.exp(generator.uniform(-2, 3)), generator.uniform(-1.2, 1.2),
                generator.uniform(-1.5, 1.5)) for _ in range(9)] for _ in range(12)]
    data = serialize_events(events)
    fixture = dict(seed=SEED, events=events, input_sha256=sha256(data), jet_count=12,
                   particles_per_jet=9, configuration_count=24, subjet_counts={})
    validator.report["fixtures"]["random_small_jets"] = fixture
    for geometry in ("pp", "ee"):
        counts = {algorithm: [len(independent_subjets(rows, geometry, algorithm, 0.75))
                              for rows in events] for algorithm in ("ca", "kt", "antikt")}
        require(len({tuple(values) for values in counts.values()}) > 1,
                "Random fixture must distinguish clustering algorithms")
        fixture["subjet_counts"][geometry] = counts
    for geometry, algorithm, observable, kappa in itertools.product(
            ("pp", "ee"), ("ca", "kt", "antikt"), ("mass", "angular"), (0.5, 1.7)):
        options = dict(geometry=geometry, algorithm=algorithm, radius=0.75,
                       observable=observable, kappa=kappa, log_min=-2, bins=49)
        expected = independent_histogram(events, **options)
        validator.case(f"random_{geometry}_{algorithm}_{observable}_{kappa}", "random_oracle",
                       data, expected, nevents=len(events), **options)


def rejection_cases(validator):
    pair = "0 10 0 0\n0 10 0 1\n"
    invalid_options = [
        ("geometry", dict(geometry="bad")), ("algorithm", dict(algorithm="durham")),
        ("observable", dict(observable="theta")), ("zero_radius", dict(radius=0)),
        ("nan_radius", dict(radius="nan")), ("large_radius", dict(radius=4)),
        ("zero_kappa", dict(kappa=0)), ("negative_kappa", dict(kappa=-1)),
        ("large_kappa", dict(kappa=9)), ("low_log_min", dict(log_min=-13)),
        ("high_log_min", dict(log_min=1)), ("few_bins", dict(bins=2)),
        ("many_bins", dict(bins=65537)), ("zero_nevents", dict(nevents=0)),
        ("many_nevents", dict(nevents=100001)), ("too_few_jets", dict(nevents=2)),
        ("collapsed_edges", dict(log_min=math.nextafter(math.log10(math.pi), -math.inf), bins=65536)),
    ]
    for name, options in invalid_options:
        validator.case(f"reject_{name}", "rejection", pair, expect_error=True, **options)
    malformed = [
        ("empty", b""), ("no_jets", b"# no jets\n"), ("zero_jet", b"0 0 0 0\n"),
        ("missing_column", b"0 1 0\n"), ("extra_column", b"0 1 0 0 extra\n"),
        ("negative_id", b"-1 1 0 0\n"), ("overflow_id", b"18446744073709551616 1 0 0\n"),
        ("negative_pt", b"0 -1 0 0\n"), ("nan_pt", b"0 nan 0 0\n"),
        ("infinite_y", b"0 1 inf 0\n"), ("nan_phi", b"0 1 0 nan\n"),
        ("trailing_junk", b"0 1x 0 0\n"), ("large_y", b"0 1 11 0\n"),
        ("tiny_pt", b"0 1e-13 0 0\n"), ("descending_id", b"2 1 0 0\n1 1 0 0\n"),
        ("many_rows", b"0 1 0 0\n" * 4097), ("nul_eof", b"0 1 0 0\0"),
        ("nul_suffix", b"0 1 0 0\0ignored\n"), ("nul_comment", b"#\0\n0 1 0 0"),
        ("nul_id", b"0\0 1 0 0\n"),
    ]
    for name, data in malformed:
        validator.case(f"reject_{name}", "rejection", data, expect_error=True)
    validator.case("same_inode_alias", "rejection", pair, expect_error=True, alias=True)


def cms_smoke_case(validator):
    path = AUTHOR / "cms100k.txt"
    if not path.is_file():
        validator.report["fixtures"]["cms"] = dict(skipped=True, reason="cms100k.txt not present")
        return
    lines = []
    previous_id = None
    blocks = 0
    with path.open("rb") as stream:
        for line in stream:
            lines.append(line)
            fields = line.split()
            if not fields or fields[0].startswith(b"#"):
                continue
            if fields[0] != previous_id:
                blocks += 1
                previous_id = fields[0]
                if blocks == 11:
                    break
    require(blocks >= 10, "CMS smoke fixture contains fewer than 10 jets")
    data = b"".join(lines)
    validator.report["fixtures"]["cms"] = dict(path="author/cms100k.txt", jet_count=10,
                                               prefix_sha256=sha256(data), prefix_bytes=len(data),
                                               check="nonnegative bins and 0 < total weight <= 1")
    validator.case("cms_first_10_jets", "cms_smoke", data, nevents=10, algorithm="kt",
                   radius=0.3, observable="mass", log_min=-2, bins=52,
                   invariant=lambda values: require(0 < sum(values) <= 1 + ABS_TOLERANCE,
                                                    "Invalid pp kappa=1 total EWOC weight"))


def main():
    parser = argparse.ArgumentParser(description="Reproduce private EWOC checks and write author/ewoc_validation.json")
    parser.add_argument("--rebuild", action="store_true", help="force an isolated, memory-backed source build")
    arguments = parser.parse_args()
    started = time.monotonic()
    report = dict(
        schema_version=1, passed=False, seed=SEED, cases=[], fixtures={},
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        python_version=sys.version, platform=sys.platform,
        validation_scope="Private author adapter/spec; these checks do not extend the frozen public contract",
        validator_sha256=file_hash(Path(__file__)),
        tolerance=dict(absolute=ABS_TOLERANCE, relative=REL_TOLERANCE,
                       rule="abs(actual-expected) <= absolute + relative*abs(expected)",
                       relative_error_denominator_floor=ABS_TOLERANCE),
        oracle="Independent Python all-distance sequential recombination and full ordered-pair sum; no FastJet calls in oracle",
        contact_convention="mass: individual subjet mass; angular: zero; each diagonal once, distinct ordered pairs twice",
        output_convention="per-jet average of integrated bins, including both flow bins; no density or unit-area normalization",
        runtime_artifacts="Linux memfd/procfs; only the JSON report is persisted",
    )
    before = None
    try:
        require(hasattr(os, "memfd_create") and Path("/proc/self/fd").is_dir(),
                "This validator requires Linux memfd and procfs")
        before = frozen_hashes()
        report.update(adapter_sha256=file_hash(SOURCE), contract_sha256=file_hash(CONTRACT),
                      frozen_files_before=before, provenance=verify_provenance())
        with executable(report, arguments.rebuild) as binary:
            validator = Validator(binary, report)
            analytic_cases(validator)
            boundary_cases(validator)
            random_cases(validator)
            rejection_cases(validator)
            cms_smoke_case(validator)
    except Exception as error:
        report["fatal_error"] = f"{type(error).__name__}: {error}"
    finally:
        if before is not None:
            try:
                after = frozen_hashes()
                report["frozen_files_after"] = after
                report["frozen_files_unchanged"] = before == after
            except Exception as error:
                report["frozen_files_unchanged"] = False
                report["frozen_hash_error"] = str(error)
    cases = report["cases"]
    report["case_count"] = len(cases)
    report["passed_case_count"] = sum(case["passed"] for case in cases)
    report["category_counts"] = dict(Counter(case["category"] for case in cases))
    for target, key in (("max_abs_bin_error", "max_abs_bin_error"),
                        ("max_relative_bin_error", "max_relative_bin_error"),
                        ("max_l1_error", "l1_error"),
                        ("max_total_weight_error", "total_weight_error"),
                        ("max_tolerance_ratio", "max_tolerance_ratio")):
        report[target] = max((case.get(key, 0.0) for case in cases), default=0.0)
    report["passed"] = bool(cases) and all(case["passed"] for case in cases) and \
        "fatal_error" not in report and report.get("frozen_files_unchanged", False) and \
        report["category_counts"].get("random_oracle") == 24
    report["elapsed_seconds"] = time.monotonic() - started
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("passed", "case_count", "passed_case_count", "max_abs_bin_error", "max_l1_error")},
                     sort_keys=True))
    print(f"Report: {OUTPUT}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
