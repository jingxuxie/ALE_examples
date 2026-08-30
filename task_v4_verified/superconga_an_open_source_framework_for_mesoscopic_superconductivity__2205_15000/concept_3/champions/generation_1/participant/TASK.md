# Active LDOS tomography

## Mission
Recover 4–7 nonmagnetic impurities (sites and signed strengths) and an unordered
configuration of 0, 1, or 2 vortices in an 8×8 superconducting grain. Choose at
most 56 scalar site/energy LDOS measurements adaptively, then submit one scene.
This is mode E, ACTIVE EXPERIMENT DESIGN: your program selects the experiments.

This is a **microscopic diagnostic reduced problem**, not SuperConga's native
quasiclassical solver. The exact finite spin-singlet BdG Hamiltonian is public;
no self-consistent gap equation, GPU, or SuperConga installation is needed.

## Assets
`workspace/bdg.py` is the complete forward model and prior sampler.
`workspace/API.md` defines the physics and JSONL protocol. `input/model.json`
contains constants; `input/train.json` and `input/calibration.json` contain
labeled public scenes. `baseline/uniform.py` is a runnable nonadaptive baseline.
Scientific provenance is in `input/PROVENANCE.md`.

## Interface
Create `output/solve.py`, executable as `python output/solve.py`, with any helper
files inside `output/`. It accepts JSONL on stdin and emits only JSONL on stdout.
If the runner supplies an absolute output directory, put `solve.py` directly there.
A fresh subprocess receives public metadata, exchanges query/observation
messages, and sends a final estimate. Hidden scenes and seeds never enter its
input. Local calls to the public simulator must specify your own candidate scene.
Example command, from the participant directory: `python baseline/solve.py`.
Both participant and submission mounts are read-only; `/tmp` and `/output` are writable.
Use `workspace/run_local.py --submission output --split train` for labeled practice.

## Objective
The fixed target is `input/target.json`: joint reconstruction success ≥70%
overall AND ≥50% in every family, mean support F1 ≥0.90, mean relative strength
error ≤0.15, and exact vortex-configuration accuracy ≥90%, with no protocol
failures. A joint success requires F1 ≥0.85, relative strength error ≤0.20, and
the exact vortex configuration. The suite has four draws per family; no reference
solver or baseline-relative criterion is used.

## Resources
56 noiseless scalar LDOS queries, one CPU core, 90 CPU seconds / 120 wall seconds,
2 GiB address space per episode. Python standard library, NumPy, and SciPy only.
No network, hidden files, or cross-episode persistence. Write scratch data only
in `/tmp` or `/output`. All local simulation and inference
count against the same time budget. Details and training commands are in the API.
