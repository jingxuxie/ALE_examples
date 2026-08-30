# Bounded champion stress search 1

This private sidecar writes only in this directory. It does not modify the
participant, evaluator, thresholds, champion submission, or concept status.
No authoring/generator agents are launched.

Gate: the completed official `attempts/v_1.evaluation.json` must report a valid
official pass. Use the exact frozen `attempts/v_1.frozen/policy.py` through main's
existing Landlock/seccomp wrapper and the existing `run_case` oracle/scorer.

Predeclared broad search: `hidden.generator.suite("adversary-v1", 64)` gives
384 balanced instances with new private HMAC parameter/noise labels, independent
of official and calibration splits. Eight parent worker threads use distinct
single-CPU affinities, inherited by the wrapper; each policy still has one CPU,
45 seconds, a 15-second response deadline, 72 measurements, and the wrapper's
2 GiB memory limit. Every child gets a fresh scratch directory and only the
existing public oracle messages. Labels, keys, and this sidecar are not readable
by the participant. The run has a 13-minute scheduling deadline.

Repeat rule, fixed before seeing the broad cases: repeat at most eight parameter
instances, ten independent noise realizations each, only if a frozen scientific
aggregate check fails, any case is invalid, or a family contains at least three
cases with BOTH point loss > .22 and combined loss > .165. Rank candidates from
flagged families by point loss then combined loss. A single 90% interval miss or
one selected extreme is not a counterexample. Record repeated-parameter means,
coverage, spread, and persistence. Three distinct parameter instances in the
same family must sustain a failure before calling it a reproduced cluster.

The .165 and .22 case-level cutoffs above are screening devices, not replacements
for the fixed family-aggregate acceptance rule. Noise repeats of selected hard
parameters are NOT an unbiased new population evaluation. Even a reproduced
conditional cluster does not retroactively change a passing broad-suite score.
Potential scientific causes require inspection and discussion with main before
any new task generation; this sidecar never edits the participant.

Run with `PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python search.py`.
`broad_report.json` separates scientific checks from the official-split flag;
the adversary split must not be mislabeled as an official tournament. Full
private realizations are saved only here for reproducibility across later key
rotations. Integrity hashes are taken before and after the search.
