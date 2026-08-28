# c03_mps author handoff

## Public freeze and layout

`participant/` contains the mission, full numerical contract, exactly two unlabeled small examples, and a standalone NumPy/SciPy exact/product baseline. It contains neither TeNPy nor the later ALPS MPS code. `attempt/` is initially empty and is owned by main's runner. No participant runner is launched by this sidecar.

The public artifact is a small ED/product starting point for the model capabilities present in the 2011 library, not a claim that this Python baseline was written by the original authors. It intentionally does not include a ready MPS implementation. No post-2011 code is disguised as a historical public artifact.

## Existing private solution and provenance

- Original release paper: <https://arxiv.org/abs/1101.2646v4>.
- Exact 2011 repository state: `c03821cf7f03ed652f64dad4e3b76d40ae379097`, 2011-05-23, <https://github.com/ALPSim/ALPS/tree/c03821cf7f03ed652f64dad4e3b76d40ae379097>. The historical DMRG interface is `applications/dmrg/dmrg/dmrg.h`. Main has the corresponding archive subset at `../private/sources/ALPS_20110523_subset.tar` relative to this concept root. The archive is not a reference solver for the new task.
- Official later method: <https://arxiv.org/abs/1407.0872v2>, with first MPS import `006cbc8ef2bc3e6abc080c0bc015b1a105751b0d` and paper-era snapshot `34688482fbc09fe7d359987f3e1e223fa07bfcb2`: <https://github.com/ALPSim/ALPS/tree/34688482fbc09fe7d359987f3e1e223fa07bfcb2/applications/dmrg/mps>. This is an existing later solution, not an author-invented tensor solver. Modern ALPS HEAD is NOT a suitable substitute: MPS was removed in commit `f21adf7e9d5edac90cc6a218d1710a0703d83e41` on 2026-07-03.
- Executable independent reference: TeNPy **v1.0.6**, commit **`b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04`**, <https://github.com/tenpy/tenpy/tree/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04>.
- Actual solver: `tenpy/algorithms/dmrg.py`, `TwoSiteDMRGEngine`; tensors/contractions: `tenpy/networks/mps.py`; Bose-Hubbard model: `tenpy/models/hubbard.py`; spin site definitions: `tenpy/networks/site.py`; graph-to-MPO interface: `tenpy/models/model.py`.
- Exact pinned source links: <https://github.com/tenpy/tenpy/blob/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04/tenpy/algorithms/dmrg.py>, <https://github.com/tenpy/tenpy/blob/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04/tenpy/models/hubbard.py>, <https://github.com/tenpy/tenpy/blob/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04/tenpy/models/model.py>, <https://github.com/tenpy/tenpy/blob/b5408eaf11d3f3ed8fc71de96a8b681c8e4c7c04/tenpy/networks/mps.py>.

`reference/generate.py` only maps the declared Hamiltonians to these existing models/MPO APIs, prepares conserved sectors, invokes the existing two-site DMRG engine, and calls existing expectation-value contractions. It does not implement an MPS optimizer. A private copy of the pinned dependency is under `reference/vendor/tenpy`; its Cython extension can be compiled in that copy without modifying main's source tree or any global installation. The original dependency license remains in that copy.

## Cases and independent bottlenecks

`challenge_pool/manifest.json` records six core and six challenge cases, two per family in each split. The physical inputs are deterministic authored benchmark instances, not experimental data or reproductions of an exact published table.

- Spin-one chains: 40/56 core sites, 48/64 challenge sites. Nonlocal string correlators and the Sz=2 minus Sz=0 sector difference accompany local correlations and energy. The sector gap is deliberately not mislabeled the first open-chain gap, since Haldane edge states matter.
- Spin-half ladders: 40/56 core sites, 48/64 challenge sites. Rung/leg ordering, inhomogeneous anisotropic exchange and fields, longitudinal versus transverse correlators, and an Sz=1 sector excitation require distinct handling.
- Bose-Hubbard chains: 32/40 core sites, 36/48 challenge sites. Local cutoffs 3/4, nonuniform hopping/potentials, particle/hole sectors, off-diagonal coherence, and connected density correlations are separately specified. The finite local cutoff is part of the Hamiltonian, not an uncontrolled approximation.

