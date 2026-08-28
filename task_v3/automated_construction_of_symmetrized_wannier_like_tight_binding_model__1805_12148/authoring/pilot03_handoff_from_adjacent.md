# Handoff to the pilot03 workflow builder

The parent assigned the adjacent builder **pilot02 full operator symmetry/response**. Please use only the pilot03 slot for disentanglement/localization. Do not build the EBR-search reserve as a fifth concept.

## Executable source and real data

- Existing official source clone: `authoring/sources/wannier-berri`, commit `e046ddc4bfe026ba1f9af2376f04babac5677425`.
- Start with `tests/test_wannierise.py::test_sitesym_Fe`, lines 174 onward. This is an actual frozen-window + symmetry-adapted localization regression, not a proposed algorithm.
- Stored numerical inputs: `tests/data/Fe-444-sitesym/Fe.{amn,eig,mmn,chk,bkvec}.npz` and `Fe_TR={True,False}.sawf.npz`, plus `Fe.win`. The overlap file is 11,897,150 bytes; the whole required input set is small enough to retain all bands and all 64 mesh points.
- The test loads `WannierData.from_npz(seedname=.../Fe, files=['amn','eig','mmn','chk'])`, attaches the symmetry object, applies the selected window mode, and calls `wannierise(sitesym=True, localise=True, num_iter=40, conv_tol=1e-6, mix_ratio_z=1, parallel=..., savechk=False)`.
- Use a serial call (`parallel=False`) before attempting the full parametrized pytest file. The global conftest imports unrelated systems and is unnecessary.
- The private reference source is `wannierberri/wannierisation/wannierise.py`, `symmetry/sawf.py`, and `symmetry/sawf_kirr.py`. The tests contain exact spread references, symmetry equalities, center checks, and a DFT band comparison.

## Artifact hygiene and independent bottlenecks

Inspect `.chk.npz` keys before passing it to participants. Preserve lattice/k-mesh metadata but reset or omit any already-optimized gauge unless the task is explicitly a restart/refinement task. Keep target spread arrays and `Fe_bands_pw.dat` evaluator-side. The initial `.amn` and overlap/eigenvalue arrays are the defensible pre-solution state.

Score frozen-band/subspace retention independently from symmetry-adapted localization. Neither matching sorted eigenvalues nor one final group average establishes successful localization. Compare gauge-invariant projectors/centers/spreads and symmetry constraints rather than an arbitrary elementwise gauge.

The smaller genuine fallback in the *same* pilot03 concept is `tests/data/diamond/` with `test_wannierise`. Its 4-WF/8-k-point reference spread is `0.39864755`, but it is a smoke/debug aid rather than a replacement for the full Fe problem. Avoid packaging this target in the participant directory.

## Environment/version warning

System Python is 3.10, while this source declares Python >=3.11. Managed interpreters already exist at `/srv/home/xuandong/.local/share/uv/python/cpython-3.12.10-linux-x86_64-gnu/bin/python3.12` and the corresponding 3.11 path. The adjacent builder is creating **`authoring/wb_reference_env`** with Python 3.12 and the pinned source plus symmetry extra; ask the parent for its readiness rather than modifying it while reference generation is running. Use your own environment if additional changes are needed.

Do not infer the current package version from GitHub's release banner: PyPI is 26.7.0 (July 14, 2026), whereas GitHub `/releases/latest` reports v1.7.0. The source pin is the oracle. Do not install all test extras: that needlessly adds GPAW, unrelated model packages, and distributed execution. Newer `irrep` itself has sizeable transitive dependencies, so reuse the verified private environment where possible.

## Primary URLs

- https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/tests/test_wannierise.py
- https://github.com/wannier-berri/wannier-berri/tree/e046ddc4bfe026ba1f9af2376f04babac5677425/tests/data/Fe-444-sitesym
- https://github.com/wannier-berri/wannier-berri/blob/e046ddc4bfe026ba1f9af2376f04babac5677425/wannierberri/wannierisation/wannierise.py
- https://www.sciencedirect.com/science/article/pii/S0010465522003642

This handoff identifies an existing executable test; it is not a claim that pilot03 has been built or run by the adjacent builder.
