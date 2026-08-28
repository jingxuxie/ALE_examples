import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"

PRIVATE = Path(__file__).resolve().parent
PILOT = PRIVATE.parent
sys.path.insert(0, str(PILOT.parent.parent / "authoring"))

from isolated_eval import run_solver
from scoring import score_answer


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def read_frozen(relative, digest):
    path = PILOT / relative
    contents = path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != digest:
        raise RuntimeError("frozen file hash mismatch: " + relative)
    return json.loads(contents)


def summarize(cases):
    family_scores = {}
    for family in sorted({case["family"] for case in cases}):
        family_scores[family] = sum(case["score"] for case in cases if case["family"] == family) / sum(case["family"] == family for case in cases)
    count = len(cases)
    mean = sum(case["score"] for case in cases) / count
    component_scores = {name: sum(case[name] for case in cases) / count
                        for name in ("algebra", "sector_f1", "transfer_f1")}
    component_scores.update({name: sum(case[name]["score"] for case in cases) / count for name in ("analog", "digital")})
    return {"mean_core": mean, "worst_family": min(family_scores.values()),
            "family_scores": family_scores, "component_scores": component_scores, "cases": cases,
            "score": mean}


def evaluate(submission, split, timeout=60, participant=None):
    manifest = json.loads((PRIVATE / "manifest.json").read_text())
    results = []
    for entry in manifest["splits"][split]:
        case = read_frozen(entry["case_path"], entry["case_file_sha256"])
        truth = read_frozen(entry["reference_path"], entry["reference_file_sha256"])
        execution = run_solver(Path(submission).resolve(), Path(participant).resolve() if participant else PILOT / "participant", case,
                               timeout=timeout, memory_gib=6, startup_grace=30)
        answer = execution.get("result") if execution.get("ok") else {}
        try:
            encoded = canonical(answer)
            if len(encoded.encode()) > 32 * 1024 * 1024:
                raise ValueError("response exceeds 32 MiB")
        except (ValueError, TypeError, OverflowError) as error:
            answer = {}
            execution["error"] = str(error)
        report = score_answer(case, truth["answer"]["certificate"], answer, entry["anchors"])
        report.update({"id": case["id"], "family": case["family"], "length": case["length"],
                       "seconds": execution.get("seconds"), "max_rss_kib": execution.get("max_rss_kib"),
                       "runner_ok": bool(execution.get("ok")), "runner_error": execution.get("error")})
        results.append(report)
    report = summarize(results)
    report.update({"split": split, "case_count": len(results), "manifest_version": manifest["version"]})
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--split", choices=("screening", "challenge", "confirmation"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--participant", type=Path)
    parser.add_argument("--timeout", type=float, default=60)
    arguments = parser.parse_args()
    if not 0 < arguments.timeout <= 60:
        parser.error("timeout must be in (0,60]")
    report = evaluate(arguments.submission, arguments.split, arguments.timeout, arguments.participant)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, sort_keys=True))


if __name__ == "__main__":
    main()
