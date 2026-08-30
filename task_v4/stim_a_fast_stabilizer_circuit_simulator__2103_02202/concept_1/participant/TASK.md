# Robust detector-readout compression

Commission a fixed low-bandwidth decoder for a Clifford error-correction instrument. Its detector front end can retain only a small subset of the available parity taps. Both the tap selection and the deterministic logical correction table must work across all specified deployment noise regimes.

The supplied categorical Pauli-fault channels are already compiled into exact detector/logical signatures. `input/` contains representative commissioning instances; `workspace/` contains the format specification and exact local scoring utilities. `baseline/solve.py` is a runnable greedy commissioning baseline.

Submit a self-contained `solve.py` and any dependencies you write in your output directory. The evaluator runs:

```
python3 solve.py --input INSTANCE.json --output ANSWER.json
```

The answer selects at most the instance's tap budget and supplies one correction bit for every retained syndrome. Minimize the largest exact logical-error probability across that instance's regimes. The selection and table cannot depend on the unknown regime.

At evaluation, your submitted files and the supplied assets are read-only; the current working directory and `/tmp` are writable scratch space. You may ship compiled binaries or compile into scratch space.

Hidden instances cover biased, correlated, and drifting fault channels within the public format and size limits. Passing requires at least **20% mean relative reduction** in worst-regime risk against the supplied baseline and at least **10% reduction in each family's mean**. All answers must be valid. Each instance has a 45-second wall-clock limit, one CPU, and 2 GiB address-space limit. Python, NumPy, SciPy, and the system C++ compiler are available; network access and external packages are not. Runtime includes any compilation. No global optimum or report is required.
