import hashlib
import json
import shutil
import subprocess
from pathlib import Path


PENDING = Path(__file__).resolve().parent
ROOT = PENDING.parent.parent
SELECTED = PENDING / "robustness_exploration" / "candidates" / "middle_cross_45"


def json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def text_patch(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        original = path.read_text()
        if original == content:
            return
        patch = "*** Begin Patch\n*** Update File: " + str(path) + "\n@@\n"
        patch += "".join("-" + line + "\n" for line in original.splitlines())
        patch += "".join("+" + line + "\n" for line in content.splitlines())
    else:
        patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n"
        patch += "".join("+" + line + "\n" for line in content.splitlines())
    subprocess.run(["apply_patch", patch + "*** End Patch\n"], check=True)


def hashes(directory):
    result = {}
    for path in sorted(directory.rglob("*")):
        if "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            raise ValueError("Unexpected symlink: " + str(path))
        if path.is_file():
            result[str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def protected_state():
    return {
        "participant": hashes(ROOT / "participant"),
        "evaluator": hashes(ROOT / "evaluator"),
        "status.json": hashlib.sha256((ROOT / "status.json").read_bytes()).hexdigest(),
    }


def main():
    before = protected_state()
    provenance = json.loads((SELECTED / "provenance.json").read_text())
    oracle = json.loads((PENDING / "family_oracle/middle_cross_45/summary.json").read_text())
    config = json.loads((SELECTED / "input/config.json").read_text())
    assert provenance["selected_target"] == config["target_ratio"] == 1.09
    assert provenance["private_score"] > 1.09 > oracle["champion_oracle_score"]
    assert oracle["admissible"] and oracle["genuine_failure"]
    participant = PENDING / "participant"
    evaluator = PENDING / "evaluator"
    shutil.copytree(PENDING / "archived_originals/participant", participant,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(PENDING / "reporting_only/evaluator", evaluator,
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    for filename in ("config.json", "reference.npz"):
        shutil.copy2(SELECTED / "input" / filename, participant / "input" / filename)
        shutil.copy2(SELECTED / "input" / filename, evaluator / "hidden/frozen_input" / filename)
    shutil.copy2(SELECTED / "witness.npz", evaluator / "hidden/witness.npz")
    shutil.copy2(SELECTED / "audit.json", evaluator / "hidden/discovery_audit.json")
    shutil.copy2(SELECTED / "provenance.json", evaluator / "hidden/discovery_provenance.json")
    text_patch(participant / "TASK.md", """# Matched normal states across distinct phonon spectra

Find two anisotropic electron–phonon kernels with identical complete normal-state mass renormalization and identical static pairing matrices, but a critical-temperature ratio of at least **1.09 in every supplied spectral scenario and refinement**. The same pair must work throughout; optimizing only one spectrum is insufficient.

## Assets and interface

- `input/reference.npz` is the fixed feasible constraint instance; `input/config.json` fixes all bounds, tolerances, spectral scenarios, refinements, and the target.
- `input/FORMAT.md` supplies every equation and the artifact format. `workspace/physics.py` is a working solver and artifact validator; `workspace/check.py` is the public check. Implement search, not an equation solver.
- `workspace/solve.py` is a runnable starting point; `baseline/solve.py` emits the same feasible reference twice.
- Produce `witness.npz` with only a real numeric array `kernels` of shape `(2,3,8,8)`. Evaluation consumes this artifact, never submitted code.

## Constraints

Both kernels independently match all supplied per-mode labeled weighted row sums, mode diagonals, and the full static aggregate. Each mode matrix is symmetric and within the fixed entry bounds. Comparisons use published absolute tolerances. Patch and mode labels are fixed; do not change the input. Mode labels do not imply frequency ordering across scenarios.

## Scoring and success

The score is the minimum ordered high/low critical-temperature ratio across all four spectral scenarios and all prescribed Matsubara grids. Choose the kernel ordering once from the nominal fine grid and retain it everywhere. A repeated reference scores `1.0`.

`admissible` means the matrix constraints pass. `valid` additionally requires score at least `1.09`, refinement convergence, and the independent signed-frequency and regular-row controls. The evaluator reports a reason, `core_score`, `worst_family_score`, timing/resources, and a saved audit. Both score summaries equal the minimum ratio just defined; admissibility alone is not success. There is no absolute temperature-difference target.

Run `python workspace/check.py witness.npz --output public_check.json` from this directory. The public check reports constraints and physics; the evaluator adds independent audits. The supplied spectra are distinct positive-phonon stress scenarios, not small isotope uncertainties or a claimed material trajectory. This is a clean, constant-DOS, Fermi-surface-restricted model with zero Coulomb pseudopotential, not a claim of synthesizable materials.
""")
    original_format = (PENDING / "archived_originals/participant/input/FORMAT.md").read_text()
    anchor = "## Artifact\n"
    additional = """## Fixed spectral scenarios

The nominal mode energies are `(4,25,100)` meV. Keep the three mode matrices and their labels unchanged while applying each scenario to both submitted kernels:

| Scenario | Mode energies (meV) |
|---|---|
| `nominal` | `(4,25,100)` |
| `compressed_spectrum` | `(4.2,25,95)` |
| `expanded_spectrum` | `(3.8,25,105)` |
| `independent_branch_0` | `(4,100,45)` |

The last scenario independently shifts two branches and reverses their frequency ordering. Do not sort the frequencies without applying the same permutation to all mode-resolved data. The matrices parameterize integrated mode couplings, not fixed delta-function spectral weights: the prefactor `Omega_s C_sij / 2` changes with the scenario. Every scenario separately has matched isotropic spectra and matched normal-state functions between the two kernels.

These are alternative effective positive-phonon models used for a worst-case stress test, not a realistic isotope range or a continuous material deformation. No matrix invariant or bound depends on the chosen scenario. The required minimum ratio is `1.09` over nine evaluations: two grids for each of four scenarios, plus the nominal `M=384` grid. The full static aggregate remains fixed even when branch energies cross. `core_score` and `worst_family_score` both denote this minimum; evaluator resource measurements exclude candidate search because no candidate code is executed.

"""
    if original_format.count(anchor) != 1:
        raise ValueError("Unexpected FORMAT structure")
    text_patch(participant / "input/FORMAT.md", original_format.replace(anchor, additional + anchor))
    shutil.copytree(participant / "input", PENDING / "input", dirs_exist_ok=True)
    text_patch(PENDING / "DECISION.md", """# Pending generation 1: independently shifted phonon branches

Status: proposed for parent review only. No active participant/evaluator/status file is changed, no new fresh runner is launched, and no original numerical contract is rewritten.

## Selection and evidence

The original fresh trials both solve the original 1.12 task at effectively identical scores. The exact higher unrounded result (v2, 1.1245411788778297) and its frozen submission, launch manifest, and evaluations are archived in `../../champions/generation_1`. Its original-control replay reproduces that score. The two passing n=8 pool alternatives and the constant-total-row anticorrelated case are also solved by the actual search; these are not hardness evidence.

The selected input is `robustness_exploration/candidates/middle_cross_45`. It retains the original n=8 constraint arrays, three modes, bounds, and solver conventions; it adds the positive branch scenario `(4,100,45)` meV to the three original spectra. This is a minimax change, not a dimension, path, label, invalid-input, or formula-implementation trap. The original row profiles remain; the unsuccessful anticorrelated exploration is not concealed.

| Measured quantity | Ratio |
|---|---:|
| Private independently audited witness | 1.094955838159416 |
| Target fixed from private evidence before replay | 1.09 |
| Actual champion, original compressed-family setting | 1.0741927523646932 |
| Best actual search over every public family setting | 1.082574580261811 |
| Stronger oracle recombining all 16 produced endpoints | 1.0877026333364312 |

The oracle artifact is admissible, converged, and independently audited. Its target shortfall is 0.0022973666635688; the private/oracle gap is 0.007253204822984749. The private target margin is 0.004955838159416. The target follows the predeclared private-only rule: largest 0.01-spaced ratio at least 0.003 below a private witnessed score, requiring at least 1.08. It is not increased after observing the champion. Selection over a private pool is adversarial task design, not a statistical generalization claim.

The private solution balances two active worst-case constraints: compressed-spectrum ratio 1.094955838159416 and independently shifted ratio 1.0949561065713225. This establishes competing spectral objectives; it does not prove multiple difficult local minima or global optimality. The milder `middle_cross_60` and the other retained cases are honestly recorded as solved. `middle_cross_35` also defeats the oracle but misses its target much more narrowly, so it is not selected.

## Actual-method replay and resources

`champion_adapter/path_only.diff` changes only the public participant path; an AST check establishes that the algorithm is unchanged. Each family uses the recorded `--count 48 --starts 24` search and `--count 192 --starts 0 --resume ...` refinement. There is no literal success-ratio stop in v2; its stationarity tolerances are not target thresholds and remain untouched. All public `--family` configurations are granted, then all output endpoints may be combined. The strongest resulting pair is checked independently. Thus a stale path, family default, target, or dimension cannot explain the gap.

`family_oracle/middle_cross_45/summary.json`, `family_oracle_summary.json`, and `champion_replays/oracle_middle_cross_45__*/` preserve artifacts, logs, GNU-time CPU/wall/RSS measurements, and audits. The replay uses bwrap with only public input/code and a fresh writable output; no hidden witness is mounted. A prior sandbox-startup failure was retried and is not counted as an optimization failure. `explore_robustness.py`, `family_oracle.py`, `replay_champion.py`, and the original pool generator preserve reproducibility. `prepare_pending.py` assembles this draft; `validate_pending.py` verifies it without launching a fresh model.

## Scientific interpretation and limits

The same per-mode labeled rows guarantee the complete normal-state functions agree within each scenario; the same full static aggregate rules out a static Perron-eigenvalue score. All entries, frequencies, and spectral weights are nonnegative, and coupling bounds are unchanged. Frequency branches are fixed labels, not an energy-sorted indexing convention. The enlarged shifts are alternative effective models, not realistic isotope perturbations or an ab initio material claim.

This is a changed robustness task with a lower ratio target than generation 0, not a mathematically nested feasible-set strengthening of its success condition. The empirical requirement is an admissible actual-method failure and a private audited pass. A minimax-aware search can improve the champion, and a new fresh model may solve this quickly; there is no unsupported hardness guarantee. The finite Matsubara operators and drift tests are the numerical contract, not interval certification of the infinite-cutoff limit. The n=8 public draft is distinct from the larger private follow-up; see the subsequent shortcut evidence.

## Additional shortcut evidence: not recommended as a hard ratchet

After the full draft validated, `mixing_sanity_probe.py` tested a new two-parameter algorithm: independently interpolate the low and high endpoints between the compressed-spectrum and independently shifted-family champion outputs. A 41-point grid for each parameter, caching single-kernel transitions at M=48, finds a pair with independently audited score **1.094290457685765**, above the unchanged 1.09 target. The full probe, including final audit, takes **8.621409096999999 CPU seconds**; the selected high/low independent-family fractions are 0.875 and 0.575.

This is not the unchanged champion method, so it does not invalidate the actual replay gap. It does demonstrate that a simple small-dimensional extension solves the proposed task. The validated n=8 draft is therefore **not recommended as strong hardness evidence**. A separate bounded, nonidentical 24-patch planted-instance investigation is stored under `large_patch_probe/`; its outcome must be assessed independently. No target is raised to evade this shortcut and no active package is changed.

## Reporting-only change

The pending evaluator's numerical physics, artifact guards, signed-frequency assembly, regular-row control, and old-case validity logic are byte-identical to the frozen originals. The reporting wrapper adds a reason on every outcome, explicitly defines `core_score = worst_family_score = score`, and measures evaluator CPU/wall/peak RSS. `reporting_only/REPORTING_REGRESSION.json` demonstrates unchanged original baseline/champion scores and verdicts. Archived old outputs remain untouched. The selected new input/target is a separate, explicit numerical task change, not part of this formatting fix.

Only the parent may promote this draft or launch a new fresh attempt. Private artifacts and this decision record must not enter the participant mount.
""")
    manifest = {
        "schema_version": 1,
        "selected_case": "middle_cross_45",
        "target_ratio": 1.09,
        "target_rule": provenance["private_only_target_rule"],
        "target_retuned_after_champion_replay": False,
        "public": hashes(participant),
        "trusted_evaluator": hashes(evaluator),
        "protected_active_before": before,
        "protected_active_after": protected_state(),
    }
    assert manifest["protected_active_before"] == manifest["protected_active_after"]
    json_write(PENDING / "package_manifest.json", manifest)
    json_write(PENDING / "status.json", {
        "schema_version": 2,
        "generation": 1,
        "status": "pending_validation",
        "ready_for_parent_review": False,
        "active_package_overwritten": False,
        "new_fresh_runner_launched": False,
        "target_frozen": True,
        "target_ratio": 1.09,
        "selected_case": "middle_cross_45",
        "private_score": provenance["private_score"],
        "champion_oracle_score": oracle["champion_oracle_score"],
        "private_witness": "evaluator/hidden/witness.npz",
        "reason": "Draft assembled from pre-fixed private evidence; exact draft validation is pending.",
    })
    print(json.dumps({"pending": str(PENDING), "target_ratio": 1.09, "active_unchanged": True}))


if __name__ == "__main__":
    main()
