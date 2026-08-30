# Identify a parity-invisible residual channel

Diagnose which of three correlated residual-error mechanisms is installed in
an unknown device. You can choose excitation sites, retain a frame for repeated
parity measurements, and decide when to classify the device as `RR`, `RS`, or
`SS`. The mechanisms have identical degree and common-neighbor counts.

The complete public model and budgets are in `input/simulator.py` and
`input/contract.json`; `input/dev_cases.json` supplies labeled development
episodes. `baseline/policy.py` is a working weak diagnostic policy.

Submit a self-contained standard-library Python file named **`policy.py`** in
your writable output directory. It exchanges newline-delimited JSON over
stdin/stdout: `start` chooses a source, `parity` supplies a hexadecimal bit mask,
and `guess` terminates the episode. Flush every request and send diagnostics
only to stderr. See `workspace/INTERFACE.md` for the exact protocol.

Each episode permits **160 frames, 480 parity replies, eight replies per frame,
and 64 selected coordinates per mask**. The submitted file is limited to
128 KiB; evaluation allows 12 wall seconds, eight CPU seconds and 512 MiB
address space per episode. You have one hour to develop the policy using
installed offline tools; task assets are read-only.

The fixed hidden target is **171/180 correct overall and at least 18/20 in each
of nine mechanism × contamination cells**. Budget, protocol and resource
violations count as incorrect. Scores include accuracy, worst-cell accuracy
and resource validity. Hidden episodes use fresh independent seeds.

Public validation, from this directory:
`python3 workspace/dev_evaluate.py --policy /path/to/output/policy.py --output /path/to/output/dev_score.json`.
The same command accepts `--policy baseline/policy.py` and `--limit 9` for a
short run. This is a controlled synthetic diagnosis problem motivated by
Cascade parity cancellation, not a claim about deployed QKD error frequencies.
