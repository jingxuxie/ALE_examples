import csv
import json
from pathlib import Path


def read_table(root, filename):
    return list(csv.DictReader((root / filename).open()))


def write_report(root):
    root = Path(root)
    results = read_table(root, 'results.csv')
    scaling = read_table(root, 'scaling.csv')
    controlled = read_table(root, 'controlled.csv')
    validation = json.loads((root / 'validation.json').read_text())
    production = [row for row in results if row['configuration'] == 'production']
    lookup = {row['row_id']: row for row in results}
    resource = {row['row_id']: row for row in scaling}
    claims = json.loads((root / 'claims.json').read_text())
    for dimension in [32, 64]:
        left = resource['resource_oscillator_%d/structured' % dimension]
        right = resource['resource_oscillator_%d/dense' % dimension]
        claims.append({'id': 'structured_cost_%d' % dimension, 'table': 'scaling.csv',
                       'left': left['row_id'], 'right': right['row_id'], 'metric': 'wall_seconds',
                       'relation': 'le' if float(left['wall_seconds']) <= float(right['wall_seconds']) else 'gt',
                       'interpretation': 'Measured structured versus dense operator action, identical equations and tolerances; single-run timing, not a universal speedup.'})
    for row in controlled:
        if row['configuration'] == 'harmonics_0':
            right = next(item for item in controlled if item['case'] == row['case'] and item['configuration'] == 'harmonics_6')
            claims.append({'id': row['case'] + '_sidebands', 'table': 'controlled.csv',
                           'left': row['row_id'], 'right': right['row_id'], 'metric': 'distance_to_comparator',
                           'relation': 'le' if float(row['distance_to_comparator']) <= float(right['distance_to_comparator']) else 'gt',
                           'interpretation': 'Dropping physical drive sidebands versus retaining six; both compared with adaptively converged production.'})
    (root / 'claims.json').write_text(json.dumps(claims, indent=2))
    summary = ['| Case | Production/refined full-map distance | Ablation/refined distance | Solve seconds | Peak MiB |',
               '|---|---:|---:|---:|---:|']
    for row in production:
        ablation = lookup[row['case'] + '/ablation']
        summary.append('| %s | %.3g | %.3g | %.3g | %.1f |' %
                       (row['case'], float(row['distance_to_refined']), float(ablation['distance_to_refined']),
                        float(row['wall_seconds']), float(row['peak_mib'])))
    scale_table = ['| Run | Seconds | Peak MiB | Comparator distance | Boundary population |',
                   '|---|---:|---:|---:|---:|']
    for row in scaling:
        scale_table.append('| %s | %.3g | %.1f | %.3g | %.3g |' %
                           (row['row_id'], float(row['wall_seconds']), float(row['peak_mib']),
                            float(row['distance_to_comparator']), float(row['boundary_population'])))
    control_table = ['| Controlled change | Distance from recorded comparator |', '|---|---:|']
    for row in controlled:
        control_table.append('| %s | %.4g |' % (row['row_id'], float(row['distance_to_comparator'])))
    numerical = read_table(root, 'validation.csv')
    largest_test_error = max(float(row['maximum_absolute_error']) for row in numerical)
    worst_refinement = max(float(row['distance_to_refined']) for row in production)
    minimum_eigenvalue = min(float(row['minimum_eigenvalue']) for row in production)
    large = resource['resource_oscillator_112/structured']
    rotated = resource['resource_oscillator_112/rotated_structured']
    dense = resource['resource_oscillator_64/dense']
    sparse = resource['resource_oscillator_64/structured']
    report = f'''# Qualification of the migrated open-system service

## Outcome

The repaired executable implements three different physical contracts rather than
three labels for one local-noise solver. For the supplied cases, the largest
production/refined full-trajectory-or-channel difference is {worst_refinement:.3g}.
The local-noise/amplitude ablation is substantially different from the microscopic
or correctly specified collapse model. Refinement is **not** an independent truth
label: analytic limits, matrix-element construction, basis covariance, branch
invariance, and resource-sized comparisons supply separate evidence.

The validation runner executed **{validation['tests_run']} tests**, with
{validation['failures']} failures and {validation['errors']} errors. The largest
recorded analytic/covariance comparison error is {largest_test_error:.3g}; individual
tolerances and errors are in `validation.csv`. The minimum production state
eigenvalue is {minimum_eigenvalue:.6g}. In the nonsecular Redfield case this is a
property of the requested generator, not a reason to replace it by a CP equation.
No density matrix or Choi matrix is renormalized, symmetrized, or positivity-projected.

## Reproduction and artifact map

From this output directory:

```sh
bash run.sh solve input/noisy_gate.json scratch/gate --config production
bash run.sh solve input/spectroscopy_ladder.json scratch/ladder --config refined
bash run.sh solve input/coupled_spins.json scratch/local --config ablation
bash run.sh campaign input regenerated
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python workspace/validate.py regenerated
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python workspace/audit.py regenerated
```

`run.sh` fixes OpenBLAS, OpenMP, and MKL to one thread. Only Python, NumPy, SciPy,
Pillow, psutil, and the standard library are used. Pytest was absent in the actual
interpreter despite the task description; the executable unittest runner also
runs both supplied tiny checks. No package installation, paper, reference output,
or external quantum simulator was used. Participant assets were copied before
editing and left unchanged.

`results.csv` contains all three configurations. `ablation.csv` selects production
and ablation. `scaling.csv` contains cutoff and implementation/size studies.
`controlled.csv` records secularization, sideband cutoff, quasienergy branch,
and absolute-time experiments. Each raw run saves `result.npz`, `metrics.json`,
`input.json`, `input.npz`, and `options.json`, so modified cases have executable
manifests rather than undocumented in-memory edits. NPZ arrays are laboratory
states and expectations at every requested time, including nonuniform grids.
The figures are generated from those table rows; `figures/sources.json` records
their source tables, metrics, and row IDs. `claims.json` contains executable
row-to-row comparisons, not unsupported accuracy labels.

## Baseline, inspection, revision, rerun

1. Before editing, the copied original workspace completed the six-case campaign.
   Its source, arrays, metrics, and tables remain in `baseline/`. Production and
   ablation were exactly identical: `engine` was never consulted by propagation.
   A small refinement difference therefore measured convergence of the wrong
   common model, not agreement between local and microscopic dissipation.
2. Inspection found collapse amplitudes used as `abs(c)` rather than `abs(c)**2`,
   missing control breakpoints, and row-major channel construction at a column-major
   API boundary. Static and driven bath models were both replaced by Hermitian
   local jumps evaluated at one total-Hamiltonian energy span. The baseline
   resonator production/refined state discrepancy was 1.89e-4. The original
   cumulative-process memory statistic also did not isolate cases.
3. The first repaired campaign (`iteration_1/`) separated the physical models,
   correctly squared amplitudes, split controls, and repaired channel/Choi maps.
   Thirteen analytic and representation tests passed. This changed the local
   comparison from identical output labels into genuine physical/numerical
   ablations. Early trace/positivity checks alone had not identified these errors.
4. A controlled 112-dimensional complex basis rotation then exposed a remaining
   numerical issue: maximum trajectory difference 1.63e-6, despite final-state
   error only 5.92e-11. The largest discrepancy occurred at an intermediate output
   time (0.42), making a final-state-only check inadequate. The original evidence
   is archived in `revision/before/`, `revision/scaling_before.csv`, and
   `revision/calibration/`. Tightening absolute tolerance reduced the discrepancy
   to 2.04e-8 with modest cost; a 0.025 maximum step also suppressed Hermiticity
   drift but cost about 4.76 seconds versus 1.40 seconds for the scaled tolerance.
   These observations are consistent with error control and interpolants on weakly
   populated stiff components, not a physical basis dependence.
5. The final integrator divides the state absolute tolerance by Hilbert dimension,
   converting the RMS component tolerance toward a Frobenius tolerance. It retains
   only requested outputs rather than all dense-output polynomials for large jobs.
   The rerun rotated-112 discrepancy is {float(rotated['distance_to_comparator']):.3g}.
   `revision/calibration_after/` records the follow-up experiments. Process RSS is
   now sampled every 2 ms in each isolated worker, avoiding inherited high-water
   marks. Harmonic initialization also accounts for energy span and drive
   bandwidth, avoiding false convergence when both small cutoffs omit a distant
   sideband. Final tables and validation are rerun after these changes.

## Equations and implementation

### Prescribed collapse operators

The laboratory equation is
`drho/dt = -i[H(t),rho] + sum |c_k(t)|^2 D[C_k](rho)`,
where `D[C](rho)=C rho C† - (C†C rho + rho C†C)/2`.
Complex amplitudes, offsets, absolute times, and carrier interference are retained.
DOP853 integrates separately across every step edge. Gaussian centers and points
one, two, four, six, and eight widths away are integration boundaries, preventing
an adaptive solver from jumping over a narrow pulse. Oscillating controls also
bound the maximum integration step independently of the output grid. Step-edge
evaluation uses the left limit for the ending interval and the right value for
the next interval; the isolated endpoint has zero measure in the propagator.

Large jobs apply operators to density matrices directly, never build a d^2 by d^2
Liouvillian, and cache adjoints/Gram matrices. Sparse operator actions are chosen
from actual matrix structure. For dense supplied rotations, an H0 eigenbasis is
used only if it reduces operator occupancy; returned states are rotated back.
Tiny operator entries below a relative roundoff threshold can be dropped in the
sparse representation. No tensor-product basis, real matrices, diagonal
observables, or pure initial state is assumed.

### Static weak-coupling baths

In an H0 eigenbasis, `A(w)[a,b] = A[a,b]` when `w=E_b-E_a`.
Positive frequency therefore releases system energy. The two-sided spectrum is
used directly, with no extra 2*pi. Independent baths are summed incoherently.
For nonsecular evolution define `B = sum_w S(w) A(w)/2`; each bath contributes

`B rho A + A rho B† - A B rho - rho B† A`.

This retains all nonsecular terms and omits the Lamb shift as specified. An
independent double-transition sum is tested against this compact construction.
For secular evolution, each equal-frequency sector forms one coherent jump
`sqrt(S(w))*sum A(w)`. Frequencies more than 1e-7 apart are never grouped. This
preserves dark-state interference inside exact degeneracies and diagonal
dephasing, without coherently merging different baths. Small constant generators
are propagated by matrix exponentials at every requested elapsed time. Static
production and refined rows can consequently agree exactly: their exponential
algorithm is the same, so those zero differences are not a convergence study.
Thermal Gibbs states, known two-level rates, the white-noise nonsecular limit,
complex common-bath dark states, and independent degenerate baths are separate
checks of this generator.

### Periodic spectral baths

One period of the closed-system propagator is integrated at tight tolerance.
The numerically computed monodromy is polar-corrected to a unitary before a
unitary Schur decomposition. This removes integration roundoff from the *closed
unitary problem*, not from any density matrix. Periodic modes are
`P(t)=U(t)V exp(+i epsilon t)` and are evaluated from piecewise dense unitary
interpolants. FFT coefficients use
`P† A P = sum_k A_k exp(+i k Omega t)`.
For a component `(a,b,k)`, the physical released frequency is
`epsilon_b - epsilon_a - k Omega`. Components at equal physical frequency are
summed before constructing their dissipator, separately for each bath.

The fully secular dissipator is constant in the full Floquet interaction frame.
It evolves the entire density matrix, not just populations. Laboratory states
are reconstructed with `W(t)=P(t mod T) exp(-i epsilon t)` and the initial state
is transformed using `W(times[0])`. This retains initial coherences, all
micromotion, diagonal/dephasing sectors, and the absolute start time. It also
handles equal physical frequencies involving different harmonics and remains
independent of quasienergy branch choices. There is no integration across
thousands of physical periods: only the requested times enter small matrix
exponentials and micromotion reconstruction.

FFT samples and retained positive/negative harmonics are doubled together until
the generator Frobenius difference times the duration is below the configured
target. Initial sampling accounts for Hamiltonian span, drive frequency, and
branch displacement. The final sample count, harmonic cutoff, generator delta,
and convergence flag are saved with each Floquet result. If the refinement cap
is reached, a warning and false flag are emitted, rather than silently declaring
convergence. In deliberately fixed-cutoff ablations, generator delta -1 means
"not measured". This empirical criterion is not a rigorous uniform error bound.

### Process boundary

The state and every matrix unit are integrated together as one linear batch.
The public channel satisfies `vec_F(rho_final) = channel @ vec_F(rho_initial)`.
Choi blocks are `E(|i><j|)` with input subsystem first; a TP channel has Choi
trace d, not one. Internal row-major arithmetic does not alter this public
convention. Analytic amplitude-damping Kraus maps, a complex rotated channel,
identity Choi matrices, partial trace, and channel/state consistency are tested.

## Main results and meaningful ablations

The reported distance is the maximum state Frobenius difference over *all*
requested times, enlarged if necessary by the **unnormalized full channel**
Frobenius difference. It is not divided by dimension, and it is not merely a
final expectation difference.

{chr(10).join(summary)}

For spectral manifests, `ablation` replaces the microscopic bath by the original
Hermitian local-noise model, evaluated at the total static energy span. It keeps
accurate controls and propagation, so its large discrepancy is a physical-model
difference, not deliberately loose integration. This local Hermitian noise is
unital and does not reproduce a finite-temperature bath's transition-specific
emission/absorption balance. For explicit-collapse manifests, `ablation` instead
uses `abs(c)` rather than `abs(c)**2`; its difference isolates the migration's
rate-versus-amplitude error. Local periodic ablations use a one-period channel
and integer matrix powers, making even the comparison model efficient at long
horizons. A single ablation flag thus has an explicitly documented, meaningful
intervention for each contract, rather than pretending all contracts are one model.

Production/refined changes tighten ODE tolerances 100-fold, increase initial FFT
resolution/cutoff, and tighten Floquet generator convergence. Independent tests
also compare a longitudinally driven spin with analytic Bessel-weighted sideband
rates, including zero-frequency dephasing; a folded static spectrum with the
static secular solver; and a zero-bath driven system with direct unitary dynamics.
The Bessel and folded-spectrum checks include thousands of periods.

{chr(10).join(control_table)}

These additional experiments show that secularization can change trajectories,
sideband truncation is a real numerical/physical decision, and branch or integer
period shifts must not change the answer. A low sideband cutoff is not justified
by trace, Hermiticity, or positivity. The retained Redfield negativity likewise
does not show that an implementation is wrong: complete positivity is not the
contract for a nonsecular equation.
The `long_production` and `long_refined` rows compare each other on a separate
nonuniform trajectory extending 10000.173 periods, rather than comparing arrays
on different time grids. Their saved timings expose the horizon-independent
Floquet propagation cost; intermediate micromotion samples are retained.

## Cutoff and resource study

{chr(10).join(scale_table)}

Supplied cutoff rows truncate the actual resonator matrices and renormalize the
*new problem's initial state only*. Their comparator distance embeds the entire
smaller state into the 32-dimensional supplied space with zeros, including the
discarded coherences and populations. Boundary population is an additional warning
indicator, not a proof of convergence or a basis-independent observable. No
infinite-dimensional claim follows from these finite-cutoff comparisons.

The controlled size series defines the same Kerr resonator, displacement, thermal
mixture, pulses, and collapse amplitudes at dimensions 16, 32, 64, and 112. Its
manifests are saved under `runs/resource_oscillator_*/`. The implementation
comparison uses identical operators, equations, tolerances, and output times;
only dense versus structured multiplication changes. Structured rows compare
with themselves (distance zero), dense/rotated/refined rows compare with the
corresponding structured production run. They are not all comparisons with an
independent reference. At dimension 64 the measured dense/structured time ratio
is {float(dense['wall_seconds']) / float(sparse['wall_seconds']):.3g}. The
112-dimensional structured run takes {float(large['wall_seconds']):.3g} seconds
and peaks at {float(large['peak_mib']):.1f} MiB in the sampled worker measurement.
The rotated-112 row includes basis recovery and laboratory output transforms.

Solver time excludes interpreter startup and file serialization. Peak RSS is a
2-ms sample of the complete isolated run after imports/input arrival, including
output serialization; it may miss shorter transients. Timing is a single run per
row, not a statistically estimated speedup; small-dimension overhead can erase
sparse gains. BLAS uses one thread. Stored trajectories require O(number_of_times
* d^2) memory. There is no dense d^4 operator for the large-resonator path.

## Limitations and release decision

- Internal refinement and invariants are necessary but not sufficient. Analytic
  limits and representation equivalence support qualification; no independent
  oracle was available for every complete supplied trajectory.
- Redfield describes the specified second-order Markov model, not exact
  microscopic finite-memory dynamics. Its negative eigenvalues are retained.
- Floquet inputs must actually satisfy their declared periodic Hamiltonian.
  Very sharp controls, extreme bandwidth, near-threshold frequency splittings,
  or very long coherent horizons can require tighter tolerances or higher caps.
  The cap/convergence diagnostics expose this rather than changing the model.
- Sparse acceleration depends on structure in some accessible basis. Generic
  dense explicit-collapse operators still work but can cost O(d^3) per RHS.
  Small entry thresholding is a floating-point approximation, tested by dense
  and rotated comparisons here, not an exact symbolic sparsity proof.
- The empirical resource/accuracy study covers the supplied experiments and
  controlled dimensions through 112, not every admissible parameter extreme.
  The 60-second worker watchdog protects campaign jobs; the solver does not
  promise that arbitrary stiff parameters can always meet that envelope.

For the executed suite, implementation/convergence fixes make representation
and refinement differences small, while model-choice differences remain large.
That distinction, rather than agreement of two mislabeled local-noise outputs,
is the basis of this qualified release.
'''
    (root / 'report.md').write_text(report)
