# Bounded baseline

From `participant/`, run:

```
python3 baseline/generate.py --output workspace --seed 1701 --restarts 4 --steps 60000
python3 check.py workspace --report workspace/local_report.json
```

Only NumPy and the Python standard library are used. The generator reads only
the public target. It preserves counts and cyclic spacing, minimizes the full
integer squared autocorrelation error, and writes static `design.json` plus
search diagnostics. Every accepted update uses an exact integer correlation
increment, independently recomputed at each restart and before output.

The search is reproducible for a fixed seed and proposal budget, without a
wall-clock stopping condition. Its score is not assumed to pass. The bundled
`design.json`, `search_report.json`, and `grade_report.json` are the seed-1701
reference run. Authoring diagnostics are not instructions to reproduce a
private event, and no private random seed is provided.
