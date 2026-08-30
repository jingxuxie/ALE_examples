import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True

import numpy as np
from scipy.linalg import eigh
from scipy.signal import find_peaks

from adapter import CHAMPION, CONCEPT, ROOT, load_champion
from experiment import audit, discrepancies, hamiltonian, load_problem, response, score, summarize, write_json


def official_score(case_dir, design_dir):
    mirror = case_dir / "private" / "official_mirror"
    (mirror / "evaluator" / "hidden").mkdir(parents=True, exist_ok=True)
    participant = mirror / "participant"
    if not participant.exists():
        participant.symlink_to(case_dir / "public", target_is_directory=True)
    hashes = {f"participant/input/{name}": hashlib.sha256((case_dir / "public" / "input" / name).read_bytes()).hexdigest() for name in ("device.json", "target.npz")}
    write_json(mirror / "evaluator" / "hidden" / "freeze.json", {"core_target": .96, "worst_family_target": .94, "sha256": hashes})
    specification = importlib.util.spec_from_file_location("private_original_evaluator", CHAMPION / "evaluator" / "evaluate.py")
    evaluator = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(evaluator)
    evaluator.ROOT = mirror
    return evaluator.evaluate(design_dir)


def static_diagnostics(case):
    started = time.monotonic()
    case_dir = ROOT / "cases" / case
    config, target = load_problem(case_dir / "public" / "input")
    witness = np.array(json.loads((case_dir / "private" / "design.json").read_text())["pattern"])
    optimize, continuation, discrete = load_champion(case_dir / "public", case_dir / "private")
    model = optimize.Model()
    random = np.random.default_rng(348)
    continuous = random.uniform(.1, .9, len(witness))
    report = {"case": case, "witness_official_score": official_score(case_dir, case_dir / "private"), "jacobian_gradient_relative_errors": {}}
    for mode in ("linear", "log", "sqrt"):
        residual, jacobian = model.residual_jacobian(continuous, mode=mode, budget_weight=0, binary_weight=0)
        loss, gradient = model.evaluate(continuous, mode=mode)
        report["jacobian_gradient_relative_errors"][mode] = float(np.linalg.norm(2 * jacobian.T @ residual - gradient) / np.linalg.norm(gradient))
    for name, pattern in (("witness", witness.astype(float)), ("uniform", np.full(len(witness), .375))):
        residual, jacobian = model.residual_jacobian(pattern, budget_weight=0, binary_weight=0)
        singular = np.linalg.svd(jacobian, compute_uv=False)
        report[name + "_jacobian"] = {"largest_singular_value": float(singular[0]), "smallest_singular_value": float(singular[-1]), "condition_number": float(singular[0] / singular[-1]), "rank_at_1e-8": int(np.sum(singular > singular[0] * 1e-8)), "parameter_count": len(witness)}
    features = []
    sites = config["width"] * config["height"]
    for condition_index, condition in enumerate(config["conditions"]):
        eigenvalues, vectors = eigh(hamiltonian(config, witness, condition), check_finite=False)
        selected = np.flatnonzero((eigenvalues > 0) & (eigenvalues < .3))
        fractions = np.sum(np.abs(vectors[:sites, selected]) ** 2, axis=0)
        spacings = np.diff(eigenvalues[selected])
        features.append({"condition": condition["name"], "positive_subgap_energies": eigenvalues[selected].tolist(), "median_subgap_spacing": float(np.median(spacings)) if len(spacings) else None, "electron_hole_mixing": (4 * fractions * (1 - fractions)).tolist(), "ldos_peaks_by_probe": [int(len(find_peaks(spectrum, prominence=max(.01, .1 * np.ptp(spectrum)))[0])) for spectrum in target[condition_index]], "ldos_max": float(target[condition_index].max())})
    report["spectral_features"] = features
    gap_off = dict(config, gap_d=0., gap_xy=0.)
    report["gap_off_relative_rmse"] = discrepancies(config, response(gap_off, witness), target)["relative_rmse"]
    count, budget = len(witness), int(witness.sum())
    report["log2_unconstrained_binary_layout_count"] = (math.lgamma(count + 1) - math.lgamma(budget + 1) - math.lgamma(count - budget + 1)) / math.log(2)
    report["generation2_log2_layout_count"] = (math.lgamma(65) - math.lgamma(25) - math.lgamma(41)) / math.log(2)
    clock = time.monotonic()
    swap_model = discrete.SwapModel(stride=6, conditions=1)
    moves, losses = swap_model.all_swaps(witness, chunk=8)
    checks = []
    for index in np.linspace(0, len(moves) - 1, 5, dtype=int):
        changed = witness.copy()
        removed, added = moves[index]
        changed[removed], changed[added] = 0, 1
        direct = swap_model.evaluate(changed, False)[0]
        checks.append(float(abs(direct - losses[index])))
    report["discrete_port_validation"] = {"swap_count": len(moves), "max_direct_loss_error": max(checks), "seconds": time.monotonic() - clock, "stride": 6, "conditions": 1, "purpose": "Validate dimensional/onsite port of preserved low-rank swap helper; it did not produce the original successful submission."}
    report["seconds"] = time.monotonic() - started
    report["passed"] = bool(report["witness_official_score"]["passed"] and max(report["jacobian_gradient_relative_errors"].values()) < 1e-6 and report["discrete_port_validation"]["max_direct_loss_error"] < 1e-8)
    write_json(case_dir / "private" / "diagnostics.json", report)
    if not report["passed"]:
        raise RuntimeError("Static independent diagnostics failed")
    print(json.dumps({"case": case, "static_seconds": report["seconds"], "verified": report["passed"], "witness_jacobian": report["witness_jacobian"], "discrete": report["discrete_port_validation"]}), flush=True)
    return report


