# concept_3: parity-resolved finite phi4 gap prediction

**Mode D, generation-time builder package.** Release only `participant/` to a
participant. All other directories, especially teacher seeds, high-cutoff
spectra, certificates, hidden targets, scoring code, and adversary fixtures,
remain evaluator-side. No participant agent was launched and no tested
participant or champion is claimed.

## Frozen objective and assets

- The three targets, six families, 192/48/72 split sizes, scoring rule, primary
  success thresholds, and teacher-admission tolerances were fixed in
  `evaluator/hidden/target_contract.json` before teacher generation or baseline
  scoring. Its SHA-256 is recorded by the private generation ledger and final
  status. No metric-driven target or data selection took place.
- Public low-cutoff spectra use two oscillator frequencies at local dimensions
  4, 6, and 8. Six balanced families cross two/three open sites with single-well,
  crossover, and double-well parameter bins. Three supervised positive gap
  targets include tunnelling splittings and within-parity particle-like
  excitations. Dimensionless Hamiltonian realizations are unique across splits.
- `participant/TASK.md` is the concise mission, interface, budget, and objective.
  `participant/input/PHYSICS.md` and `DISTRIBUTION.md` define all physics,
  observables, distributions, and numerical-admission conditions. Public
  labelled training and validation assets are JSON, not an embedded teacher.
- `participant/baseline/predict.py` is a fixed NumPy-only predictor. Its first
  successful public and hidden runs are retained under `attempts/`; neither
  its hyperparameters nor the target were tuned using those scores.

## Numerical teacher

The seed is arXiv:1302.5582v3 (Milsted, Haegeman, Osborne). This is an independent
finite-chain implementation of the lattice phi4 Hamiltonian described in
`PHYSICS.md`, not a reproduction of the source's infinite-MPS results or a
claim about continuum masses. All targets come from direct finite-matrix
simulations of that Hamiltonian, not a formula or fitted/extrapolated truth.

`evaluator/hidden/teacher.py` builds padded oscillator operators before taking
projected powers, assembles the open-chain tensor-product Hamiltonian, and
diagonalizes each global parity block separately. A common classical energy
shift and extended-precision Rayleigh evaluation reduce numerical loss. The
smallest splittings are admitted only when residual/roundoff and cutoff checks
resolve them; parity resolution does not magically eliminate all subtraction
error in the tunnelling gap.

Every admitted case retains at least three increasing high-cutoff spectra,
per-state residuals, orthogonality checks, two consecutive gap-change checks,
and an independent-frequency high-cutoff spectrum. Labels are exactly the
last reference-basis Ritz gaps. Final local cutoffs are 36 or 44, versus the
participant maximum of 8. The largest teacher parity block is 42,592 states.
The 312 certificates and generation cache are private and fully reproducible
from the private ledger. Eight candidate draws were rejected numerically.

These are empirical cutoff/basis convergence certificates, **not rigorous
infinite-Hilbert-space tail bounds**. Residuals alone only certify the finite
matrices. Full numerical extrema and baseline uncertainty are recorded in
`attempts/build_report.json` and `status.json`.

## Evaluator and isolation

From this directory:

```text
python evaluator/evaluate.py --submission participant/baseline --output attempts/baseline_hidden.json
python evaluator/evaluate.py --submission participant/baseline --output attempts/baseline_validation.json --split validation
```

Linux bubblewrap and libseccomp are required host isolation dependencies.
Numerical generation and prediction need only NumPy/SciPy. The evaluator never
imports a submitted module. It copies only the submitted files, public assets,
and the current batch's low-cutoff features into a fresh filesystem namespace.
Submission/public mounts are read-only; output and temporary storage are fresh.
Only system runtime libraries/configuration are additionally visible.

Scoring and private labels stay in the parent, outside the solver filesystem
and PID namespace. No evaluator or adversary file is mounted into the solver;
the small trusted resource/bootstrap runner is passed as Python command text.
Network namespaces plus seccomp disable networking, subprocess creation, and
external execution. CPU, address-space, file-size, descriptor and wall-clock
limits are enforced; stdin is `/dev/null`. Missing/unusable isolation fails
closed, with no unrestricted fallback. Nested outer sandboxes may require the
host harness to approve running this same isolated evaluator outside the outer
sandbox. The solver itself remains inside bubblewrap.

Strict JSON validation rejects duplicate keys/IDs, unknown fields/IDs,
nonpositive/nonfinite/boolean/string gaps, malformed output, symlinks and
oversized output. The objective uses log differences, not unsafe division, and
reports finite, explicitly capped relative-error diagnostics. SHA-256 checks
detect corruption of trusted data/code before and after prediction; the
manifest is itself part of the trusted host boundary, not a digital signature
against a hostile benchmark administrator.

## Reproduction and validation

```text
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python evaluator/hidden/generate.py --workers 4
python evaluator/hidden/seal.py
python adversary/validate.py
python evaluator/hidden/finalize.py
```

Generation resumes the private per-case cache and fails if the frozen contract
changes. Do not distribute seeds, caches, certificates, or hidden test files.
The self-checks independently validate projected powers with Hermite
quadrature, projection nesting, harmonic limits, parity, dense spectra,
all certificates, disjoint physical draws, absence of private IDs/seeds in
public files, exact score identities, malformed/NaN cases, forbidden filesystem
reads/writes, subprocess/network denial, output/submission links, memory/CPU/
wall/file-size limits, manifest tampering, and missing-sandbox failure.

The package remains a `hard_open_candidate`: baseline failure and low-cutoff
defects demonstrate neither a lower bound on difficulty nor the absence of a
better solver. Reported bootstrap intervals describe sampling variation of
this small fixed hidden batch, not uncertainty over every possible method.
