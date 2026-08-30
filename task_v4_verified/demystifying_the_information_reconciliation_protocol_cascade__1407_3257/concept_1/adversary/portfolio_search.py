import copy
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "adversary/portfolio"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "participant"))
from baseline import baseline_policy
from cascade_sim import run_frame, validate_policy
from scoring import TARGET, evaluate_suite


def save(relative, value):
    text = json.dumps(value, indent=2, allow_nan=False) + "\n"
    destination = OUTPUT / relative
    patch = f"*** Begin Patch\n*** Add File: {destination}\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch"], input=patch, text=True, check=True, capture_output=True)


def rule(conditions, **action):
    return {"when": conditions, "action": action}


def size(basis, scale):
    return {"basis": basis, "scale": scale, "round": "nearest"}


def portfolio():
    variants = []
    seen = set()

    def add(name, policy, hypothesis):
        validate_policy(policy)
        digest = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
        if digest not in seen:
            variants.append((name, copy.deepcopy(policy), hypothesis))
            seen.add(digest)

    for passes in [10, 11, 9, 12]:
        for scale in [4, 2, 6, 8]:
            policy = baseline_policy()
            policy["max_passes"] = passes
            policy["schedule"][1]["size"] = size("parity", scale)
            add(f"parity_{scale}_passes_{passes}", policy,
                "Combine measured parity-inversion benefit with a shorter fixed verification tail.")
    for passes in [10, 11]:
        for scale in [2, 4, 6]:
            for batch in ["pass", "smallest"]:
                policy = baseline_policy()
                policy["max_passes"] = passes
                policy["schedule"][1]["size"] = size("parity", scale)
                for action in policy["schedule"]:
                    action["batch"] = batch
                policy["rules"] = [rule([["pass_index", "lt", 1], ["latency", "ge", 0.004]],
                                        size=size("paper_first", 0.5))]
                add(f"latency_first_parity_{scale}_{passes}_{batch}", policy,
                    "Spend more first-pass parity bits only when latency is costly, then adapt using the parity estimate.")
    for quiet in [4, 5, 6]:
        for scale in [2, 4, 6]:
            policy = baseline_policy()
            policy["schedule"][1]["size"] = size("parity", scale)
            policy["schedule"][3]["size"] = size("frame", 0.25)
            policy["rules"] = [rule([["pass_index", "ge", 5], ["quiet_passes", "ge", quiet]], stop=True),
                               rule([["pass_index", "lt", 1], ["latency", "ge", 0.006]], size=size("paper_first", 0.5))]
            add(f"quarter_quiet_{quiet}_parity_{scale}", policy,
                "Quarter-frame tail partitions buy stronger collision detection per round; stop only after a quiet streak.")
    for minimum in [8, 9, 10]:
        for quiet in [5, 6, 7]:
            policy = baseline_policy()
            policy["schedule"][1]["size"] = size("parity", 4)
            policy["rules"] = [rule([["pass_index", "ge", minimum], ["quiet_passes", "ge", quiet]], stop=True),
                               rule([["pass_index", "lt", 1], ["latency", "ge", 0.006]], size=size("paper_first", 0.5))]
            add(f"half_min_{minimum}_quiet_{quiet}", policy,
                "Retain cheap half-frame tail parities while spending extra passes on late public corrections.")
    for scale in [0.5, 1, 2]:
        policy = baseline_policy()
        policy["max_passes"] = 10
        policy["schedule"][1]["size"] = size("remaining", scale)
        add(f"remaining_{scale}_passes_10", policy,
            "Approximate residual QBER from parity-derived QBER minus observed corrections.")
    return variants


def summarize(name, report, seconds):
    return {"name": name, "split": report["split"], "core_score": report["core_score"],
            "worst_family_score": report["worst_family_score"],
            "family_improvements": {family: 1 - values["ratio"] for family, values in report["families"].items()},
            "normal_failures": report["candidate_total"]["failures"],
            "stress_failures": report["stress"]["failures"], "stress_fer": report["stress"]["fer"],
            "passed": report["passed"], "seconds": seconds}


def merit(summary):
    target_margin = min(summary["core_score"] - TARGET["overall_reduction"],
                        summary["worst_family_score"] - TARGET["family_reduction"])
    return (summary["passed"], summary["normal_failures"] == 0,
            summary["stress_fer"] <= TARGET["max_stress_fer"], target_margin,
            summary["core_score"])


