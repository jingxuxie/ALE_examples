import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from cases import cases
from run import check_frozen, run_case


ROOT = Path(__file__).resolve().parent


def hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob("*") if path.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", choices=("ladder", "patch", "triangular"), required=True)
    parser.add_argument("--selected-v1", action="store_true")
    arguments = parser.parse_args()
    check_frozen()
    label = "selected_v1" if arguments.selected_v1 else "actual_champion"
    source = ROOT / (label + "_snapshot")
    expected = json.loads((ROOT / (label + "_manifest.json")).read_text())["files"]
    assert hashes(source) == expected
    results = []
    for case in cases(seed=49371023, sizes=(24, 28, 44, 36), topologies=(arguments.topology,)):
        case["spec"]["protocol"] = "efficient-detector-calibration-v2"
        leaf = ROOT / "candidates" / label / case["id"] / "submission"
        shutil.copytree(source, leaf)
        logs = ROOT / "runs" / (label + "_logs")
        logs.mkdir(parents=True, exist_ok=True)
        result = run_case(case, leaf, ["/usr/bin/python3", "/submission/solution.py"], logs)
        actual = hashes(leaf)
        result["complete_source_files_unchanged"] = all(actual[name] == value for name, value in expected.items())
        result["source_sha256"] = expected["solution.py"]
        result["original_source_file_count"] = len(expected)
        assert result["complete_source_files_unchanged"]
        results.append(result)
        (ROOT / "runs" / (label + "_" + arguments.topology + ".json")).write_text(json.dumps({
            "status": "authorized_actual_champion_stress_only", "new_generation": False, "targets": None,
            "selection_provisional_until_main_confirms": not arguments.selected_v1, "cases": results}, indent=2) + "\n")
        print(json.dumps(result), flush=True)
    check_frozen()


if __name__ == "__main__":
    main()
