# Source-workflow fragment

`siam_model.py` is the original model-preparation function from the official
`hczhai/block2-example-data` repository, file `06-SIAM/00-dmrg.py`, commit
`ee9868b32ce1527a5067707f21f178128ad4d9b0`, extracted without the original
large-cluster driver settings or target traces. It is historical evidence;
the authoritative model meanings for this handoff are in `input/MODELS.md`.
The original license is preserved in `LICENSE`.

The compiled numerical engine and its Python API are unmodified official
block2 0.5.3 binaries/sources. The benchmark integration layer is not official
upstream code. No upstream outcome is implied by its behavior. A bundled
library-loader adjustment handles this machine's dynamic-link environment.
