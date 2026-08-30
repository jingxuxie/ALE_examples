import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import sys
import time
from subprocess import PIPE

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator" / "hidden"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "authoring"))

import numpy as np

import forward_model as model
from resources import CpuTreeMonitor, ResourceError, ResourceSandbox, REVISION, SAMPLE_INTERVAL

TARGET = json.loads((ROOT / "evaluator" / "hidden" / "target.json").read_text())
MAX_LINE = 65536
MAX_STDERR = 65536


class ProtocolError(Exception):
    pass


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("nonfinite JSON value")

    try:
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError, RecursionError) as error:
        raise ProtocolError("invalid JSON") from error
    if not isinstance(result, dict):
        raise ProtocolError("message must be an object")
    return result


class Channel:
    def __init__(self, process, deadline, resources=None):
        self.process = process
        self.deadline = deadline
        self.resources = resources
        self.selector = selectors.DefaultSelector()
        self.selector.register(process.stdout, selectors.EVENT_READ, "stdout")
        self.selector.register(process.stderr, selectors.EVENT_READ, "stderr")
        self.buffer = b""
        self.stderr = b""
        self.stdout_open = True
        os.set_blocking(process.stdin.fileno(), False)

    def pump(self):
        if self.resources is not None:
            self.resources.check()
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ProtocolError("wall time limit")
        for key, _ in self.selector.select(min(remaining, SAMPLE_INTERVAL)):
            chunk = os.read(key.fileobj.fileno(), 4096)
            if not chunk:
                self.selector.unregister(key.fileobj)
                if key.data == "stdout":
                    self.stdout_open = False
            elif key.data == "stdout":
                self.buffer += chunk
                first_line = self.buffer.split(b"\n", 1)[0]
                if len(first_line) > MAX_LINE or len(self.buffer) > 2 * MAX_LINE:
                    raise ProtocolError("stdout limit")
            else:
                self.stderr += chunk
                if len(self.stderr) > MAX_STDERR:
                    raise ProtocolError("stderr limit")

    def read(self):
        if self.resources is not None:
            self.resources.check()
        while b"\n" not in self.buffer:
            if not self.stdout_open:
                raise ProtocolError("EOF before complete final")
            self.pump()
        line, self.buffer = self.buffer.split(b"\n", 1)
        if len(line) > MAX_LINE:
            raise ProtocolError("stdout line limit")
        try:
            return strict_json(line.decode("utf-8"))
        except UnicodeDecodeError as error:
            raise ProtocolError("invalid UTF-8") from error

    def send(self, message):
        payload = (json.dumps(message, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            while payload:
                if self.resources is not None:
                    self.resources.check()
                if time.monotonic() >= self.deadline:
                    raise ProtocolError("wall time limit sending observation")
                try:
                    written = os.write(self.process.stdin.fileno(), payload)
                    payload = payload[written:]
                except BlockingIOError:
                    self.pump()
        except (BrokenPipeError, OSError) as error:
            raise ProtocolError("closed input pipe") from error

    def finish(self):
        self.process.stdin.close()
        self.deadline = min(self.deadline, time.monotonic() + 3.0)
        while self.selector.get_map() or self.process.poll() is None:
            if self.buffer:
                raise ProtocolError("output after final")
            self.pump()
        if self.buffer:
            raise ProtocolError("output after final")
        if self.process.returncode != 0:
            raise ProtocolError("nonzero process exit")
        if self.resources is not None:
            self.resources.check(force=True)

    def close(self):
        self.selector.close()


def score_scene(truth, estimate):
    truth = model.validate_scene(truth)
    estimate = model.validate_scene(estimate)
    true_sites = {item["site"] for item in truth["impurities"]}
    predicted_sites = {item["site"] for item in estimate["impurities"]}
    support_f1 = 2.0 * len(true_sites & predicted_sites) / (len(true_sites) + len(predicted_sites))
    true_potential = model.potential_of(truth)
    strength_error = float(np.linalg.norm(model.potential_of(estimate) - true_potential) / np.linalg.norm(true_potential))
    vortex_exact = int(truth["vortices"] == estimate["vortices"])
    success = (support_f1 >= TARGET["episode"]["support_f1_min"]
               and strength_error <= TARGET["episode"]["relative_strength_error_max"] and bool(vortex_exact))
    return {"support_f1": support_f1, "relative_strength_error": strength_error,
            "vortex_exact": vortex_exact, "vortex_count_exact": int(len(truth["vortices"]) == len(estimate["vortices"])),
            "joint_success": int(success),
            "quality": 0.45 * support_f1 + 0.25 * max(0.0, 1.0 - strength_error) + 0.30 * vortex_exact}


def failed_metrics():
    return {"support_f1": 0.0, "relative_strength_error": 2.0, "vortex_exact": 0,
            "vortex_count_exact": 0, "joint_success": 0, "quality": 0.0}


def metadata():
    return {"type": "metadata", "protocol": "ldos-jsonl-v1", "model": model.SPEC, "target": TARGET}


def run_episode(case, participant, submission, entry, wall_seconds=None, cpu_seconds=None):
    truth = model.validate_scene(case["scene"])
    table = model.ldos_table(truth)
    result = {"case_id": case["id"], "family": case["family"], "protocol_valid": False,
              "queries": 0, "metrics": failed_metrics(), "transcript": []}
    start = time.monotonic()
    duration = model.SPEC["wall_seconds"] if wall_seconds is None else wall_seconds
    cpu_limit = model.SPEC["cpu_seconds"] if cpu_seconds is None else cpu_seconds
    with ResourceSandbox(participant, submission, seconds=cpu_limit, memory_gib=2) as sandbox:
        process = sandbox.start(["/usr/bin/python3", "/submission/" + entry], stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True)
        monitor = CpuTreeMonitor(process, cpu_limit)
        channel = Channel(process, start + duration, monitor)
        try:
            channel.send(metadata())
            while True:
                message = channel.read()
                if message.get("type") == "final":
                    if set(message) != {"type", "estimate"}:
                        raise ProtocolError("invalid final keys")
                    estimate = model.validate_scene(message["estimate"])
                    channel.finish()
                    result["estimate"] = estimate
                    result["metrics"] = score_scene(truth, estimate)
                    result["protocol_valid"] = True
                    break
                site, energy_index = model.validate_action(message)
                if result["queries"] >= model.SPEC["query_budget"]:
                    raise ProtocolError("query budget exceeded")
                result["queries"] += 1
                observation = {"type": "observation", "query_index": result["queries"],
                               "site": site, "energy_index": energy_index,
                               "value": round(float(table[site, energy_index]), 12),
                               "remaining": model.SPEC["query_budget"] - result["queries"]}
                result["transcript"].append({"action": message, "observation": observation})
                channel.send(observation)
        except (ProtocolError, ResourceError, ValueError, TypeError, OverflowError, OSError) as error:
            result["error"] = str(error)
        finally:
            sandbox.stop()
            result["resource_accounting"] = monitor.report(result["protocol_valid"])
            channel.close()
            result["stderr"] = channel.stderr.decode("utf-8", errors="replace")
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
    result["cpu_seconds"] = result["resource_accounting"]["cpu_seconds"]
    result["wall_seconds"] = time.monotonic() - start
    if result["cpu_seconds"] > cpu_limit:
        result["protocol_valid"] = False
        result["error"] = "CPU time limit"
    if result["wall_seconds"] > duration:
        result["protocol_valid"] = False
        result.setdefault("error", "wall time limit")
    if not result["protocol_valid"]:
        result["metrics"] = failed_metrics()
    return result


def aggregate(results, official=False):
    if not results:
        raise ValueError("empty evaluation")
    mean = lambda name: float(np.mean([result["metrics"][name] for result in results]))
    families = {family: [result for result in results if result["family"] == family] for family in model.SPEC["families"]}
    family_success = {family: float(np.mean([result["metrics"]["joint_success"] for result in group])) if group else 0.0
                      for family, group in families.items()}
    values = {"core_joint_success": mean("joint_success"), "worst_family_joint_success": min(family_success.values()),
              "mean_support_f1": mean("support_f1"), "mean_relative_strength_error": mean("relative_strength_error"),
              "vortex_configuration_accuracy": mean("vortex_exact"), "vortex_count_accuracy": mean("vortex_count_exact"),
              "mean_quality": mean("quality"), "family_joint_success": family_success,
              "protocol_failures": sum(not result["protocol_valid"] for result in results),
              "mean_cpu_seconds": float(np.mean([result["cpu_seconds"] for result in results])),
              "max_cpu_seconds": max(result["cpu_seconds"] for result in results),
              "mean_wall_seconds": float(np.mean([result["wall_seconds"] for result in results])),
              "max_wall_seconds": max(result["wall_seconds"] for result in results)}
    required = TARGET["suite"]
    checks = {
        "core": values["core_joint_success"] >= required["core_joint_success_min"],
        "worst_family": values["worst_family_joint_success"] >= required["worst_family_joint_success_min"],
        "support": values["mean_support_f1"] >= required["mean_support_f1_min"],
        "strength": values["mean_relative_strength_error"] <= required["mean_relative_strength_error_max"],
        "vortices": values["vortex_configuration_accuracy"] >= required["vortex_configuration_accuracy_min"],
        "protocol": values["protocol_failures"] == 0,
    }
    full = all(len(group) == TARGET["evaluation_episodes_per_family"] for group in families.values())
    values.update({"checks": checks, "target_met_on_this_sample": all(checks.values()),
                   "official_suite": bool(official and full), "passed": bool(official and full and all(checks.values()))})
    unmet = [name for name, satisfied in checks.items() if not satisfied]
    reason = "target_met" if not unmet else "target_not_met:" + ",".join(unmet)
    if not (official and full):
        reason = "nonofficial_sample;" + reason
    values.update({"core_score": values["core_joint_success"],
                   "worst_family_score": values["worst_family_joint_success"],
                   "runtime_score": max(0.0, 1.0 - values["mean_wall_seconds"] / model.SPEC["wall_seconds"]),
                   "valid": values["protocol_failures"] == 0,
                   "protocol": "valid" if values["protocol_failures"] == 0 else "invalid",
                   "reason": reason})
    return values


def load_cases(split):
    if split == "evaluation":
        draws = json.loads((ROOT / "evaluator" / "hidden" / "seeds.json").read_text())["draws"]
        return [{"id": item["id"], "family": item["family"], "scene": model.draw_scene(item["seed"], item["family"])}
                for item in draws]
    return json.loads((ROOT / "participant" / "input" / (split + ".json")).read_text())["episodes"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, default=ROOT / "participant" / "baseline")
    parser.add_argument("--entry", default="solve.py")
    parser.add_argument("--split", choices=("train", "calibration", "evaluation"), default="evaluation")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output", type=Path, default=ROOT / "attempts" / "evaluation.json")
    arguments = parser.parse_args()
    participant = ROOT / "participant"
    submission = arguments.submission.resolve()
    private = (ROOT / "evaluator").resolve()
    if private == submission or submission in private.parents or private in submission.parents:
        parser.error("submission must not contain private evaluator files")
    if Path(arguments.entry).name != arguments.entry or not (submission / arguments.entry).is_file():
        parser.error("entry must be a filename inside the submission directory")
    output = arguments.output.resolve()
    if ROOT not in output.parents or participant in output.parents:
        parser.error("report must stay in concept_3 outside participant")
    cases = load_cases(arguments.split)
    if arguments.limit is not None:
        if arguments.limit <= 0:
            parser.error("limit must be positive")
        cases = cases[:arguments.limit]
    results = []
    for case in cases:
        result = run_episode(case, participant, submission, arguments.entry)
        results.append(result)
        print(json.dumps({"case": case["id"], "valid": result["protocol_valid"], "metrics": result["metrics"],
                          "seconds": round(result["wall_seconds"], 3)}, allow_nan=False), file=sys.stderr, flush=True)
    report = {"schema": "ldos-evaluation-v1", "split": arguments.split,
              "isolation": "resources.ResourceSandbox(authoring.sandbox.Sandbox)",
              "checker_revision": REVISION,
              "checker_sha256": {name: hashlib.sha256((ROOT / "evaluator" / name).read_bytes()).hexdigest()
                                 for name in ("evaluate.py", "resources.py", "resource_guard.py")},
              "target_sha256": hashlib.sha256((ROOT / "evaluator" / "hidden" / "target.json").read_bytes()).hexdigest(),
              "summary": aggregate(results, official=arguments.split == "evaluation"), "episodes": results}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report["summary"], indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
