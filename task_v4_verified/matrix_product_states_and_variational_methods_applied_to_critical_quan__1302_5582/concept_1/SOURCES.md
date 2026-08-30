# Sources and scope

- Ashley Milsted, Jutho Haegeman, Tobias J. Osborne, *Matrix product states and
  variational methods applied to critical quantum field theory*, arXiv:1302.5582v3
  (15 May 2014), Phys. Rev. D 88, 085030. Source consulted through
  `https://arxiv.org/abs/1302.5582` and `https://arxiv.org/pdf/1302.5582`.
  This is the scientific motivation: variational MPS for lattice phi4, finite local
  Hilbert spaces, convergence near a transition, and a product-state comparison.
- The finite open chains, fields, basis frequencies, requested parity sectors,
  resource limits, scoring, cases, and implementations here are newly authored
  benchmark design, not data or a reproduction of the paper's infinite-chain
  numerical results. No reference code was copied from the paper or a tensor library.
- Projected powers use padded oscillator matrices. The definition in
  `participant/input/CONTRACT.md` and the independently tested public contractor
  are the numerical specification; no renormalization convention is implicit.

Generation-time baseline and teacher runs provide correctness/achievability evidence
only. They do not establish that the target is difficult or attainable within the
participant budgets. That requires main's isolated attempts after review.
