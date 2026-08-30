from common import ROOT, checked_field, energy_gradient, read_case, write_json

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path

from evaluate import aggregate, invalid_case, score_field
from run_search import isolated_run


def load_proposal():
    manifest = read_case(ROOT / "proposal/manifest.json")
    target = read_case(ROOT / "proposal/target.json")
    for relative, expected in manifest["sha256"].items():
        if hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() != expected:
            raise ValueError("frozen proposal modified: " + relative)
    for reference in manifest["cases"]:
        case = read_case(ROOT / reference["case_path"])
        for kind in ("baseline", "witness"):
            field = checked_field(ROOT / reference[kind + "_path"], case)
            energy, unused, rms = energy_gradient(case, field)
            if abs(energy - reference[kind + "_energy"]) > 1e-9 or rms > 0.002:
                raise ValueError("reference validation failed")
    return manifest, target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    manifest, target = load_proposal()
    directory = ROOT / "runs" / args.label
    directory.mkdir(exist_ok=True)
    def run(reference):
        case = read_case(ROOT / reference["case_path"])
        raw = isolated_run(ROOT / reference["case_path"], args.submission.resolve(), directory, args.label)
        if not raw["valid"]:
            return invalid_case(reference, raw["reason"], raw.get("wall_seconds", 0))
        field = checked_field(directory / reference["case_id"] / "field.npz", case)
        return score_field(reference, case, field, raw["wall_seconds"], target)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        records = list(executor.map(run, manifest["cases"]))
    report = aggregate(records, target)
    report["submission"] = str(args.submission.resolve())
    report["timing_kind"] = "same trusted Sandbox, 60 seconds per case, one core, 2GiB; six independent processes"
    report["source_sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in args.submission.resolve().glob("*.py")}
    write_json(directory / "score.json", report)
    print({key: value for key, value in report.items() if key != "cases"})


if __name__ == "__main__":
    main()
