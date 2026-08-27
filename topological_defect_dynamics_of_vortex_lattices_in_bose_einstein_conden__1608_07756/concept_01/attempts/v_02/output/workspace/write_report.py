import csv
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent.parent


def table(name):
    return list(csv.DictReader((ROOT / name).open()))


def value(name, case, frame, column):
    matches = [row for row in table(name) if row['case'] == case and int(row['frame']) == frame]
    if len(matches) != 1:
        raise ValueError((name, case, frame, len(matches)))
    return float(matches[0][column])


def evidence(name, case, frame, column):
    return dict(table=name, case=case, frame=frame, column=column)


def claim(identifier, statement, first, second, comparison='difference'):
    first_value = value(first['table'], first['case'], first['frame'], first['column'])
    second_value = value(second['table'], second['case'], second['frame'], second['column'])
    result = first_value - second_value if comparison == 'difference' else first_value / second_value
    return dict(id=identifier, statement=statement.format(value=result), evidence=[first, second], comparison=comparison, value=result)


def main():
    claims = [
        claim('erasure_vs_cluster_final',
              'At t=6, one-core erasure has g6_far larger than seven-core erasure by {value:.6g}. This is a finite-window, fixed-ROI comparison, not indefinite vacancy stability.',
              evidence('results.csv', 'vacancy', 4, 'g6_far'), evidence('results.csv', 'cluster', 4, 'g6_far')),
        claim('erasure_vs_reversal_far_final',
              'At t=6, erasure minus reversal in g6_far is {value:.6g}: a small far-bin advantage, not a universal ordering over distance and time.',
              evidence('results.csv', 'vacancy', 4, 'g6_far'), evidence('results.csv', 'reverse', 4, 'g6_far')),
        claim('erasure_vs_reversal_near_final',
              'At t=6, erasure minus reversal in g6_near is {value:.6g}; the negative value reverses the ranking seen in the far bin.',
              evidence('results.csv', 'vacancy', 4, 'g6_near'), evidence('results.csv', 'reverse', 4, 'g6_near')),
        claim('erasure_vs_reversal_early',
              'At t=1, erasure minus reversal in g6_far is {value:.6g}. Its early advantage does not imply preservation throughout arbitrarily long evolution.',
              evidence('results.csv', 'vacancy', 2, 'g6_far'), evidence('results.csv', 'reverse', 2, 'g6_far')),
        claim('erasure_order_loss',
              'The erasure case changes g6_far by {value:.6g} between t=0 and t=6. Better than cluster removal does not mean preserved crystalline order.',
              evidence('results.csv', 'vacancy', 4, 'g6_far'), evidence('results.csv', 'vacancy', 0, 'g6_far')),
        claim('temporal_sensitivity_order',
              'Primary minus half-step refinement for cluster g6_far at t=6 is {value:.6g}; this quantifies temporal sensitivity on the supplied grid only.',
              evidence('results.csv', 'cluster', 4, 'g6_far'), evidence('refinement.csv', 'cluster', 4, 'g6_far')),
        claim('temporal_sensitivity_field',
              'The cluster phase-aligned L2 wavefunction discrepancy between primary and refinement at t=6 is {value:.6g}, subtracting the exactly zero initial discrepancy. No spatial error bound is claimed.',
              evidence('convergence.csv', 'cluster', 4, 'wave_l2'), evidence('convergence.csv', 'cluster', 0, 'wave_l2')),
        claim('ablation_order_sensitivity',
              'Primary minus second-order ablation for cluster g6_far at t=6 is {value:.6g}. Both methods propagate the same conservative equation and use identical measurements.',
              evidence('results.csv', 'cluster', 4, 'g6_far'), evidence('ablation.csv', 'cluster', 4, 'g6_far')),
        claim('healing_without_immediate_filling',
              'Mean density within r<0.35 rises by {value:.6g} from t=0 to t=0.2 in isolated erasure. It fills dynamically; the imprint itself leaves density unchanged.',
              evidence('healing.csv', 'isolated_heal', 2, 'core_mean_density'), evidence('healing.csv', 'isolated_heal', 0, 'core_mean_density')),
        claim('measurement_false_core',
              'On the same repaired isolated t=0 field, the original minimum detector reports {value:.6g} more bulk positive cores than signed phase winding. A remaining density dip is not a vortex.',
              evidence('measurement_only.csv', 'isolated_heal', 0, 'nplus'), evidence('experiments/calibration_primary/results.csv', 'isolated_heal', 0, 'nplus')),
        claim('worst_family_numerical_sensitivity',
              'At t=6 in the synthetic driven elliptic transfer, coarse-Yoshida versus refined wave discrepancy is {value:.6g} times primary versus refined discrepancy. This compares numerical designs, not different physical hypotheses.',
              evidence('coarse_sensitivity.csv', 'elliptic_drive', 5, 'wave_l2'), evidence('convergence.csv', 'elliptic_drive', 5, 'wave_l2'), comparison='ratio'),
    ]
    (ROOT / 'claims.json').write_text(json.dumps(claims, indent=2, allow_nan=False))
    primary = table('results.csv')
    calibration = table('experiments/calibration_primary/results.csv')
    transfer = table('experiments/transfer_primary/results.csv')
    convergence = table('convergence.csv')
    scaling = table('scaling.csv')
    audit = table('audit.csv')
    campaign_cases = ['control', 'vacancy', 'reverse', 'cluster']
    final_rows = []
    for case in campaign_cases:
        selected = [row for row in primary if row['case'] == case][-1]
        final_rows.append('| ' + case + ' | ' + ' | '.join(f'{float(selected[column]):.6f}' for column in ['g6_near', 'g6_far'])
                          + ' | ' + '/'.join(selected[column] for column in ['nplus', 'nminus'])
                          + ' | ' + selected['n6'] + ' | ' + f'{float(selected["defect_radius"]):.4f}' + ' |')
    campaign_convergence = [row for row in convergence if row['case'] in campaign_cases]
    transfer_convergence = [row for row in convergence if row['case'] not in campaign_cases + ['isolated_heal']]
    maximum_wave = max(float(row['wave_l2']) for row in campaign_convergence)
    maximum_density = max(float(row['density_relative_l2']) for row in campaign_convergence)
    maximum_order = max(float(row['g6_max_difference']) for row in campaign_convergence)
    maximum_core = max(float(row['matched_core_rms']) for row in campaign_convergence)
    norm_drift = max(abs(float(row['norm']) - value('results.csv', row['case'], 0, 'norm')) for row in primary)
    energy_drift = max(abs(float(row['energy']) - value('results.csv', row['case'], 0, 'energy')) for row in primary)
    runtime_rows = []
    for variant in ['primary', 'ablation', 'refinement']:
        selected = [row for row in scaling if row['variant'] == variant]
        runtime_rows.append(f'| {variant} | {sum(float(row["wall_seconds"]) for row in selected):.3f} | '
                            f'{sum(float(row["cpu_seconds"]) for row in selected):.3f} | '
                            f'{max(float(row["max_rss_kib"]) for row in selected) / 1024:.2f} |')
    transfer_rows = []
    for case in sorted({row['case'] for row in transfer}):
        selected = [row for row in transfer if row['case'] == case]
        differences = [row for row in transfer_convergence if row['case'] == case]
        transfer_rows.append(f'| {case} | {max(float(row["wave_l2"]) for row in differences):.3g} | '
                             f'{max(float(row["density_relative_l2"]) for row in differences):.3g} | '
                             f'{max(abs(float(row["norm"]) - float(selected[0]["norm"])) for row in selected):.3g} |')
    old_initial = value('baseline_remeasured.csv', 'isolated_heal', 0, 'energy')
    old_final = value('baseline_remeasured.csv', 'isolated_heal', 5, 'energy')
    new_initial = float(calibration[0]['energy'])
    new_final = float(calibration[-1]['energy'])
    coarse_rows = table('experiments/calibration_coarse/results.csv')
    coarse_energy_drift = float(coarse_rows[-1]['energy']) - float(coarse_rows[0]['energy'])
    higher = table('higher_refinement.csv')[-1]
    independent = table('independent_solver.csv')
    report = f'''# Research handoff: conservative phase engineering in a rotating condensate

## Executive assessment

**One-core phase erasure preserves more of the measured orientational correlation than seven-core erasure over these saved observations, but it does not uniformly outperform circulation reversal.** At t=6 its far-bin correlation exceeds the cluster value by {claims[0]['value']:.6f}; its advantage over reversal in that bin is only {claims[1]['value']:.6f}. At the same time, its near-bin correlation is **lower** than reversal by {-claims[2]['value']:.6f}. At t=1 the erasure far-bin advantage over reversal is {claims[3]['value']:.6f}. Thus the answer depends on length scale and observation time, not just the intervention name.

Neither single-core intervention retains control-like order to t=6. The vacancy far-bin correlation falls from {value('results.csv', 'vacancy', 0, 'g6_far'):.6f} to {value('results.csv', 'vacancy', 4, 'g6_far'):.6f}. The short-time absence of a central singularity, density healing, and the survival of some bond order are distinct statements. None establishes indefinite vacancy stability or a thermodynamic phase transition.

All data here are deterministic numerical experiments on the supplied reconstructed initial states, **not archived laboratory measurements**. There is one common lattice preparation, no ensemble of initial states, and no statistical confidence interval.

### Final campaign snapshot, t=6

| Case | g6 near [0,2.8) | g6 far [5.6,20) | bulk N+/N- | bulk sixfold N6 | defect RMS radius |
|---|---:|---:|---:|---:|---:|
{chr(10).join(final_rows)}

Source: `results.csv`, frame 4, columns `g6_near`, `g6_far`, `nplus`, `nminus`, `n6`, `defect_radius`. Initial positive bulk counts are 32 (control), 31 (erasure), 31 plus one negative (reversal), and 25 (cluster): the phase increments perform the intended circulation changes without removing density. The negative core in reversal remains present at every saved frame through t=6. Fixed-mask counts can change as vortices cross the bulk boundary; they are not an atom-number measurement or a conserved count of all vortices.

## Reproducible entry point and files

From this output directory:

```bash
bash run.sh /absolute/path/to/manifest.json /new/result/directory
bash run.sh /absolute/path/to/manifest.json /new/result/directory /absolute/path/to/config.json
python workspace/test_calibration.py
python workspace/test_validation.py
bash reproduce.sh
```

`run.sh` defaults to the neighboring `config.json`, limits numerical-library threads to one, resolves assets relative to the manifest, and accepts arbitrary case names and rectangular grids. It writes raw complex128 fields, exact requested times, all frame diagnostics, `results.csv`, `scaling.csv`, and `configuration.json`. The new-name, multiple-imprint, negative-rotation, driven smoke test uses `experiments/smoke_input/manifest.json`; its result directory deliberately contains a space. No branch in propagation or measurements depends on case names.

`inputs/` is an unmodified copy of the supplied manifests, states, and measurement contract. `provenance.json` records source/input hashes. The participant assets were never edited. `workspace/` contains the executable source, tests, independent audit, data reduction, and Pillow plotting code. NumPy, SciPy, and Pillow suffice; no network, GPU, MATLAB, pytest, or additional package installation is used.

`results.csv`, `ablation.csv`, and the extra `refinement.csv` copy the corresponding experiment tables. `scaling.csv` combines their measured case costs with `variant`. `convergence.csv`, `audit.csv`, `healing.csv`, `coarse_sensitivity.csv`, `ablation_sensitivity.csv`, `measurement_only.csv`, and `baseline_remeasured.csv` are derived from saved fields/tables. Quantitative assertions with machine-readable row/column references are in `claims.json`.

## Baseline diagnosis: run, inspect, revise, rerun

The original modules were copied before editing and retained in `experiments/baseline/workspace/`. The first executed experiment was the original isolated calibration. The supplied analytic suite passed phase-only imprinting but failed negative-core sign and uniform-flow partition tests (`experiments/baseline/tests.txt`). Its diagnostic found t=0 relative density change about 2e-16, while the final density changed by 1.140 relative to its post-imprint value. Reported norm stayed exactly one, but this was not evidence of conservative evolution.

Inspection distinguished five failure mechanisms:

1. **Imprinting was already phase-only.** It was not the source of instantaneous atom removal. The original multiplication by exp(i times the summed phase increments) is preserved. An erasure leaves a depleted density core at t=0; it must heal through evolution, not be filled by hand.
2. **Propagation applied a real exponential to the interaction.** The local factor contained exp(-dt g rho/2), not exp(-i dt g rho/2). Reusing that stale factor after kinetic evolution compounds the error. Per-step normalization hid the damping while redistributing density. Rotation used a nonunitary, explicit finite-difference Euler update. These are physical/integration errors, not plotting errors.
3. **Density minima were labeled as positive vortices.** This loses circulation sign and confuses residual holes or sound minima with phase zeros. On the *same repaired* isolated t=0 raw field the legacy detector reports one bulk positive vortex and the phase detector reports none (`measurement_only.csv` versus `experiments/calibration_primary/results.csv`). This measurement-only comparison does not confound detector and integrator changes.
4. **The original order calculation imposed six nearest neighbors.** It removed guard cores, ignored material labels/holes, forced coordination counts, and used the first core's local magnitude squared rather than a two-core conjugated correlation. It could not reliably diagnose coordination defects or decorrelated orientations.
5. **The original current split was Cartesian, not Helmholtz.** Independently unwrapped phases do not define a global vortex velocity field. Labeling x-current energy compressible and y-current energy incompressible fails even a uniform-flow analytic calibration. Finite differences also disagreed with the required spectral measurement convention.

The original isolated run's energy, recomputed with the **same spectral convention used by the repaired system**, changes from {old_initial:.9f} to {old_final:.9f}; the repaired run changes from {new_initial:.9f} to {new_final:.9f}. Its second moment at t=3.2 changes from the baseline's {value('experiments/baseline/calibration/results.csv', 'isolated_heal', 5, 'r2'):.6f} to the repaired {float(calibration[-1]['r2']):.6f}. The baseline table itself uses a different finite-difference energy, so it is not used for this energy comparison. `baseline_remeasured.csv` separates that measurement difference from the bad raw dynamics.

The late baseline pathology is **not exclusively a detector artifact**: its t=3.2 raw field contains {int(value('baseline_remeasured.csv', 'isolated_heal', 5, 'nplus'))} positive and {int(value('baseline_remeasured.csv', 'isolated_heal', 5, 'nminus'))} negative bulk phase zeros when remeasured, whereas the original minimum detector reports {int(value('experiments/baseline/calibration/results.csv', 'isolated_heal', 5, 'nplus'))} positive minima and no negative cores. With the large unphysical energy increase, these are numerical defects of the corrupted evolution, not evidence that the prescribed conservative isolated erasure creates a vortex gas. The repaired calibration has no ROI phase cores at any saved time.

There was a second numerical iteration after repairing the physics: a three-stage fourth-order composition at dt=0.008 looked acceptable on the lattice but changed isolated calibration energy by {coarse_energy_drift:.6g} by t=3.2. The retained `experiments/coarse/`, `calibration_coarse/`, and `transfer_coarse/` reruns use final measurement code, so `coarse_sensitivity.csv` is a genuine timestep/design comparison. Earlier `pilot*` runs retain intermediate diagnostic versions and are **not** treated as clean convergence evidence. Subgrid zero finding was hardened with an analytic bilinear fallback when Newton's iteration leaves a winding plaquette; a deterministic randomized winding regression covers this failure mode.

The initial repaired production candidate (three-stage Yoshida, dt=0.002) and its dt=0.001 check remain under `experiments/yoshida_primary/` and `yoshida_refinement/`. A five-stage fourth-order composition at dt=0.004 reduced both measured campaign cost and discrepancy against that finer candidate. The final primary/refinement pair uses this improved composition. No normalization or filtering was introduced to obtain agreement.

The coarse candidate also fails a worst-family check: the driven elliptic transfer has final wave discrepancy {value('coarse_sensitivity.csv', 'elliptic_drive', 5, 'wave_l2'):.6g} and a signed ROI core-count discrepancy of {int(value('coarse_sensitivity.csv', 'elliptic_drive', 5, 'signed_core_count_difference'))}, relative to refinement. Final primary discrepancy is {value('convergence.csv', 'elliptic_drive', 5, 'wave_l2'):.6g} with identical signed counts. Unitarity alone therefore does not guarantee a resolved nonlinear split-step trajectory. This is why a plausible-looking lattice run was insufficient to select the production timestep/design.

## Numerical method

The equation is the prescribed conservative rotating-frame GPE, i dpsi/dt = (T + V(t) + g|psi|^2 - omega Lz) psi, in oscillator units. Arrays remain `[ny,nx]`, with physical x on axis 1 and y on axis 0; cell area is dx times dy. No resampling, relaxation, density editing, or phenomenological damping is applied.

The basic self-adjoint split step is local half-step, horizontal half-step, vertical full-step, horizontal half-step, local half-step. The directional Fourier symbols are

* Hx = kx^2/2 + omega y kx,
* Hy = ky^2/2 - omega x ky.

Their sum is exactly the discretized kinetic-minus-rotation operator, including the sign of -omega Lz. Each directional subflow is a unit-modulus one-dimensional FFT multiplier. The local subflow is exp(-i h [V + g|psi|^2]); its density is invariant during that subflow, and the second local factor is recomputed from the updated state. The drive is evaluated at each basic substep midpoint. Composition includes physical time as part of the nonautonomous flow.

Primary uses the symmetric fourth-order sequence S(p h) S(p h) S((1-4p) h) S(p h) S(p h), p=1/(4-4^(1/3)). Negative substeps are real-time reversible flows, not damping. `config.json` sets maximum macrostep 0.004. `refinement_config.json` sets 0.002 with the identical method. Primary caps dt times maximum kinetic symbol at 2.0 and dt times initial maximum |g|rho at 0.2; refinement halves both caps as well, so a capped case receives genuine temporal refinement. These are conservative resolution safeguards, not a proof of an error bound for arbitrary inputs. Each observation interval is evenly subdivided to reach its requested time exactly; `scaling.csv:dt` records the actual maximum macrostep.

The substantive ablation uses the underlying **second-order** Strang composition at maximum dt=0.008 (kinetic cap 2.8), with the same equation, inputs, intervention, core detector, and observables. It is faster but less accurate; it is not a renamed copy or a change in physical damping. The retained three-stage Yoshida option provides an additional independent composition design.

## Measurement implementation and validation

Signed cores come from wrapped phase differences around nonperiodic plaquettes, then simultaneous real/imaginary bilinear zeros at subgrid resolution. Newton refinement has an analytic quadratic fallback; density minima alone never trigger detection. Membership is rounded to the nearest original sample and restricted to positive ROI. The numerical box is not interpreted as a toroidal lattice ROI.

For each positive label, Delaunay triangulation uses **all positive guard and bulk cores**. Candidate edges are rejected if any nearest-sample point along their segment leaves the label, with spacing at most half the smaller grid spacing. Different labels never share edges. One- and two-core cases and collinear point sets are handled deterministically. Bulk coordination counts span 0 through 12. Non-sixfold defect radius is the RMS distance from the manifest intervention center, not an annular boundary or a convex-hull artifact.

Local sixfold order is the mean of exp(6i theta) over distinct admissible neighbors. Correlations are real(local_first times conjugate(local_second)), averaged over **unordered distinct bulk pairs**, including pairs in different labels. Half-open physical radial bins, pair counts, and zeros for empty bins are retained. In addition to required output, JSON records neighbor edges, local complex order, positions, labels, and bulk flags to make the topology auditable. Guard-core geometry and the interpolation convention are fixed across the final numerical comparisons.

Current uses spectral derivatives of the complex field: u=Im(conj(psi) grad psi)/|psi|, set to zero where rho <= 1e-12 max(rho). It is lab-frame current: rigid rotation is **not** subtracted. Longitudinal/transverse Fourier projection assigns the zero mode to the transverse component. Shell energies are sums with cell_area/(2 nx ny) weight, not shell means or extra powers of k. Quantum energy uses spectral derivatives of |psi|. Rotating energy is computed directly from grad psi and angular momentum, not reconstructed by assuming a discrete chain rule.

The supplied three analytic tests and 12 extended unittest tests pass. The latter cover rectangular plane waves and shell normalization; longitudinal flow; real-amplitude quantum energy; signed pairs and nonvortex density dips; simultaneous imprints; guard-assisted triangular order; annular edge rejection; cross-domain conjugated correlations; a nonlinear plane wave with nonunit initial norm; a rotating harmonic coherent state (rotation sign); driven fourth-order convergence; and randomized winding/bilinear-zero robustness.

`workspace/audit.py` independently reconstructs spectral observables using NumPy FFTs from saved raw fields, verifies first-frame imprints, dtype/shape/times, CSV-JSON agreement, bulk signed counts, segment containment, coordination, conjugated pair correlations, and defect radius. The maximum audited primary measurement residual is {max(float(row['max_measurement_residual']) for row in audit):.3g}; maximum Helmholtz Parseval residual is {max(float(row['helmholtz_parseval_residual']) for row in audit):.3g}. This verifies consistency, not absolute continuum accuracy. A finite-grid product/chain rule need not make Eq+Ec+Ei exactly equal to direct kinetic energy near resolved vortex cusps; that residual is reported transparently in `audit.csv` and is not forced to zero.

## Convergence, conservation, and cost

Across all campaign saved frames, primary versus half-step refinement gives maximum phase-aligned wavefunction L2 discrepancy **{maximum_wave:.6g}**, relative density L2 discrepancy **{maximum_density:.6g}**, matched signed-core position RMS **{maximum_core:.6g}**, and maximum change of any correlation bin **{maximum_order:.6g}**. The matched-core metric is accompanied by signed count differences in `convergence.csv`; no missing core is silently assigned zero error. Global phase is removed only for wavefunction comparisons, never to renormalize observables.

Maximum campaign norm drift is {norm_drift:.6g}; maximum absolute rotating-energy drift is {energy_drift:.6g}. Norm is never reset. The energy test is appropriate here because these cases are undriven. For the driven transfer case only norm conservation is expected; time-dependent trap work changes rotating-frame energy.

An additional cluster run at maximum dt=0.001 is retained in `experiments/ultrafine/`. At t=6, primary-versus-ultrafine wave L2 is {float(higher['primary_vs_ultrafine_wave_l2']):.6g}; refinement-versus-ultrafine is {float(higher['refinement_vs_ultrafine_wave_l2']):.6g}. The two successive halving discrepancies have ratio {value('convergence.csv', 'cluster', 4, 'wave_l2') / float(higher['refinement_vs_ultrafine_wave_l2']):.4f}, consistent with approaching fourth-order behavior rather than assuming that the first refined result is exact. See `higher_refinement.csv`.

A separate, non-split RK4 integration of the **full spectral rotating nonlinear operator**, dt=0.0001, checks the first nonzero observation of vacancy and all three transfers. The largest primary-versus-RK4 wave discrepancy is {max(float(row['primary_wave_l2']) for row in independent):.6g}; the largest refinement-versus-RK4 discrepancy is {max(float(row['refinement_wave_l2']) for row in independent):.6g}. RK4 norm drift is at most {max(abs(float(row['rk4_norm_drift'])) for row in independent):.6g}. This independent-in-time algorithm tests the directional splitting, rotation sign, drive timing, and nonlinearity without sharing the splitting composition; it is a short-time check, not a second full-window reference. Code, saved RK4 fields, measured check costs, and comparisons are in `workspace/independent_check.py`, `experiments/independent/`, and `independent_solver.csv`.

| Variant | measured wall seconds, four-case campaign | measured CPU seconds | peak process RSS, MiB |
|---|---:|---:|---:|
{chr(10).join(runtime_rows)}

These are actual single-thread `perf_counter`, `process_time`, and `getrusage` measurements, including loading, diagnostics, compression, and writing. RSS is the process high-water mark as observed after each case, therefore a conservative cumulative bound rather than a fresh per-case allocation measurement. Primary and refinement have the same 160x160 supplied output grid; refinement changes time resolution, not spatial resolution. The five-case hidden workload has not been observed or timed, so its runtime is not asserted. There is ample margin below 1 GiB in the measured runs, but different grids and required stability caps can cost more.

Temporal agreement does **not** bound spatial discretization, finite-box, phase-imprint cusp, subgrid localization, or finite-mask errors. No altered-grid result is passed off as the requested output. In particular, equal conserved energy alone would not have detected all of the coarse-composition error. Near-degenerate Delaunay edges can produce discrete topology changes; continuous field and core-position discrepancies are therefore reported alongside order metrics.

### Additional geometry transfers

`workspace/make_transfer.py` generates explicitly identified synthetic, non-relaxed tests: a rectangular driven elliptic cloud with signed cores and negative rotation, an annular current whose central winding lies outside material ROI, and two labeled separated domains with guard regions. They are not additional target conclusions or surrogates for unseen acceptance data. Each is propagated through t=6 with primary and refined settings on its own original rectangular grid.

| Transfer | maximum wave L2 discrepancy | maximum relative density discrepancy | maximum norm drift |
|---|---:|---:|---:|
{chr(10).join(transfer_rows)}

Their raw fields, full diagnostics, per-case timings, configurations, and audits are under `experiments/transfer_primary/` and `transfer_refinement/`. Geometry-specific analytic tests separately enforce no edges through annular holes, no inter-label neighbors, correct cross-domain correlations, and correct rectangular spectral units. These tests establish implementation transfer checks, not equilibration or long-term physical stability of the artificial preparations.

## Physical interpretation and limits

The isolated erasure calibration is the cleanest separation of density healing and topology. Mean density inside r<0.35 increases from {value('healing.csv', 'isolated_heal', 0, 'core_mean_density'):.6f} at t=0 to {value('healing.csv', 'isolated_heal', 2, 'core_mean_density'):.6f} at t=0.2, while there are no detected ROI phase cores at any saved time. At t=0.2 Ec={float(calibration[2]['Ec']):.6g} and Ei={float(calibration[2]['Ei']):.6g}. The released phase constraint permits density refill and predominantly compressible motion, not an atom-number deletion. Oscillations continue: conservative dynamics has no mechanism requiring monotonic relaxation to a stationary filled state. The compressible density-weighted kinetic component is a useful sound diagnostic, not a direct phonon population or a unique acoustic energy in an inhomogeneous vortex lattice.

The control remains highly ordered, whereas all interventions excite breathing, sound, and lattice rearrangement. Cluster erasure is the strongest disruption at the supplied samples. Single erasure initially retains more far-bin order than reversal, but both end far below control. The endpoint erasure/reversal ranking is opposite in near and far bins. Their coordination counts also differ substantially despite similar far-bin values: topological coordination and orientational coherence are complementary, not interchangeable. A six-neighbor count by itself is not proof of orientational order.

All statements concern five saved lattice frames over [0,6]. Lines in figures only connect those samples; unsampled extrema, defect trajectories, annihilation times, and time-integrated ordering are not inferred. The far bin spans a finite cloud, not an infinite-distance limit. Fixed ROI and bulk labels, finite vortex number, and possible near-degenerate triangulations constrain interpretation. There is no claim of indefinite vacancy stability, universal superiority over reversal, a melting transition, irreversible heating, or experimental validation.

## Figure regeneration and evidence map

```bash
python workspace/analyze.py
python workspace/plot_results.py
python workspace/write_report.py
```

* `figures/primary_result.png`: `results.csv` columns `time`, `g6_near`, `g6_far`, `defect_radius`, `Ec`, grouped by case.
* `figures/robustness_or_scaling.png`: `convergence.csv:wave_l2`; differences of `results.csv:g6_far` and `ablation.csv:g6_far`; and `scaling.csv:wall_seconds,max_rss_kib` grouped by variant.
* `figures/calibration_healing.png`: `healing.csv` and `baseline_healing.csv:core_mean_density`; isolated primary and baseline `results.csv:r2`.
* `figures/density_snapshots.png`: primary raw NPZ densities and JSON signed cores at t=0,1,6; annotations use the primary table's far correlation and bulk signed counts. The density scale and displayed physical window are common to all panels.

The claims file gives exact numeric differences and unambiguous table/case/frame/column references. Baseline, coarse, alternative, refinement, analytic, transfer, and measurement-only investigations are retained separately rather than conflated into the primary evidence.
'''
    (ROOT / 'report.md').write_text(report)
    print(f'Wrote report and {len(claims)} row-referenced claims.')


if __name__ == '__main__':
    main()
