# Finite phi4 gap prediction

Predict three converged, parity-resolved excitation gaps of interacting open
two- and three-site phi4 chains from small local-Hilbert-space spectra. The
hidden cases cover single-well, crossover, and double-well regimes, including
small tunnelling splittings. These are finite-system gaps, not continuum masses
or an infinite-volume critical-point estimate.

## Assets

`input/train.json` contains 192 labelled cases. `input/validation_inputs.json`
and `input/validation_labels.json` contain 48 public development cases.
`input/PHYSICS.md` defines the Hamiltonian and fields; `input/DISTRIBUTION.md`
specifies the sampling domain. Each input has spectra at local cutoffs 4, 6, 8
in two oscillator bases. Hidden high-cutoff labels and teacher code are not
participant assets. `baseline/predict.py` is a runnable reference;
`workspace/` is your working area.

## Interface and resources

Submit a directory containing `predict.py`. The evaluator invokes:

```text
python predict.py --input INPUT.json --train TRAIN.json --output OUTPUT.json
```

Input has `{"schema_version":1,"cases":[...]}`. Return exactly
`{"schema_version":1,"predictions":[{"id":"...","targets":{"odd_gap":1.0,"even_gap":2.0,"odd_spacing":2.0}}]}`,
with one entry per requested ID, no extras, and strictly positive finite numbers.
Order is irrelevant. The fixed hidden batch has 72 cases. Python 3.10,
NumPy 1.21.5 and SciPy 1.8.0 are available. Limits: 30 CPU seconds, 60 wall
seconds, 2 GiB address space, one BLAS thread, 32 MiB submission, 1 MiB output.
No network, child processes, external commands, or access outside staged public
files, submission, system libraries, and temporary/output storage is permitted.

## Objective

For every case and target let `e = abs(log(prediction / reference))`.
`core = exp(-mean(e)/0.05)`; `worst = exp(-max_family(mean(e))/0.05)`.
The score is `0.75*core + 0.25*worst` (higher is better). Families are the three
regimes crossed with chain length. The fixed primary success target requires
mean error <= 0.03, worst-family mean <= 0.06, and pooled 95th-percentile error
<= 0.12. Invalid output or resource violation scores zero. Relative errors are
also reported. Teacher cutoff/basis agreement is required within 0.00002 in
log-gap, much smaller than these thresholds; labels are not extrapolated.

Evaluation: `python evaluator/evaluate.py --submission DIR --output FILE`.
Add `--split validation` for the public development set. Only `participant/`
is released to participants; the evaluator remains with the benchmark host.
