import json
from pathlib import Path
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))
from sandbox_runner import run_submission
from trusted_contractor import load_mps, measure


def main():
    canary = ROOT / "evaluator" / "hidden" / "isolation_canary.txt"
    canary.write_text("Generation-only sentinel, not a solver input.\n")
    request = {"version": 1, "case_id": "runner-probe", "seed": 123,
               "n_sites": 8, "local_dim": 6, "bond_cap": 6, "sector": "any",
               "omega": [1.0] * 8, "mass2": [0.5] * 8, "lambda4": [2.0] * 8,
               "field": [0.0] * 8, "coupling": [1.0] * 7,
               "budget_seconds": 6.0, "wall_seconds": 30.0,
               "private_canary": str(canary)}
    reports = []
    for scenario in ("isolation", "process", "network", "symlink", "malformed", "spin"):
        current = dict(request, probe_scenario=scenario)
        if scenario == "spin":
            current.update(budget_seconds=1.0, wall_seconds=10.0)
        result = run_submission(ROOT / "adversary" / "runner_fixture", ROOT / "participant",
                                ROOT / "adversary" / "runner_checks" / scenario, current)
        if scenario in ("isolation", "process", "network"):
            assert result["process_valid"], (scenario, result)
            measure(load_mps(result["state_path"], current), current)
        elif scenario in ("symlink", "spin"):
            assert not result["process_valid"], (scenario, result)
            if scenario == "spin":
                assert result["cpu_accounted"] and result["cpu_seconds"] >= 1.0 and not result["timed_out"], result
        else:
            assert result["process_valid"], (scenario, result)
            try:
                load_mps(result["state_path"], current)
            except (ValueError, OSError, zipfile.BadZipFile):
                pass
            else:
                raise AssertionError("malformed NPZ accepted")
        reports.append(dict(result, scenario=scenario))
    summary = {"passed": 6, "failed": 0, "checks": reports}
    (ROOT / "adversary" / "runner_validation.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"passed": 6, "failed": 0}))


if __name__ == "__main__":
    main()
