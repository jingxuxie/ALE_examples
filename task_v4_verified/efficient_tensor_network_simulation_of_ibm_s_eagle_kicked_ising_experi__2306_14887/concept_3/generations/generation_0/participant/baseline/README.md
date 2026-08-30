# Weak nominal-only baseline

`pulses.json` is a valid precomputed baseline artifact, not a robust solution.
You may use it as a warm start. From the participant directory, score or
reproduce it with:

```bash
python workspace/score_public.py --submission baseline
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python baseline/run_baseline.py --output submission
```

The default run optimizes nominal fidelity only, with global tied angles
and seed 148873. `--mode random --trials 32` gives a cheaper random/ramp
baseline. Use the exact simulator and public calibration family to design
a robust two-group sequence; nominal success alone is insufficient.
