# Input, output, and evaluation contract

Implement a reusable `solver.py` invoked as:

`python solver.py INPUT.npz OUTPUT.npz`

Recover the significant **nonidentity Pauli strings and their probabilities** from calibrated, noisy Pauli-eigenvalue estimates. Channels have 40–100 qubits, arbitrary-weight errors, collisions in the subsampling patterns, and potentially a weak nonsparse remainder. The identity can carry most probability. Dense enumeration of all strings is not feasible. Only NumPy, SciPy, and Python's standard library are available. Each input runs independently with one CPU thread, 2 GiB address space, and a 120-second wall-time limit. Submit the single Python file, not predictions for the example.

## Input schema

Scratch files have a 32 MiB individual-file limit; at most 64 file descriptors may be open. Submit a regular output file, not a symlink. Valid schema-sized outputs are much smaller than the 16 MiB compressed/32 MiB decompressed output-validation bounds.

NPZ files contain only these numeric arrays; use `allow_pickle=False`:

| Key | dtype, shape | Meaning |
|---|---|---|
| `n_qubits` | int64 scalar | Number of qubits, `n` |
| `hashes` | uint8 `(G,b,2*n)` | Binary full-row-rank sampling matrices; rows within a group commute symplectically |
| `offsets` | uint8 `(T,2*n)` | Character masks: zero row, the `2*n` standard basis rows in order, then additional binary masks |
| `eigenvalues` | float64 `(G,T,2**b)` | Noisy eigenvalue estimates, in the order defined below |
| `noise_std` | float64 `(G,T)` | Known standard deviation of each eigenvalue estimate along its last axis |
| `recovery_floor` | float64 scalar | Probability threshold used to assess significant support |
| `max_terms` | int64 scalar | Maximum number of nonidentity strings in your output |

For a Pauli string `E`, define `e=(x0,z0,x1,z1,...)` with `I=(0,0)`, `X=(1,0)`, `Y=(1,1)`, `Z=(0,1)`. All binary algebra is modulo two. For last-axis index `v`, let `v_bits[j]=(v >> j)&1`, `j=0,...,b-1`. Define the character mask

`q[g,t,v] = offsets[t] XOR (v_bits @ hashes[g] mod 2)`.

The measured Pauli has `(x,z)` bits `(q_z,q_x)` on each qubit. Its noiseless eigenvalue is

`lambda(q) = sum_E p(E) * (-1)**(e dot q mod 2)`.

`eigenvalues[g,t,v] = lambda(q[g,t,v]) + noise`, with independent mean-zero Gaussian noise of the supplied standard deviation, including independently acquired repeats of the same mask. These are fitted eigenvalue estimates, not single-shot outcomes; do not clip them to `[-1,1]`. The underlying channel probabilities are nonnegative and sum to one. The approximately sparse remainder also consists of physical Pauli errors, not additional measurement noise. There is no promised bound on Pauli weight, locality, or a known candidate support. Hidden inputs vary the channel, sampling matrices, noise, and dimensions; no seed, family, or ground truth is in an input.

Typical dimensions are `G=3..5`, `b=6..8`, `T=2*n+33..2*n+49`, with at most 512 significant terms. Significant probabilities may span several thousand-fold. The single public input is an unlabeled format example, not a training set.

## Output schema

Write an NPZ with exactly:

- `paulis`: uint8 `(K,n)`, `K<=max_terms`, using `0=I, 1=X, 2=Y, 3=Z`; rows must be unique and nonidentity.
- `probabilities`: float64 `(K,)`, finite, nonnegative probabilities in the same order.
- `p_identity`: float64 scalar, finite and nonnegative.

Require `p_identity + probabilities.sum() <= 1` (numerical tolerance `1e-8`). Any remaining mass is interpreted as a completely depolarizing channel: uniform over all `4**n` Pauli strings. Empty support is allowed. No auxiliary files or input-specific hardcoded outputs.

## Evaluation

Let `A` be nonidentity probability L1 error divided by true nonidentity mass, `F` significant-support F1 at `recovery_floor`, and `B` relative spectral L2 error on unseen nonidentity observables after subtracting each channel's identity atom. Diffuse remaining mass counts in `A`; omitted background is not free. Neither numerical error is capped. Define `L = 0.45*A + 0.35*(1-F) + 0.20*B`. The probability-estimation loss is `E = (0.45*A + 0.20*B)/0.65`.

For each case, privately calibrated strong and weak losses define `s=max(L_strong,1e-4)*L_weak`. The continuous grade is `s/(s+L**2)`, with no clipping or saturation plateau. Probability estimation is separately graded by the same formula with `E` and its own calibration; support recovery is separately reported as `F`. Thus numerical improvements remain valuable even outside the calibration interval. Invalid outputs or exceeded resource limits receive zero. Reports include both subcomponent scores, raw errors, mean score, worst-family mean, family means, individual cases, and runtime. The identity cannot dominate these errors. A filesystem-confined child sees only the solver, its input, writable scratch space, and the Python runtime; no private answers.
