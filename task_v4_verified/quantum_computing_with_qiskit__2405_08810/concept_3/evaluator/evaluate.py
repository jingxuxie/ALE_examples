import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "participant" / "input"))
from model import CONFIG
from runtime import aggregate, run_episode


class SubmissionError(ValueError):
    pass


class InfrastructureError(RuntimeError):
    pass


def failure_report(error, infrastructure=False):
    score = None if infrastructure else 30.0
    return {"valid": False, "passed": False, "core_score": score, "mean_nrmse": score,
            "worst_family_score": score, "resource_score": 0.0, "reason": str(error),
            "infrastructure_error": infrastructure}


def load_sandbox():
    helper_path = ROOT.parent / "authoring" / "sandbox.py"
    specification = importlib.util.spec_from_file_location("trusted_common_sandbox", helper_path)
    if specification is None or specification.loader is None:
        raise InfrastructureError("common sandbox helper unavailable; no unsafe fallback")
    helper = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(helper)
    return helper.sandbox_command


def evaluate(submission_path, command_factory=None, episode_limit=None, startup_handshake=None):
    try:
        submission = Path(submission_path).resolve(strict=True)
    except (OSError, RuntimeError) as error:
        raise SubmissionError("submission unavailable: " + str(error)) from error
    if submission.is_file():
        if submission.name != "solution.py":
            raise SubmissionError("entrypoint must be solution.py")
        submission = submission.parent
    if not (submission / "solution.py").is_file():
        raise SubmissionError("submission must contain solution.py")
    hidden = ROOT / "evaluator" / "hidden"
    for protected in (ROOT / "evaluator", ROOT / "adversary"):
        if submission == protected or submission in protected.parents or protected in submission.parents:
            raise SubmissionError("submission cannot contain or reside in a private evaluator directory")
    try:
        encoded = (hidden / "episodes.json").read_bytes()
        manifest = json.loads((hidden / "manifest.json").read_text())
    except (OSError, ValueError) as error:
        raise InfrastructureError("frozen suite unavailable: " + str(error)) from error
    commitment_path = ROOT / "adversary" / "target_commitment.json"
    if commitment_path.exists():
        commitment = json.loads(commitment_path.read_text())
        current_config_hash = hashlib.sha256((ROOT / "participant" / "input" / "config.json").read_bytes()).hexdigest()
        if commitment["config_sha256"] != current_config_hash or commitment["suite_sha256"] != manifest["episodes_sha256"]:
            raise InfrastructureError("frozen target or suite commitment mismatch")
    if hashlib.sha256(encoded).hexdigest() != manifest["episodes_sha256"]:
        raise InfrastructureError("frozen suite checksum mismatch")
    suite = json.loads(encoded)["episodes"]
    if len(suite) != 32 or any(sum(episode["family"] == family for episode in suite) != 8 for family in CONFIG["suite"]["families"]):
        raise InfrastructureError("invalid frozen family balance")
    factory = command_factory or load_sandbox()
    handshake = command_factory is None if startup_handshake is None else startup_handshake
    command_options = {"entrypoint": "solution.py", "args": ()}
    if handshake:
        command_options["ready_marker"] = True
    command = factory(ROOT / "participant", submission, **command_options)
    results = []
    selected = suite if episode_limit is None else suite[:episode_limit]
    for episode_index, episode in enumerate(selected):
        result = run_episode(command, episode["parameters"], episode["measurement_seed"], startup_handshake=handshake)
        result["family"] = episode["family"]
        results.append(result)
        if result.get("infrastructure_error"):
            return {**failure_report(result["reason"], infrastructure=True), "episodes": results}
        print(json.dumps({"episode": episode_index, "family": result["family"], "nrmse": result["nrmse"],
                          "valid": result["valid"], "wall_seconds": result["wall_seconds"],
                          "startup_wall_seconds": result["startup_wall_seconds"], "reason": result["reason"]}), file=sys.stderr, flush=True)
    report = {**aggregate(results), "episodes": results, "suite_sha256": manifest["episodes_sha256"],
              "sandbox": "common bwrap helper" if command_factory is None else "trusted injected command factory",
              "full_suite": len(results) == 32}
    if not report["full_suite"]:
        report["passed"] = False
        report["reason"] = "smoke run only; full frozen suite required"
    return report


def main():
    parser = argparse.ArgumentParser(description="Hidden active-design evaluation; never imports submission code")
    parser.add_argument("submission", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--smoke", type=int, choices=range(1, 33))
    arguments = parser.parse_args()
    try:
        report = evaluate(arguments.submission, episode_limit=arguments.smoke)
    except SubmissionError as error:
        report = failure_report(error)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as error:
        report = failure_report(error, infrastructure=True)
    encoded = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if arguments.output:
        arguments.output.write_text(encoded)
    print(encoded)
    return 0 if report.get("valid") else 1


if __name__ == "__main__":
    sys.exit(main())
