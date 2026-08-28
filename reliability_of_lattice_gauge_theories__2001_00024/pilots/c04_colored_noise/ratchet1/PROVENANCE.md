# Provenance and scientific boundary

The main source is Halimeh and Hauke, *Reliability of lattice gauge theories*,
arXiv:2001.00024. Fig. 3 and the energy-protection discussion distinguish small
gauge leakage from observable drift near V/lambda^2; the methods paragraph notes
direct exponentiation for extremely long evolution. The follow-up is Kumar,
Hauke, and Halimeh, *Suppression of 1/f noise in quantum simulators of gauge
theories*, arXiv:2210.06489, the actual full 12-page paper. Appendix B supplies
the explicit secular formalism and the protected early gamma*t/V^beta guide.
Sources checked: `https://arxiv.org/pdf/2001.00024` and
`https://arxiv.org/pdf/2210.06489`.

The ratchet uses exactly the original c04 public mathematical model, with an
explicit late-time range. Finite-band inference, infrared regularization,
correlated baths, actuator budgets/crosstalk, and the dimension-64 ring are
benchmark-author extensions, not measured device data or reproduced paper figures.
This is the defined weak-coupling Markov/secular effective model, not exact
non-Markovian classical 1/f trajectories. The time-grid risk is the public
discrete trapezoidal objective, not a claim of convergence to a continuous-time
average over all rapid oscillations.

Private source snapshots originate in the completed original author reference
and validated author-only late-time probe. They are NOT official paper-author
code and are NOT the initial participant submission. Snapshot hashes and original
paths are recorded in `private/snapshot_manifest.json`. Ratchet execution is
self-contained except for the mandatory common task-root isolated runner, whose
path and hashes are recorded by the evaluator. The original pilot, its attempt,
and the late-time probe are preserved.

The snapshot manifest records the initial copies, before ratchet-only amendments:
the public protocol adds the late-time range, isolation limits and actual weak
anchor definition; the independent numerical cross-check adds controlled
subdivision for the public finite-frequency clustering tolerance. The target
engine and scoring source remain byte-identical. Final current hashes are in
`private/freeze.json`; no amended helper is presented as a byte-identical copy.

One reserved signed-protection action has a 1.96e-9 within-block frequency spread
under the unchanged 1e-8 frequency rule. Blindly assuming exact commutation would
fail the original conservative guard: 0.5*T^2*||[D,C]||F = 9.76e-7. The centered
block exponential keeps the exact coherent diagonal and all dissipator entries.
The independent dissipator-eigh check now uses centered symmetric product steps
only when needed, with a conservative commutator subdivision bound of 1e-10 per
block. No case, generator, scoring threshold, or residual tolerance was changed
to hide this effect. The aggregate refined indicator is at most 6.05e-10, and the
maximum observed full-density disagreement is 4.58e-13. This is a controlled
finite-cluster correction to the commuting check, not a claim that the clustered
generator commutes exactly at infinite precision.

The bounded probe established a specific initial-solver worker timeout at T=10000
while the independently cross-checked reference succeeded. It did not establish
that all solvers, a specialist spectral solver, or a fresh agent will fail.
The precommitted anti-compression/rejection rule is in `ANTI_COMPRESSION.md`.
