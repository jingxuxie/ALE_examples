# Private author evidence

The author searched 800 pilot profiles and 6,000 refinement profiles. The
selected proxy is the average of three 128-level windows at energy densities
0.49, 0.50, and 0.51 versus exact ranks [308,616). Exploratory broader-window
proxies were discarded before selecting the final, unchanged criteria.

The privileged witness is `champions/witness.json`, with its reproduced
report in `champions/evaluation.json`. It has core 0.063160392066314 and
worst-family mean 0.058752787089975445, and passes all primary criteria.
Four of 32 deliberately selected calibration finalists passed; this is not
a fresh-agent success rate. The fields originate in a noisy two-domain
structured search, not an analytic solution or a symmetry-sector mixture.

The default baseline, seed 1992, has core 0.008669727799609183 and worst-family
mean 0.006029969353057357. It is valid but fails. Its witness and reproduced
report are `baseline_witness.json` and `baseline_evaluation.json`.

Existing validation rejects 40 malformed/static controls before any
diagonalization, reproduces the champion's scores exactly on repetition,
matches the shared root Hamiltonian exactly, and finds maximum per-member
evr/evd discrepancy 1.723066134218243e-13. See `validation.json` for the
recorded environment and resource measurements. The champion evaluation
uses 33 full spectra, one worker, and one BLAS thread.

A separate post-selection diagnostic of 128 additional perturbations gives
core 0.05863796191624983 and worst-family mean 0.05270861466260535. All its
family means exceed the claim's 0.05 bound, but its core does not meet the
stronger primary 0.060 certificate. It is neither a grading condition nor
a claimed passing holdout certificate, and was not used for selection.

The main runner owns freeze and independent attempts. No fresh agents were
launched here; no concept_1 or concept_2 data were accessed. All private
searches stay in adversary/, and attempts/ remains reserved for fresh
sessions. At the user's request, no further experiments or validation were
performed for the final concise-TASK and report-alias edits.
