# Private author evidence

Do not include this directory in participant bundles. All pilot and search
records were moved here before freeze; `../attempts/` contains no author
searches or fresh agent sessions.

`calibrate.py` screens 800 deterministic profiles and tests 46 shortlisted
profiles on preliminary perturbations. `refine.py` screens another 6,000
profiles, combining an independent structured scan and mutations of pilot
leaders, then checks 166 preliminary finalists. These scans compare several
candidate proxies; only the final three-128-level-window proxy is graded.
`protocol_calibration.py` writes the fixed SHA-derived public offsets and
checks 32 finalists. Its protocol-writing entry point refuses to run after
`freeze.json` exists. It chooses the author champion from the public protocol
before examining the separate 128-perturbation diagnostic holdout.

`validate_package.py` performs static-input, isolation, indexing,
reproducibility, root-helper, and alternative-LAPACK-driver audits.
The preparatory `finalize.py` was not used to freeze this package; the main
runner owns final freeze and launch. Do not rerun author searches or
calibration against the live package. All generator pools are capped at eight processes and all
linear algebra is single-threaded. No LLM sessions or external solvers are
launched by these scripts.

`baseline*_witness.json` and their `.search.json` summaries are conventional
unstructured baselines, not fresh-agent attempts. `champions/` contains
private author evidence, not a participant-visible seed or solution.
