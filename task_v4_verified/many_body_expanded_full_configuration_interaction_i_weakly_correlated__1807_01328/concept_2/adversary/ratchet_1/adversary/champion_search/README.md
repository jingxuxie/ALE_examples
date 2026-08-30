# Private challenge of the actual fresh B2 champion

This is privileged generation evidence, not participant material. It does not
change the solved generation-2 task or its official result. The earlier bounded
portfolio is stopped and archived, not resumed. No generation-3 packet or frozen
target is created here.

Run `python -B challenge.py` in this directory, with stdin closed. It snapshots the
actual final `attempts/v_2/witness.json` and main's official report, archives the
earlier portfolio, validates two independent Hamiltonian constructions, and saves
the complete reproducible assay. A rerun reuses completed result cells.
`python -B challenge.py --tests-only` runs independent energy, malformed-input,
common-energy-shift, common-density-shift, and deterministic-repeat tests.
`python -B challenge.py --reproduce examples/EXAMPLE.json` reconstructs and fully
verifies an example, including all seven MBE orders and closure.

The model remains the original three-pair, ten-spatial-orbital seniority-zero
effective Hamiltonian. Its diagonal is the sum of occupied pair energies and
unordered pair-density interactions; off-diagonal pair transfers have explicitly
checked spin-fermion signs. Full-coefficient uncertainty means the 100 independent
coefficients of this restricted model: ten pair energies, 45 real pair-transfer
coefficients, and 45 density coefficients. It does not mean all integrals of an
unrestricted ab initio electronic Hamiltonian, or preserve Coulomb representability
that the original effective testbed did not impose.

The grid uses 128 iid 100-coordinate uniform rows, paired across eight families
and radii 0.001, 0.002, 0.003, 0.005, 0.010 Eh. A separate 512-row confirmation
assay is declared in advance at the original 0.001 Eh radius for VV-only noise,
previously fixed controls, and all coefficients. Each draw is centered on the
unchanged champion, not on a previous draw. Upper-triangle transfer and density
coefficients are uniform on the intersection of the original symmetric bound and
the local radius interval, then mirrored exactly. Pair energies are independently
uniform on their local intervals. Matrix diagonals stay zero. Physical failures
are counted, never rejected and replaced. Common rows enable paired comparisons;
different cells must not be pooled as independent samples.

All original weak-reference, spectral-gap, diagonal-margin, triple-parent, missing
tail, and ratio thresholds remain unchanged. Every case uses independent matrix
construction, two eigensolver paths, and direct versus recursive increments.
Representative passing and failing examples receive complete order-seven closure
checks. Failures are clustered as numerical, physical, material tail, parents,
and ratio. A lost triple gate means that perturbed Hamiltonian is no longer this
particular screening counterexample; it does not invalidate the original witness
or prove a screening theorem. Any target proposal is private and awaits approval.
