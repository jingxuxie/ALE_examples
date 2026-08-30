# Runnable baseline

From the participant directory run:

```bash
python baseline/search.py --submission submission --trials 48 --seed 14887
```

The original fixed-seed baseline mixes constant-field grids with smooth random
pulses, then ranks four finalists using the original five zero-drift families.
It fully verifies the selected candidate on the new 325-waveform contract using
up to four single-threaded workers. It contains no private witness or tuned seed.
It writes `witness.json` and an untrusted diagnostic `search_report.json`.
Only `witness.json` is consumed by the host evaluator.