def final_diagnostics(case):
    case_dir = ROOT / "cases" / case
    config, target = load_problem(case_dir / "public" / "input")
    witness = np.array(json.loads((case_dir / "private" / "design.json").read_text())["pattern"])
    records = [(json.loads(path.read_text()), path) for path in (case_dir / "runs").glob("*/stage_*.json")]
    best, best_path = min(records, key=lambda entry: entry[0]["score"]["relative_rmse"])
    valid = [(record, path) for record, path in records if record["score"]["valid"]]
    best_valid, valid_path = min(valid, key=lambda entry: entry[0]["score"]["relative_rmse"])
    report = {"case": case, "best_any_stage": str(best_path.relative_to(ROOT)), "best_any_score": best["score"], "best_valid_stage": str(valid_path.relative_to(ROOT)), "best_valid_score": best_valid["score"], "grid_refinement": []}
    directory = case_dir / "private" / "best_blind_valid"
    directory.mkdir(exist_ok=True)
    write_json(directory / "design.json", {"pattern": best_valid["pattern"]})
    report["best_valid_official_score"] = official_score(case_dir, directory)
    for factor in (1, 2, 4):
        refined = dict(config, energies=np.linspace(-.3, .3, factor * (len(config["energies"]) - 1) + 1).tolist())
        refined_target = response(refined, witness)
        report["grid_refinement"].append({"factor": factor, "energy_count": len(refined["energies"]), "score": score(refined, refined_target, np.array(best_valid["pattern"]))})
    optimize, continuation, discrete = load_champion(case_dir / "public", case_dir / "private")
    model = optimize.Model()
    with np.load(valid_path.with_suffix(".npz")) as arrays:
        continuous = arrays["continuous"]
    residual, jacobian = model.residual_jacobian(continuous, budget_weight=0, binary_weight=0)
    singular = np.linalg.svd(jacobian, compute_uv=False)
    report["best_valid_relaxed_rmse"] = float(np.linalg.norm(residual))
    report["best_valid_relaxed_condition_number"] = float(singular[0] / singular[-1])
    report["best_valid_hamming_distance"] = int(np.count_nonzero(np.array(best_valid["pattern"]) != witness))
    report["oracle_line_profile"] = [{"fraction": float(fraction), "relative_rmse": float(np.sqrt(model.evaluate((1 - fraction) * continuous + fraction * witness, False)[0]))} for fraction in np.linspace(0, 1, 31)]
    report["oracle_note"] = "Witness used only for diagnostic line profile and validation, never to initialize a blind search. Interpolated points need not be fabrication-feasible binary masks."
    write_json(case_dir / "private" / "final_diagnostics.json", report)
    return report


