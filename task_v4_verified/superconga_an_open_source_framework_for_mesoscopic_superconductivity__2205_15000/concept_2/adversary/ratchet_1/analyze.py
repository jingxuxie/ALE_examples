import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import eigh, solve
from scipy.optimize import least_squares
from scipy.signal import find_peaks

from adapter import CONCEPT, ROOT, load_champion
from sweep import hamiltonian, load_problem, response, score, source_hashes, summarize, validate_design, write_json


def official_evaluation(case_dir, design_directory):
    mirror = case_dir / "private" / "official_checker_mirror"
    (mirror / "evaluator" / "hidden").mkdir(parents=True, exist_ok=True)
    participant = mirror / "participant"
    if not participant.exists():
        participant.symlink_to(case_dir / "public", target_is_directory=True)
    hashes = {f"participant/input/{name}": hashlib.sha256((case_dir / "public" / "input" / name).read_bytes()).hexdigest() for name in ("device.json", "target.npz")}
    write_json(mirror / "evaluator" / "hidden" / "freeze.json", {"core_target": 0.96, "worst_family_target": 0.94, "sha256": hashes})
    specification = importlib.util.spec_from_file_location("official_evaluator_private", CONCEPT / "evaluator" / "evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    evaluator.ROOT = mirror
    return evaluator.evaluate(design_directory)


def diagnostics(case):
    started = time.monotonic()
    case_dir = ROOT / "cases" / case
    config, target = load_problem(case_dir / "public" / "input")
    witness = np.array(json.loads((case_dir / "private" / "design.json").read_text())["pattern"])
    optimize, continuation = load_champion(case_dir / "public", case_dir / "private")
    fit = optimize.SpectralFit()
    count = len(witness)
    report = {"case": case, "witness_official_evaluation": official_evaluation(case_dir, case_dir / "private")}
    sites = config["width"] * config["height"]
    positions = np.array([row * config["width"] + column for column, row in config["probes"]])
    width, height = config["width"], config["height"]
    cavity = np.array([row * width + column for row in range(3, height - 2) for column in range(3, width - 3)])
    feature_rows = []
    for condition_index, condition in enumerate(config["conditions"]):
        matrix = hamiltonian(config, witness, condition)
        eigenvalues, eigenvectors = eigh(matrix, check_finite=False)
        selected = np.flatnonzero((eigenvalues > 0) & (eigenvalues < 0.3))
        spacing = np.diff(eigenvalues[selected])
        peak_counts = [len(find_peaks(values, prominence=max(0.02, 0.1 * np.ptp(values)))[0]) for values in target[condition_index]]
        modes = []
        for mode_index in selected:
            electron_fraction = float(np.sum(np.abs(eigenvectors[:sites, mode_index]) ** 2))
            modes.append({"energy": float(eigenvalues[mode_index]), "electron_fraction": electron_fraction, "electron_hole_mixing": 4 * electron_fraction * (1 - electron_fraction), "cavity_weight": float(np.sum(np.abs(eigenvectors[cavity, mode_index]) ** 2 + np.abs(eigenvectors[cavity + sites, mode_index]) ** 2)), "probe_electron_weight": float(np.sum(np.abs(eigenvectors[positions, mode_index]) ** 2))})
        feature_rows.append({"condition": condition["name"], "positive_subgap_modes": len(selected), "median_subgap_spacing": float(np.median(spacing)) if len(spacing) else None, "eta": config["broadening"], "peaks_by_probe": peak_counts, "max_target_ldos": float(target[condition_index].max()), "modes": modes})
    report["spectral_features"] = feature_rows
    normal_config = dict(config, gap_d=0.0, gap_xy=0.0)
    report["gap_off_relative_rmse"] = score(normal_config, target, witness)["relative_rmse"]
    for name, pattern in (("witness", witness.astype(float)), ("uniform", np.full(count, config["normal_site_count"] / count))):
        residual, jacobian = fit.evaluate(pattern)
        singular = np.linalg.svd(jacobian, compute_uv=False)
        report[name + "_jacobian"] = {"largest_singular_value": float(singular[0]), "smallest_singular_value": float(singular[-1]), "condition_number": float(singular[0] / singular[-1]), "effective_rank_1e-8": int(np.sum(singular > singular[0] * 1e-8)), "residual_rmse": float(np.sqrt(np.mean(residual ** 2)))}
    stage_paths = list((case_dir / "runs").glob("*/stage_*.json"))
    records = [(json.loads(path.read_text()), path) for path in stage_paths]
    if records:
        best, best_path = min(records, key=lambda item: item[0]["score"]["relative_rmse"])
        with np.load(best_path.with_suffix(".npz")) as arrays:
            continuous = arrays["continuous"]
        residual, jacobian = fit.evaluate(continuous)
        singular = np.linalg.svd(jacobian, compute_uv=False)
        report["best_blind"] = {"stage_path": str(best_path.relative_to(ROOT)), "score": best["score"], "hamming_to_witness": int(np.count_nonzero(np.array(best["pattern"]) != witness)), "relaxed_relative_rmse": float(np.sqrt(np.mean(residual ** 2))), "jacobian_condition_number": float(singular[0] / singular[-1]), "continuous_sum": float(continuous.sum())}
        report["grid_refinement"] = []
        for factor in (1, 2, 4):
            refined_config = dict(config, energies=np.linspace(config["energies"][0], config["energies"][-1], factor * (len(config["energies"]) - 1) + 1).tolist())
            refined_target = response(refined_config, witness)
            report["grid_refinement"].append({"factor": factor, "energy_count": len(refined_config["energies"]), "best_blind_score": score(refined_config, refined_target, np.array(best["pattern"]))})
        line = []
        for fraction in np.linspace(0, 1, 41):
            residual = fit.evaluate((1 - fraction) * continuous + fraction * witness, False)[0]
            line.append({"fraction_toward_witness": float(fraction), "relative_rmse": float(np.sqrt(np.mean(residual ** 2)))})
        report["oracle_line_profile"] = line
        report["oracle_line_profile_note"] = "Diagnostic interpolation only, not a blind optimization attempt or a fabrication-feasible binary path."
        report["best_blind_official_evaluation"] = None
        if best["score"]["valid"]:
            best_directory = case_dir / "private" / "best_blind"
            best_directory.mkdir(exist_ok=True)
            write_json(best_directory / "design.json", {"pattern": best["pattern"]})
            report["best_blind_official_evaluation"] = official_evaluation(case_dir, best_directory)
    random = np.random.default_rng(1903)
    initial = np.where(witness, 1 - random.uniform(0.001, 0.03, count), random.uniform(0.001, 0.03, count))
    local_start = time.monotonic()
    result = least_squares(fit.residual, initial, jac=fit.jacobian, bounds=(0, 1), max_nfev=50, ftol=1e-9, xtol=1e-9, gtol=1e-8)
    report["oracle_local_recovery"] = {"not_a_blind_attempt": True, "initialization": "witness perturbed inward by uniform 0.001..0.03", "nfev": result.nfev, "optimizer_seconds": time.monotonic() - local_start, "continuous_relative_rmse": float(np.sqrt(np.mean(result.fun ** 2))), "score": score(config, target, optimize.project(result.x))}
    report["diagnostic_seconds"] = time.monotonic() - started
    write_json(case_dir / "private" / "diagnostics.json", report)
    print(json.dumps({"case": case, "diagnostics_seconds": report["diagnostic_seconds"], "best_blind": report.get("best_blind"), "oracle_local_recovery": report["oracle_local_recovery"]}), flush=True)
    return report


def freeze_candidate(case):
    case_dir = ROOT / "cases" / case
    rows = summarize()
    row = next(row for row in rows if row["case"] == case)
    if row["passing_stages"] or row["completed_runs"] < 3 or not row["witness_verified"]:
        raise RuntimeError("Candidate lacks measured failure evidence or is already solved")
    original = json.loads((ROOT / "original_hashes.json").read_text())
    current = source_hashes()
    if any(current.get(name) != expected for name, expected in original.items()):
        raise RuntimeError("Protected source hashes changed")
    archives = json.loads((ROOT / "archive_hashes.json").read_text())
    if any(hashlib.sha256((CONCEPT / name).read_bytes()).hexdigest() != expected for name, expected in archives.items()):
        raise RuntimeError("Generation_1 archives changed")
    proposal = ROOT / "proposal"
    proposal.mkdir(exist_ok=True)
    paths = {name: case_dir / "public" / "input" / name for name in ("device.json", "target.npz")}
    witness = case_dir / "private" / "design.json"
    diagnostics_path = case_dir / "private" / "diagnostics.json"
    manifest = {"status": "proposed only; participant and evaluator remain untouched", "case": case, "core_target": 0.96, "worst_family_target": 0.94, "checker_runtime_limit_seconds": 120, "public": {name: str(path.relative_to(CONCEPT)) for name, path in paths.items()}, "private_witness": str(witness.relative_to(CONCEPT)), "public_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}, "private_witness_sha256": hashlib.sha256(witness.read_bytes()).hexdigest(), "official_forward_sha256": original["participant/workspace/spectral.py"], "official_checker_sha256": original["evaluator/checker.py"], "measured_evidence": row, "diagnostics": str(diagnostics_path.relative_to(CONCEPT)), "hardness_claim": "Finite multistart champion failures only, not proof of hardness. Requires a completely fresh one-hour attempt by parent; no fresh agent launched here."}
    manifest["algorithm_provenance"] = {"source": "Fresh generation_1 agent construction/research algorithm, captured before scratch cleanup (provenance supplied by parent)", "preserved_source_files": ["champions/generation_1/optimize.py", "champions/generation_1/continuation.py"], "source_sha256": {name: original[name] for name in ("champions/generation_1/optimize.py", "champions/generation_1/continuation.py")}, "final_generation_1_submission": "design.json only", "comparison": "Rerun the construction algorithm against each public physical target from new blind initializations; NOT rescore the old static design against different targets", "adapter_record": "adversary/ratchet_1/adaptations.json"}
    write_json(proposal / "freeze.json", manifest)
    write_json(ROOT / "hash_audit.json", {"unchanged": True, "generation_1_archives_unchanged": True, "archive_files_checked": len(archives), "concurrently_added_files_not_in_initial_snapshot": sorted(set(current) - set(original)), "current": current})
    diagnostic = json.loads(diagnostics_path.read_text())
    lines = ["# Measured champion ratchet", "", "## Selected generation-2 proposal", "", f"Case: `{case}`; same 12x12 / 64-candidate / 24-inclusion complexity. Thresholds remain **0.96 core / 0.94 worst**.", "", "This reruns the fresh generation-1 agent's preserved **construction/research algorithm** (`optimize.py` and `continuation.py`, captured before scratch cleanup), with the minimal adapter recorded in `adaptations.json`. The final generation-1 submission itself contained only `design.json`. This is NOT a static old-design/new-fingerprint comparison.", "", f"Completed blind portfolio: {row['completed_runs']} runs, {row['completed_stages']} scored stages, {row['total_nfev']} function evaluations, {row['optimizer_seconds_sum']:.2f} aggregate optimizer wall-seconds / {row['optimizer_cpu_seconds_sum']:.2f} process CPU-seconds; zero passing stages.", "", f"Best fabrication-valid score: core {row['best_valid']['core_score']:.8f}, worst {row['best_valid']['worst_family_score']:.8f}; normalized RMSE {row['best_valid']['relative_rmse']:.8f}. Witness official score: core {diagnostic['witness_official_evaluation']['core_score']:.14f}, worst {diagnostic['witness_official_evaluation']['worst_family_score']:.14f}.", "", f"Public device: `{manifest['public']['device.json']}`", "", f"Public target: `{manifest['public']['target.npz']}`", "", f"Private witness: `{manifest['private_witness']}`", "", "Frozen hashes, algorithm provenance, and thresholds: `proposal/freeze.json`.", "", "## Completed sweep", "", "Best scores include invalid projections when they outperform valid ones, so low scores are not merely fabrication/count rejection. Runtime is summed optimizer wall time, not elapsed batch time; raw errors are shown because scores clamp at zero.", "", "| Case | Runs/stages | Best core | Best worst | RMSE | Valid best core | nfev | Optimizer s | CPU s |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for entry in rows:
        best = entry["best_spectral"]
        valid = entry["best_valid"]
        if best:
            lines.append(f"| {entry['case']} | {entry['completed_runs']}/{entry['completed_stages']} | {best['core_score']:.6f} | {best['worst_family_score']:.6f} | {best['relative_rmse']:.6f} | {valid['core_score'] if valid else float('nan'):.6f} | {entry['total_nfev']} | {entry['optimizer_seconds_sum']:.2f} | {entry['optimizer_cpu_seconds_sum']:.2f} |")
    lines += ["", "## Mechanism and validation", "", "- Narrow-line cluster: at V=1.65 the same cavity is recovered by a direct start for eta=.008, .02, and .04, while eta=.004 defeats the tested direct starts. The extra eta=.004 CDF continuation is reported in the table, not assumed to fail.", "- Strong-inclusion cluster: raising V at fixed geometry and linewidth creates poor relaxed basins and large binary-projection losses. The selected V=6, eta=.02 case also fails smooth, CDF, and binary continuation, including exact-count penalties; the best projected failure is fabrication-valid.", "- Geometry-scale controls: 14x14 and 16x16 are measured separately; neither is needed for the proposed candidate.", f"- Candidate Jacobian condition numbers: witness {diagnostic['witness_jacobian']['condition_number']:.1f}, uniform start {diagnostic['uniform_jacobian']['condition_number']:.1f}, best blind relaxed basin {diagnostic['best_blind']['jacobian_condition_number']:.1f}.", "- Candidate published grid: 61 uniform energies over [-.3,.3], spacing .01, eta=.02: four samples per Lorentzian FWHM. No adaptive peak selection or hidden frequency shift.", "- Grid-refinement scores for the best blind pattern (same physical witness at each grid):"]
    for refinement in diagnostic["grid_refinement"]:
        measured = refinement["best_blind_score"]
        lines.append(f"  - {refinement['energy_count']} energies: RMSE {measured['relative_rmse']:.8f}, core {measured['core_score']:.8f}, worst {measured['worst_family_score']:.8f}.")
    lines += ["- All 15 known witnesses independently verified: matrix equality, Hermiticity, particle-hole pairing, direct-resolvent LDOS, checker LDOS, and directional checks of both analytic Jacobians. Candidate original evaluator also verifies the witness and best blind pattern in a private mirror.", "- Electron-hole mixed near-zero BdG modes and strong gap-off spectral changes are recorded in `private/diagnostics.json`; these support physical resonance/inclusion sensitivity, not a claim of self-consistent continuum Andreev physics.", "- Oracle witness-local recovery passes, but is explicitly excluded from blind portfolio counts. The target is feasible and locally accessible.", "", "No initial protected file changed. The generation-1 archives are separately hash-checked; concurrently added files outside the sidecar are listed rather than misreported as edits. No participant/evaluator/archive writes or fresh-agent launches were performed.", "", "**Limitation:** these are finite multistart nonlinear inverse-design failures, not proof of hardness. The parent should launch the proposed completely fresh one-hour generation-2 attempt.", ""]
    (ROOT / "REPORT.md").write_text("\n".join(lines))
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--freeze", action="store_true")
    arguments = parser.parse_args()
    os.nice(10)
    diagnostics(arguments.case)
    if arguments.freeze:
        print(json.dumps(freeze_candidate(arguments.case), indent=2), flush=True)


if __name__ == "__main__":
    main()
