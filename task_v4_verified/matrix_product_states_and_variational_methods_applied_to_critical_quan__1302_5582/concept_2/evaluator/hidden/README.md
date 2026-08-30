# Trusted checker

`trusted_physics.py` is an identical copy of the public mathematical checker,
outside the participant allowlist. The evaluator imports no submitted code.
All observable targets and tolerances are public; the actual tensor is the
entire witness.

Contract v4 retains every v3 admissibility, energy, two-point, and four-point
criterion and adds at most 10% relative error in the third joint cumulant of
three XX interval composites over 252 public sextuples, all of span at most
256. The authoritative submitted value uses literal full-tensor raw six-,
four-, and two-point contractions followed by own-state cumulant subtraction.
It assumes neither exact canonicality nor exact parity, and does not impose
the ground state's determinant identity on a submitted state. All six family
qualities must equal one; the core is their geometric mean.

The previous `test_validation.py` and `test_ratchet_2.py` are preserved.
`test_ratchet_3.py` adds independent 252-point target and tensor checks,
finite-spin ED, complex/gauge and tolerance-edge checks, full public/trusted
agreement, NPZ/symlink rejection, and v3 regression coverage. Test reports and
quarantined bytecode belong only in `adversary/ratchet_3/`.

The public baseline is the previously passing v3 tensor only, with no prior
construction source. It fails v4. Solvability of v4 is unknown; checker
validation is not a feasibility claim and does not launch fresh attempts.
