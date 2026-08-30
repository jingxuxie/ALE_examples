# Ratchet-3 private search provenance

Inspected on 2026-08-28. Writes are confined to this directory. Participant,
trusted evaluator, root status, and prior archives are not modified.

## Permitted artifact evidence

- `../../attempts/v_6/state.npz`, SHA256
  `036e6d9068edb0ac38ce3d3fc4bd935dffcd0b86189f5af25bc4b2f46dde0bea`.
- `../../attempts/v_5/state.npz`, SHA256
  `793cc670ac2326e141a6db3c285c597b0839d50a28e90448a5f82780dc6e6c94`.
- Their completed audit/evaluation JSON and submitted summary JSON. No
  construction source or session log is needed or read for this search.
- The frozen `../../evaluator/evaluate.py` is invoked independently on both
  artifacts, and its complete scores are retained in this directory.
- The existing `../fourpoint_search/search.py` and `fourpoint.py` supply the
  unchanged 15,133-quartet mesh and certified four-point machinery. The
  wrapper redirects every output to this new directory before executing
  either scan. Historical output key names containing `v2` refer to the
  legacy helper; the independently invoked evaluator reports the actual
  frozen `critical-vacuum-v3` contract.

Main's scientific champion choice is v6: lower energy excess and materially
smaller errors in each two-point family, with essentially equal composite
precision. Both core scores saturate at one, so that scalar alone cannot
distinguish the witnesses. Both artifacts are retained as comparisons rather
than treating a failure of the weaker artifact as a failure of the champion.

## Primary sources inspected

- Mbeng, Russomanno, Santoro, *The quantum Ising chain for beginners*,
  SciPost Physics Lecture Notes 82 (2024), Section 8. The inspected HTML
  develops the Jordan-Wigner strings and Wick determinants and gives the
  critical elementary contraction `-2/[pi*(1+2(j-j'))]`.
  https://arxiv.org/html/2009.09208v2
  https://doi.org/10.21468/SciPostPhysLectNotes.82
  Equation numbering differs between PDF and the currently rendered HTML;
  the section and explicit contraction, not a fragile equation number, are
  the reference. The publisher landing page was access-denied on direct
  retrieval; the primary arXiv manuscript was readable.
- Yizhuang Liu, *Spin-operator form factors of the critical Ising chain and
  their finite volume scaling limits*, arXiv:2601.00751v4, Sections 1-2.
  This supplies context for NS/R sectors and the Cauchy structure. Its
  Hamiltonian has different prefactors and a different field sign, so its
  energy normalization is not copied into our target.
  https://arxiv.org/html/2601.00751v4
- *Order parameter statistics in the critical quantum Ising chain*,
  author-hosted manuscript, equation (6): ordered equal-time multipoint
  critical spin correlators have a product structure in the continuum.
  This motivates higher moments but is **not** used as an exact finite-lattice
  target; our numerical certificates use the lattice Cauchy determinant.
  https://austenlamacraft.github.io/mwe/assets/pdfs/papers/Ising.pdf

The six-spin factorization and stable composite-cumulant formula are derived
in `TARGET_DERIVATION.md` and independently checked against direct spin ED.
No passing tensor for any proposed new target is claimed by this search.
