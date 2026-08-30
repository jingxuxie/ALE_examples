# Spectrally matched disorder layouts

Design a controlled finite-chain experiment that separates two diagnostics used in the Pal–Huse study: adjacent-gap statistics and the fraction of a long-wavelength spin modulation that relaxes. This is a finite-system diagnostic test, not a claim about a thermodynamic phase.

For each field multiset in `input/spec.json`, submit two permutations of its indices. Both layouts must contain exactly the same fields. Across the specified field-strength and calibration-perturbation families, the layouts must have closely matched mean adjacent-gap ratios but substantially different dynamical fractions. The requirements apply to every multiset, not just their average.

Assets: `workspace/physics.py` computes the observables; `workspace/check.py` checks public perturbations; `baseline/solve.py` writes a weak valid-format design. The model is the periodic spin-1/2 Heisenberg chain, exchange J=1, total Sz=0. Observables use the rank slice `N//3:2*N//3`. The dynamical fraction is the mean of Eq. (6) of arXiv:1010.1992 over those eigenstates. The full executable definition and all thresholds are in the supplied specification and checker.

Deliver `design.json` in the output directory: `{"layouts": [{"id": "...", "high": [indices], "low": [indices]}, ...]}`. Index lists are permutations of `0..L-1`. The evaluator reads this artifact without running submitted code, and recomputes the physics independently. No supplied observable values are trusted.

The hidden evaluation uses the disclosed perturbation distribution and fixed committed seeds. It scores diagnostic matching, separation, and worst-family robustness. Passing requires every numerical condition in `input/spec.json`; no optimization recipe is prescribed. Development budget: one hour, four numerical-library threads, no network. Evaluation: 240 seconds, 2 GiB, one numerical thread.
