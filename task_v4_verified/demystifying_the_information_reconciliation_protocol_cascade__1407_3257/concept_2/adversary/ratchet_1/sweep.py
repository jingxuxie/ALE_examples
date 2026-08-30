import argparse
import concurrent.futures
import hashlib
import importlib.util
import itertools
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import time


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT.parents[1] / "champions/generation_1"
sys.path.insert(0, str(ARCHIVE / "participant/workspace"))
sys.path.insert(0, str(ARCHIVE / "evaluator"))
from replay import replay, validate
from reproduce import reproduce
from adapt import adapt_sources


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def read_json(path):
    return json.loads(path.read_text())


def geometry(deployment):
    groups = [math.ceil(deployment["n"] / specification["block_size"]) for specification in deployment["passes"]]
    offsets = [0, *itertools.accumulate(groups)]
    incidence = [[0] * 6 for position in range(deployment["n"])]
    rows = []
    for pass_index, specification in enumerate(deployment["passes"]):
        block_size = specification["block_size"]
        for start in range(0, deployment["n"], block_size):
            block = specification["permutation"][start:start + block_size]
            rows.append(sum(1 << position for position in block))
            for position in block:
                incidence[position][pass_index] = start // block_size
    basis = {}
    for row in rows:
        while row:
            pivot = row.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = row
                break
            row ^= basis[pivot]
    return {"group_counts": groups, "check_offsets": offsets[:-1], "checks": len(rows), "rank": len(basis), "incidence": incidence}


def certify(deployment, errors):
    validate(deployment, errors)
    assert 1 <= len(errors) <= 24
    families = {}
    for priority in ("earliest", "shortest"):
        observed = replay(deployment, errors, priority)
        independent = reproduce(deployment, errors, priority)
        assert observed == independent
        assert observed["initial_odd"] >= 6
        assert len(observed["corrected"]) >= 6
        assert len(observed["residual"]) >= 8
        families[priority] = observed
    return {"passed": True, "error_weight": len(errors), "families": families}


def activate(deployment, core):
    assert 8 <= len(core) <= 18 and len(core) == len(set(core))
    core_set = set(core)
    for specification in deployment["passes"]:
        for start in range(0, deployment["n"], specification["block_size"]):
            block = specification["permutation"][start:start + specification["block_size"]]
            assert len(core_set.intersection(block)) % 2 == 0
    first_pass = deployment["passes"][0]
    activation = []
    for start in range(0, deployment["n"], first_pass["block_size"]):
        block = first_pass["permutation"][start:start + first_pass["block_size"]]
        if not core_set.intersection(block):
            activation.append(block[0])
        if len(activation) == 6:
            break
    errors = sorted(core + activation)
    certificate = certify(deployment, errors)
    return {"errors": errors}, certificate


