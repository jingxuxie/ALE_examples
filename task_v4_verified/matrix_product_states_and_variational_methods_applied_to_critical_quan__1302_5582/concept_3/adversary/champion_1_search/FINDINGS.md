# Champion 1 audit: final findings

Original D v1 is legitimately solved. No leakage or scoring loophole was observed; the solver reconstructs the Hamiltonian from public parameters and uses an efficient dressed onsite basis.

Fresh original-domain results: 360 independently seeded certified cases, five balanced 72-case batches (three IID, two edge-enriched). All original primary thresholds pass. Pooled score 0.999999999155; worst cell log-gap error 6.023e-09.

Per-batch solver CPU 8.575–9.561 s; wall 17.135–47.619 s; maximum solver RSS 70.9 MiB. CPU/RSS are measured in the trusted bootstrap, not inferred from bubblewrap's launcher.

Emptying training data, deleting all low-cutoff spectra, relabelling IDs/families and reversing input order leaves the numerical predictions identical. Only source-identical predict.py is staged; fresh labels, certificates and host paths are excluded.

New-generation pilots and measured control failures are recorded in FINAL_REPORT.json and extension_results.json. Unsupported v1 length/schema errors are not counted as scientific failures. Each accepted pilot has direct computed labels and cutoff/basis checks; an L4 case also has an independent full-Fock cross-check.

Concrete proposal: inhomogeneous parity-preserving L4/L6 chains, fully public physical parameters and low Fock cutoffs 4/6, original score tolerances and 30-CPU-second budget. See target_proposal.json. This is NOT a retroactive ratchet and is NOT ready to freeze: a complete new certified corpus and full-batch adaptive/sparse/MPS control tests are still required. Achievability is unknown.

No original participant assets or original evaluator files were modified. No fresh agents were launched. No hardness claim is made.
