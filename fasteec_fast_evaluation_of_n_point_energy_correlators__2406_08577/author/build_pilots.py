import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import shutil
import subprocess
import time

import numpy as np

from weak_baseline import compute as compute_weak


ROOT = Path(__file__).resolve().parent.parent
AUTHOR = ROOT / "author"
CONCEPTS = ["weighted", "fractional", "resolved", "ewoc"]
SPECS = {
    "weighted": "Deliver a batched weighted angular-correlator engine. Extend the supplied unit-weight angular implementation to all requested weight and reclustering modes without losing high-order throughput. Follow input/CONTRACT.md. Write solve.py in the attempt directory; it must accept --input JOB.json --output RESULT.json. Validate your work and briefly describe limitations in your final response.",
    "fractional": "Extend the supplied integer angular-correlator engine to continuous positive orders. Preserve the specified finite-resolution observable, signed contributions, and contact terms on high-multiplicity jet ensembles. Follow input/CONTRACT.md. Write solve.py in the attempt directory; it must accept --input JOB.json --output RESULT.json. Validate your work and briefly describe limitations in your final response.",
    "resolved": "Build a joint angular-correlation engine that retains conditional geometry and nonlinear energy weights discarded by the supplied projected implementation. Deliver both requested orders with correct contacts, orientation, and practical ensemble throughput. Follow input/CONTRACT.md. Write solve.py in the attempt directory; it must accept --input JOB.json --output RESULT.json. Validate your work and briefly describe limitations in your final response.",
    "ewoc": "Build an energy-weighted subjet-observable engine for the supplied jet records. Support the requested collision geometries, recombination modes, and observables with consistent weighting and normalization. Follow input/CONTRACT.md. Write solve.py in the attempt directory; it must accept --input JOB.json --output RESULT.json. Validate your work and briefly describe limitations in your final response.",
}

COMMON = """# Execution contract

The entrypoint is `python /absolute/attempt/solve.py --input JOB.json --output RESULT.json`.
Resolve the job's relative `events_file` against JOB.json's directory. Each event
row is `event_id pt rapidity phi`, with massless constituents and positive pt.
IDs are contiguous from zero. Azimuth is periodic modulo 2*pi. `nevents` is the
number of supplied jets. Input order is not meaningful except for exact angular
ties, for which stable constituent order is the convention. No external files
or network access are required.

JOB contains `kind`, `events_file`, `nevents`, and a list `queries`. Return
`{"histograms": [[...], ...], "claims": {"method": "...", "limitations": "..."}}`:
one flat numerical histogram per query, in query order. Report per-jet mean bin
**masses**, not densities or unit-area rescalings. Use finite double-precision
JSON numbers. Claims do not earn accuracy credit. The sample is an interface
fixture, not a labeled training set.

Unless a concept-specific axis convention below overrides this paragraph,
logarithmic distance/mass axes have `bins` equal log10 bins between `log_min`
and 0. Clamp underflow (including zero/contact) to bin zero and overflow to the
last bin. For x>10^log_min the bin is
`min(bins-1, floor((log10(x)-log_min)*bins/(-log_min)))`.

The environment has Python, NumPy, SciPy, and g++17. A local static FastJet 3.4.3
dependency is in `workspace/vendor`. Compile with
`-I<workspace>/vendor/include <workspace>/vendor/lib/libfastjet.a -lm`.
The historical implementation in `workspace/legacy` is an intentionally
incomplete starting point. There is no requirement to retain its architecture.
Keep generated binaries and intermediate files in the attempt directory, not
the read-only participant directory.

Evaluation uses multiple unlabeled CMS-derived ensembles, including rare
high-multiplicity jets, and analytic/kinematic checks. Constituent counts are
not reduced for evaluation (up to 139 in the real sample). Large jobs may use
100,000 jets. One CPU thread and 3 GiB address space are available. A job is
terminated after max(60 s, 5*the stored reference runtime +20 s), including
entrypoint startup; cache compilation in your attempt directory. Accuracy is
continuous normalized L1 skill relative to the supplied weak starting
contact-only weak approximation, with a characteristic error scale 2.5% of its error (minimum
0.0005). Runtime receives a smooth penalty on a scale of
20 s +12*reference runtime. Both mean and worst-family results are reported;
a missing central family cannot be hidden by easier cases.
"""

