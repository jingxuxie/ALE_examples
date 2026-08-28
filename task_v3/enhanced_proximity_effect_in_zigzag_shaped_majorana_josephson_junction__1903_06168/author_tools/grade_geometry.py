import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]


def limits(offset):
    resource.setrlimit(resource.RLIMIT_AS, (6 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (2400, 2400))
    available = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, available[offset:offset+2])


def run_request(job):
    case, solver, pilot, evidence, timeout, offset = job
    request = json.loads(case.read_text())
    identifier = request["request_id"]
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       BENCHMARK_SOLVER=str(solver), BENCHMARK_PARTICIPANT=str(pilot/"participant"))
    with tempfile.TemporaryDirectory(prefix="geometry-grading-") as temporary:
        staging = Path(temporary)
        input_path, output_path = staging/"request.json", staging/"result.json"
        input_path.write_text(json.dumps(request))
        started = time.monotonic()
        with (evidence/f"{identifier}.stdout.log").open("w") as stdout, (evidence/f"{identifier}.stderr.log").open("w") as stderr:
            process = subprocess.Popen([sys.executable, str(ROOT/"author_tools/sandbox_solver.py"),
                                        "--input", str(input_path), "--output", str(output_path)],
                                       stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                       env=environment, start_new_session=True, preexec_fn=partial(limits, offset))
            status = "completed"
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                returncode = process.wait()
                status = "time_limit"
        if output_path.exists():
            (evidence/"results"/f"{identifier}.json").write_bytes(output_path.read_bytes())
        return dict(request_id=identifier, status=status, returncode=returncode,
                    runtime_seconds=time.monotonic()-started, cpu_pair_offset=offset)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot", type=Path, default=ROOT/"pilots/04_geometry_design")
    parser.add_argument("--solver", type=Path)
    parser.add_argument("--round", default="initial")
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument("--parallel-scoring", action="store_true")
    parser.add_argument("--cpu-offset", type=int, default=0)
    args = parser.parse_args()
    pilot = args.pilot.resolve()
    solver = (args.solver or pilot/"attempt/solve.py").resolve()
    evidence = pilot/"private/runs"/args.round
    evidence.mkdir(parents=True, exist_ok=True)
    results = evidence/"results"
    results.mkdir(exist_ok=True)
    environment = dict(os.environ, OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       BENCHMARK_SOLVER=str(solver), BENCHMARK_PARTICIPANT=str(pilot/"participant"))
    diagnostics = []
    cases = sorted((pilot/"private/challenge_pool").glob("*/request.json"))
    jobs = [(case, solver, pilot, evidence, args.timeout, args.cpu_offset+2*(index % 3)) for index, case in enumerate(cases)]
    with ProcessPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_request, job) for job in jobs]
        for future in as_completed(futures):
            diagnostics.append(future.result())
            print(json.dumps(diagnostics[-1]), flush=True)
    (evidence/"execution.json").write_text(json.dumps(diagnostics, indent=2)+"\n")
    report = evidence/"score.json"
    if args.parallel_scoring:
        scorers = []
        for case in cases:
            case_report = evidence/f"{case.parent.name}.score.json"
            command = [sys.executable, str(pilot/"private/evaluator.py"), "--results-dir", str(results),
                       "--case", case.parent.name, "--workers", "3", "--output", str(case_report)]
            scorers.append((subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL), case_report))
        records = []
        scoring_rules = set()
        for process, case_report in scorers:
            if process.wait() != 0:
                raise RuntimeError(f"Trusted case scoring failed: {case_report}")
            case_score = json.loads(case_report.read_text())
            if not case_score["complete"]:
                raise RuntimeError(f"Trusted case scoring is incomplete: {case_report}")
            records.extend(case_score["cases"])
            scoring_rules.add(case_score["scoring_rule"])
        if len(scoring_rules) != 1 or len(records) != len(cases):
            raise RuntimeError("Inconsistent independent case reports")
        core = sum(record["score"] for record in records)/len(records)
        worst = min(records, key=lambda record: record["score"])
        combined = dict(complete=True, scoring_rule=scoring_rules.pop(), cases=records,
                        score=core, core_score=core,
                        core_feasibility=sum(record["core_feasible"] for record in records)/len(records),
                        worst_family_score=worst["score"], worst_family=worst["request_id"])
        report.write_text(json.dumps(combined, indent=2, allow_nan=False)+"\n")
    else:
        subprocess.run([sys.executable, str(pilot/"private/evaluator.py"), "--results-dir", str(results),
                        "--workers", "3", "--output", str(report)], env=environment, check=True,
                       stdin=subprocess.DEVNULL)
    print(str(report), flush=True)


if __name__ == "__main__":
    main()
