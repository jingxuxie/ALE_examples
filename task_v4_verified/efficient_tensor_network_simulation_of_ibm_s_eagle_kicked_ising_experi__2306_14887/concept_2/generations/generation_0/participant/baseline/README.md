# Runnable baseline

From the participant directory run:

```bash
python baseline/search.py --submission submission --trials 48 --seed 14887
```

The fixed-seed baseline mixes constant-field grids with smooth random pulses,
then verifies its four best nominal candidates against all five families.
It writes `witness.json` and an untrusted diagnostic `search_report.json`.
Only `witness.json` is consumed by the host evaluator.
