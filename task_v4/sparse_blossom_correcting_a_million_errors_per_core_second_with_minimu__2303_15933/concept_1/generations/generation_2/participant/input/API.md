# Submission API

The entry point is `OUTPUT_DIR/submission.py`. The evaluator adds the participant
root, `input/`, `input/runtime/`, and your submission directory to `sys.path`.
Sibling files and precompiled shared libraries may be used; symlinks and external
runtime paths may not. Maximum collected artifacts: 256 MiB and 4,096 files.

```
class Decoder:
    def __init__(self, model):
        ...

    def decode(self, syndromes):
        ...
```

`model` is a dictionary loaded by `models.load_model(case_directory)`:

| Key | Value |
| --- | --- |
| `case_id`, `family`, `profile` | Descriptive strings; do not encode labels |
| `distance`, `rounds` | Toric lattice size and number of data-noise time layers |
| `num_detectors`, `num_mechanisms`, `num_observables` | D, M, 4 |
| `detector_matrix` | C-contiguous uint8 H, shape (D, M), binary |
| `observable_matrix` | uint8 L, shape (4, M), binary |
| `probabilities` | float64 independent mechanism probabilities, shape (M,) |
| `detector_coordinates` | int64 (D, 4): (x, y, time, CSS sector) |
| `mechanism_kind` | Unicode (M,): X, Z, Y, XX, ZZ, YY_time, or readout |
| `dem_text` | Full equivalent Stim detector error model; `^` pieces fire together |
| `px`, `pz`, `py`, `pair`, `measurement`, `burst` | Base rates, BEFORE the named profile |

The numerical `probabilities` and complete DEM are authoritative. Nonuniform
profiles change actual mechanism probabilities, not H or L. The generator in
`models.py` specifies all geometry and rates without hidden model parameters.

`syndromes` is a C-contiguous binary uint8 array of shape (N, D). Return a NumPy
array of shape (N, 4) with boolean or integer dtype, containing only 0 and 1.
Column order is exactly L's row order. Each row is an independent shot; no latent
state is shared between shots. Support arbitrary N, row permutations and repeated
calls. A decoder may cache model-dependent work. A fresh decoder is constructed
for each case. Final evaluation gives one batch per case, containing the two
hidden splits; labels, baseline predictions and split boundaries are not inputs.

The starter imports the supplied baseline. To change its native implementation,
copy its Python/C++ files and build a sibling `decoder.so` inside OUTPUT_DIR. The
baseline file uses its own `__file__` to locate the binary. Runtime compilation
and spawning subprocesses during evaluation are not supported.

`input/run_public.py` is an unsandboxed local convenience tool, safe only for your
own code. Its timing excludes imports and is diagnostic, not the official CPU
measurement. Use `models.sample_model(model, shots, seed)` to make new independent
training or validation shots; it returns syndromes, logical labels, and faults.

## Public worker protocol for infrastructure

`/usr/bin/python3 -I input/worker.py REQUEST.json RESPONSE.json` reads a JSON object:

```
{
  "submission": "/submission/submission.py",
  "participant_root": "/participant",
  "limits": {"cpu_seconds": 180, "address_bytes": 6442450944},
  "items": [{"case_id": "r2_pairs_9", "syndromes": "/request/r2_pairs_9.npz", "predictions": "/out/r2_pairs_9.npz"}]
}
```

The numeric limit here is illustrative; `target.json` supplies the frozen value.
Input NPZ contains **only `syndromes`**. Output NPZ contains **only `predictions`**.
The response contains optional diagnostic timings/versions, never trusted scores.
The trusted parent retains labels and baseline predictions, validates output,
and measures process CPU independently. The worker interface is NOT an isolation
boundary by itself: the main evaluator must launch it in the supplied bwrap
sandbox (or an equally audited external sandbox), with no private tree mounted.
