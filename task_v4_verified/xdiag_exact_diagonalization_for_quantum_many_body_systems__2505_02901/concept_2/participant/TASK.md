# Calibration-aware many-body pulse compiler

Compile one hardware-admissible pulse that realizes a specified coherent action
on a six-dimensional register encoded in an interacting eight-spin ring. The
same pulse must meet all four public static-calibration contracts. Matching
individual populations or independently phasing the six output states is not
sufficient.

`input/` contains the complete Hamiltonians, initial register, target isometries,
hardware limits, and mathematical acceptance contract. `workspace/simulate.py`
provides a runnable public forward model; `baseline/solve.py` is a weak runnable
search. There are no undisclosed calibration points or target states.

Write `pulse.json` in your designated output directory. Its interface is
`{"schema_version": 1, "amplitudes": [[a0, a1, a2], ...]}` with exactly 24
chronologically ordered rows. The slice duration is fixed; no other artifact
is needed for acceptance. You may use any implementation to construct this
artifact.

Optionally include `solve.py` supporting `--input INPUT_DIRECTORY --output
OUTPUT_PULSE_JSON` for reproducible compilation on fully specified instances of
the same model. It is not required, is not executed by this evaluator, and does
not change acceptance of the fixed public witness task.

Acceptance requires a mean coherent-isometry fidelity of at least **0.999995**,
a certified worst-superposition fidelity of at least **0.99999** for every
calibration, and compliance with the amplitude, adjacent-jump, endpoint, and
integrated-control limits. The evaluator independently propagates the submitted
pulse. It reports coherent accuracy, worst-calibration accuracy, physical
resource use, and validation time.

The construction budget is one hour, CPU only, at most four CPU threads and
8 GiB memory. `/usr/bin/python3` with NumPy 1.21 and SciPy 1.8 is available;
external packages, network services, and access outside the supplied participant
tree and your designated writable output directory are unavailable. Treat the
participant tree as read-only and place scratch work in your output directory.

Example baseline invocation from the participant directory:

```sh
/usr/bin/python3 -B baseline/solve.py --input input --output /your/output
```
