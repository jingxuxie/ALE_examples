# Primary-source grounding

Inspected on August 28, 2026 using the arXiv primary full texts.

- Higgott and Gidney, **Sparse Blossom: correcting a million errors per core
  second with minimum-weight matching**, arXiv:2303.15933v2, January 14, 2025.
  Sections 2.1–2.3 explicitly formulate detector/observable matrices and known
  mechanism priors, restrict the matching construction to independent graphlike
  mechanisms (at most two detectors), and use log-odds edge weights.
- Takou and Brown, **Estimating decoding graphs and hypergraphs of memory QEC
  experiments**, arXiv:2504.20212v1, April 28, 2025. Sections II.1–II.2 discuss
  inference from syndrome statistics, why the graphlike two-point procedure
  does not separate higher-order events, and extensions using multipoint
  information. Their simulations and inference assumptions are distinct from
  this benchmark.

Source locators: `https://arxiv.org/html/2303.15933v2` and
`https://arxiv.org/html/2504.20212v1`.

This task is a new synthetic experimental-design benchmark inspired by those
modeling requirements. Shared shot modes, exposure controls, categorical
footprints, budgets, and rate distributions are author-designed. No claim is
made that these interventions exist on hardware, that the data constitute a QEC
circuit, that inferred rates imply a particular logical error rate, or that this
reproduces either paper. The supplied analytic likelihood is exact for the stated
toy process; it does not rely on a graphlike approximation.
