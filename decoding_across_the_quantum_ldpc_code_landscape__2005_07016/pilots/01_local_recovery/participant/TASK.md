# Sparse recovery service

Replace the incomplete recovery service with a decoder that reliably preserves encoded information across sparse quantum-code and circuit-fault matrices, without global dense elimination becoming the latency bottleneck.

Submit `solve.py` and any local dependencies in the attempt directory. Run it as `python solve.py --input CASE.npz --output ANSWER.npz`. The interface is specified in `input/FORMAT.md`; `workspace/baseline.py` is a working, incomplete baseline, and `workspace/legacy_2020` supplies the original native BP/OSD implementation for reuse or replacement. Use only the supplied files and installed Python/NumPy/SciPy or C++ tooling; network access is unavailable.

Evaluation measures syndrome validity, logical recovery, runtime, and worst-family robustness relative to baseline and private reference. Hidden batches contain up to 400 shots, 250,000 fault variables, and 20,000 checks; the memory budget is 1.5 GiB. A batch has at least 30 seconds, with its exact budget supplied as `budget_seconds` when evaluated. Do not hard-code sample outputs.
