# Efficient active detector calibration

Build a standalone Python program that chooses calibration experiments and
estimates positive fault-channel rates from detector syndromes. This is an
explicitly **synthetic** inverse problem inspired by decoder calibration, not a
claim about physical hardware or a requirement to implement a matching decoder.

You receive a complete observation law, a connected detector graph, known local
channel footprints, allowed interventions, and resource budgets. Rates are
unknown. Channels overlap, some primary footprints alias, rare channels span
different useful exposure scales, and an unobserved shot-level mode creates
correlations. All detectors are active. The three regimes contain 14–20
detectors and 43–77 channels.

Your program must infer rates efficiently **and allocate experiments**. Uniform
shots and low-order moment fitting are useful controls, not assumed solutions.
You may use any latent-blind algorithm, including adaptive or nonadaptive
policies; adaptivity is judged through recovery, not through a syntactic rule.

## Success

- Per episode: at most **40,000 shots**, **64 queries**, **4,000 shots/query**,
  **60 CPU seconds**, and **3 GiB address space**.
- The wall watchdog is 900 seconds after initialization, with a separate
  300-second startup allowance. CPU, not host scheduling delay, is scored.
- There are 12 hidden episodes: four per regime, with four channel families.
  Compute RMS natural-log rate error in each regime/family cell, weighting its
  episodes equally; then mean and maximum over the 12 cells.
- Pass requires **mean ≤ 0.075**, **worst cell ≤ 0.125**, and every episode valid.
  These targets were fixed before generation-two policy trials and fresh runs.

Submit `solution.py` in your writable attempt directory. It runs as
`/usr/bin/python3 /submission/solution.py` and communicates only through
stdin/stdout JSON lines. Print diagnostics to stderr. Hidden rates and sampling
seeds remain in a separate trusted process; your program never receives them.

Read `input/API.md` for the exact law and protocol. Public training episodes
include rates for development; they are independent of the private fixtures.
`baseline/solution.py` is a runnable, deliberately limited pairwise-moment
baseline. `baseline/previous_champion.py` is the unchanged preceding-generation
champion, supplied as an additional reference.

For public local testing, run from the read-only participant directory. Set
`ATTEMPT_DIR` to the actual writable output directory provided by your launcher;
the quoted path below is a placeholder, not a predefined mount:

```
ATTEMPT_DIR="/absolute/writable/path/from/launcher"
/usr/bin/python3 input/local.py --episode 0 --workdir "$ATTEMPT_DIR" --output "$ATTEMPT_DIR/training_report.json" -- /usr/bin/python3 "$ATTEMPT_DIR/solution.py"
```

The public tester uses ordinary subprocesses and does not certify hidden
resource limits. NumPy and SciPy are available with `/usr/bin/python3`.
You have one hour of fresh coding time. Do not access evaluator/private data.
