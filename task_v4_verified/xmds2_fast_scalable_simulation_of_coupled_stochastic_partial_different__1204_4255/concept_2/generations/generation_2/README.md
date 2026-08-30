# Generation 2 staging package

Self-contained, not yet promoted. Expose only `participant/` to future tested agents. Status remains `pending_tournament`; no fresh agent has been launched for this generation.

The baseline is the verified generation-1 champion. The model, parameter ranges, three-time density-gap target 0.30, certificate limit 1e-4, diagnostic limits and four-solve reference validation are unchanged. The public family now combines the original five members with all 32 corners of an independent five-dimensional calibration/shape/phase box without hidden or randomly drawn grading points. This is a finite-design robustness challenge, not a continuous-box proof.

Run the commands in `participant/workspace/README.md`. Evaluation uses a 660-second wall / 400-second CPU budget, one thread and 1376 MiB address space. `adversary/test_controls.py` runs schema, file-type, numerical-order and frozen-copy checks after the baseline has been copied to `attempts/baseline.json`.

Main must review the frozen manifest and privileged evidence before promotion. No root initial-generation files are modified by this staging package.

The binary objective enables certified early rejection without changing the acceptance set. Wall allowance is 660 seconds, CPU allowance remains 400 seconds. Continuous margin diagnostics are not the official score.