def freeze(case):
    rows = summarize()
    row = next(entry for entry in rows if entry["case"] == case)
    if row["full_strength_completed_seeds"] != list(range(48)):
        raise RuntimeError("Full 48-seed six-stage original-strength portfolio is not complete")
    if row["passing_stages"]:
        raise RuntimeError("Candidate solved: do not freeze as a surviving ratchet")
    case_dir = ROOT / "cases" / case
    diagnostic = json.loads((case_dir / "private" / "diagnostics.json").read_text())
    if not row["verified"] or not diagnostic["passed"]:
        raise RuntimeError("Candidate has not passed independent validation")
    final = final_diagnostics(case)
    protected = audit()
    proposal = ROOT / "proposal"
    proposal.mkdir(exist_ok=True)
    public = {name: case_dir / "public" / "input" / name for name in ("device.json", "target.npz")}
    witness = case_dir / "private" / "design.json"
    manifest = {"status": "proposed generation_3 only; live participant/evaluator and all champion archives unchanged", "case": case, "core_target": .96, "worst_family_target": .94, "runtime_limit_seconds": 120, "public": {name: str(path.relative_to(CONCEPT)) for name, path in public.items()}, "private_witness": str(witness.relative_to(CONCEPT)), "public_sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in public.items()}, "private_witness_sha256": hashlib.sha256(witness.read_bytes()).hexdigest(), "algorithm_provenance": "Fresh generation_2 construction/research source, not static design: optimize.py, continuation.py, discrete.py research snapshots; identical to preserved source. The generation_2 final submission retained design.json, construction sources, and research outputs; generation_1 alone cleaned down to design.json.", "source_sha256": {name: hashlib.sha256((CHAMPION / "research" / name).read_bytes()).hexdigest() for name in ("optimize.py", "continuation.py", "discrete.py")}, "successful_strategy_preserved": "Original 48 seeds 0..47, linear/log/sqrt modes, SLSQP exact count equality, all six binary penalty weights .02/.1/.3/1/3/10, maxiter250/stage and ftol1e-9", "measured_evidence": row, "independent_witness": diagnostic["witness_official_score"], "best_valid_official": final["best_valid_official_score"], "protected_hash_audit": protected, "limitation": "Finite portfolio failure, not proof of hardness. Parent must launch the final fresh one-hour attempt; no fresh agents launched by this sidecar."}
    manifest["matched_12_full_portfolio"] = next(entry for entry in rows if entry["case"] == "islands12_v6_eta0.01")
    manifest["pending_runs_by_case"] = {entry["case"]: sorted(path.name for path in (ROOT / "cases" / entry["case"] / "runs").iterdir() if path.is_dir() and not (path / "result.json").exists()) for entry in rows}
    manifest["pending_run_policy"] = "Pending auxiliary or broad-screen runs are NOT counted as completed failures; CPU totals count scored stages only. All 48 primary continuation seeds ARE complete before this packet is frozen."
    write_json(proposal / "freeze.json", manifest)
    lines = ["# Generation-3 champion ratchet", "", f"Selected case: `{case}`. Acceptance thresholds stay **.96 core / .94 worst**.", "", "## Algorithm provenance and strength", "", manifest["algorithm_provenance"], "", manifest["successful_strategy_preserved"], "", "This is NOT an old-layout/new-fingerprint comparison. Blind optimization calls the preserved construction algorithm. The gen2 control reproduces its exact seed-7 solution. Eight original 450-iteration L-BFGS starts, their 300-evaluation least-squares continuations, and eight 350-evaluation cold least-squares starts are additionally attempted on the primary; completed and pending runs are distinguished in the source records.", "", "## Physical controls", "", "Four geometries (14,16,18,20) cross V=3.2/6 and eta=.01/.02. Two matched 12x12 island controls supplement the original gen2 target. Candidate counts are 96/144/192/256 and normal budgets 36/54/72/96: exactly 3/8 normal material, open boundaries, fixed prescribed chiral-gap model. Four interior corners are held superconducting on sizes 14/18 solely to retain the exact fraction. Masks are first-feasible correlated metallic islands, selected before optimization, never by failure or spectral fingerprint. Each geometry uses the same mask across V and eta.", "", "All spectra are uniformly sampled on [-.3,.3] at step eta/2 (four samples per Lorentzian FWHM). The 16x16 case was predeclared as the moderate-size full-strength primary before fitting; 18/20 are scaling controls, not the selected obstacle.", "", "## Measured sweep", "", "Screening = seeds 0,1,2, six stages, maxiter80; it is NOT equivalent to the original-strength test. Full = all six stages with original maxiter250. Scores below include all scored stages, including partial runs. Raw RMSE prevents clipped zero scores from hiding differences. Runtime sums are aggregate process time, not elapsed sidecar time.", "", "| Case | Completed runs | Full seeds | Stages | Best core | Best worst | RMSE | Best valid core | CPU seconds |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for entry in rows:
        best = entry["best_spectral"]
        valid_score = entry["best_valid"]
        if best:
            valid_text = f"{valid_score['core_score']:.6f}" if valid_score else "none"
            lines.append(f"| {entry['case']} | {entry['completed_runs']} | {len(entry['full_strength_completed_seeds'])} | {entry['scored_stages']} | {best['core_score']:.6f} | {best['worst_family_score']:.6f} | {best['relative_rmse']:.6f} | {valid_text} | {entry['optimizer_cpu_seconds_sum']:.2f} |")
    lines += ["", "## Candidate evidence", "", f"Original-strength continuation: 48 complete seeds, 288 stages, no pass. All-method total: {row['scored_stages']} scored stages, {row['nfev']} function evaluations, {row['optimizer_cpu_seconds_sum']:.2f} CPU-seconds. Best valid core/worst = {row['best_valid']['core_score']:.8f}/{row['best_valid']['worst_family_score']:.8f}; best score even ignoring fabrication validity = {row['best_spectral']['core_score']:.8f}. Thus failure is not just count/connectivity rejection.", "", f"Known witness official core/worst = {diagnostic['witness_official_score']['core_score']:.14f}/{diagnostic['witness_official_score']['worst_family_score']:.14f}; checker wall time {diagnostic['witness_official_score']['runtime_seconds']:.3f}s. Matrix/LDOS/direct-resolvent validation, all three objective gradients, least-squares Jacobians, and low-rank swap-helper consistency are independently checked.", "", f"Jacobian condition numbers: witness {diagnostic['witness_jacobian']['condition_number']:.1f}, uniform {diagnostic['uniform_jacobian']['condition_number']:.1f}, best valid relaxed endpoint {final['best_valid_relaxed_condition_number']:.1f}. Binary-layout entropy before connectivity: {diagnostic['log2_unconstrained_binary_layout_count']:.2f} bits versus {diagnostic['generation2_log2_layout_count']:.2f} bits at 64/24. This is a search-space description, not a hardness proof.", "", "Refined-grid rescoring of the best valid blind mask:"]
    for refinement in final["grid_refinement"]:
        measured = refinement["score"]
        lines.append(f"- {refinement['energy_count']} energies: core={measured['core_score']:.8f}, worst={measured['worst_family_score']:.8f}, RMSE={measured['relative_rmse']:.8f}.")
    matched = manifest["matched_12_full_portfolio"]
    lines += ["", "## Attribution and pending branches", "", f"The matched 12x12 many-island case completed {len(matched['full_strength_completed_seeds'])} full-strength seeds; its best valid core score is {matched['best_valid']['core_score']:.6f}. Consequently many-inclusion geometry itself matters: these data do not isolate dimension growth as the sole cause. The proposed 16x16 case combines that physical landscape with a substantially larger binary design space, rather than relying on 18/20 matrix costs.", "", manifest["pending_run_policy"], ""]
    for pending_case, pending in manifest["pending_runs_by_case"].items():
        if pending:
            lines.append(f"- Still running at snapshot: {pending_case}: {', '.join(pending)}.")
    lines += ["", "## Handoff", "", f"- Public device: `{manifest['public']['device.json']}`", f"- Public target: `{manifest['public']['target.npz']}`", f"- Private feasible witness: `{manifest['private_witness']}`", "- Frozen hashes, thresholds, and algorithm provenance: `proposal/freeze.json`.", "", "The failures identify finite-budget many-inclusion nonlinear inverse-design/search obstructions for this champion, not impossibility or one-hour hardness. A new method, more starts, or longer runs may still succeed. No live assets or champion sources were changed; no agents were launched.", ""]
    (ROOT / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps(manifest, indent=2), flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case")
    parser.add_argument("--freeze", action="store_true")
    arguments = parser.parse_args()
    os.nice(10)
    if arguments.freeze:
        freeze(arguments.case)
    else:
        static_diagnostics(arguments.case)


if __name__ == "__main__":
    main()
