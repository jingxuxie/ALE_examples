# Circuit-to-detector compiler
Implement `workspace/solve.py --input case.json --output answer.json`.
Compile parsed noisy Clifford measurement circuits into exact detector/observable error signatures and probabilities; do not decode syndromes.
The starter is a correct but slow one-fault-at-a-time compiler; replace it with a scalable method.
Read `input/FORMAT.md`; helpers and tiny worked examples are in `workspace/`.
Hidden cases cover surface and nongeometric HGP extraction, repeats, resets, both measurement bases, and correlated independent Pauli faults.
Each case permits 8 CPU seconds and 1536 MiB; wall allowance is at least 60 seconds. Only standard Python, NumPy, and SciPy are available; no circuit-compiler libraries or private assets.
Continuous semantic-plus-CPU scoring maps the weak baseline to 0 and the exact reference to 100 without clipping; correctness comes first.
