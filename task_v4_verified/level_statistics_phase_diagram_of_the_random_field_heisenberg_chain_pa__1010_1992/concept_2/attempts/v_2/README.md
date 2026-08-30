# Spectrally matched disorder layouts

`design.json` is the submission artifact. It contains one pair of index permutations for each of the three supplied field multisets.

The search uses the supplied exact-diagonalization implementation, the central rank slice, and field-label-wise calibration noise shared between both layouts and all scales. Candidate layouts are canonicalized only under rotations and reflections of the periodic chain. Numerical work uses at most four workers, each with one numerical-library thread.

Search stages are implemented in `search.py`, `refine.py`, `enrich.py`, `low_search.py`, `targeted.py`, and `bank1_search.py`. `joint.py` compares combinations using shared perturbation draws across banks. Exact observable evaluations are cached in `observations.jsonl`. The original assets are not modified.

`public_report.json` records the supplied checker's recomputation of the final artifact. `selection_validation.json` and `bank1_validation.json` record candidate-selection tests. `validation.json` tests the final artifact on 24 further calibration-noise draws. Bootstrap summaries estimate finite five-draw performance; they are not guarantees for the undisclosed evaluation seeds.

The design is a finite-chain diagnostic experiment, not a thermodynamic phase claim. Residual spectral-matching failures were observed during perturbation testing; the full robustness requirements are not certified.

Final public-check result: valid format, six of nine families pass, core score 85.8579737263471, worst-family score 47.969867890381984. Thus this is a best-found submission, not a solution meeting every requested numerical threshold.
