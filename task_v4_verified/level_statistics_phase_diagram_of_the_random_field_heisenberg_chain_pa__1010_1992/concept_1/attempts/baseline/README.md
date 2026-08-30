# Authoring baseline

The runnable baseline is `participant/workspace/predict.py` with
`baseline.pkl.gz` and `descriptors.py`. It is a 200-tree ExtraTrees model
trained only on the 1,600 training labels; validation labels are never
included in this fitted artifact. It has 250 shift/spin/dihedral-invariant
field, Fourier, resonance, block and weighted-Laplacian descriptors.

Public-validation RMSE is 0.03895205336432697 overall and
0.045517380138216955 worst-family. Fixed targets stay 0.035 and 0.050.
This is a usable nonpassing starter, not a privileged passing solution.
Only public-validation scores informed calibration; hidden labels did not.

Performance fixes are batched descriptors, single-threaded numerical
kernels and portable gzip/pickle serialization. The original authoring
joblib artifact is archived here because the user-site joblib version
differs from the isolated system version. It is not submitted.
The tree-count diagnostic and original 600-tree artifact are retained;
the provided model uses its first 200 trees for runtime headroom. The
streaming process exits immediately after flushing its response, avoiding
unneeded interpreter/model cleanup. Official timing evidence is public in
`participant/input/official_streaming_benchmark.json`.

No fresh solving agent or adversarial agent has been launched. No
champion is claimed. Main owns all subsequent fresh attempts.
