# Available native binary decoder

`legacy_2020/` contains the original native binary BP+OSD implementation
and its dependencies, including its original license. It is supplied as
already-solved infrastructure, not as the solution to this task. You may
adapt and compile it with the installed g++ toolchain; no Python decoder
package or Numba is available in the participant sandbox.

Relevant entry points are `src/bp_osd.h`, `src/bp_osd.cpp`,
`src/bp_decoder_ms.c`, and `src/bp_decoder_ps.c`; `include/` supplies the
sparse binary matrix implementation and other original dependencies.
The original constructor accepts a scalar binary channel probability.
The task provides per-qubit four-outcome probabilities, general local frames,
and a different executable API, so the snapshot is not a drop-in solution.

`solve.py` is a separate concise independent-marginal linear-syndrome baseline.
It does not use this native decoder, propagate conditional channel information,
or optimize logical success. `smoke.py` checks shapes and syndrome consistency
only. Neither passing smoke nor compiling the native sources measures quality.
