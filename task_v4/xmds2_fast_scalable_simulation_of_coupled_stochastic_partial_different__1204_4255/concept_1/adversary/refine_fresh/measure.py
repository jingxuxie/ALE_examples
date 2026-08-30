import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "participant" / "workspace"))
from model import check


def scores(rows):
    families = {}
    for family in sorted({row["family"] for row in rows}):
        selected = [row["ratio"] for row in rows if row["family"] == family]
        families[family] = 1 - math.exp(sum(map(math.log, selected)) / len(selected))
    overall = 1 - math.exp(sum(math.log(row["ratio"]) for row in rows) / len(rows))
    return {"core_score": overall, "family_scores": families, "worst_family_score": min(families.values()), "cost": sum(row["cost"] for row in rows), "baseline_cost": sum(row["baseline_cost"] for row in rows), "cost_targets_met": overall >= 0.20 and min(families.values()) >= 0.08}


def encode(instance, version):
    values = [instance["dimensions"], len(instance["sizes"]), instance["capacity"], len(instance["requests"])]
    values.extend(instance["sizes"])
    values.extend(value for row in instance["axis_cost"] for pair in row for value in pair)
    values.extend(value for row in instance["transpose_cost"] for value in row)
    for request in instance["requests"]:
        values.extend([request["field"], request["mask"], request["layout"]])
        if version.startswith("v1"):
            values.append(sum(1 << field for field in set(request["updates"])))
        else:
            values.append(len(request["updates"]))
            values.extend(request["updates"])
    return " ".join(map(str, values)) + "\n"


def measure(spec):
    cases_path = ROOT / "evaluator" / "hidden" / "cases.json"
    cases = json.loads(cases_path.read_text())
    directory = HERE / "results"
    directory.mkdir(exist_ok=True)
    name = spec["name"]
    payload = "".join(json.dumps(case["instance"], separators=(",", ":")) + "\n" if spec.get("json_protocol") else encode(case["instance"], spec["version"]) for case in cases)
    payload_path = directory / (name + ".input")
    payload_path.write_text(payload)
    command = spec.get("command", [str(HERE / "sources" / spec["version"] / "planner")])
    command = [str(HERE / item) if item.startswith("./") else item for item in command]
    environment = {key: value for key, value in os.environ.items() if not key.startswith(("PLANNER_", "REFINE_"))}
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "TMPDIR": str(HERE / "tmp")})
    environment.update({key: str(value) for key, value in spec.get("env", {}).items()})
    cpu = spec.get("cpu", sorted(os.sched_getaffinity(0))[len(os.sched_getaffinity(0)) // 2])
    limit = spec.get("timeout", 120)

    def limits():
        os.sched_setaffinity(0, {cpu})
        resource.setrlimit(resource.RLIMIT_AS, (1024 ** 3, 1024 ** 3))
        resource.setrlimit(resource.RLIMIT_CPU, (math.ceil(limit), math.ceil(limit) + 1))
        resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024 ** 2, 64 * 1024 ** 2))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    timed_out = False
    peak_rss = 0
    peak_as = 0
    resource_violation = None
    with payload_path.open() as stdin, (directory / (name + ".plans.jsonl")).open("w+") as stdout, (directory / (name + ".stderr")).open("w+") as stderr:
        process = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=stderr, env=environment, cwd=HERE, preexec_fn=limits, start_new_session=True)
        while process.poll() is None:
            pending = [process.pid]
            visited = set()
            resident = 0
            address_space = 0
            while pending:
                process_id = pending.pop()
                if process_id in visited:
                    continue
                visited.add(process_id)
                try:
                    for line in Path("/proc/%s/status" % process_id).read_text().splitlines():
                        if line.startswith("VmRSS:"):
                            resident += int(line.split()[1])
                        if line.startswith("VmSize:"):
                            address_space += int(line.split()[1])
                        if line.startswith("Cpus_allowed_list:") and line.split()[1] != str(cpu):
                            resource_violation = "expanded CPU affinity"
                    children = Path("/proc/%s/task/%s/children" % (process_id, process_id)).read_text()
                    pending.extend(map(int, children.split()))
                except (FileNotFoundError, ProcessLookupError):
                    pass
            peak_rss = max(peak_rss, resident)
            peak_as = max(peak_as, address_space)
            if address_space > 1024 ** 2:
                resource_violation = "aggregate address-space limit"
            if time.perf_counter() - started > limit or resource_violation:
                timed_out = time.perf_counter() - started > limit
                os.killpg(process.pid, 9)
                break
            time.sleep(0.025)
        process.wait()
        elapsed = time.perf_counter() - started
        stdout.seek(0)
        lines = stdout.read().splitlines()
        stderr.seek(0)
        error = stderr.read()[-8000:]
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    rows = []
    failure = None
    if timed_out or resource_violation or process.returncode or len(lines) != len(cases):
        failure = "planner failed/timed out/wrong output count"
    else:
        for case, line in zip(cases, lines):
            try:
                result = check(case["instance"], json.loads(line))
                rows.append({"id": case["id"], "family": case["family"], "baseline_cost": case["baseline"]["cost"], "ratio": result["cost"] / case["baseline"]["cost"], **result})
            except Exception as exception:
                failure = str(exception)
                break
    report = {"spec": spec, "valid": failure is None, "failure": failure, "cases": rows, "elapsed_seconds": elapsed, "cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime, "peak_sampled_rss_kib": peak_rss, "peak_sampled_as_kib": peak_as, "memory_sample_scope": "aggregate process tree", "resource_violation": resource_violation, "cpu_affinity": [cpu], "as_limit": 1024 ** 3, "returncode": process.returncode, "timed_out": timed_out, "stderr": error, "hidden_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(), "scope": "Direct authoring test; official isolated validation remains separate"}
    if failure is None:
        report.update(scores(rows))
    (directory / (name + ".json")).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("cases", "stderr")}, separators=(",", ":")), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("specs", type=Path)
    args = parser.parse_args()
    specs = json.loads(args.specs.read_text())
    for spec in specs:
        measure(spec)


if __name__ == "__main__":
    main()
