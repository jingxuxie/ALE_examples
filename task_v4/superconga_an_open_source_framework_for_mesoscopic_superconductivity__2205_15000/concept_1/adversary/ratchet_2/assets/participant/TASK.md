# Lower-energy states in perforated superconducting grains

Improve supplied converged superconducting states in connected, perforated
mesoscopic grains. The task uses the explicitly defined, gauge-covariant,
near-critical-temperature Ginzburg–Landau lattice model in `input/MODEL.md`,
with a prescribed physical vector potential. It is not a reproduction of
SuperConga's self-consistent quasiclassical theory.

Assets include an exact energy/gradient API, development inputs, a runnable
baseline, and the previous solver in `baseline/champion.py`. Each evaluation
input contains its own frozen baseline state; lower-energy witness fields
remain private. Input and scoring contracts are in `input/API.md` and
`input/SCORING.md`.

Submit `solve.py` at the root of your output directory. It is invoked once per
case as `python3 solve.py --input CASE_JSON --output RESULT_NPZ` and must write
the complete complex order parameter as the NPZ array `psi`.

Three held-out perforated-grain cases form one family. Pass requires mean gap
closure at least **0.65**, worst-family closure at least **0.45**, no regression
from any provided baseline, and independent gradient RMS at most **0.002**.
The baseline-to-witness energy gaps are fixed before this attempt. Neither
scores nor claimed energies from the submission are trusted.

You have one hour of development. Evaluation allows **60 wall/CPU seconds per
case, one CPU core, 2 GiB memory, 256 MiB scratch, and a 4 MiB NPZ output**.
Use Python standard library, NumPy, and SciPy only; no external executables,
GPU, network, private files, or cross-case persistence. Runtime is reported
separately and cannot compensate for poor states.
