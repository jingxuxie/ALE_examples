# Fourteen-site spin dynamics

**Concept 1, generation 2, ratchet 1 — Mode D: HIDDEN PREDICTION.**
Predict the sample-specific Pal–Huse dynamical spin fraction `f` for
**L=14 only**. Inputs are exact, ordered site fields for a periodic
spin-1/2 Heisenberg ring with `J=1` and total `Sz=0`. The observable
averages Eq. (6) over the middle third of energy-ranked eigenstates.

## Objective

On 320 hidden L14 realizations, achieve **overall RMSE <= 0.035** and
**worst-family RMSE <= 0.050** simultaneously. Errors use the physical
`[0,1]` scale. Four equally represented families share the published
amplitude law: iid uniform, ordered blocks, alternating correlated
profiles, and shuffled near-resonant pairs. L10/L12 accuracy is not graded.

## Interface and limits

Submit `predict.py` and its assets. It is started without arguments.
Within **60 startup seconds**, load assets and print and flush `READY\n`.
Only then receive one stdin JSON line:
`{"cases":[{"id":"...","L":14,"fields":[...]}]}`.
Return one JSON line, `{"predictions":[{"id":"...","f":0.5}]}`,
flush, and exit. Supply exactly one finite `[0,1]` prediction per ID.

Inference has **3 wall seconds**, four enforced CPU cores, 2,048 MiB
address space, and no network. Hidden fields are unavailable during
startup. Search/training has a one-hour allowance; use at most eight
simulation workers with one BLAS thread each. Any approach respecting
the protocol is permitted; a passing solution is not guaranteed.

## Public assets

- `input/train.jsonl`: 320 new labeled L14 realizations.
- `input/validation.jsonl`: 160 independent labeled L14 realizations.
- `input/auxiliary_*_L10_L12.jsonl`: 1,920 earlier public labels, all usable for training.
- `workspace/`: starter code, physics, public generators and training code; copy into your output directory to modify.
- `baseline/`: self-contained runnable baseline fitted from public labels.
- `input/PROTOCOL.md`: complete physics, distributions, schemas and restrictions.

No earlier solving-agent code or learned artifact is supplied. Private
evaluation data must not be accessed. Model quality and runtime evidence
are recorded separately from the fixed scoring requirements.
