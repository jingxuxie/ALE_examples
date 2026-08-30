# Correlated logical decoding: residual accuracy under a compute budget

Improve the supplied strong decoder's **joint logical-frame accuracy** on known
local-noise toric-code models. The baseline already combines compiled belief
propagation, reliability-ordered search, an ensemble, and logical-class scoring.
This is an improvement task, not an implementation of sparse blossom or a
request to reproduce one named algorithm.

Six cases cover three families: overlapping spatial pairs, known nonuniform
crosstalk, and coupled space-time pair/readout faults. The likelihood model is
fully public. Predict the four logical-frame bits from each syndrome; the most
probable physical explanation need not give the most probable logical class.

## Assets and interface

- `input/cases/`: exact known models, matrices, probabilities and detector DEMs.
- `input/calibration/`: 256 independently sampled labeled shots per case, with
  baseline predictions. `input/models.py` also supports generating your own data.
- `baseline/`: the promoted decoder, Python/C++ source and ready-to-use binary.
- `input/runtime/`: local NumPy, SciPy, Stim 1.15.0 and PyMatching 2.4.0 runtime.
- `input/API.md`: precise `Decoder(model).decode(syndromes)` contract.

The participant tree is read-only. **Copy `workspace/submission.py` to
`$OUTPUT_DIR/submission.py` and edit there.** Put any compiled code and other
needed artifacts in that same output directory. Only this directory is collected.
No explanation document is required.

## Frozen objectives and resources

All gates must pass on 3,072 hidden shots: **20% fewer failures** than the supplied
baseline overall, **15% fewer** on the independent holdout, no increase in any
family's pooled failure count, and a positive lower endpoint of the paired 95%
absolute-improvement interval. All four bits must be correct for a shot to pass.

CPU is limited to **1.25 times the frozen measured baseline CPU, rounded up to a
whole second**; the exact cap is in `input/target.json`. Imports, construction and
decoding all count. One process/thread, 6 GiB address space, and a generous 900 s
wall watchdog apply. Use CPU time, not shared-host waiting time, for optimization.
Development time is one hour. Internet access is unavailable. Compile native
artifacts during development with `/usr/bin/g++`; child processes/threads are
blocked during evaluation. Use `/usr/bin/python3` and the bundled runtime.

Run public calibration with:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/python3 input/run_public.py --submission "$OUTPUT_DIR/submission.py" --report "$OUTPUT_DIR/public_report.json"
```

Calibration is feedback, not the hidden objective. Do not rely on batch order,
hidden labels, seeds, evaluator files, or data outside the provided assets.
