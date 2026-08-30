# Private candidate-ratchet stress pool — NOT ACTIVE

This sidecar does not change the current task, participant assets, evaluator,
status, champions, attempts, baseline anchor, target, or prelaunch seal. It does
not launch a fresh agent. The parent may use it only as evidence for a later
decision, after fresh v2 actually passes the existing task. No automatic ratchet
or new pass target is defined here.

## Predetermined scientific design

`plan.json` fixes twelve probes before measurement: eight independent, broader
seeds of the exact existing generator (all five original families represented),
and four explicitly next-generation probes. There is no filtering of seeds based
on a participant's failures and no shape-, filename-, or identity-dependent score.

The next-generation probes are two matched 4096/8192 positive-Matsubara pairs,
one retarded multiband material and one weak-interband near-critical material.
Both use a positive four-Einstein-mode spectrum with energy ratios
`[0.002, 0.04, 0.30, 1]`: a 500-fold phonon-energy span. The upper phonon energy
divided by temperature is 1500 and 3000, respectively. Thus halving temperature
requires doubling the number of Matsubara frequencies to keep the same physical
upper cutoff, approximately 17.15 times the largest phonon energy. This is an
actual low-temperature/retardation requirement, not array padding. The soft mode
has energy 3T and 6T, so it remains physically distinct from the hard mode.

Within each pair, patch geometry, quadrature weights, phonon spectrum, and bare
coupling pattern are shared. The ordinary-retardation pair keeps interaction
strengths fixed, giving two temperatures of the same synthetic material. The
weak-interband pair rescales the electron–phonon coupling at each temperature to
hold the normal-state leading pairing eigenvalue at 1.00003; this is a controlled
near-critical family, not a fixed-material temperature sweep. Every rescaling
and spectral calibration evaluation is recorded in `parameters.json`.

The physical scope remains the seed paper's constant-DOS, Fermi-surface-patch,
finite-cutoff imaginary-axis reduction with the supplied screened repulsion and
nonnegative Einstein spectral densities. No Wannier interpolation, ab initio
material prediction, continuum-cutoff extrapolation, uniqueness theorem, or
free-energy ground-state certificate is claimed. Reference certification is
for the exact finite equations only. The same common Coulomb/frequency cutoff
convention is retained, not silently changed with matrix size.

**The four 4096/8192 cases are outside the current disclosed parameter/shape
contract.** They are only potential next-generation evidence. A failure there
is not a current-task failure, and a fixed-size allocation alone is not evidence
of a numerical-convergence defect. Any later expansion would require an explicit
new contract and resource/attainability review.

## Evidence and limits

Each case stores the public instance separately from private parameters and a
certificate. The offline witness is the existing privileged solver, executed
from starting amplitudes 1.0 and 2.7. Both solutions are independently checked
using full blocked direct Matsubara sums, not the FFT used during solving.
Required reference residuals are below 5e-11 for both equations, with cross-start
branch distance below 2e-6 and positive low-frequency gaps on every patch.
Normal-state eigenvalue and a nonzero gap-amplitude floor are also checked.
An unsuccessful construction is explicitly uncertified and cannot be used for
scoring. `reference.npz` is written only for certified cases.

Offline construction may exceed 12 CPU seconds. It establishes numerical branch
validity only. Separately, `champion_report.json` measures the existing
fixture-free privileged submission through the **unchanged** sealed evaluator's
isolated runner: 12 total CPU seconds, one process/thread, 2048 MiB, existing
residual/branch gates, and generic scratch input/output filenames. Candidate
timers are not trusted. A CPU failure or absent measurement is not a joint
attainability claim. Per-case direct verification, cross-start disagreement,
generation details, and measured resource behavior are retained.

Construction plus candidate measurements and trusted verification have an
aggregate 900-CPU-second ceiling. Every construction worker also has a hard CPU
limit; parent usage and child usage are counted together. All persistent writes,
logs, reports, jobs, and temporary scratch live inside this sidecar. Python
bytecode writes are disabled when importing existing read-only builder modules.

## Private commands

From this directory, build and measure the existing privileged solver:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B build_pool.py
```

After—not before—the parent has confirmed fresh v2 passes the active task, the
parent can evaluate that completed submission without generating or activating
anything:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -B build_pool.py --evaluate-only --submission /absolute/path/to/completed/submission --report fresh_v2_pool_report.json
```

Use the original-seed and out-of-contract summaries separately. Cluster actual
failures by residual, branch distance, weak-gap ratio, critical eigenvalue,
temperature/phonon ratios, and measured CPU—not by incidental array shape.
