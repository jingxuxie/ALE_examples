# Valid-neighbor failure family and radius choice

This is the second ratchet, not a change of primary mode. The sole objective
remains a Hamiltonian-derived unphysical real-orbital population prediction,
now robust over a fixed public finite integral stencil.

Main's `adversary/generation_2_stress/report.json` uses Gaussian symmetric
integral perturbations projected into the original domain. It finds large DAD
and energy-error failure clusters. Across 384 probes for each old fresh witness,
DAD fails in 266 and 165 cases and energy accuracy in 218 and 163 cases.
These are genuine valid-Hamiltonian responses, not invalid-input rejections.

The worker separately calibrated 120 orthonormal symmetric pair-matrix axes,
both signs plus the base, at radii 0.001, 0.002, and 0.003. At **0.001** both old
fresh champions already fail in valid neighbors; all 241 points are in domain:

- The large witness has maximum DAD 0.0124271 and energy error 0.000593944,
  with 221 DAD and 122 energy failures; its minimum population violation remains
  0.590125. Thus losing the target itself is not the explanation.
- The second witness has maximum DAD 0.00128130 and energy error 0.000244053,
  with four DAD and 30 energy failures; minimum population violation is 0.155754.

The smaller proposed radius, 0.001, is therefore sufficient; there is no need to
choose a larger and potentially overrestrictive scale. Full results, including
separate domain counts and conservative interior-shift probes, are in
`stencil_calibration.json`. No out-of-domain case is counted in a physics cluster.

The stencil is deterministic, fully public, and normalized by pair-matrix
Frobenius norm. There are no secret directions and no continuum-ball claim.
Each point keeps the original canonical-HF counterterm prescription and its own
unchanged 65-point ground-connection path. The resource limit, not any original
physical bound, is increased from 45 to 900 seconds to cover all 241 certificates.

This strengthens a task-supplied screening heuristic motivated by the original
CCSD-RDM and DAD sources. Neither paper is credited with a robust-physicality
theorem. Absence of a searched witness would not prove impossibility. Private
warm-start feasibility and fresh-agent difficulty must be reported separately.
