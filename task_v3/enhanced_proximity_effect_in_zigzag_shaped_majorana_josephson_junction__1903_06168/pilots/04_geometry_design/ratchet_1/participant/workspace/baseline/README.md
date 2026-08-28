# Public starting optimizer

`solve.py`, `geometry.py`, and `fast_physics.py` form a working earlier optimizer. From the participant working directory, run:

```sh
python workspace/baseline/solve.py --input input/example.json --output /absolute/attempt/baseline_run.json
```

It uses the request's physical bounds and fabrication validator, and it returns the required geometry format. Its regional sampling policy predates the exact `operating_points` objective. It may be reused or replaced; it contains no private reference design. The input's `baseline_geometry` is the fixed starting layout used for scoring, not a promise about the outcome of rerunning a time-limited search.
