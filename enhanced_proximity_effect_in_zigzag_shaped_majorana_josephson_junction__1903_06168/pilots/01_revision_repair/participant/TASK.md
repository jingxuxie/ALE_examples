# Repair the junction analysis service

Repair the supplied historical geometry/Hamiltonian service so that it returns
correct spatial barrier responses and excitation gaps for the requested devices.
Preserve the model's lattice, region, and parameter conventions. You may modify
or replace the implementation; correctness of the numerical outputs is what matters.

Submit `attempt/solve.py`, executable as:

```sh
python attempt/solve.py --input REQUEST.json --output RESULT.json
```

Each invocation receives one externally supplied request. See `input/SCHEMA.md`
for the contract and `workspace/README.md` for the runnable starting point.
Only finite JSON results are accepted. Evaluation balances the different device
families and reports their scores and runtime separately. Allow 60 seconds and
2 GiB per invocation. The supplied runtime targets Python 3.10 on Linux x86_64.
