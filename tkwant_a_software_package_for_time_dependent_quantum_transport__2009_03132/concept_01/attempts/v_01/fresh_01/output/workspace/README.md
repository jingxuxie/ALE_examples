# Portable scattering/source transport

The grading entry point is `../run.sh`. It preserves the caller's working
directory and accepts `--cases FILE --output DIRECTORY --config NAME`.
Production, conservative and occupation-averaging ablation are supported.
The solver does not read the bundled development cases when executing a batch.

Active numerical path:

1. `model.py`: complex matrix decoding, orientation, finite sparse embedding.
2. `scattering.py`: independent lead occupations, adaptive continuum quadrature,
   localized sectors, shallow-bound infinite-tail normalization and diagnostics.
3. `protocols.py`: all additive and phase-drive semantics.
4. `source_evolution.py`: correction-only source evolution, state batching.
5. `observables.py`: absolute density and incoming oriented current.
6. `simulate.py`: actual numerical configurations and response-only boundaries.

Retarded surfaces and incoming weights are not flattened into a wide-band bath.
The full specified lead cell and intercell matrices are retained. Surface
broadening is a numerical retarded regularizer, not a physical relaxation rate.
`accuracy_warning` is a useful failure alarm, not an exhaustive certification.

`../report.md` states the method, measured evidence and limitations.
`check_tests.py` runs the pytest-compatible assertion tests without requiring
pytest itself. `experiment.py`, `qualification.py`, `finalize.py` and
`audit_artifacts.py` reproduce and validate the evidence package.

`legacy_transport/` and `legacy_driver.py` preserve the unrepaired candidate for
reproduction only. `upstream/` contains licensed historical provenance and is
never imported by the active solver.
