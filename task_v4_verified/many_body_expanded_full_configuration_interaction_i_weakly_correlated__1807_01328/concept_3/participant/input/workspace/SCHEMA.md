# Data and submission schema

All archives use NumPy NPZ, `allow_pickle=False`, no object arrays, and row-aligned samples. Train has 1,280 rows, validation 384, and `test_features.npz` 288. The latter contains **no labels**. IDs are independent random 128-bit hexadecimal tokens, not seeds or parameter encodings.

Let N be the row count, O = `n_pairs` (2 or 3), and V = `n_virtual` (6–9). Occupied indices are 0…O−1; virtual indices O…O+V−1. Padding is zero. Virtual order is independently randomized. Every energy is in `synthetic_Eh`.

| Key | Shape / dtype | Meaning |
| --- | --- | --- |
| `ids` | (N,) U32 | Stable opaque IDs |
| `n_pairs`, `n_virtual`, `family` | (N,) int8 | Sizes and family code |
| `onsite` | (N,12) float64 | Diagonal pair energies, not single-electron energies |
| `density` | (N,12,12) float64 | Symmetric pair-density interactions, zero diagonal |
| `occupied_profile` | (N,3) float64 | Positive unit-norm occupied-source profile; not transfer magnitudes |
| `positions` | (N,9) float64 | Virtual geometry in [0,1] |
| `groups` | (N,9) int8 | Binary virtual groups |
| `pair_sign` | (N,36) int8 | Known virtual–virtual transfer signs ±1; zero padding |
| `diagonal_gaps` | (N,3,9) float64 | Reference-to-single-pair-replacement diagonal energy costs |
| `reference_energy` | (N,) float64 | Occupied-reference energy |
| `cas1`, `inc1` | (N,9) float64 | Singleton CAS correlation energies = first increments |
| `cas2`, `inc2` | (N,36) float64 | Pair CAS correlation energies and connected increments |
| `cas3`, `inc3` | (N,84) float64 | Triple CAS correlation energies and connected increments |
| `truncated_correlation` | (N,) float64 | Sum of connected increments through order three |
| `tail` | (N,) float64 | **Train/validation only:** full correlation minus truncated correlation |

Pair slots follow `list(itertools.combinations(range(9), 2))`; triple slots use combinations of size 3. A slot is present exactly when its largest index is less than V. Valid slots are **not necessarily a contiguous prefix**. CAS arrays are correlation energies relative to the same reference, never absolute eigenvalues. Increments use subset inclusion–exclusion and may have either sign.

Family codes: 0 coherent, 1 repulsive, 2 screened, 3 frustrated, 4 mixed_range, 5 bottleneck. Train and validation contain only 0–3, balanced over family × pair count × virtual count. Test has 48 cases per family, including entirely held-out 4 and 5. Cases are independent Hamiltonians, not repeated observations of a parent. Generating independent examples from any family is allowed.

## Submission

Use `np.savez_compressed("predictions.npz", ids=test["ids"], tail=prediction.astype(np.float64))`. Exactly these two keys are permitted. IDs must be Unicode U32; predictions float32 or float64. Both shapes must be (288,). Duplicates, unknown/missing IDs, nonfinite/complex/integer predictions, objects, extra keys, malformed archives and symlinks are invalid. Limit: 8 MiB compressed and uncompressed. Magnitudes above 1e6 are invalid to prevent overflow. Ordering is arbitrary; the evaluator aligns by ID.

## Scoring

`core_score` is RMSE of the signed tail. `worst_family_score` is the largest of six separate family RMSEs. Pass requires core ≤ min(3e−5, 0.65 × baseline_core) **and** worst family ≤ min(6e−5, 0.75 × baseline_worst). Lower is better. MAE, 95th-percentile and maximum absolute error are secondary diagnostics only. Reports include `valid`, `passed`, `reason`, evaluator runtime and peak RSS. Participant training time is not inferable from a static file and is null, not zero.

No row-level hidden errors or labels are returned. Visible test features are intentional: this is fixed-set hidden prediction, not an online Hamiltonian oracle. `manifest.json` records public file hashes; `baseline_reference.json` records aggregate frozen baseline scores and effective limits.
