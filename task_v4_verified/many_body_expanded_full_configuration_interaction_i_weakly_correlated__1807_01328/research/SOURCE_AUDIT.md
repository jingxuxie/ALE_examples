# Source audit

Access date: **2026-08-28** (America/Los_Angeles). Primary-source, bounded research;
no numerical experiments, local-runner validation, or fresh-agent attempts.
Source IDs and exact artifact/API URLs are recorded in [sources.json](../sources.json).

## Seed and task boundary

**S1:** Eriksen and Gauss, *Many-Body Expanded Full Configuration Interaction. I.
Weakly Correlated Regime*, [arXiv:1807.01328v2](https://arxiv.org/abs/1807.01328v2),
revised 2018-10-15; [journal DOI](https://doi.org/10.1021/acs.jctc.8b00680).
The 38-page preprint PDF was inspected at these anchors:

- **Section 2, Eq. 3:** virtual-orbital decomposition of correlation energy.
- **Section 2.1, Screening, Eqs. 4–8:** cancellation can falsely satisfy a
  successive-energy stopping rule; accumulated same-sign increments can matter.
  Parent/subtuple screening determines which child calculations remain accessible.
- **Section 2.2, Recent Advancements, Eq. 9:** intermediate-base expansions require
  compatible convergence behavior.
- **Section 4.1, Screening Revisited, Tables 1–2 and Figures 2–3:** water examples
  show sensitivity to screening and finite subsolver precision, including apparent
  divergence for some base-assisted expansions with insufficient screening.

The main session's **E: adaptive CAS query**, **B: false-convergence witness**, and
**D: tail prediction** are task adaptations on **explicit paired-electronic model
systems**, not paper datasets, ab initio molecular benchmarks, or PyMBE results.
Their motivation maps respectively to S1 Section 2.1; S1 Sections 2.1/4.1; and S1
Sections 2.1/4.1 plus S3 Section 2.3. This is a provenance mapping, not validation
of the main session's model, oracle, difficulty, or outcomes. Direct formula
implementation, API wiring, and reproduction of published numbers are excluded.

## Inspected follow-up observations

- **S3 — [2406.11343v1](https://arxiv.org/html/2406.11343v1), Sections 2.1–2.3, 4–5:**
  subset CASCI root ordering can change; incorrect roots impair recursive
  convergence. Reference enlargement and clustering trade fewer increments for
  more expensive subproblems. Fixed-percentage pruning forces termination even
  without convergence. Adaptive error estimates use empirical increment decay,
  distributions, and cancellation; the authors report rare bound exceedances on
  small systems, tail effects, and solver/roundoff contamination. Section 5 makes
  strict bounds conditional on the empirical relationships: no universal
  certificate for B/D, nor evidence that these task instances will be difficult.
- **S4 — [2403.17836v2](https://arxiv.org/html/2403.17836v2), Sections 4.1.3–4.1.4,
  4.2 and 5:** truncated MBE-CASSCF lacks exact active-orbital rotation invariance;
  natural-orbital results can oscillate with tighter screening. Active–active
  optimization failed for tetracene in the reported tests. Large quintet reference
  spaces made increments beyond order six memory-prohibitive; multiple local
  minima were not addressed. These are follow-up-specific observations.
- **S5 — [2407.21576v1](https://arxiv.org/html/2407.21576v1), discussion around
  Figure 1:** equal CASCI energies do not imply equal recursive increments unless
  the necessary subtuple equivalences also hold. Near-symmetry errors can amplify
  through recursion, motivating numerically exact symmetrization. This supports
  a possible audit mode, not an observed defect in the main session's models.

## Official repository and historical fixes

**S6:** [official PyMBE](https://gitlab.com/januseriksen/pymbe), GitLab project
`1656775`; observed `master` head **`625495802c2f29868e4b2605dd4784f327a64a6b`**,
committed **2024-06-24**. Inspected README, screening/clustering source excerpts,
eight recent commit records, and two full fix diffs through read-only public API
requests. Browser access was uneven; approved network reads succeeded without
cloning or saving source artifacts. The README already advertises reference
selection, clustering, and adaptive screening. This is not a verified 2018 code
snapshot or an exhaustive code review.

- **S7 — [788ca41cb646b7725abeae690da76354080b98c3](https://gitlab.com/januseriksen/pymbe/-/commit/788ca41cb646b7725abeae690da76354080b98c3), 2024-06-22:**
  the diff adds `symm_eqv_inc_clusters` and passes each symmetry-related tuple's
  cluster decomposition into increment subtraction instead of reusing one layout.
- **S8 — [9e0794b584c8bb12d8cdc19e438a68ab16648cca](https://gitlab.com/januseriksen/pymbe/-/commit/9e0794b584c8bb12d8cdc19e438a68ab16648cca), 2024-06-22:**
  clustering gains a zero-pair-correlation guard that raises `RuntimeError` and
  advises increasing `screen_start`. Both findings describe historical fixes,
  not reproduced failures or claims of current unfixed bugs.
- **S9:** public all-state issues, releases, and tags API queries each returned
  `[]`; no discussion or release evidence was obtained. This does not establish
  absence of private/deleted material or absence of defects.

## Data and access limitations

**S2:** the seed's arXiv record lists ancillary **`si.pdf`**. Its Supporting
Information statement (PDF page 26) describes coordinates, reference energies,
and solver settings; this sidecar did not successfully retrieve the ancillary
contents. Public paper tables and the listed SI must not be described as absent.

No separate, machine-readable original-paper dataset, integral archive, or
complete increment/query trace was located in the bounded paper/repository and
exact-ID/DOI searches. This is **not located**, not proof of nonexistence. No
original numerical artifact was imported into E/B/D by this sidecar. Background
records 1905.02786, 1910.03527, and 2008.03610 were opened at metadata level only;
they supply no additional verified mechanism here. The main session retains
responsibility for construction, execution, evaluation, and final concept choice.
