# Starter code

The complete small NumPy/SciPy two-site variational engine is provided, so the
task is not to reproduce a tensor library. `solve.py` deliberately runs only one
sweep at a small active bond. It exactly projects requested parity at output.
`mps.py` also exposes product initialization, MPO construction (including an
optional global parity bias), canonicalization, and a sweep with a CPU deadline.
Only the physical Hamiltonian in the contract is scored, never a biased MPO.

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

The distribution includes mass2 roughly -2.8 to +0.8, positive quartic couplings
1.2 to 2.8, positive springs 0.06 to 1.5, oscillator frequencies 0.55 to 1.85,
interfaces/weak links, and optional fields with magnitude <= 0.004. Parity-fixed
cases always have zero field. "Crossover" denotes finite-chain behavior, not an
externally supplied critical coupling. All coefficients are explicit in requests.
