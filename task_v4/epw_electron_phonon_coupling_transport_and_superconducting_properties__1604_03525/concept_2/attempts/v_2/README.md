# Temperature-transferable event compression

Run the standalone submission with:

```sh
python3 solve.py --input INPUT_NPZ --output OUTPUT_NPZ
```

Dependencies are NumPy and SciPy. No trained assets or input-specific tables are
needed. The solver uses one numerical thread.

## Method

The initial sample combines effective-resistance importance with normalized
transport-response and probe-dissipation importance over every supplied
temperature. A spanning forest repairs any disconnected initial selection.

All selected events then share one bounded, nonnegative multiplier vector.
Degree and probe residuals are linear in that vector. Conductivity residuals
use the full inverse collision operator and are whitened by the original
conductivity tensor. Bounded, preconditioned Gauss–Newton subproblems fit these
three observables together; a line search checks the actual nonlinear error.

Periodically, nearly unused events are exchanged for events with favorable
residual gradients. Each exchange preserves a spanning tree. The solver keeps
the best selection according to the exact maximum diagnostic, including all
temperatures, rather than merely its least-squares objective.

Optimization has a 75-second internal deadline and a 40-iteration outer limit.
The output always uses at most the supplied event budget.

## Validation

`validation.json` records the public development-catalogue results. Validation
ran the submission as a separate process with a 4 GiB address-space limit and
checked its output using the supplied physical scoring model. These are
development measurements, not predictions of hidden scores.

- All 12 supplied catalogues produce valid, connected outputs.
- Mean score: **98.89/100**.
- Worst-family mean: **98.73/100**.
- Maximum measured runtime: **71.30 seconds**.

`stress_validation.json` separately records two locally derived 448-state
catalogues with 24 probes and six or eight branches. Both outputs validate:
scores are **96.65** and **99.06**, with runtimes below **64.05 seconds**.

Additional checks cover immediate-deadline fallback, initial connectivity
repair, tree-preserving exchanges at a near-minimum edge budget, exact output
filenames, and unchanged output when the full catalogue fits the budget.
