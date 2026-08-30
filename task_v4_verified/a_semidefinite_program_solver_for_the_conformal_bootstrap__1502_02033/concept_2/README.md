# Concept 2: collective continuum false acceptance

Freeze-ready **mode B / counterexample** task. Deploy `participant/` only.
Main owns any launcher, fresh-agent attempt, and final classification; this
privileged worker has not launched agents or modified another concept.

Run the supplied search from `participant/`:

```sh
python workspace/baseline_search.py --output workspace/witness.json --trials 4
```

Grade the data from concept_2, without running participant code:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -I evaluator/evaluate.py participant/workspace/witness.json --output attempts/score.json
```

The submission is a degree-2..24 rational Chebyshev 4x4 matrix polynomial with
trace one, bounded coefficient envelope, exact noncommutation, positive small
principal minors at the witness, and a collective rational vector. Success
requires an exact normalized quotient at most `-1e-7` while all three frozen
floating screening profiles accept. No interval/SOS certificate is used by the
target. Exact constraints/evidence use an independent private fraction checker.

`status.json` records freeze hashes, test/score results, and the pending fresh
assessment. `evaluator/README.md` specifies the read-only trust boundary and
grading details. Primary-source URLs and limitations are private in
`adversary/provenance.md`. `adversary/control_report.json` records the bounded
generation pilot; it is not a fresh-agent result. No champion is known.
