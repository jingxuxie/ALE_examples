import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import select
import signal
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parent.parent


def checked_cost(instance, plan):
    if type(plan) is not dict or set(plan) != {"slices", "merges"}:
        raise ValueError("expected exactly slices and merges")
    slices = plan["slices"]
    if type(slices) is not list or any(type(index) is not int for index in slices):
        raise ValueError("invalid slices")
    if len(set(slices)) != len(slices) or any(index < 0 or index >= len(instance["edges"]) for index in slices):
        raise ValueError("invalid slices")
    edges = instance["edges"]
    sliced = set(slices)
    active = {vertex: set() for vertex in range(instance["n"])}
    for index, edge in enumerate(edges):
        if index not in sliced:
            active[edge["u"]].add(index)
            active[edge["v"]].add(index)

    def elements(indices):
        return math.prod(edges[index]["dim"] for index in indices)

    allocations = {vertex: elements(indices) for vertex, indices in active.items()}
    live_storage = sum(allocations.values()) + bool(slices)
    peak = live_storage
    merges = plan["merges"]
    if type(merges) is not list or len(merges) != instance["n"] - 1:
        raise ValueError("wrong merge count")
    one_slice_work = 0
    for step, pair in enumerate(merges):
        if type(pair) is not list or len(pair) != 2 or any(type(index) is not int for index in pair):
            raise ValueError("invalid merge pair")
        left, right = pair
        if left == right or left not in active or right not in active:
            raise ValueError("invalid live tensor ID")
        result_indices = active[left].symmetric_difference(active[right])
        one_slice_work += elements(active[left].union(active[right]))
        output_size = elements(result_indices)
        peak = max(peak, live_storage + output_size)
        live_storage += output_size - allocations.pop(left) - allocations.pop(right)
        del active[left], active[right]
        active[instance["n"] + step] = result_indices
        allocations[instance["n"] + step] = output_size
    if len(active) != 1 or next(iter(active.values())):
        raise ValueError("non-scalar final tensor")
    assignments = elements(sliced)
    total = assignments * one_slice_work + assignments - 1
    return {"work": total, "log2_work": math.log2(total), "peak_elements": peak,
            "feasible": peak <= instance["memory_elements"]}


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, 2 * 1024 ** 3))
    resource.setrlimit(resource.RLIMIT_CPU, (46, 46))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 ** 2, 2 * 1024 ** 2))
    os.setsid()


