# Scored runs

`baseline_validation.json` and `baseline_hidden.json` are rejected prelaunch
v1 runs, also archived under `../adversary/prelaunch_v1/attempts/`.
`baseline_*_v2.json` use the inherited v1 ridge setting for comparison.
`baseline_*_v2_tuned.json` are the authoritative v2 baseline scores after a
validation-only six-setting sweep selected ridge strength 4.

Each run invokes a subprocess through the trusted isolated runner. No fresh
scientific agent has been launched by this builder. `.scratch/` contains only
retained public input, candidate output, and logs from selected smoke tests;
it must not be distributed as a participant training resource.
