"""Bounded privileged sweeps; never launches agents or a broad optimization job."""

import os

for thread_variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[thread_variable] = "1"

import argparse
import json
import time
from pathlib import Path

import numpy as np

import cases


def run():
    start = time.process_time()
    entries = []
    controls = [("rank_deficient_psd", cases.rank_deficient_psd(), True)]
    constant = np.zeros((3, 4, 4))
    constant[0] = np.eye(4) / 4.0
    controls.append(("constant_psd", constant, True))
    for order in (2, 4, 7, 11):
        document, checked = cases.eligible_candidate(seed=8100 + order, order=order, depth=-3e-4, gap=3e-4)
        controls.append(("coupled_strict_psd_degree_" + str(checked["degree"]), cases.floating(document), True))
    quadratic, center = cases.narrow_quadratic()
    uniform_floor = float(np.linalg.eigvalsh(cases.guard.evaluate_matrices(quadratic, np.linspace(0, 1, 257)))[:, 0].min())
    controls.append(("narrow_rotated_quadratic", quadratic, False))
    for label, coefficients, expected in controls:
        started = time.process_time()
        reports = cases.guard.screen_all(coefficients)
        observed = [report["accepted"] for report in reports]
        entries.append({"label": label, "expected_acceptance": expected, "acceptances": observed, "ok": all(accepted == expected for accepted in observed), "cpu_seconds": time.process_time() - started, "profiles": reports})
    sweep = []
    for order in (2, 4, 7, 11):
        for gap in (1e-8, 2e-6, 3e-4):
            for seed in (2901, 7719):
                document, checked = cases.eligible_candidate(seed=seed, order=order, depth=3e-7, gap=gap)
                started = time.process_time()
                reports = cases.guard.screen_all(cases.floating(document))
                accepted = sum(report["accepted"] for report in reports)
                sweep.append({"seed": seed, "order": order, "gap": gap, "degree": checked["degree"], "valid": True, "evidence_valid": checked["evidence_valid"], "rayleigh_float": float(checked["rayleigh"]), "profiles_accepted": accepted, "passed": bool(checked["evidence_valid"] and accepted == 3), "cpu_seconds": time.process_time() - started, "stages": [report.get("last_stage", report.get("failure")) for report in reports]})
    return {"kind": "privileged_generation_controls_not_fresh_attempt", "date": "2026-08-28", "guard_version": cases.guard.VERSION, "psd_and_negative_controls": entries, "controls_passed": all(entry["ok"] for entry in entries), "single_uniform_mesh_quadratic_minimum": uniform_floor, "narrow_quadratic_center": str(center), "bounded_sweeps": sweep, "sweep_count": len(sweep), "witnesses_found": sum(entry["passed"] for entry in sweep), "cpu_seconds": time.process_time() - start, "caveat": "Finite pilot only; neither existence nor hardness is proved. No fresh agent tested here."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(Path(__file__).with_name("control_report.json")))
    arguments = parser.parse_args()
    report = run()
    Path(arguments.output).write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("controls_passed", "sweep_count", "witnesses_found", "cpu_seconds")}, allow_nan=False))
    if not report["controls_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
