# Generation-only artifacts

The public physical contract and fidelity thresholds were chosen before witness
generation. `build_instance.py` creates one common admissible pulse and computes
all public target columns using dense matrix exponentials. It refuses to
overwrite an existing target or witness. The private seed and pulse remain under
`evaluator/hidden/`; no seed, intermediate trajectory, or pulse is in public data.

This is an inverse compilation problem, not undisclosed-physics generalization:
all four complete calibration contracts are public. Long evolution time 20.4,
three noncommuting control channels, six coherent register columns, and joint
hardware limits make a short-time local inverse or independent state transfer
insufficient as a general solution. Actual one-hour agent hardness remains
unmeasured until the parent tournament.

`validate.py` writes `validation_report.json`, updates baseline/witness scores,
freezes public hashes, and records tournament readiness in `../status.json`.
Its corruption cases audit checker validity; they are not champion counterexample
search. No champion-ratchet generation has been run. A broader future instance
must disclose its full new target family before testing a fresh solver; a fixed
pulse cannot be called wrong merely for failing unrelated targets.
