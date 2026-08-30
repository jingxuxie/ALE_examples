# Robust flat Chern-band witness

## Mission
Design a range-three, two-orbital semiconductor-inspired lattice spin block whose
lowest band remains flat, energy-isolated, and topological throughout the specified
manufacturing uncertainty set. This is a reduced model, not calibrated HgTe.

## Assets
- `input/SPEC.md`, `input/model.json`: complete model, allowed support, uncertainties.
- `input/targets.json`: fixed acceptance thresholds.
- `input/CERTIFICATION.md`: the continuum and topology certificate used for scoring.
- `input/witness.schema.json`: JSON witness schema.
- `workspace/model.py`, `workspace/probe.py`: public numerical helpers and mesh probes.
- `baseline/design.py`: a runnable weak BHZ design, not a passing witness.

## Interface
Write `witness.json` in your designated output directory. Submit that directory or
the JSON file. No submitted program is executed. Use finite real coefficients in
the specified order; optional Fourier channels must be exactly zero when unused.
Keep public assets unchanged. Run the baseline with
`python baseline/design.py --output /your/output/witness.json` and inspect it with
`python workspace/probe.py /your/output/witness.json` from the participant directory.

## Objective
Use at most **8** optional symmetry-orbit channels. The certified worst-case lower
bandwidth must be **<= 0.175**, both direct and indirect gaps **>= 3.0**, and the
lower-band Chern number **-1**, in the convention of `input/SPEC.md`. All properties
must survive the entire public uncertainty box, not just a list of sample points.
Acceptance uses the conservative certificates in `input/CERTIFICATION.md`; raw
sampled extrema are insufficient. Score is the clipped minimum of the three
threshold ratios, and is zero if input or topology validation fails.

## Resources
Local Python, NumPy, and SciPy; no network or kdotpy installation is needed.
The discovery budget is 3600 seconds. Output is one JSON file of at most 32768
bytes; the evaluator reads data only. Mesh probes are not acceptance certificates.