WEIGHTED = """
## Weighted projected observable

Query fields: `order` (integer 2..8), `kappa` (1..2), `algorithm` (`ca` or
`kt`), `resolution` (>1 for ca, >0 for kt), `log_min`, `bins`.

For uncompressed particles, sum over ordered order-tuples **with replacement**
the weight product of `(pt_i/sum_j pt_j)^kappa`; histogram the maximum pairwise
rapidity/periodic-azimuth distance in the tuple. Coincident indices count.

For compatibility the target uses the following finite-resolution prescription,
not the exact uncompressed observable. Recluster each supplied jet with FastJet
R=1.5 and `pt_scheme`, using the requested algorithm (generalized-kT powers
0 and 1 respectively). At every binary split let theta be the rapidity/azimuth
distance of the children. Resolve both children with
`exclusive_subjets(theta^2/(1.5^2*resolution))` in the requested clustering tree.
At this node include only tuples whose support intersects both children;
descendant-only contributions use their own resolution. Geometry is the
pt-scheme subjet rapidity and azimuth. For kappa=1 use subjet pt divided
by the original scalar total pt. For kappa!=1 use sum of constituent pt^kappa
divided by the original scalar total pt^kappa as each subjet's weight.
Single-particle leaves contribute the corresponding order-th power at zero.
These rules define the observable even where finite-resolution errors differ
from the exact particle-level result. Inputs recluster into a single R=1.5 jet.
"""

FRACTIONAL = """
## Continuous-order projected observable

Query fields: `nu` (positive real), `nsub` (integer 2..16), `log_min`, `bins`.
For a finite set S with fractions z_i define W(empty)=0 and
`W_nu(S) = (sum_{i in S} z_i)^nu - sum_{T proper subset of S} W_nu(T)`.
Histogram W_nu(S) at the largest pair distance within S; singleton distance
is zero. This is not interpolation between integer orders, and the result
need not be a positive measure.

The compatibility target uses a specified bounded-resolution prescription:
recluster each supplied jet with generalized-kT power 0, R=1.5, FastJet `pt_scheme`.
At each binary split resolve **each child separately** into at most
floor(nsub/2) exclusive subjets, using `exclusive_subjets_up_to`. Evaluate
the subset measure on this local union, counting only subsets intersecting
both children, then include descendant-only contributions at their own splits.
Fractions at a node are pt-scheme subjet pt divided by the **original
jet's scalar sum of constituent pt**. At original leaves include z_i^nu at
zero. This finite-resolution definition, including independent per-child
caps, is the target; do not substitute either an exact full-particle observable
or an anchor-distance projection. Inputs recluster into one R=1.5 jet.

The target is defined mathematically, but evaluation does not require tiny
relative accuracy for near-zero weights. Integer collapse, signed geometry,
and realistic multiplicity are separate checks. The normalization of a
compressed approximation is not forcibly reset to one.
"""

