# Numerical format and physical conventions

## Physical model

Qubits are numbered from zero. A Pauli row uses `0=I, 1=X, 2=Y, 3=Z`, in qubit-index order, with no phase encoded. Circuit lists are chronological. A library gate executes its primitive operations chronologically; opcodes are `1=H`, `2=S=diag(1,i)`, `3=CX` (first qubit controls second), `4=CZ`, `5=SWAP`. Single-qubit operations have second index `-1`. Ideal Clifford signs matter.

A library gate with noise channel `g>=0` implements `U_g ∘ Λ_g`: noise acts **before** the entire ideal gate. A gate with channel `-1` is perfect and consists only of single-qubit operations. Every nonnegative channel labels exactly one library gate. Preparation and measurement noise channels are `-2` and `-1`, respectively; these channel identifiers are distinct from the perfect-gate sentinel's role in `gate_noise`.

Each factor mask declares a nonempty set of at most two qubits. For a gate channel, every Pauli `E` with exactly that support and arbitrary nonidentity axes has an unknown positive rate `r[g,E]`. Its channel is the composition of `exp(r[g,E] (EρE−ρ))` over all its declared factors and axes. Equivalently, its Pauli eigenvalue is

`λ_g(P) = exp(−2 Σ_E r[g,E] 1{E and P anticommute})`.

For preparation or measurement, a factor `F` has an unknown positive depolarizing strength `s[c,F]`, with

`λ_c(P) = exp(−Σ_F s[c,F] 1{F intersects support(P)})`.

Different channels have independent unknown rates. Factors within a channel are unique; undeclared rates are zero. All channels are stationary across experiments. There are no additional errors. The model is exact, not a sparse-support recovery problem.

For each listed circuit with final observable `P`, let its ideal inverse-conjugated observable be `σP_in`, where `P_in` has no encoded phase and `σ=±1`. Preparation makes the product of positive single-qubit eigenstates specified by `P_in`; identity sites are maximally mixed. The preparation channel acts on this state, then the listed noisy circuit runs. The measurement channel acts immediately before measuring the signed parity of the **listed unsigned** final Pauli `P`. Counts are actual `+1` parities, not absolute contrasts or sign-corrected counts. This convention specifies the prepared state without a separate input array.

## Input arrays

Load with `numpy.load(..., allow_pickle=False)`. All arrays are numeric; integers have their natural meaning, masks contain only zero/one. Let `n` be qubits, `L` library gates, `O` primitives, `F` factors, `T` training records, `H` held-out records, `Q` queries, and `K` query terms.

| Key | Shape | Meaning |
|---|---|---|
| `schema_version`, `n_qubits` | scalar | Version `1`, and `n` |
| `gate_ptr` | `(L+1,)` | Offsets into `gate_ops` |
| `gate_ops` | `(O,3)` | Primitive opcode, first qubit, second qubit |
| `gate_noise` | `(L,)` | Nonnegative channel ID or perfect-gate `-1` |
| `factor_channel`, `factor_mask` | `(F,)`, `(F,n)` | Channel and support of each factor |
| `train_ptr`, `train_gates` | `(T+1,)`, `(train_ptr[-1],)` | Offsets and library-gate indices |
| `train_observable` | `(T,n)` | Final unsigned Pauli observable |
| `train_shots`, `train_plus` | `(T,)` | Independent binomial trial count and `+1` count |
| `holdout_ptr`, `holdout_gates` | `(H+1,)`, `(holdout_ptr[-1],)` | Unmeasured circuits, same encoding |
| `holdout_observable` | `(H,n)` | Their final unsigned observables |
| `query_ptr` | `(Q+1,)` | Offsets into the three term arrays |
| `query_channel`, `query_pauli`, `query_coeff` | `(K,)`, `(K,n)`, `(K,)` | Channel, Pauli and real coefficient of each query term |

All offset arrays start at zero, are nondecreasing, and end at the corresponding flat-array length. A query is `Σ_j query_coeff[j] (−log λ_query_channel[j](query_pauli[j]))`, with terms selected by its offsets. Gate, factor, qubit and query orderings carry no additional information. Negative query coefficients are allowed.

## Outputs and identifiability

Write exactly these finite numeric arrays to `OUTPUT.npz`:

| Key | Shape | Meaning |
|---|---|---|
| `structural_identifiable` | `(Q,)` | Probability in `[0,1]` that the query is structurally identifiable |
| `calibration_identifiable` | `(Q,)` | Probability in `[0,1]` that the query is identifiable from the supplied calibration designs |
| `query_log_estimate` | `(Q,)` | Estimated query value; ignored where calibration identifiability is false |
| `holdout_mean` | `(H,)` | Predicted latent parity expectation in `[-1,1]`, not `+1` probability |

Structural identifiability means that every two interior positive-rate models indistinguishable by **all** experiments using this gate set, arbitrary perfect single-qubit Clifford controls, and the preparation/measurement convention above agree on the query. Calibration identifiability replaces “all experiments” with just the noiseless expectations of the supplied training designs. These are exact model properties, not statistical confidence tests or boundary effects. Structural identifiability need not imply calibration identifiability. Every held-out expectation is calibration-identifiable. Gauge-dependent rate vectors themselves are not requested.

## Scoring and limits

Identification (35%), supported query estimation (25%), and held-out prediction (40%) are scored separately. Identification uses class-balanced Brier error for each of its two arrays. Query estimation uses mean squared error after dividing each query by `Σ_j |coeff_j| max(1, weight(P_j))`; unsupported queries are omitted. Prediction uses mean squared error against the latent signed parity means. For each case and component, `scale = weak_baseline_loss/4 + 12*strong_reference_loss` is fixed privately from input-only solvers. Its score is `scale/(scale+your_loss)`, and the case score is the weighted mean. There is no clipping or tolerance plateau: any decrease in positive loss increases the score. The baseline need not score zero and the reference need not score one. Reports include case details, family means, worst-family mean and runtime.

Core systems range from 4 to 20 qubits, with a coupled 20-qubit case in every family; all challenge cases have 20 or 24 qubits. There are up to 24 noisy library gates, two-qubit noise factors, unequal shot budgets and incomplete calibration sectors. Large cases have connected ideal-interaction and noise-factor graphs, not replicated independent blocks. Some calibrations cover only the computational Pauli sector despite controls being available in principle. The example is smaller and unlabeled. Per hidden case: a fresh process, 120 seconds wall time, 3 GiB address space, one numerical thread, and a 16 MiB file-size cap. Only the submitted file is staged; use NumPy/SciPy and the standard library. Private data and other cases are inaccessible. Do not use the network. `example.npz` is the sole public sample; `../workspace/` is for development.