def construct(size, block_sizes, weight, spread, seed):
    generator = random.Random(seed)
    first_size = block_sizes[0]
    first_groups = list(range(size // first_size))
    occupancies = [2] * (weight // 2) if spread == "pairs" else [4] * (weight // 4) + ([2] if weight % 4 else [])
    core_groups = generator.sample(first_groups, len(occupancies))
    core = sorted(position for group, occupancy in zip(core_groups, occupancies) for position in generator.sample(range(group * first_size, (group + 1) * first_size), occupancy))
    trigger_groups = generator.sample([group for group in first_groups if group not in core_groups], 6)
    triggers = sorted(group * first_size + generator.randrange(first_size) for group in trigger_groups)
    core_set = set(core)
    passes = [{"block_size": first_size, "permutation": list(range(size))}]
    for pass_index, block_size in enumerate(block_sizes[1:], 1):
        selected_groups = generator.sample(range(size // block_size), len(occupancies))
        slots = [position for group, occupancy in zip(selected_groups, occupancies) for position in generator.sample(range(group * block_size, (group + 1) * block_size), occupancy)]
        shuffled_core = list(core)
        generator.shuffle(shuffled_core)
        remainder = [position for position in range(size) if position not in core_set]
        generator.shuffle(remainder)
        permutation = [None] * size
        for slot, position in zip(slots, shuffled_core):
            permutation[slot] = position
        available = iter(remainder)
        passes.append({"block_size": block_size, "permutation": [next(available) if position is None else position for position in permutation]})
    deployment = {"n": size, "passes": passes, "version": 1}
    witness = {"errors": sorted(core + triggers)}
    certificate = certify(deployment, witness["errors"])
    return deployment, witness, {"seed": seed, "n": size, "block_sizes": block_sizes, "core_weight": weight, "spread": spread, "occupancies_per_pass": occupancies, "core": core, "triggers": triggers, "certificate": certificate}


def compile_geometry(directory, deployment, details):
    directory.mkdir(parents=True, exist_ok=True)
    header = "#include <array>\n"
    constants = {"length": deployment["n"], "checks": details["checks"], "syndrome_words": math.ceil(details["checks"] / 64), "max_block_size": max(specification["block_size"] for specification in deployment["passes"]), "matrix_rank": details["rank"]}
    for name, value in constants.items():
        header += f"constexpr int {name} = {value};\n"
    for name in ("group_counts", "check_offsets"):
        header += f"constexpr std::array<int, 6> {name} = {{{', '.join(map(str, details[name]))}}};\n"
    (directory / "geometry.hpp").write_text(header)
    commands = []
    for method, source, initial in (("bp", "bp_search", None), ("group", "group_search", 20), ("group_v3", "group_search", 1000)):
        command = ["g++", "-O3", "-march=native", "-std=c++17", "-I", str(directory), str(ROOT / "sources" / f"{source}.cpp"), "-o", str(directory / method)]
        if initial is not None:
            command.append(f"-DINITIAL_BEST={initial}")
        completed = subprocess.run(command, capture_output=True, text=True)
        commands.append({"command": command, "returncode": completed.returncode, "stderr": completed.stderr})
        if completed.returncode:
            write_json(directory / "compile.json", commands)
            raise RuntimeError(completed.stderr)
    write_json(directory / "compile.json", commands)


def prepare():
    adapt_sources()
    configurations = []
    for size, block_size in ((2048, 32), (4096, 64), (8192, 128)):
        for weight in (14, 16, 18):
            configurations.append((f"n{size}_b{block_size}_w{weight}_pairs", size, [block_size] * 6, weight, "pairs"))
    for size, block_size, weight, spread in ((2048, 16, 18, "pairs"), (2048, 64, 18, "pairs"), (4096, 32, 18, "pairs"), (8192, 64, 18, "pairs"), (4096, 64, 18, "quartets"), (8192, 128, 18, "quartets")):
        configurations.append((f"n{size}_b{block_size}_w{weight}_{spread}", size, [block_size] * 6, weight, spread))
    configurations.append(("n4096_mixed_w18_pairs", 4096, [32, 48, 64, 96, 48, 64], 18, "pairs"))
    cases = []
    original = read_json(ARCHIVE / "participant/input/deployment.json")
    original_witness = read_json(ARCHIVE / "evaluator/hidden/privileged_witness.json")
    constructions = [("archive_control", original, original_witness, {"seed": None, "n": original["n"], "block_sizes": [specification["block_size"] for specification in original["passes"]], "core_weight": 14, "spread": "pairs", "certificate": certify(original, original_witness["errors"])})]
    for index, (name, size, block_sizes, weight, spread) in enumerate(configurations):
        deployment, witness, construction = construct(size, block_sizes, weight, spread, 2814082026 + index * 104729)
        constructions.append((name, deployment, witness, construction))
    geometries = {}
    for name, deployment, witness, construction in constructions:
        directory = ROOT / "cases" / name
        write_json(directory / "deployment.json", deployment)
        write_json(directory / "privileged_witness.json", witness)
        details = geometry(deployment)
        geometry_id = f"n{deployment['n']}_" + "_".join(str(specification["block_size"]) for specification in deployment["passes"]) + f"_r{details['rank']}"
        construction.update({key: value for key, value in details.items() if key != "incidence"})
        if "core" in construction:
            common = [sum(details["incidence"][first][pass_index] == details["incidence"][second][pass_index] for pass_index in range(6)) for first, second in itertools.combinations(construction["core"], 2)]
            construction["core_pair_shared_checks_histogram"] = {str(count): common.count(count) for count in range(7)}
        construction["deployment_sha256"] = hashlib.sha256((directory / "deployment.json").read_bytes()).hexdigest()
        construction["geometry_id"] = geometry_id
        write_json(directory / "construction.json", construction)
        (directory / "blocks.txt").write_text("".join(" ".join(map(str, memberships)) + "\n" for memberships in details["incidence"]))
        geometries[geometry_id] = (deployment, details)
        cases.append({"case": name, "geometry_id": geometry_id, **{key: construction[key] for key in ("n", "block_sizes", "core_weight", "spread", "rank", "seed")}})
    write_json(ROOT / "cases.json", cases)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(compile_geometry, ROOT / "bin" / geometry_id, deployment, details) for geometry_id, (deployment, details) in geometries.items()]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    print(json.dumps({"cases": len(cases), "geometries": len(geometries), "certified": len(constructions)}, indent=2), flush=True)


def run_job(job):
    case_directory = ROOT / "cases" / job["case"]
    directory = ROOT / "runs" / job["phase"] / job["case"] / job["label"]
    if (directory / "result.json").exists():
        return read_json(directory / "result.json")
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(case_directory / "blocks.txt", directory / "blocks.txt")
    shutil.copyfile(case_directory / "deployment.json", directory / "deployment.json")
    construction = read_json(case_directory / "construction.json")
    if job["method"] == "sat":
        command = [sys.executable, "-B", str(ROOT / "sources/sat_search.py"), "--seed", str(job["seed"]), "--seconds", str(job["seconds"])]
    else:
        executable = ROOT / "bin" / construction["geometry_id"] / job["method"]
        if job["method"].startswith("archived_"):
            executable = ARCHIVE / "submission" / job["method"].removeprefix("archived_")
        command = [str(executable), str(job["seconds"]), str(job["seed"])]
        if "group" in job["method"]:
            command.extend([str(job["grouping_pass"]), str(job["chosen_groups"])])
    write_json(directory / "launch.json", {**job, "command": command, "cwd": str(directory), "utc_start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    started = time.monotonic()
    timed_out = False
    with (directory / "stdout.log").open("w") as stdout, (directory / "stderr.log").open("w") as stderr:
        process = subprocess.Popen(command, cwd=directory, stdout=stdout, stderr=stderr, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        while True:
            waited, status, resources = os.wait4(process.pid, os.WNOHANG)
            if waited:
                returncode = os.waitstatus_to_exitcode(status)
                process.returncode = returncode
                break
            if time.monotonic() - started > job["seconds"] + 8 and not timed_out:
                timed_out = True
                process.kill()
            time.sleep(0.05)
    elapsed = time.monotonic() - started
    log = (directory / "stdout.log").read_text()
    best_weights = [int(weight) for weight in re.findall(r"^BEST (\d+):", log, re.MULTILINE)]
    progress = re.findall(r"^PROGRESS (\d+) ([0-9.e+\-]+).*", log, re.MULTILINE)
    result = {**job, "wall_seconds": elapsed, "user_cpu_seconds": resources.ru_utime, "system_cpu_seconds": resources.ru_stime, "max_rss_kib": resources.ru_maxrss, "returncode": returncode, "external_timeout": timed_out, "best_weight": min(best_weights) if best_weights else None, "last_progress": progress[-1] if progress else None, "solved": False, "error": None}
    for core_name in ("bp_core.json", "sparse_core.json", "group_core.json", "sat_core.json"):
        core_path = directory / core_name
        if not core_path.exists():
            continue
        core = read_json(core_path)["errors"]
        if not 8 <= len(core) <= 18:
            continue
        try:
            witness, certificate = activate(read_json(case_directory / "deployment.json"), core)
            write_json(directory / "witness.json", witness)
            write_json(directory / "certificate.json", certificate)
            result.update(solved=True, best_weight=len(core), certificate_passed=True)
        except (AssertionError, ValueError, TypeError) as exception:
            result["error"] = f"invalid solver core: {exception}"
    if returncode != 0 and not timed_out:
        result["error"] = (directory / "stderr.log").read_text()[-1500:]
    write_json(directory / "result.json", result)
    print(json.dumps({key: result[key] for key in ("phase", "case", "label", "wall_seconds", "solved", "best_weight", "error")}), flush=True)
    return result


def portfolio(cases, phase, seconds):
    jobs = []
    for case in cases:
        scaled = max(0, math.floor(0.84 * case["rank"] / case["block_sizes"][0]))
        variants = [("group", 478931, 0, scaled), ("group", 812931, 1, max(0, math.floor(0.84 * case["rank"] / case["block_sizes"][1]))), ("group", 57377, 2, 0), ("group_v3", 918273, 0, scaled), ("bp", 345778, None, None)]
        if phase == "confirmation":
            variants.extend([("group", 982451653, 0, 2), ("group", 15485863, 1, 3), ("group", 32452843, 3, scaled), ("group_v3", 49979687, 4, 0), ("bp", 271828, None, None), ("sat", 104729, None, None)])
        for method, seed, grouping_pass, chosen_groups in variants:
            label = f"{method}_s{seed}" + (f"_p{grouping_pass}_g{chosen_groups}" if grouping_pass is not None else "")
            jobs.append({"case": case["case"], "phase": phase, "method": method, "seed": seed, "grouping_pass": grouping_pass, "chosen_groups": chosen_groups, "seconds": seconds, "label": label})
    return jobs


def run_campaign(phase, seconds, workers, selected):
    cases = read_json(ROOT / "cases.json")
    if selected:
        cases = [case for case in cases if case["case"] in selected]
        assert len(cases) == len(selected)
    jobs = portfolio(cases, phase, seconds)
    write_json(ROOT / f"{phase}_plan.json", jobs)
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(run_job, jobs))
    write_json(ROOT / f"{phase}_results.json", {"wall_seconds": time.monotonic() - started, "workers": workers, "results": results})
    summarize()


def summarize():
    cases = read_json(ROOT / "cases.json")
    all_results = [read_json(path) for path in sorted((ROOT / "runs").glob("*/*/*/result.json"))]
    summaries = []
    for case in cases:
        results = [result for result in all_results if result["case"] == case["case"]]
        solved = [result for result in results if result["solved"]]
        best = [result["best_weight"] for result in results if result["best_weight"] is not None]
        summaries.append({**case, "runs": len(results), "successes": len(solved), "failures_within_cap": len(results) - len(solved), "run_errors": sum(result["error"] is not None for result in results), "best_weight": min(best) if best else None, "fastest_success_seconds": min(result["wall_seconds"] for result in solved) if solved else None, "total_search_wall_seconds": sum(result["wall_seconds"] for result in results)})
    write_json(ROOT / "search_results.json", {"cases": summaries, "runs": all_results})
    print(json.dumps(summaries, indent=2), flush=True)


def select_candidate(name):
    directory = ROOT / "cases" / name
    deployment = read_json(directory / "deployment.json")
    witness = read_json(directory / "privileged_witness.json")
    certificate = certify(deployment, witness["errors"])
    write_json(ROOT / "deployment.json", deployment)
    write_json(ROOT / "privileged_witness.json", witness)
    write_json(ROOT / "validation.json", certificate)
    write_json(ROOT / "candidate_construction.json", read_json(directory / "construction.json"))
    bundle = ROOT / "candidate_validation"
    shutil.copytree(ARCHIVE / "evaluator", bundle / "evaluator", dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "hidden"))
    write_json(bundle / "participant/input/deployment.json", deployment)
    manifest = {"deployment_sha256": hashlib.sha256((bundle / "participant/input/deployment.json").read_bytes()).hexdigest(), "bounds": {"max_errors": 24, "min_residual": 8, "min_corrected": 6, "min_initial_odd": 6}}
    write_json(bundle / "evaluator/hidden/manifest.json", manifest)
    write_json(ROOT / "manifest.json", manifest)
    command = [sys.executable, "-B", str(bundle / "evaluator/evaluate.py"), "--submission", str(ROOT / "privileged_witness.json"), "--report", str(ROOT / "independent_score.json")]
    completed = subprocess.run(command, capture_output=True, text=True)
    (ROOT / "independent_check.log").write_text(completed.stdout + completed.stderr)
    assert completed.returncode == 0
    score = read_json(ROOT / "independent_score.json")
    assert score["passed"] and score["core_score"] == score["worst_family_score"] == 1.0
    write_json(ROOT / "selection.json", {"case": name, "deployment_sha256": manifest["deployment_sha256"], "checker_command": command, "score": score})
    print(json.dumps({"selected": name, "passed": score["passed"], "core_score": score["core_score"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "sweep", "confirmation", "summary", "select"))
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--case", action="append", default=[])
    arguments = parser.parse_args()
    if arguments.action == "prepare":
        prepare()
    elif arguments.action == "summary":
        summarize()
    elif arguments.action == "select":
        assert len(arguments.case) == 1
        select_candidate(arguments.case[0])
    else:
        run_campaign(arguments.action, arguments.seconds, arguments.workers, arguments.case)