EWOC = """
## Subjet observables

Query fields: `geometry` (`pp` or `ee`), `algorithm` (`ca`, `kt`, `antikt`),
`radius` (positive, at most pi), `observable` (`mass` or `angular`),
`kappa` (positive), `log_min`, `bins` (at least 3).

Convert each input constituent to the massless four-vector
`(pt*cos(phi), pt*sin(phi), pt*sinh(y), pt*cosh(y))`. Recluster all constituents
of each supplied jet together, retaining every inclusive subjet at zero pt cut.
Use FastJet E-scheme. The pp algorithms are Cambridge/Aachen, kT, and anti-kT.
The ee algorithms are finite-radius `ee_genkt_algorithm` with powers 0, +1,
and -1, respectively, not exclusive Durham clustering. The radius is an angle
in radians in ee and a rapidity/azimuth radius in pp.

Let P_i denote a recombined subjet. The denominator W is the sum of ORIGINAL
constituent scalar pt in pp and original constituent energies in ee. Define
`z_i=pt(P_i)/W` in pp, `z_i=E(P_i)/W` in ee. For every ordered pair (i,j),
including each diagonal once, add `(z_i*z_j)^kappa` at coordinate X:

- Mass, i!=j: `sqrt((P_i+P_j)^2)` in GeV, including both subjet masses.
- Mass, i==j: `sqrt(P_i^2)`, the individual subjet mass, not twice that mass.
- Angular, i!=j: recombined-axis rapidity/periodic-azimuth distance in pp;
  three-momentum opening angle in radians in ee.
- Angular, i==j: zero.

Apply kappa AFTER recombination. Do not divide mass by the parent momentum,
discard massive diagonal contributions, substitute massless merged axes,
or normalize the output to unit area. Sum over bins equals the per-jet mean
of `(sum_i z_i^kappa)^2`. E-scheme does not conserve scalar pt in pp.

This concept OVERRIDES the common logarithmic-axis convention. There are
`bins-2` finite logarithmic cells between 10^log_min and U, plus separate
underflow and overflow. U=10000 GeV for mass and U=pi for angular. If F=bins-2
and L=log10(U), finite edges are `10^(log_min+(L-log_min)*k/F)` for k=0..F.
Cell zero contains X<10^log_min; finite cell k+1 contains the interval between
edges k and k+1; the final cell contains X>=U. Exact upper edges belong to the
cell on their right. Output still uses the common JSON interface and per-jet
mean bin masses.
"""


def shell(command, **kwargs):
    return subprocess.run(command, check=True, **kwargs)


def compile_official():
    private_source = AUTHOR / "reference_source"
    private_source.mkdir(exist_ok=True)
    binary_dir = AUTHOR / "bin"
    binary_dir.mkdir(exist_ok=True)
    for filename in ["eec_compute.h", "eec_higher_weight.h", "eec_nu_point.h", "read_events.h", "banner.h", "LICENSE"]:
        shutil.copyfile(AUTHOR / "FastEEC" / filename, private_source / filename)
    for name in ["eec_fast", "eec_fast_weight", "eec_fast_kt", "eec_fast_kt_weight", "eec_fast_nu_point"]:
        text = (AUTHOR / "FastEEC" / (name + ".cc")).read_text()
        text = text.replace("f.open(fname);", "f.open(fname);\n    f.precision(17);")
        (private_source / (name + ".cc")).write_text(text)
        shell(["g++", "-O3", "-std=c++17", "-I" + str(AUTHOR / "fastjet" / "include"), str(private_source / (name + ".cc")), str(AUTHOR / "fastjet" / "lib" / "libfastjet.a"), "-lm", "-o", str(binary_dir / name)])
    for name in ["resolved", "ewoc"]:
        source = AUTHOR / "adapters" / (name + "_reference.cpp")
        if source.exists():
            shell(["g++", "-O3", "-std=c++17", "-I" + str(AUTHOR / "fastjet" / "include"), str(source), str(AUTHOR / "fastjet" / "lib" / "libfastjet.a"), "-lm", "-o", str(binary_dir / (name + "_reference"))])


def queries(kind):
    base = {"log_min": -4.0, "bins": 48}
    if kind == "weighted":
        return [dict(base, order=order, kappa=kappa, algorithm=algorithm, resolution=resolution) for order, kappa, algorithm, resolution in [(3, 1.5, "ca", 8), (7, 2.0, "ca", 8), (4, 1.0, "kt", 0.03), (6, 1.5, "kt", 0.03)]]
    if kind == "fractional":
        return [dict(base, nu=nu, nsub=cap) for nu, cap in [(0.15, 12), (0.6, 16), (1.7, 14), (4.5, 12)]]
    if kind == "resolved":
        return [dict(base, order=order, ratio_bins=6, phi_bins=8, nu1=nu1, nu2=nu2, **({"nu3": nu3} if order == 4 else {})) for order, nu1, nu2, nu3 in [(3, 1.0, 1.0, 1.0), (3, 0.65, 1.7, 1.0), (4, 1.2, 0.45, 1.6), (4, 1.0, 1.0, 1.0)]]
    return [dict(base, geometry=geometry, algorithm=algorithm, radius=radius, observable=observable, kappa=kappa) for geometry, algorithm, radius, observable, kappa in [("pp", "antikt", 0.15, "mass", 1.0), ("pp", "kt", 0.08, "angular", 1.5), ("ee", "ca", 0.12, "mass", 1.0), ("ee", "kt", 0.18, "angular", 2.0)]]


