# Branch-correct anisotropic Eliashberg solver

## Mission
Improve the supplied public nonlinear imaginary-axis baseline. Recover the
nonzero same-sign superconducting branch across multiband, retarded-scale,
nearly critical, weak-interband, and combined materials. Physics operators and
their derivative API are supplied. Fine anisotropic patch models, very close or sheet-selective pairing
instabilities, weak induced gaps, and low temperatures make branch correctness
and resource use important. Some materials resolve smooth anisotropic phonon
spectra using dozens of distinct quadrature bins. A small residual alone is not success.

## Assets
`input/` contains the operator, public instances, baseline measurement, and
`FORMAT.md`. `workspace/solve.py` is the editable starting submission;
`baseline/solve.py` is the supplied public baseline. Paths here are relative to
this participant directory. Set `OUTPUT_DIR` to the writable output directory
specified by the launch prompt when running development examples.

## Interface
Submit a directory containing `solve.py`, invoked as
`python solve.py --input FILE --output FILE`. Write finite float arrays `delta`
and `z` in one NPZ. Package all required code/assets in your output directory.
Detailed equations, dimensions, and the helper API are in `input/FORMAT.md`.

## Objective
Solve at least 18 of 20 hidden instances and at least 3 of 4 in every family,
and improve worst-family acceptance by at least 0.25 over the measured supplied
public baseline. Normal-state solutions, wrong relative signs, and inaccurate
weak gaps do not receive credit.

## Resources
Pure single-process Python with NumPy/SciPy; one thread; no external processes,
network, or private-file access. Every fresh invocation gets 12 total CPU seconds
including startup, 2048 MiB address space, and an 1800-second wall safety ceiling.
Wall time is not a performance score. Submitted code/assets must fit in 32 MiB;
the output file and its expanded NPZ payload must each fit in 32 MiB.

## Scoring
Score is the minimum of the five family acceptance fractions. Each accepted
case must have independently checked normalized gap residual <= `2e-8`,
renormalization residual <= `2e-9`, and maximum per-patch normalized distance
to the certified branch <= `0.002`, with correct low-frequency relative signs.
A single global sign reversal is equivalent. Every quality and resource gate
is mandatory; exact norms and parameter ranges are in `input/FORMAT.md`.