One sufficiently capable MPS package can solve these models. The anti-compression justification is realistic exponential Hilbert-space size plus independent sector preparation, operator/convention correctness, variational convergence, and different correlation contractions. It is not a claim that every generic tensor method fails. ED, product states, uniform-energy interpolation, and an energy-only answer cannot satisfy all components.

## Reproduction

Run commands from `c03_mps/`. They never launch a participant agent.

```
PYTHONDONTWRITEBYTECODE=1 python private/reference/cases.py
PYTHONDONTWRITEBYTECODE=1 python private/reference/generate.py --split small
PYTHONDONTWRITEBYTECODE=1 python private/reference/generate.py --split all --workers 6
PYTHONDONTWRITEBYTECODE=1 python private/reference/audit.py
python private/evaluator.py --submission /path/to/submission --split core --report /path/to/report.json
```

Do not rerun `cases.py` after public freeze unless intentionally starting a new concept version: it rewrites the same two public examples as well as private case files. Individual references can be generated with `--case CASE_ID --split core|challenge --chis 64,128,192 --workers 1`. All reference workers set BLAS thread counts to one in their own process environment only.

## Reference validity and stored artifacts

- `reference/validation/small_exact.json`: six independent full-Hilbert-space sparse/dense diagonalization checks versus TeNPy, two per family; all sector energies/gaps and all correlation conventions are checked, including string endpoints/signs and bosonic connected subtraction. ED residuals are recorded.
- `reference/data/*.json`: strong outputs, weak product outputs, exact input hash, source pin, every bond-dimension stage, per-sector energies/charges/norm errors/sweep histories/times, and final convergence differences.
- References require agreement between successive chi values in energy per site, the actual gap, AND the largest correlation difference. Energy convergence alone never marks a reference ready. Default chi stages are 64, 128, 192, stopping after the first converged pair. The high-chi states are warm-started, so this is a practical convergence check, not a rigorous ground-state error certificate.
- `reference/generation.log`, `reference/logs/`, `reference/tenpy_build.log`: generation and dependency-build evidence.
- `reference/validation/artifact_audit.json`: reference self-score, weak score, perfect-energy-only failure, zero-correlation diagnostic, invalid-output behavior, norm and final-sweep checks, and input hash validation for all 12 cases.

The evaluator refuses missing/unconverged/mismatched author references with exit 2. An incomplete author reference is never scored as a participant failure.

## Evaluation and isolation

The score is `0.20*energy + 0.30*gap + 0.50*mean(correlation-kind scores)`. Each component is `1/(1+(RMS_error/scale)^2)`. Scale combines a physical absolute floor and a fixed fraction of the weak-to-strong RMS distance; energy is compared per site. Correlation kinds receive independent scores, and tiny individual reference entries never appear in denominators. Time is recorded but is not a graded component below 600 seconds.

Set `ALPS_EVAL_WRAPPER` to main's shared `private/sandbox_exec.py` for actual submission execution. The evaluator honors that wrapper, copies only one physical input into an isolated temporary directory, and reads `_resource.json` before cleanup. It supplies an 8192 MiB memory cap and four threads to match the public target. When submission is a directory, the wrapper receives an anchor path INSIDE that directory so the shared wrapper's parent-directory mount cannot accidentally expose the entire concept root. The ordinary solver command receives only its own script, temporary input, and temporary output paths. No private reference path or hidden pool path is passed to it.

Without the wrapper, this evaluator is a development harness, not a security boundary. Main is responsible for the escalated bwrap invocation and agent/attempt isolation.
