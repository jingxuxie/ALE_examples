# Existing author-design probe inventory

**No counterexample is claimed.** Main must compare completed submitted geometries on these identical points before any acceptance or ratchet decision.

## Official grid

`generate_plots.ipynb` code cell 9 defines mu = linspace(10,15,4), EZ = linspace(0.5,1.5,4). `generate_data.ipynb` code cell 7 orders `product(mu_pts, EZ_pts)`: flat index = 4*mu_index + EZ_index. The 16 exact points and notebook hashes are in `official_grid.json`. This is not the separate 30x30 phase-diagram grid.

## Unmodified artifacts

All included masks are exact epoch 800 of 801 snapshots in Zenodo 7266609 v2. Raw NPZ arrays, canonical geometry JSON, per-member hashes, morphology, and unchanged manufacturing checks are saved. The seed and zigzag robustness archives contain no stored 16-point gap arrays; their values below are fresh physical measurements, not claimed archived values. `no_mirror_sym` is excluded and never used as a hard reference.

## Full 51-momentum probes

| Grid index | mu / EZ (meV) | existing_reference | seed_1 | zigzag |
|---|---|---|---|---|
| 0 | 10 / 0.5 | 0.09866529 (Q=-1) | 0.10877763 (Q=-1) | 0.10824434 (Q=-1) |
| 4 | 11.666667 / 0.5 | 0.10078063 (Q=-1) | 0.10807575 (Q=-1) | 0.10329400 (Q=-1) |
| 8 | 13.333333 / 0.5 | 0.10718589 (Q=-1) | 0.10545518 (Q=-1) | scout_timeout |
| 12 | 15 / 0.5 | 0.11028756 (Q=-1) | 0.09911387 (Q=-1) | 0.10985270 (Q=-1) |
| 1 | 10 / 0.83333333 | scout_timeout | scout_timeout | scout_timeout |
| 13 | 15 / 0.83333333 | scout_timeout | scout_timeout | scout_timeout |

Completed 11/18 measurements. Existing-reference agreement with the stored official 16-grid values: maximum error 1.6653345369377348e-16 meV.

Non-topological or incomplete values are not eligible strong references. Pointwise maxima across different author masks are an inventory, not a single realizable robust design. A public-screen score near 0.18 at different operating points cannot substitute for the pending submitted-geometry comparison. The initial participant, evaluator, challenge pool, and attempt are unchanged.
