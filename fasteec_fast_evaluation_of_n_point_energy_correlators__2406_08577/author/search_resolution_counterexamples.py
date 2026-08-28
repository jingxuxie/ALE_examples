"""Bounded, sandboxed, source-grounded low-order resolution counterexample search."""

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import statistics
import subprocess
import sys
import time
import traceback

import numpy as np


ROOT = Path(__file__).resolve().parent.parent
TIMER = """import json,os,resource,subprocess,sys,time
start=time.monotonic()
completed=subprocess.run(sys.argv[1:])
end=time.monotonic()
usage=resource.getrusage(resource.RUSAGE_CHILDREN)
print('\\n__EXECUTION__ '+json.dumps({'wall_seconds':end-start,'cpu_seconds':usage.ru_utime+usage.ru_stime,'affinity':sorted(os.sched_getaffinity(0)),'returncode':completed.returncode}),flush=True)
sys.exit(completed.returncode)
"""


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def write_json(path, record):
    path.write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n")


def functions_from(path, names):
    module = ast.parse(path.read_text())
    selected = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in names]
    scope = {"sys": sys, "np": np, "Path": Path, "math": math}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), scope)
    return scope


def select_events(path, capacity=1024):
    started = time.monotonic()
    checksum = hashlib.sha256()
    selected = []
    current_id, current = None, []
    event_count = 0

    def consider(identifier, rows):
        nonlocal event_count
        if not rows:
            return
        event_count += 1
        if len(rows) >= 80:
            item = (len(rows), -identifier, tuple(rows))
            if len(selected) < capacity:
                heapq.heappush(selected, item)
            elif item[:2] > selected[0][:2]:
                heapq.heapreplace(selected, item)

    with path.open("rb") as stream:
        for raw in stream:
            checksum.update(raw)
            fields = raw.split()
            if not fields:
                continue
            if len(fields) != 4:
                raise ValueError("Malformed CMS record")
            identifier = int(fields[0])
            if identifier != current_id:
                if current_id is not None and identifier <= current_id:
                    raise ValueError("CMS events are not ordered")
                consider(current_id, current)
                current_id, current = identifier, []
            current.append(b" ".join(fields[1:]))
    consider(current_id, current)
    events = [{"source_id": -identifier, "M": count, "rows": rows}
              for count, identifier, rows in sorted(selected, reverse=True)]
    return events, {"data_sha256": checksum.hexdigest(), "events_scanned": event_count,
                    "selected_unique_events": len(events), "multiplicities": [event["M"] for event in events],
                    "selection": "Largest unique real jets with M>=80; all constituent rows retained, no resampling or truncation",
                    "selection_wall_seconds": time.monotonic() - started}