def load_events():
    data = np.loadtxt(AUTHOR / "cms100k.txt")
    offsets = np.flatnonzero(np.r_[True, data[1:, 0] != data[:-1, 0], True])
    events = [data[offsets[index]:offsets[index + 1], 1:] for index in range(len(offsets) - 1)]
    counts = np.array([len(event) for event in events])
    record = {"jets": len(events), "constituents": len(data), "min": int(counts.min()), "median": float(np.median(counts)), "p90": float(np.quantile(counts, 0.9)), "p99": float(np.quantile(counts, 0.99)), "maximum": int(counts.max()), "sha256": hashlib.sha256((AUTHOR / "cms100k.txt").read_bytes()).hexdigest()}
    (AUTHOR / "data_audit.json").write_text(json.dumps(record, indent=2))
    return events, counts


def write_events(path, events):
    with path.open("w") as stream:
        for event_id, event in enumerate(events):
            for pt, rapidity, phi in event:
                stream.write(f"{event_id} {pt:.15g} {rapidity:.15g} {phi:.15g}\n")


def scaffold(kind, sample_events):
    pilot = ROOT / "pilots" / kind
    for directory in ["participant/input", "participant/workspace/legacy", "private/reference", "private/challenge_pool", "attempt"]:
        (pilot / directory).mkdir(parents=True, exist_ok=True)
    participant = pilot / "participant"
    (participant / "TASK.md").write_text("# Mission\n\n" + SPECS[kind] + "\n")
    extra = WEIGHTED if kind == "weighted" else FRACTIONAL if kind == "fractional" else EWOC if kind == "ewoc" else (AUTHOR / "specs" / (kind + "_contract.md")).read_text() if (AUTHOR / "specs" / (kind + "_contract.md")).exists() else "\nPENDING AUTHOR ADAPTER; DO NOT LAUNCH.\n"
    if kind == "resolved":
        extra = "\nQuery fields: `order`, `log_min`, `bins`, `ratio_bins`, `phi_bins`, `nu1`, `nu2`, and `nu3` for order 4. Omitted nu fields default to 1.\nThe following radial-bin convention overrides the common default.\n" + extra
    if kind == "ewoc":
        extra = "\nQuery fields: `geometry`, `algorithm`, `radius`, `observable`, `kappa`, `log_min`, `bins`.\n" + extra
    (participant / "input" / "CONTRACT.md").write_text(COMMON + extra)
    for filename in ["eec_fast.cc", "eec_compute.h", "read_events.h", "banner.h", "LICENSE"]:
        contents = subprocess.check_output(["git", "-C", str(AUTHOR / "FastEEC"), "show", "0.1:" + filename])
        (participant / "workspace" / "legacy" / filename).write_bytes(contents)
    vendor = participant / "workspace" / "vendor"
    shutil.copytree(AUTHOR / "fastjet" / "include", vendor / "include", dirs_exist_ok=True)
    (vendor / "lib").mkdir(exist_ok=True)
    shutil.copyfile(AUTHOR / "fastjet" / "lib" / "libfastjet.a", vendor / "lib" / "libfastjet.a")
    shutil.copyfile(AUTHOR / "fastjet-3.4.3" / "COPYING", vendor / "COPYING")
    job = {"kind": kind, "events_file": "sample.txt", "nevents": len(sample_events), "queries": queries(kind)}
    write_events(participant / "input" / "sample.txt", sample_events)
    (participant / "input" / "sample.json").write_text(json.dumps(job, indent=2))
    shutil.copyfile(AUTHOR / "evaluator_template.py", pilot / "private" / "evaluator.py")
    shutil.copyfile(AUTHOR / "weak_baseline.py", participant / "workspace" / "baseline.py")
    provenance = {"starting_commit": "54e6886", "private_commit": "54811e2" if kind == "fractional" else "54e6886" if kind == "weighted" else subprocess.check_output(["git", "-C", str(AUTHOR / "ResolvedEnergyCorrelators"), "rev-parse", "HEAD"], text=True).strip(), "private_adapter": kind, "public_files": [str(path.relative_to(participant)) for path in sorted(participant.rglob("*")) if path.is_file()]}
    (pilot / "private" / "reference" / "provenance.json").write_text(json.dumps(provenance, indent=2))


