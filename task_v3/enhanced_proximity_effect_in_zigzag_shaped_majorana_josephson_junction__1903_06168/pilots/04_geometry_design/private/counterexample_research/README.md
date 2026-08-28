# Source-grounded reference pool: not an accepted counterexample

Source: https://zenodo.org/records/7266609 (v2, created 31 October 2022; MD5 `750859a1c2c847acdff9eda0ed24873e`), accompanying https://arxiv.org/abs/2205.05689 and SciPost Phys. 14, 047 (2023). Official notebook code cells are preserved locally; no optimizer is executed.

`official_grid.json` derives the 4×4 optimization grid from the plotting notebook and its flat storage order from `batch_gaps` in the generation notebook. Probe indices 0,4,8,12 span the lowest published field, EZ=0.5 meV; indices 1,13 add two controls at EZ=5/6 meV. These remain inside the published mu=10–15, EZ=0.5–1.5 region.

Included author artifacts are unmodified epoch-800 `homogeneous_filtered`, `robustness_checks/seed_1`, and `robustness_checks/zigzag`. All must pass the existing manufacturing constraints unchanged. The disconnected/non-mirrored final `no_mirror_sym` artifact is excluded, never repaired or used to manufacture hardness. JSON only renames `sc_bot`; raw NPZ masks preserve original keys and values. Hashes, exact epochs, manufacturing checks, and counts of non-graph columns are in `manifest.json`.

The initial scout uses at most 12 one-thread workers on the last allowed CPUs, each with a 2 GiB address-space cap. Each completed measurement uses all 51 half-zone momenta plus independent class-D topology. The initial scout clock is capped at approximately 10 minutes including preparation; incomplete measurements are explicitly marked and never treated as references.

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -B scout.py --workers 12
```

Main can subsequently measure an already submitted geometry on the identical saved points, without a fresh agent or changing the initial evaluator:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -B scout.py --geometry /absolute/submitted_geometry.json --workers 12 --wall-seconds 540
```

No submitted geometry is compared by this initial scout. Reference-reference improvements alone do not prove superiority to the low-dimensional profile family. Do not turn pointwise maxima across different masks into a fictitious single robust design. Main owns the old-solver comparison, root-cause decision, acceptance, and any later ratchet.
