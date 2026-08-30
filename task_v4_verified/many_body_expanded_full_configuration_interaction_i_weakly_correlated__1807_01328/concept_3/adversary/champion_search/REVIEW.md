# Review and isolation boundary

The reviewed submission is the complete 251-line `attempts/v_1/reconstruct.py`. Its numerical entry point is `reconstruct(features, generator)`. It reads only its in-memory feature dictionary and the supplied public-generator module. It performs singleton inversion, generalized-eigenvalue pair-root enumeration, local triple branch scoring, low-order consistency checks, and full inferred-Hamiltonian diagonalization. It does not open files, spawn commands, or access the network.

The module imports standard-library utilities, NumPy and SciPy. Its filesystem-loading/writing CLI is guarded by `if __name__ == "__main__"`; it is not invoked by this adapter. The loader `load_generator` is called only with `/input`, selecting the reviewed byte-identical public generator snapshot. The original hard-coded participant path is not visible inside the child.

The archived predictor and public generator are byte-identical to their original files. Checksums are recorded in `sandbox_input/source_hashes.json`, the private sampling manifest, and each launch record. No numerical lines, candidate filters, tolerances, branch selection, or fallback algorithms are changed. `replay_driver.py` is mechanical I/O adaptation only: load feature rows, call the unchanged numerical function, collect its result/diagnostics, and record exceptions without substituting another solver.

## Predictor process boundary

The submitted code executes only inside bubblewrap with separate mount, PID, user, and network namespaces, a cleared environment, and dropped capabilities. Read-only mounts provide `/usr`, the system dynamic-loader cache/alternatives, and the five-file feature/code input directory. A fresh output-only subtree is writable. `/tmp` and `/proc` are private; no home, repository, evaluator, labels, sampling seeds, or private score directory is mounted. The child verifies the absence of host/private paths and rejects forbidden label fields in its input archive. The parent passes no inherited file descriptors beyond null stdin and captured stdout/stderr.

The CLI's nested sandbox denied bubblewrap's namespace setup. The approved outer launcher therefore starts bubblewrap outside that nested sandbox; the submitted predictor still runs inside the narrow bubblewrap filesystem, never as an unsandboxed import. The trusted preparation and scoring scripts run separately and are not mounted into the predictor process.

The input directory contains only `reconstruct.py`, `generator.py`, `source_hashes.json`, `replay_driver.py`, and `challenge_features.npz`. All challenge truth, seeds, cohort membership and post-prediction comparisons remain in sibling private directories. No official launched-set score is read, invoked, or reproduced.
