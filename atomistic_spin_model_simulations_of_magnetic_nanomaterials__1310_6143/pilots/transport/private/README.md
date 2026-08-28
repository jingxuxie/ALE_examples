# Transport pilot

Owned subtree: this directory only. The source checkout remains read-only.

## Layout

- `participant/TASK.md`: concise task; `participant/input/FORMAT.md`: complete physical and JSON contract.
- `participant/input/example_*.json`: three public examples, with no privileged labels.
- `participant/workspace/`: weak cell-averaged Python baseline and genuine pre-sublattice C++ source excerpt only.
- `attempt/`: empty, reserved for a fresh agent. The author baseline submission is in `private/weak_submission/`.
- `private/reference/`: pinned official-source C++ reference, independent NumPy oracle, provenance, and validation details.
- `private/challenge_pool/manifest.json`: frozen SHA-256 indexed 6 initial / 18 challenge / 6 confirmation cases and expected arrays.
- `private/challenge_pool/reserved_seeds.json`: 24 unconsumed seeds for genuinely fresh ratchets; not confirmation cases.
- `private/evaluator.py`: JSON submission evaluator, continuous calibration, three family breakdowns, wall time and peak RSS.

## Evaluation

From the transport root (the parent of this private directory):

```
OPENBLAS_NUM_THREADS=1 /usr/bin/python3 -s private/evaluator.py --submission private/weak_submission --output baseline_scores.json --split initial
```

Use `--split challenge` or `--split confirmation` without changing the frozen calibration. The evaluator delegates execution to `../../authoring/isolated.py` through an absolute resolved import, never imports submission code, and requires the main session's Bubblewrap harness. **Run it outside the enclosing tool sandbox (with escalation in this environment): nested network-namespace setup may be blocked.** There is no silent unsandboxed fallback. The author evaluator/oracle use system NumPy outside the sandbox. Both baseline and reference submission wrappers use only the standard library, avoiding the isolated system NumPy's unresolved BLAS symlink. Main may vendor the pinned runtime before agent launch.

Strict execution mounts only the current case, submission, participant tree, output directory and system runtime. Per-case limits are 90 seconds of parent wall time, 20 seconds of in-sandbox command elapsed time, and 1 GiB address space. The 90-second allowance includes cold namespace/runtime setup on shared storage; the separate 20-second budget uses the common harness's `/usr/bin/time` `compute_seconds` measurement, which is command elapsed time, not pure CPU time. Missing command timing or an exceeded budget is an invalid execution, not a change to physical error normalization. The participant cannot see the reference, labels, source repository, or other cases. Treat `private/isolation_validation.json` as a smoke test, not a complete adversarial security audit. Peak RSS comes from the common harness; elapsed wall time is measured by the parent.

The initial weak calibration is fixed per family and per output group. Each group score is `exp(-ln(2)*relative_RMS_error/weak_error)`, with a 0.01 minimum calibration denominator. Four groups are weighted equally: resistances, currents, atomic field, instantaneous spin derivative. The overall score is the average of mean-family and worst-family score. Runtime is reported separately. Invalid outputs score zero.

## Scope and limitations

This is a bounded instantaneous transport-to-atomic-spin coupling task, not full VAMPIRE dynamics or an MPI benchmark. It retains the official channel physics, missing-interior-channel topology, current splitting, and physical atomic field projection. It does not test spin diffusion, nonmagnetic-remove indexing, wholly empty cells, or absent endpoint channels. The independent derivative output does not claim validation of a complete time integrator. Challenge cases grow stacks, cells, channels, and atom counts without adding an unrelated numerical method.

No fresh-agent attempts are launched here. `private/strong_reference_scores.json`, `private/baseline_scores.json`, and `private/reference/independent_validations.json` contain the actual performed measurements. The recorded six-case runs were performed with a 180-second startup allowance; every recorded wall and command time also satisfies the final 90/20-second policy, without rerunning or altering physical scores. Case generation refuses to overwrite a frozen manifest.
