# Correlated error queries

Write `solver.py INPUT.npz OUTPUT.npz` to infer a binary error model from local
distributions and answer normalized, activity-tilted global event queries.
The hidden interactions are not supplied. Systems approach 100 qubits; dense
joint enumeration is not viable. Return natural-log probabilities, including
extremely rare events. See `input/FORMAT.md` for the complete contract.

`workspace/` contains an incomplete local-analysis adapter and `input/example.npz`
is unlabeled. Use Python with NumPy/SciPy; submit one self-contained `solver.py`.
Each case has a 120-second wall limit and 3 GiB address-space limit. Accuracy is
scored continuously in log probability, relative to an independent-bit baseline.
