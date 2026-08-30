# Submission and runtime contract

The runtime is `/usr/bin/python3` (CPython 3.10). System packages live under `/usr`.
Compatible local wheels include NumPy 1.24.4, SciPy 1.10.1, Matplotlib 3.7.5,
NetworkX 3.1, `pymatching==2.4.0`, and `stim==1.15.0`, with their dependencies.
These are copied, not symlinked, into `input/runtime/`. The launcher
prepends this directory and the participant root to `sys.path`. Python binding
files included in those wheels are permitted runtime dependencies; upstream
C++ source trees, tests, and privileged implementations are not supplied.

Copy the starter `workspace/submission.py` to `$OUTPUT_DIR/submission.py` before
editing. The participant tree is read-only in the fresh runner. Your output
module must export:

```
class Decoder:
    def __init__(self, model: dict): ...
    def decode(self, syndromes: numpy.ndarray) -> numpy.ndarray: ...
```

`model` contains `case_id`, `family`, `distance`, `rounds`, `num_detectors`,
`num_observables` (4), `num_mechanisms`, `dem_text`, and the following arrays:

| Key | Shape and dtype | Meaning |
| --- | --- | --- |
| `detector_matrix` | `(D,M)` uint8 | Binary detector incidence H |
| `observable_matrix` | `(4,M)` uint8 | Binary logical incidence L |
| `probabilities` | `(M,)` float64 | Independent Bernoulli mechanism probabilities |
| `detector_coordinates` | `(D,4)` int64 | x, y, time, CSS sector |
| `mechanism_kind` | `(M,)` Unicode | X, Z, Y, XX, ZZ, readout, or YY_time |

Additional scalar fields specify the noise rates. `dem_text` retains the full
correlated decomposition; `^` is not a stochastic independence separator.
`input/models.py` defines the exact geometry, sampling law and a loader.

`syndromes` is a C-contiguous binary uint8 array of shape `(N,D)`, in arbitrary
shot order. Return a NumPy array of shape `(N,4)`, binary boolean or integer
dtype. No NaN, floats, abstentions, physical-error output, or extra dimensions.
A failure means **any** of the four bits is wrong; bitwise accuracy is not scored.
The evaluator creates one decoder per model and may decode one or more batches.
Predictions must be row-equivariant; do not rely on batch order or hidden split
boundaries. Copy mutable inputs if your method needs to modify them.

Only the submission directory, participant assets and ordinary system runtime
files are visible during execution. Working-directory writes are not guaranteed;
use `/tmp` for evaluation scratch. Ship trained weights or auxiliary source beside your
submission. No external symlinks. Evaluation is strictly single-process and
single-thread: a seccomp filter blocks new processes/threads. No GPU. Precompile
any native extension during development and load it in-process during evaluation;
do not invoke a compiler or subprocess from `Decoder`. This does not restrict
parallel development agents outside evaluation.

## Label-blind worker protocol

`input/worker.py REQUEST_JSON RESPONSE_JSON` is the execution entry point. A
request contains `submission` (absolute module path), `participant_root`,
`items` (a list of `{case_id, syndromes, predictions}`), and `limits`.
Each input NPZ has only `syndromes`; each output NPZ must contain `predictions`.
Paths in this protocol are paths **inside** the sandbox. The worker validates
shape, binary values and dtype. Its response contains per-case timing and
environment metadata, never labels or scores. The trusted evaluator constructs
requests, launches the worker in a filesystem/network/PID namespace, and scores
the outputs outside that namespace. A subprocess alone is not a security boundary.

The fixed hidden suite has two independent splits of 1,024 shots per model,
12,288 shots total. Calibration has 512 shots per model and is not scored.
Public calibration reports are development feedback, not a promise of passing.
