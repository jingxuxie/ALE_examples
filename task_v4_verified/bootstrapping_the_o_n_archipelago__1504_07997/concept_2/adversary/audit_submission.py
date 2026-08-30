import argparse
import importlib.util
import json
import math
from pathlib import Path

import mpmath as mp


ROOT = Path(__file__).resolve().parents[1]


def candidate_objects(value, depth=0):
    if depth > 64:
        return
    if isinstance(value, dict):
        if isinstance(value.get("id"), str) and "atoms" in value:
            yield value
        for child in value.values():
            yield from candidate_objects(child, depth+1)
    elif isinstance(value, list):
        for child in value:
            yield from candidate_objects(child, depth+1)


def precise_check(instance, certificate):
    with mp.workdps(70):
        prediction = [[mp.mpf(0)]*3 for row in instance["design"]]
        trace = mp.mpf(0)
        shared = None
        for atom in certificate["atoms"]:
            first, second = [mp.mpf(str(value)) for value in atom["ope"]]
            components = [first*first, first*second, second*second]
            trace += first*first+second*second
            if atom["index"] == 0:
                shared = first*first
            for row, values in enumerate(instance["design"]):
                kernel = mp.mpf(str(values[atom["index"]]))
                for component in range(3):
                    prediction[row][component] += kernel*components[component]
        residual = max(abs(prediction[row][component]-mp.mpf(str(target)))/
                       mp.mpf(str(instance["scales"][row][component]))
                       for row, values in enumerate(instance["target"])
                       for component, target in enumerate(values))
        return {"residual": mp.nstr(residual, 35), "trace": mp.nstr(trace, 35),
                "shared_error": None if shared is None else
                mp.nstr(abs(shared-mp.mpf(str(instance["shared_ope_squared"]))), 35)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    arguments = parser.parse_args()
    submission = arguments.submission.resolve()
    specification = importlib.util.spec_from_file_location("private_checker", ROOT/"evaluator/hidden/checker.py")
    checker = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(checker)
    instances = json.loads((ROOT/"evaluator/hidden/instances.json").read_text())["instances"]
    lookup = {instance["id"]: instance for instance in instances}
    best = {}
    best_rank = {}
    source_paths = {}
    candidate_count = 0
    scanned_bytes = 0
    skipped = []
    for path in sorted(submission.rglob("*.json")):
        if path.is_symlink() or not path.resolve().is_relative_to(submission):
            skipped.append(str(path.relative_to(submission)))
            continue
        size = path.stat().st_size
        if size > 4_000_000 or scanned_bytes+size > 64_000_000:
            skipped.append(str(path.relative_to(submission)))
            continue
        scanned_bytes += size
        try:
            data = json.loads(path.read_text())
            for candidate in candidate_objects(data):
                identifier = candidate["id"]
                if identifier not in lookup:
                    continue
                candidate_count += 1
                try:
                    valid, residual, reason = checker.check_case(lookup[identifier], candidate)
                except (ValueError, TypeError, KeyError, IndexError):
                    continue
                residual = residual if math.isfinite(residual) else math.inf
                rank = (not valid, residual)
                if identifier not in best_rank or rank < best_rank[identifier]:
                    best[identifier] = candidate
                    best_rank[identifier] = rank
                    source_paths[identifier] = str(path.relative_to(submission))
        except (ValueError, RecursionError, UnicodeError):
            skipped.append(str(path.relative_to(submission)))
    recovered = {"cases": list(best.values())}
    recovered_score = checker.score(instances, recovered)
    official = json.loads((submission/"answer.json").read_text())
    official_score = checker.score(instances, official)
    independent = {}
    for certificate in official["cases"]:
        try:
            independent[certificate["id"]] = precise_check(lookup[certificate["id"]], certificate)
        except (KeyError, TypeError, ValueError, IndexError):
            independent[certificate.get("id", "unknown")] = {"malformed": True}
    report = {"official": official_score, "recoverable_artifact_score": recovered_score,
              "best_candidate_paths": source_paths, "candidate_count": candidate_count,
              "scanned_bytes": scanned_bytes, "skipped_json_files": skipped,
              "complete_json_scan": not skipped, "independent_70_digit_checks": independent,
              "packaging_only_failure": not official_score["passed"] and recovered_score["passed"],
              "scope": "Static scan of saved JSON candidates; no entrant code executed and no solver feedback."}
    arguments.report.parent.mkdir(parents=True, exist_ok=True)
    arguments.report.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(json.dumps({key: report[key] for key in ("candidate_count", "complete_json_scan", "packaging_only_failure")}))
    print(json.dumps({"official_core": official_score["core_score"], "recoverable_core": recovered_score["core_score"]}))


if __name__ == "__main__":
    main()