class Search:
    def __init__(self, root, cpu, budget):
        self.root, self.cpu = root, cpu
        self.author = root / "author"
        self.attempt = root / "pilots" / "weighted" / "attempt"
        self.participant = self.attempt.parent / "participant"
        self.output = self.author / "resolution_search"
        self.output.mkdir(exist_ok=True)
        self.stage = self.attempt / "resolution_probes"
        self.stage.mkdir(exist_ok=True)
        self.deadline = time.monotonic() + budget
        evaluator = functions_from(self.author / "evaluator_template.py", {"sandbox_command", "discrepancy"})
        self.sandbox_command = evaluator["sandbox_command"]
        self.discrepancy = evaluator["discrepancy"]
        self.weak = functions_from(self.author / "weak_baseline.py", {"compute"})["compute"]
        self.environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp", "LANG": "C.UTF-8",
                            "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                            "PYTHONHASHSEED": "0", "EEC_STATS": "1"}
        self.monitored = [self.attempt / name for name in ("solve.py", "engine.cpp", "engine")]
        self.monitored += [self.author / "evaluator_template.py", self.author / "weak_baseline.py",
                           Path(__file__).resolve()]
        self.monitored += [self.author / "bin" / name for name in
                           ("eec_fast", "eec_fast_weight", "eec_fast_kt", "eec_fast_kt_weight")]
        self.monitored += [self.author / "FastEEC" / name for name in
                           ("eec_compute.h", "eec_higher_weight.h", "eec_angles.cc", "read_events.h")]
        self.before = {str(path.relative_to(root)): digest(path) for path in self.monitored}
        self.report = {"started_utc": datetime.now(timezone.utc).isoformat(), "cpu": cpu,
                       "budget_seconds": budget, "source_hashes_before": self.before,
                       "cases": [], "source_grounding": {
                           "submitted_source": "pilots/weighted/attempt/engine.cpp",
                           "N2": "accumulate_block degree==2 uses direct cross-child pair loops, bypassing clique recursion",
                           "N3_N4": "Per-active-bin weighted clique moments, true-twin compression, full/left/right moment subtraction; source refs use direct sorted tuple loops",
                           "contract": "CA/kt, resolution 1024 or 1e6, orders 2/3/4 as separate single-query jobs, kappa in [1,2], bins 75/125, log_min=-5",
                           "reference": "Unmodified private official source binaries, pt_scheme and angular_distance^2/(R^2*f) cuts",
                           "angles_nu2": "At nu=2, E_s*((esum+z_j)^1-esum^1)=z_s*z_j; summing anchors plus z_s^2 contacts gives the exact full-particle ordered pair measure. Used as auxiliary validation/timing, never silently substituted for a finite-resolution target.",
                       }, "methodology": {
                           "scoring": "Unchanged evaluator discrepancy, weak baseline, scale=max(0.0005,0.025*weak_relative_l1), core=1/(1+(error/scale)^1.25), runtime=1/(1+(wall/(20+12*reference_wall))^2)",
                           "timing": "Inner supervisor measures launch-to-exit execution only, excluding bwrap and supervisor Python startup. Real solve.py and warm engine-only timings are separate; all children pinned to the same CPU.",
                           "scaling_gate": "Only scale when two repeated warm engine timing ranges are entirely slower than the reference timing range; no new quality threshold or failure cutoff",
                           "sandbox": "Uses evaluator_template.sandbox_command; submitted attempt additionally read-only, only public job/result directory writable at resolution_probes alias; private labels never mounted",
                           "compile_cache": "Use existing warm submitted engine unchanged; EEC_STATS diagnostics enabled, EEC_ORACLE absent",
                           "scope": "Runtime/quality probes, not fresh-agent difficulty evidence; no new hard solution or concept",
                       }}

    def limits(self):
        os.setsid()
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024 ** 3, 3 * 1024 ** 3))
        os.sched_setaffinity(0, {self.cpu})

    def sandbox(self, public, alias, target):
        command = self.sandbox_command(self.participant, self.attempt / "solve.py", alias)
        bind = command.index("--bind")
        command[bind] = "--ro-bind"
        split = command.index("--chdir")
        command[split:split] = ["--bind", str(public), str(alias)]
        split = command.index("--chdir") + 2
        return command[:split] + [sys.executable, "-c", TIMER, *map(str, target)]

    def execute(self, command, directory, name, payload=None, timeout=60):
        if self.deadline - time.monotonic() < min(timeout, 5):
            raise TimeoutError("Sidecar work budget exhausted; not a submitted failure")
        started = time.monotonic()
        with (directory / (name + ".stdout")).open("w") as stdout, (directory / (name + ".stderr")).open("w") as stderr:
            process = subprocess.Popen(command, stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
                                       stdout=stdout, stderr=stderr, text=True, env=self.environment,
                                       preexec_fn=self.limits, cwd=directory)
            try:
                process.communicate(payload, timeout=min(timeout + 60, max(1, self.deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise TimeoutError("Censored by sidecar wall budget; not assigned a submission failure")
        output = (directory / (name + ".stdout")).read_text()
        stderr = (directory / (name + ".stderr")).read_text()
        markers = [line[len("__EXECUTION__ "):] for line in output.splitlines() if line.startswith("__EXECUTION__ ")]
        if process.returncode != 0 or len(markers) != 1 or "Error:" in output:
            raise RuntimeError(f"{name}: exit={process.returncode}; {stderr[-1800:]}")
        timing = json.loads(markers[0])
        if timing["affinity"] != [self.cpu]:
            raise RuntimeError("CPU affinity drift")
        timing["sandbox_and_supervisor_overhead_seconds"] = time.monotonic() - started - timing["wall_seconds"]
        timing["command"] = command
        stats = re.search(r"seconds=([\d.eE+-]+) splits=(\d+) subjets=(\d+) max_subjets=(\d+) recursions=(\d+)", stderr)
        if stats:
            timing["engine_stats"] = dict(zip(("internal_seconds", "splits", "subjets", "max_subjets", "recursions"),
                                                (float(stats[1]), *map(int, stats.groups()[1:]))))
        write_json(directory / (name + ".timing.json"), timing)
        return timing, "\n".join(line for line in output.splitlines() if not line.startswith("__EXECUTION__ ")).strip()

    def quality(self, prediction, reference, weak):
        error = self.discrepancy(prediction, reference)
        weak_error = self.discrepancy(weak, reference)
        scale = max(0.0005, 0.025 * weak_error)
        quality = 1 / (1 + (error / scale) ** 1.25) if math.isfinite(error) else 0.0
        absolute = np.abs(np.asarray(prediction) - np.asarray(reference))
        return {"relative_l1": error, "max_absolute_error": float(absolute.max()),
                "l1_error": float(absolute.sum()), "weak_relative_l1": weak_error,
                "characteristic_scale": scale, "core_quality": quality}

    def prepare(self):
        if self.cpu not in os.sched_getaffinity(0) or self.cpu == 383:
            raise RuntimeError("Requested isolated CPU unavailable or conflicts with main evaluator")
        if (self.attempt / "engine").stat().st_mtime_ns < (self.attempt / "engine.cpp").stat().st_mtime_ns:
            raise RuntimeError("Submitted cache is stale; refusing to modify submitted files")
        self.events, selection = select_events(self.author / "cms100k.txt")
        self.report["selection"] = selection
        public = self.output / "sandbox_probe"
        public.mkdir(exist_ok=True)
        alias = self.stage / "sandbox_probe"
        alias.mkdir(exist_ok=True)
        hidden = [str(self.author / "cms100k.txt"), str(self.author / "bin" / "eec_fast"),
                  str(self.output), str(self.root / "pilots" / "weighted" / "private")]
        guard = "import json,os; paths=" + repr(hidden) + "; visible=[p for p in paths if os.path.exists(p)]; print(json.dumps({'private_paths_visible':visible})); assert not visible"
        timing, output = self.execute(self.sandbox(public, alias, [sys.executable, "-c", guard]), public, "guard")
        self.report["sandbox_check"] = {"result": json.loads(output), "timing": timing}
        source = (self.author / "FastEEC" / "eec_angles.cc").read_text()
        source = source.replace("f.open(fname);", "f.open(fname);\n    f.precision(17);")
        angles_source = self.output / "eec_angles_17.cc"
        angles_source.write_text(source)
        self.angles = self.output / "eec_angles_17"
        command = ["g++", "-O3", "-std=c++17", "-I" + str(self.author / "FastEEC"),
                   "-I" + str(self.author / "fastjet" / "include"), str(angles_source),
                   str(self.author / "fastjet" / "lib" / "libfastjet.a"), "-lm", "-o", str(self.angles)]
        with (self.output / "angles_build.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=log, check=True, timeout=45,
                           env=dict(os.environ, TMPDIR=str(self.output)), preexec_fn=self.limits)
        self.report["angles_driver"] = {"source_sha256": digest(angles_source), "binary_sha256": digest(self.angles),
                                         "change": "17-digit serialization only, same as existing private reference builds"}
        self.save()

    def case(self, query, count, label, repeat=1):
        events = self.events[:count]
        if len(events) != count:
            raise ValueError("Insufficient distinct actual high-M jets; no replication permitted")
        directory = self.output / label
        directory.mkdir(exist_ok=True)
        public = directory / "public"
        public.mkdir(exist_ok=True)
        alias = self.stage / label
        alias.mkdir(exist_ok=True)
        data = b"".join(str(index).encode() + b" " + row + b"\n"
                        for index, event in enumerate(events) for row in event["rows"])
        (public / "events.txt").write_bytes(data)
        job = {"kind": "weighted", "events_file": "events.txt", "nevents": count, "queries": [query]}
        write_json(public / "job.json", job)
        weak = self.weak(job, public / "events.txt")["histograms"][0]
        name = "eec_fast" + ("_kt" if query["algorithm"] == "kt" else "") + ("_weight" if query["kappa"] != 1 else "")
        options = [query["order"], query["resolution"]] + ([query["kappa"]] if query["kappa"] != 1 else []) + [-5, query["bins"]]
        payload = f"{alias / 'events.txt'}\n{count} 1\n" + " ".join(map(str, [query[key] for key in
                   ("order", "kappa", "algorithm", "resolution", "log_min", "bins")])) + "\n"
        refs, engines, wrappers = [], [], []
        for iteration in range(repeat):
            reference_file = directory / f"reference_{iteration}.txt"
            command = [sys.executable, "-c", TIMER, str(self.author / "bin" / name), str(public / "events.txt"),
                       str(count), *map(str, options), str(reference_file)]
            timing, unused = self.execute(command, directory, f"reference_{iteration}")
            refs.append(timing)
            values = np.fromstring(reference_file.read_text(), sep=" ")
            if len(values) != query["bins"] + 4 or list(values[:4]) != [count, query["bins"], -5, 0]:
                raise ValueError("Unexpected official histogram header")
            reference = (values[4:] / count).tolist()
            timeout = max(60, 5 * timing["wall_seconds"] + 20)
            timing, raw = self.execute(self.sandbox(public, alias, [self.attempt / "engine"]), directory,
                                       f"engine_{iteration}", payload, timeout)
            engines.append(timing)
            engine = json.loads(raw)["histograms"][0]
            timing, unused = self.execute(self.sandbox(public, alias, [sys.executable, self.attempt / "solve.py",
                                             "--input", alias / "job.json", "--output", alias / "result.json"]),
                                         directory, f"submitted_{iteration}", timeout=timeout)
            wrappers.append(timing)
            prediction = json.loads((public / "result.json").read_text())["histograms"][0]
        ref_wall = statistics.median(item["wall_seconds"] for item in refs)
        engine_wall = statistics.median(item["wall_seconds"] for item in engines)
        submitted_wall = statistics.median(item["wall_seconds"] for item in wrappers)
        quality = self.quality(prediction, reference, weak)
        runtime_score = 1 / (1 + (submitted_wall / (20 + 12 * ref_wall)) ** 2)
        record = {"id": label, "query": query, "nevents": count,
                  "source_ids": [event["source_id"] for event in events],
                  "multiplicities": [event["M"] for event in events], "data_sha256": hashlib.sha256(data).hexdigest(),
                  "single_query_job": True, "reference_binary": name,
                  "reference_execution_seconds": ref_wall, "engine_execution_seconds": engine_wall,
                  "submitted_execution_seconds": submitted_wall, "engine_reference_ratio": engine_wall / ref_wall,
                  "submitted_reference_ratio": submitted_wall / ref_wall, "reference_timings": refs,
                  "engine_timings": engines, "submitted_timings": wrappers,
                  "quality": quality, "engine_vs_submitted": self.quality(engine, prediction, weak),
                  "runtime_score": runtime_score, "score": quality["core_quality"] * runtime_score,
                  "evaluator_timeout_seconds": max(60, 5 * ref_wall + 20),
                  "genuine_algorithmic_slowdown": repeat >= 2 and min(item["wall_seconds"] for item in engines)
                  > max(item["wall_seconds"] for item in refs)}
        if query["order"] == 2 and query["kappa"] == 1:
            angles_output = directory / "angles.txt"
            timing, unused = self.execute([sys.executable, "-c", TIMER, str(self.angles), str(public / "events.txt"),
                                           str(count), "2", "-5", str(query["bins"]), str(angles_output)], directory, "angles")
            angles = (np.fromstring(angles_output.read_text(), sep=" ")[4:] / count).tolist()
            independent = [0.0] * query["bins"]
            for event in events:
                particles = [tuple(map(float, row.split())) for row in event["rows"]]
                total = math.fsum(particle[0] for particle in particles)
                for first in particles:
                    for second in particles:
                        distance = math.hypot(first[1] - second[1], math.remainder(first[2] - second[2], math.tau))
                        position = 0 if distance <= 1e-5 else min(query["bins"] - 1, max(0, math.floor((math.log10(distance) + 5) * query["bins"] / 5)))
                        independent[position] += first[0] * second[0] / total ** 2 / count
            record["angles_nu2"] = {"timing": timing, "against_independent_ordered_pairs": self.quality(angles, independent, weak),
                                     "finite_reference_against_exact_pairs": self.quality(reference, independent, weak),
                                     "against_official_finite_target": self.quality(angles, reference, weak),
                                     "used_for_scoring": False}
        write_json(directory / "case.json", record)
        self.report["cases"].append(record)
        self.save()
        print(json.dumps({"id": label, "N": query["order"], "events": count, "ratio": record["engine_reference_ratio"],
                          "core": quality["core_quality"], "submitted_seconds": submitted_wall}), flush=True)
        return record

    def save(self):
        write_json(self.output / "report.json", self.report)

    def run(self):
        self.prepare()
        for order in (2, 3, 4):
            for algorithm in ("ca", "kt"):
                for resolution in (1024.0, 1e6):
                    for bins in (75, 125):
                        if self.deadline - time.monotonic() < 90:
                            self.report["screening_stopped_for_budget"] = True
                            break
                        query = {"order": order, "kappa": 1.0 if order == 2 else 1.5, "algorithm": algorithm,
                                 "resolution": resolution, "bins": bins, "log_min": -5.0}
                        self.case(query, 2, f"screen_N{order}_{algorithm}_f{int(resolution)}_b{bins}")
        candidates = sorted(self.report["cases"], key=lambda case: case["engine_reference_ratio"], reverse=True)
        confirmed = []
        for candidate in candidates[:3]:
            if candidate["engine_reference_ratio"] <= 1 or self.deadline - time.monotonic() < 65:
                continue
            record = self.case(candidate["query"], 8, "confirm_" + candidate["id"], repeat=2)
            if record["genuine_algorithmic_slowdown"]:
                confirmed.append(record)
        if confirmed:
            strongest = max(confirmed, key=lambda case: case["engine_reference_ratio"])
            previous = strongest
            for count in (32, 128, 512, 1024):
                if count > len(self.events):
                    continue
                allowance = count / previous["nevents"] * (previous["submitted_execution_seconds"]
                             + previous["engine_execution_seconds"] + previous["reference_execution_seconds"])
                if self.deadline - time.monotonic() < max(25, 1.5 * allowance):
                    break
                previous = self.case(strongest["query"], count, f"scaled_{count}_" + strongest["id"])
                previous["scaling_authorized_by"] = strongest["id"]
                self.save()
        self.report["source_hashes_after"] = {str(path.relative_to(self.root)): digest(path) for path in self.monitored}
        self.report["submitted_and_reference_sources_unchanged"] = self.before == self.report["source_hashes_after"]
        self.report["observed_source_drift"] = {
            name: {"before": checksum, "after": self.report["source_hashes_after"][name]}
            for name, checksum in self.before.items()
            if checksum != self.report["source_hashes_after"][name]
        }
        submitted_prefix = "pilots/weighted/attempt/"
        self.report["submitted_sources_unchanged"] = all(
            checksum == self.report["source_hashes_after"][name]
            for name, checksum in self.before.items() if name.startswith(submitted_prefix)
        )
        self.report["template_changed_during_search"] = "author/evaluator_template.py" in self.report["observed_source_drift"]
        hardest = min(self.report["cases"], key=lambda case: case["score"]) if self.report["cases"] else None
        self.report["summary"] = {"completed_cases": len(self.report["cases"]), "confirmed_algorithmic_slowdowns": [case["id"] for case in confirmed],
                                  "hardest_case": hardest["id"] if hardest else None,
                                  "finding": "confirmed runtime-only slowdown; inspect unchanged evaluator scores, not an invented failure threshold" if confirmed else "no confirmed counterexample in the bounded search",
                                  "new_precision_threshold": False, "new_target": False,
                                  "submitted_sources_modified": not self.report["submitted_sources_unchanged"]}
        self.report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--cpu", type=int, default=381)
    parser.add_argument("--budget-seconds", type=float, default=360)
    arguments = parser.parse_args()
    search = Search(arguments.root.resolve(), arguments.cpu, arguments.budget_seconds)
    try:
        search.run()
    except Exception as error:
        search.report["sidecar_error"] = str(error)
        search.report["traceback"] = traceback.format_exc()
        search.report["error_is_not_a_submitted_failure"] = True
        search.save()
        print(traceback.format_exc(), flush=True)
        return 1
    print(json.dumps(search.report["summary"], sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