def make_case(kind, case_id, family, split, selected, query_list, source_ids):
    case_dir = ROOT / "pilots" / kind / "private" / "challenge_pool" / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    write_events(case_dir / "events.txt", selected)
    job = {"kind": kind, "events_file": "events.txt", "nevents": len(selected), "queries": query_list}
    (case_dir / "job.json").write_text(json.dumps(job, indent=2))
    return {"id": case_id, "family": family, "split": split, "source_ids": [int(index) for index in source_ids], "max_constituents": max(map(len, selected)), "nevents": len(selected)}


def build():
    events, counts = load_events()
    generator = np.random.default_rng(240608577)
    indices = generator.permutation(np.arange(100, len(events)))
    high = indices[counts[indices] >= 80]
    ordinary = indices[(counts[indices] >= 25) & (counts[indices] <= 60)]
    low = indices[counts[indices] <= 12]
    sample = [np.array([[240.0, 0.0, 0.0], [180.0, 0.18, 0.08], [80.0, -0.07, -0.16]]), events[7], events[29]]
    for kind in CONCEPTS:
        scaffold(kind, sample)
        listed = []
        configurations = [("pilot", 0), ("pool", 1), ("heldout", 2)]
        for split, offset in configurations:
            ordinary_size = 512 if kind in ["weighted", "fractional"] else 1024
            high_size = 128 if kind in ["weighted", "fractional", "resolved"] else 256
            groups = [("ordinary", ordinary[offset * 2048:offset * 2048 + ordinary_size]), ("high_multiplicity", high[offset * 512:offset * 512 + high_size]), ("sparse", low[offset * 32:offset * 32 + 24])]
            for family, selected_indices in groups:
                selected = [events[index] for index in selected_indices]
                query_list = queries(kind)
                if family == "sparse" and kind == "fractional":
                    query_list = [dict(log_min=-4.5, bins=63, nu=nu, nsub=cap) for nu, cap in [(0.03, 16), (0.5, 15), (1.0, 16), (3.0, 12)]]
                listed.append(make_case(kind, split + "_" + family, family, split, selected, query_list, selected_indices))
            transformed_indices = ordinary[10000 + offset * 256:10000 + offset * 256 + 128]
            transformed = [events[index].copy() for index in transformed_indices]
            for position, event in enumerate(transformed):
                event[:, 2] = np.mod(event[:, 2] + math.pi * 0.91, 2 * math.pi) - math.pi
                event[:, 0] *= 0.2 if position % 2 == 0 else 2.4
            query_list = queries(kind)
            listed.append(make_case(kind, split + "_rescaled_seam", "rescaled_seam", split, transformed, query_list, transformed_indices))
        manifest = {"kind": kind, "cases": listed, "public_cms_ids": [7, 29], "split_policy": "Disjoint original event IDs between pilot, inspected pool, and fresh heldout within each family; transformations use additional disjoint IDs."}
        (ROOT / "pilots" / kind / "private" / "challenge_pool" / "manifest.json").write_text(json.dumps(manifest, indent=2))


