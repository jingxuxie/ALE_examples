# Private adversarial checks

`run_checks.py` checks valid-output handling; private-file denial; clone3,
thread, network and external-process denial; symlink/FIFO/missing outputs;
exit failure; NaN/Inf; wrong shape; normalization; negative/complex/object
values; oversized archives; a huge-shape NPY header with tiny payload; forged
score/CPU logs; and extra keys. All 21 checks passed for frozen v2.

`prelaunch_v1/` preserves the rejected, too-easy version and its evidence.
All of this directory is private. Label replay in `report.json` tests only
trusted scoring arithmetic and never counts as a predictive solution.
The v2.1 scorer also passes an explicit whole-sheet permutation-invariance
sanity test; this tests a grading convention, not predictive attainability.