def main():
    started = time.monotonic()
    deadline = started + 780
    timestamp = datetime.now(timezone.utc).isoformat()
    manifest_before = (ROOT / "evaluator/frozen.json").read_bytes()
    manifest = json.loads(manifest_before)
    for relative, expected in manifest["sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"frozen input changed: {relative}")
    train = json.loads((ROOT / "participant/input/train.json").read_text())
    dev = json.loads((ROOT / "participant/input/dev.json").read_text())
    screening = copy.deepcopy(train)
    screening["split"] = "train_screen"
    for case in screening["cases"]:
        case["frame_seeds"] = case["frame_seeds"][:4]
    variants = portfolio()
    save("plan.json", {"started_utc": timestamp, "wall_budget_seconds": 780,
                       "jobs": 2, "priority": "nice 10", "privileged": True,
                       "fresh_attempt": False, "target_changed": False,
                       "screening": "First four public training frames per case plus all public training stress frames",
                       "selection": "Lexicographic success, zero normal failures, stress gate, minimum improvement margin, overall improvement",
                       "hidden_limit": 2, "frozen_manifest_sha256": hashlib.sha256(manifest_before).hexdigest(),
                       "hypotheses": [{"name": name, "hypothesis": hypothesis} for name, policy, hypothesis in variants]})
    references = {str(seed): run_frame(case, seed, baseline_policy())
                  for case in screening["cases"] for seed in case["frame_seeds"]}
    training_results = []
    lookup = {}
    for name, policy, hypothesis in variants:
        if time.monotonic() > started + 330:
            break
        lookup[name] = policy
        save(f"policies/{name}.json", policy)
        candidate_started = time.monotonic()
        result = evaluate_suite(policy, screening, references, jobs=2)
        result.pop("case_results")
        save(f"train/{name}.json", result)
        summary = summarize(name, result, time.monotonic() - candidate_started)
        training_results.append(summary)
        print(json.dumps(summary), flush=True)
    ordered = sorted(training_results, key=merit, reverse=True)
    save("training_summary.json", ordered)
    selected = []
    categories = set()
    for summary in ordered:
        category = summary["name"].split("_")[0]
        if len(selected) < 2 or category not in categories:
            selected.append(summary["name"])
            categories.add(category)
        if len(selected) == 4:
            break
    dev_results = []
    for name in selected:
        if time.monotonic() > started + 500:
            break
        candidate_started = time.monotonic()
        report = evaluate_suite(lookup[name], dev, jobs=2)
        report.pop("case_results")
        save(f"dev/{name}.json", report)
        summary = summarize(name, report, time.monotonic() - candidate_started)
        dev_results.append(summary)
        print(json.dumps(summary), flush=True)
    save("development_summary.json", sorted(dev_results, key=merit, reverse=True))
    hidden_results = []
    for summary in sorted(dev_results, key=merit, reverse=True)[:2]:
        if time.monotonic() > deadline - 45:
            break
        name = summary["name"]
        destination = OUTPUT / f"hidden/{name}.json"
        save(f"hidden/{name}.json", {"status": "running"})
        command = [sys.executable, "-B", "-I", str(ROOT / "evaluator/evaluate.py"),
                   "--policy", str(OUTPUT / f"policies/{name}.json"), "--split", "hidden", "--jobs", "2", "--output", str(destination)]
        candidate_started = time.monotonic()
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
        try:
            stdout, stderr = process.communicate(timeout=max(1, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            stdout, stderr = process.communicate()
            save(f"hidden/{name}.json", {"status": "bounded_search_timeout", "seconds": time.monotonic() - candidate_started})
            break
        report = json.loads(destination.read_text())
        if not report.get("valid"):
            hidden_results.append({"name": name, "status": "invalid", "report": report, "stderr": stderr})
        else:
            summary = summarize(name, report, time.monotonic() - candidate_started)
            hidden_results.append(summary)
            print(json.dumps(summary), flush=True)
            if report["passed"]:
                break
    unchanged = manifest_before == (ROOT / "evaluator/frozen.json").read_bytes()
    unchanged = unchanged and all(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
                                  for relative, digest in manifest["sha256"].items())
    successful = [result for result in hidden_results if result.get("passed")]
    save("summary.json", {"started_utc": timestamp, "finished_utc": datetime.now(timezone.utc).isoformat(),
                          "elapsed_seconds": time.monotonic() - started, "screened_policies": len(training_results),
                          "development_evaluations": len(dev_results), "hidden_evaluations": hidden_results,
                          "achievability": "privileged_witness_found" if successful else "unknown",
                          "successful_policies": [result["name"] for result in successful],
                          "frozen_files_unchanged": unchanged, "target_changed": False,
                          "fresh_attempt": False, "generation_worker_agents_launched": 0,
                          "interpretation": "Privileged author portfolio evidence only; not an independent fresh solve. No participant exposure or promotion outside adversary."})
    print(json.dumps({"finished": True, "achievability": "privileged_witness_found" if successful else "unknown",
                      "frozen_files_unchanged": unchanged, "seconds": time.monotonic() - started}), flush=True)


if __name__ == "__main__":
    main()