def reference(kind, case_id):
    pilot = ROOT / "pilots" / kind
    case_dir = pilot / "private" / "challenge_pool" / case_id
    job = json.loads((case_dir / "job.json").read_text())
    histograms = []
    weak_histograms = compute_weak(job, case_dir / "events.txt")["histograms"]
    started = time.monotonic()
    for query_index, query in enumerate(job["queries"]):
        output = pilot / "private" / "reference" / (case_id + "_q" + str(query_index) + ".txt")
        prefix = [str(case_dir / "events.txt"), str(job["nevents"])]
        if kind == "weighted":
            name = "eec_fast" + ("_kt" if query["algorithm"] == "kt" else "") + ("_weight" if query["kappa"] != 1 else "")
            options = [query["order"], query["resolution"]] + ([query["kappa"]] if query["kappa"] != 1 else []) + [query["log_min"], query["bins"]]
        elif kind == "fractional":
            name = "eec_fast_nu_point"
            options = [query["nu"], query["nsub"], query["log_min"], query["bins"]]
        elif kind == "resolved":
            name = "resolved_reference"
            options = [query["order"], query["log_min"], query["bins"], query["ratio_bins"], query["phi_bins"]]
        else:
            name = "ewoc_reference"
            options = [query[key] for key in ["geometry", "algorithm", "radius", "observable", "kappa", "log_min", "bins"]]
        command = [str(AUTHOR / "bin" / name)] + prefix + list(map(str, options)) + [str(output)]
        if kind == "resolved":
            command += [str(query.get("nu1", 1)), str(query.get("nu2", 1))]
            if query["order"] == 4:
                command += [str(query.get("nu3", 1))]
        process = shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if "Error:" in process.stdout:
            raise ValueError(process.stdout)
        numbers = np.fromstring(output.read_text(), sep=" ")
        if kind in ["weighted", "fractional"]:
            numbers = numbers[4:] / job["nevents"]
        if not np.all(np.isfinite(numbers)):
            raise ValueError("Nonfinite privileged reference")
        histograms.append(numbers.tolist())
    wall = time.monotonic() - started
    record = {"histograms": histograms, "weak_histograms": weak_histograms, "wall_seconds": wall, "maxrss_kb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss, "source": "official private module" if kind in ["weighted", "fractional"] else "source-derived adapter", "data_sha256": hashlib.sha256((case_dir / "events.txt").read_bytes()).hexdigest()}
    (pilot / "private" / "reference" / (case_id + ".json")).write_text(json.dumps(record))
    print(json.dumps({"kind": kind, "case": case_id, "wall_seconds": wall, "sums": [sum(histogram) for histogram in histograms]}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["compile", "build", "reference", "refresh"])
    parser.add_argument("--kind", choices=CONCEPTS)
    parser.add_argument("--split", default="pilot")
    parser.add_argument("--case")
    arguments = parser.parse_args()
    if arguments.action == "compile":
        compile_official()
    elif arguments.action == "build":
        build()
    elif arguments.action == "refresh":
        for kind in [arguments.kind] if arguments.kind else CONCEPTS:
            extra = WEIGHTED if kind == "weighted" else FRACTIONAL if kind == "fractional" else EWOC if kind == "ewoc" else (AUTHOR / "specs" / (kind + "_contract.md")).read_text()
            if kind == "resolved":
                extra = "\nQuery fields: `order`, `log_min`, `bins`, `ratio_bins`, `phi_bins`, `nu1`, `nu2`, and `nu3` for order 4. Omitted nu fields default to 1.\nThe following radial-bin convention overrides the common default.\n" + extra
            if kind == "ewoc":
                extra = "\nQuery fields: `geometry`, `algorithm`, `radius`, `observable`, `kappa`, `log_min`, `bins`.\n" + extra
            (ROOT / "pilots" / kind / "participant" / "input" / "CONTRACT.md").write_text(COMMON + extra)
            shutil.copyfile(AUTHOR / "weak_baseline.py", ROOT / "pilots" / kind / "participant" / "workspace" / "baseline.py")
    else:
        for kind in [arguments.kind] if arguments.kind else CONCEPTS:
            manifest = json.loads((ROOT / "pilots" / kind / "private" / "challenge_pool" / "manifest.json").read_text())
            for case in manifest["cases"]:
                if (arguments.case and arguments.case != case["id"]) or (not arguments.case and arguments.split != "all" and case["split"] != arguments.split):
                    continue
                reference(kind, case["id"])


if __name__ == "__main__":
    main()
