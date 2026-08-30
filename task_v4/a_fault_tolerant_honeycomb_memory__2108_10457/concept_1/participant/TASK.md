# Correlation-aware honeycomb memory decoding

Improve logical-frame recovery for noisy honeycomb quantum memories beyond the supplied two-pass correlated-matching decoder.

Assets include executable simulator/decoder dependencies, labeled development experiments, and the baseline. Each evaluation request contains a Stim circuit, its decomposed detector error model, and an unlabeled detector-syndrome array. No experiment's logical outcomes are available at inference time.

Submit `solve.py`. It is invoked as `python solve.py REQUEST_DIRECTORY OUTPUT.npy`. Write a binary NumPy array of shape `(shots,)`, predicting the single logical observable. `workspace/INTERFACE.md` specifies file formats and development commands. `PYTHONPATH` includes the supplied workspace at evaluation.

The objective is at least 20% lower family-balanced logical failure than the baseline, with no noise family's failure ratio above 0.95. Scoring uses independently sampled, hidden circuits from native entangling-measurement, standard-depolarizing, and superconducting-inspired regimes, both logical directions, and varied sizes and durations. Statistical evidence of improvement is required, not only a favorable aggregate fluctuation.

Each request allows 60 seconds wall time, one CPU core, 4 GiB address space, and 64 MiB output. No network, accelerator, persistent cross-request state, or external data is available. The submission directory may contain code and trained artifacts up to 256 MiB. Development time is one hour.
