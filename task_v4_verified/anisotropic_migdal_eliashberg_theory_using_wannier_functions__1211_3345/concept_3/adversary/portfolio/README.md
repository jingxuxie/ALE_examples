# Bounded, private achievability sidecar

This directory is not a tournament submission and must not be shared with the
running fresh agent. It does not modify participant resources, evaluator code,
hidden data, or concept status. All generated artifacts remain here.

`train.py` samples new systems from the public causal family, creates noised
observations in an exact AR-whitened orthonormal feature basis, and fits
amortized spectrum regressors. It never reads hidden labels or generating
parameters and never initializes a held-out fit from a true latent value.
The projection discards small signal modes; this is an approximation whose
adequacy is judged on independent synthetic and public validation examples.

Training has a 1000-CPU-second hard limit and one CPU thread. The total sidecar
work budget is approximately 1200 CPU seconds, including at most one frozen
hidden evaluation. `solve.py` uses only NumPy/SciPy and packaged trained arrays;
Torch is training-only. The candidate contract remains
`solve.py --input FILE --output FILE` with a `spectral_mass` NPZ output.

## Completed result: valid, not passing

The selected predictor averages three independently trained networks for each
sheet count. Training used 37,689 independent new causal simulations, exact
noise resampling in 20 AR-whitened principal coordinates, and normalized-mass
losses. The five predetermined ensemble choices were ranked on public validation
only. No private labels, private generating parameters, teacher initializations,
or true-spectrum replay entered training, selection, or prediction.

| Frozen evaluator split | Core | Worst family | Case p90 | Candidate CPU seconds | Pass |
| --- | ---: | ---: | ---: | ---: | --- |
| Public validation | 0.944546583 | 1.363904516 | 1.342063332 | 0.677538 | No |
| Full hidden | 0.940259200 | 1.314495700 | 1.437157959 | 0.454542 | No |
| Required maximum | 1.0 | 1.25 | 1.75 | 180 | |

Both outputs passed structural, finite-value, normalization, and sandbox checks.
The unchanged sandbox enforced one thread and a 4096 MiB address-space limit;
candidate CPU was measured by the frozen parent using child rusage. The only
failed accuracy gate was worst-family error, attained by the three-sheet family.
This is **not** a passing achievability witness and does not upgrade hard-open
status. No inference assets were changed after the single hidden evaluation.

Training consumed 900.144120 CPU seconds. Recorded training plus both evaluator
invocations consumed 901.882567 CPU seconds (about 15.03 CPU minutes), excluding
lightweight inspection and reporting. The sidecar stopped below its approximate
20-CPU-minute cap rather than using hidden feedback for further tuning.

## Artifacts and execution

Run from this directory:

```text
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python solve.py --input FILE --output FILE
```

Deployment requires `solve.py`, `selection.json`, both `projection_*.npz`, and
the six `network_*.npz` files, all adjacent. Training uses Torch, but deployment
uses only NumPy/SciPy. The raw simulation bank is not needed for inference.

- `training_report.json`: simulation provenance, CPU budget, synthetic checks,
  and every public-validation selection result.
- `pre_hidden_asset_manifest.json`: predictor hashes frozen before hidden scoring.
- `frozen_validation_report.json` and `frozen_hidden_report.json`: trusted scorer
  metrics, reasons, pass fields, enforced limits, and measured CPU.
- `verify.py`: invokes the unmodified frozen scorer and sandbox; redirects only
  temporary-directory placement into this sidecar. Candidate execution remains
  a subprocess and hidden labels stay in the trusted parent. Duplicate split
  evaluations are refused to avoid hidden-driven selection.

Outstanding scientific uncertainty is concentrated in the three-sheet inverse.
Finite simulation coverage, discarded low-variance feature directions, and
regression toward conditional mean spectra may all contribute; this bounded
experiment neither proves intrinsic nonidentifiability nor certifies that the
remaining worst-family gate is attainable. Participant, evaluator, task status,
and the running fresh attempt were not modified or informed by this sidecar.
