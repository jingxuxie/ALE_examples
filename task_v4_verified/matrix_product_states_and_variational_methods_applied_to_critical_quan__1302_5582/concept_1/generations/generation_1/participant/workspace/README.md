# Starting workspace

The production optimizer, tensor helpers and energy contractor are supplied so
the task is not to reproduce a tensor library. This source snapshot matches the
frozen baseline. Only the physical Hamiltonian in the contract is scored.

Copy this read-only starter into your submission/output directory before editing.
Keep `solve.py` and any imported helper files together in your submitted directory.
You may change these implementations completely. Do not depend on sibling
builder/evaluator directories. No checkpoint carries across independent requests.

Public smoke commands, from the participant directory, with `OUTPUT_DIR` set to
the writable submission/output directory named in your launch:

```
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python workspace/solve.py --request input/example_symmetric.json --output "$OUTPUT_DIR/phi4.npz"
python workspace/contractor.py --request input/example_symmetric.json --state "$OUTPUT_DIR/phi4.npz"
```

All coefficients and finite-basis conventions are explicit in requests and
`input/CONTRACT.md`. Public examples are not hidden test cases. No continuum
extrapolation, energy shift, or modified Hamiltonian is scored.