def run_solver(submission, instance, scratch):
    available_cpus = sorted(os.sched_getaffinity(0))
    instance_digest = hashlib.sha256(json.dumps(instance, sort_keys=True).encode()).digest()
    selected_cpu = available_cpus[int.from_bytes(instance_digest[:4], "little") % len(available_cpus)]
    command = ["/usr/bin/bwrap", "--unshare-all", "--die-with-parent", "--new-session",
               "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
               "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
               "--ro-bind", "/etc/ld.so.cache", "/etc/ld.so.cache",
               "--ro-bind", "/etc/alternatives", "/etc/alternatives",
               "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
               "--ro-bind", str(submission), "/submission",
               "--ro-bind", str(submission), str(submission),
               "--ro-bind", str(ROOT / "participant"), "/participant",
               "--ro-bind", str(ROOT / "participant"), str(ROOT / "participant"),
               "--ro-bind", str(ROOT / "participant" / "workspace"), "/workspace",
               "--bind", str(scratch), "/work", "--chdir", "/work", "--clearenv",
               "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
               "--setenv", "PARTICIPANT_DIR", str(ROOT / "participant"),
               "--setenv", "PYTHONDONTWRITEBYTECODE", "1"]
    user_site = Path.home() / ".local" / "lib" / "python3.10" / "site-packages"
    python_path = "/workspace"
    if user_site.is_dir():
        command.extend(["--ro-bind", str(user_site), "/user-site"])
        python_path += ":/user-site"
    command.extend(["--setenv", "PYTHONPATH", python_path])
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        command.extend(["--setenv", variable, "1"])
    bootstrap = (
        "import os,sys\n"
        "os.write(1,b'HEAVYHEX_READY\\n')\n"
        "acknowledgement=bytearray()\n"
        "while not acknowledgement.endswith(b'\\n'):\n"
        " character=os.read(0,1)\n"
        " if not character: sys.exit(96)\n"
        " acknowledgement.extend(character)\n"
        "if acknowledgement != b'HEAVYHEX_START\\n': sys.exit(97)\n"
        "os.sched_setaffinity(0,{int(sys.argv[2])})\n"
        "os.execv(sys.executable,[sys.executable,sys.argv[1]])\n"
    )
    command.extend(["--", sys.executable, "-I", "-S", "-u", "-c", bootstrap,
                    str(submission / "solve.py"), str(selected_cpu)])
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=errors, cwd=scratch, preexec_fn=limits)
        try:
            ready, _, _ = select.select([process.stdout], [], [], 180)
            if not ready or process.stdout.readline() != b"HEAVYHEX_READY\n":
                raise RuntimeError("scoring sandbox failed its startup handshake")
            started = time.monotonic()
            cpu_before = resource.getrusage(resource.RUSAGE_CHILDREN)
            stdout, _ = process.communicate(b"HEAVYHEX_START\n" + json.dumps(instance).encode(), timeout=45)
            cpu_after = resource.getrusage(resource.RUSAGE_CHILDREN)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
        except Exception:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise
        errors.seek(0)
        stderr = errors.read(2 * 1024 ** 2).decode(errors="replace")
    elapsed = time.monotonic() - started
    if process.returncode:
        raise ValueError(f"solver exit {process.returncode}: {stderr[-400:]}")
    if len(stdout) > 2 * 1024 ** 2:
        raise ValueError("output exceeds limit")
    cpu_seconds = cpu_after.ru_utime + cpu_after.ru_stime - cpu_before.ru_utime - cpu_before.ru_stime
    resources = {"launcher_cpu_seconds": cpu_seconds, "cpu_affinity": selected_cpu,
                 "cpu_accounting_scope": "launcher only; nested solver CPU accounting unavailable"}
    return json.loads(stdout), elapsed, resources


def evaluate(submission):
    challenge = json.loads((ROOT / "evaluator" / "hidden" / "challenge.json").read_text())
    outcomes = []
    families = {}
    all_valid = True
    all_feasible = True
    with tempfile.TemporaryDirectory(prefix="heavyhex_scoring_") as scratch:
        for case in challenge["cases"]:
            try:
                plan, elapsed, resources = run_solver(submission, case["instance"], scratch)
                cost = checked_cost(case["instance"], plan)
                delta = math.log2(case["baseline_work"]) - cost["log2_work"]
                all_feasible &= cost["feasible"]
                outcomes.append({"id": case["id"], "family": case["family"],
                                 "runtime_seconds": elapsed, "log2_speedup": delta, **resources, **cost})
                families.setdefault(case["family"], []).append(delta)
            except Exception as error:
                all_valid = False
                outcomes.append({"id": case["id"], "family": case["family"],
                                 "error": str(error), "runtime_seconds": 45 if isinstance(error, subprocess.TimeoutExpired) else None})
    if all_valid:
        family_scores = {family: 2 ** (sum(values) / len(values)) for family, values in families.items()}
        core = 2 ** (sum(row["log2_speedup"] for row in outcomes) / len(outcomes))
        worst = min(family_scores.values())
        smallest = 2 ** min(row["log2_speedup"] for row in outcomes)
    else:
        core, worst, smallest, family_scores = 0.0, 0.0, 0.0, {}
    passed = all_valid and all_feasible and core >= 4 and worst >= 1.1 and smallest >= 1 / 1.05
    runtime = sum(row.get("runtime_seconds") or 0 for row in outcomes)
    return {"core_score": core, "worst_family_score": worst, "family_scores": family_scores,
            "minimum_case_speedup": smallest, "runtime_seconds": runtime,
            "resource_score": {"all_memory_feasible": bool(all_feasible), "time_limit_seconds_per_case": 45},
            "valid": bool(all_valid and all_feasible), "passed": bool(passed),
            "reason": "fixed improvement target met" if passed else "invalid/resource failure or fixed 4x/1.1x/no-regression target not met",
            "cases": outcomes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    result = evaluate(arguments.submission.resolve())
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2))
