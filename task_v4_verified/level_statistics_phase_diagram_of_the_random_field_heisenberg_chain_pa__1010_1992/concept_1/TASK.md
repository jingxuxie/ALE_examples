# Fast sample-specific spin dynamics

**Mode D — HIDDEN PREDICTION.** Predict the Pal–Huse Eq. (6) dynamical
spin fraction `f` for individual random-field Heisenberg rings. Each
input supplies the exact site-ordered field vector and length, `L=10`
or `12`. Physics is periodic, `J=1`, total `Sz=0`; the target averages
over the middle third of energy-ranked eigenstates. Output lies in
`[0,1]`. This is realization-specific prediction, not phase classification.

## Objective

On 320 hidden cases, achieve **overall RMSE <= 0.035** and **worst-family
RMSE <= 0.050** simultaneously. Both are absolute errors on the physical
`[0,1]` scale. Targets are fixed before launch. The test balances both
lengths and four published families: iid uniform, ordered blocks,
alternating correlated profiles, and shuffled near-resonant pairs.

## Interface and resources

Submit a directory containing `predict.py` and its assets. Officially,
`python3 predict.py` receives no arguments. Load assets, then print and
flush `READY\n` within **60 startup seconds**. Only afterward receive
one stdin JSON line: `{"cases":[{"id":"...","L":10,"fields":[...]}]}`.
Reply with `{"predictions":[{"id":"...","f":0.5}]}`, flush, and exit.
Provide exactly one finite prediction per ID.

The complete inference response has **3 wall seconds**, four-core CPU
affinity, 2,048 MiB address space, and no network. Startup is excluded;
hidden inputs are unavailable during startup. Training/probing may use
one hour before timed inference. No passing solution is guaranteed.

## Assets

- `input/train.jsonl`: 1,600 simulated labeled records.
- `input/validation.jsonl`: 320 independent labeled records.
- `input/PROTOCOL.md`: exact physics, sampling law, schemas and restrictions.
- `workspace/`: starter to copy into your output, physics, generators and training code.
- `baseline/`: self-contained runnable baseline; file-based testing is also supported.
- `input/baseline_metrics.json` and `input/official_streaming_benchmark.json`:
  accuracy and official runtime evidence.

Private evaluation artifacts must not be accessed. Any approach respecting
the protocol is permitted.
