# Temperature-transferable collision compression

Run:

```sh
python3 solve.py --input INPUT_NPZ --output OUTPUT_NPZ
```

The submission consists of `solve.py` and `bounded.py` and requires NumPy and SciPy.
It does not load any development catalogues or precomputed training assets at runtime.

The solver constructs one temperature-independent nonnegative event reweighting.
Initial selection combines degree importance, effective resistance, and conductivity
sensitivity. A nonnegative moment fit preserves temperature-resolved degrees and
probe dissipation. Damped tensor-Jacobian refinement and event exchanges then fit
the full conductivity tensors. Connectivity is maintained during event pruning.
The best iterate is retained according to the actual worst physical diagnostic.

The eight supplied development cases all produce valid outputs. The measured mean
score is 99.88/100 and the minimum family mean is 99.73/100. Individual diagnostics
and timings are saved in `validation.json`. These are development results, not a
claim about unseen cases.

The solver uses one numerical thread and has an internal wall-clock stopping rule.
The standalone CLI also passed a synthetic maximum-size catalogue (168 states,
5 branches, 7 temperatures, 24 probes, and 1512 retained events) under a 4 GiB
address-space limit and 90-second timeout: score 99.90, runtime 67.9 seconds,
and peak resident memory 709 MiB. Details are in `resource_validation.json`.
