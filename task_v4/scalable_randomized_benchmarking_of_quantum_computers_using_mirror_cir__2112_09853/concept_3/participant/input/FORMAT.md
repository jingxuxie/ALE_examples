# Exact public contract

## Reference baseline and output

The participant tree is read-only during a fresh run. The required submission
filename is `artifact.json` inside the supplied writable OUTPUT directory.
It must be a regular file with exactly one hard link. Symlinks, hardlinks,
directories, FIFOs, devices, and other nonregular objects are rejected before
reading. Submission-root parent directories are assumed trusted by the runner.
`baseline/solve.py` performs 64 deterministic random restarts per family using
seed 211209853, with optional `--seed` and `--trials` arguments. This is an
illustrative reference, not a promised passing construction, and is not a
prescription for how to solve the task. It needs Python 3.10 or later and only
the standard library. The organizer's evaluator additionally needs NumPy.
The static-artifact evaluator imposes circuit limits, not a solver CPU-time cap.
`scorer.py --input input/spec.json --submission OUTPUT/artifact.json` provides the
complete public exact scoring implementation. It and `reference_core.py` and
`reference_faults.py` contain only validation/physics/scoring code, not a private
optimizer or a previous champion. The official evaluator uses its own trusted
copies and frozen specification; participant edits cannot change official grading.

## Artifact schema

The top-level object has exactly `schema_version` (integer 1) and `circuits` (a
list with one entry for every family in `spec.json`). Each circuit has exactly
`family` (the family ID string) and `layers` (a list, possibly empty). Each layer
has exactly `local` and `cx`. `local` lists exactly n words in qubit-index order.
`cx` lists zero or more `[control, target]` integer pairs. Example layer:

```json
{"local": ["H", "S", "I", "HS"], "cx": [[0, 1], [3, 2]]}
```

This is only a four-qubit illustration, not a valid full submission. No metadata
or score fields are permitted. Duplicate JSON keys, duplicate families, unknown
families, booleans/floats used as integers, and nonfinite numeric values are
invalid. File paths, imports, compressed archives, and external resources are
not circuit instructions.

## Gates, order, and resources

Qubits are zero-based. Edges are undirected native couplers, and either CNOT
direction is allowed. A round first applies every local word in parallel, then
its CNOT matching. Rounds execute in list order. Within a word, letters execute
left to right: `HS` means apply H then S, so its unitary is S H.

Allowed local words: `I`, `H`, `S`, `HS`, `SH`, `HSH`.

- H = (1/sqrt(2)) [[1,1],[1,-1]].
- S = diag(1,i), not its inverse; `I` is the identity.
- CNOT maps |control,target> to |control,target XOR control>.

These six words represent all unsigned one-qubit symplectic actions. They are
actual Clifford gates, not arbitrary permutations of support. No relabeling,
SWAP teleportation, ancillary space, routing shortcut, mid-circuit measurement,
or implicit all-to-all operation is permitted. SWAP must be synthesized with
native gates if wanted, and every constituent CNOT is counted.

`max_rounds` bounds local-plus-CNOT rounds; `max_cx` bounds total CNOTs. The maximum
CNOT depth is `max_rounds`. Expanding every local word to sequential native H/S
gates gives a primitive-depth upper bound of `4*max_rounds`, including CNOT slots.
No H/S count limit is imposed beyond this word/round restriction. Inverse
evaluation uses the actual U-dagger: reverse the gate sequence and replace S by
S-dagger, without charging for a second artifact. Its CNOT count/depth is the
same. S and S-dagger have the same phase-free binary action, but differ as
unitaries. Native S-dagger can be executed in a reversed schedule or expanded
as S cubed; the submitted block's primitive-depth bound is not a claim about
that S-only inverse expansion. The hard depth constraint is CNOT-round depth.

## Exact Pauli arithmetic

Represent a Pauli up to global phase by `(x,z)` in GF(2)^n x GF(2)^n: I=(0,0),
X=(1,0), Y=(1,1), Z=(0,1). Its weight is popcount(x OR z), counting a Y once.
Forward means U P U-dagger; inverse means U-dagger P U. Gate updates are:

- H(q): exchange x[q] and z[q].
- S(q) or S-dagger(q): z[q] XOR= x[q].
- CNOT(c,t): x[t] XOR= x[c]; z[c] XOR= z[t].

Inputs comprise all X/Y/Z on each site, and all nine axis combinations on each
unordered pair of distinct sites. The strata are separate: there are 48+1080
inputs for ladder16, 60+1710 for grid20, and 54+1377 for bridge18 per direction.
No random subset, distance restriction, or removal of cross-bottleneck pairs is
used. The evaluator constructs the Clifford's symplectic map and its inverse,
enumerates all inputs, and reports full weight histograms and worst inputs.

For each family, stratum s and direction d, let m be minimum output weight, W be
the integer sum of output weights, and N be the stratum size. Targets in the
specification mean:

```
m >= targets["min_" + s]
1000 * W >= targets["mean_" + s + "_milli"] * N
```

Both tests use exact integer comparisons. The corresponding score ratios are
`m / min_target` and `1000*W / (mean_milli*N)`. The family score is their minimum
over both strata and directions, capped at 1; `core_score` is the minimum family
score. All eight per-family inequalities must hold to pass. There is no hidden
statistical test, tolerance, exception for selected Paulis, or private target.

In generation 3 this defines the `ideal_score`, not the complete score. The
additional omission-robustness score is defined next. All generation-1 ideal
budgets and minimum/mean targets are unchanged.

The report includes `worst_family` (ID), `worst_family_score` (equal to
`core_score`), and exact per-family native resource counts and cap utilization.
`resource_score` is a compliance indicator: one for a schema-valid artifact
within all native limits, zero otherwise; it does not reward empty circuits.
`runtime_seconds` aliases `runtime`, measured over the full evaluation including
deletion diagnostics. `runtime_score = 1/(1+runtime_seconds)` is informational,
machine-dependent, and never gates passing. There is no runtime pass threshold.

## Mandatory robustness to up to THREE omitted CNOT instances

For the originally submitted circuit, assign every CNOT its zero-based pair
`[round_index, cx_index_within_that_original_round]`. These are occurrence IDs:
repeated use of the same directed/undirected coupler at different positions is
distinct. Enumerate EVERY subset of these instances of size zero, one, two, or
THREE. Omissions must be distinct instances; they may lie in the same round,
touch the same qubit, repeat a coupler, or occur in arbitrary different rounds.
There are exactly `1 + m + choose(m,2) + choose(m,3)` scenarios for m submitted
CNOTs, with choose(m,k)=0 when k>m. Four or more omissions are unsupported.

In each scenario, simultaneously replace the selected CNOTs by identity. Keep
all local words, other CNOTs, their directions, and their original ordering.
Do not renumber before selecting the second or third omission, repair the schedule,
resynthesize, reroute, omit local gates, or add a substitute operation. Faults
are not extra participant-supplied JSON fields: the evaluator generates them.

For each resulting unitary V, check EVERY weight-one and weight-two Pauli in
BOTH `V P V-dagger` and `V-dagger P V`. The latter is the exact inverse of the
same modified circuit, not a separately sampled inverse schedule. Each output
weight must be at least 3. The faulted circuits have no additional mean target;
the zero-omission circuit must also meet every stronger ideal target above.

Let r be the minimum weight over all inputs, directions, and omission sets.
`robustness_score = min(1, r/3)`. A family score is
`min(ideal_score, robustness_score)`; `core_score` and `worst_family_score` are
the minimum family score. Passing requires all ideal inequalities AND r >= 3
for every family. Neither means nor other families compensate for one failure.

The checker is exhaustive and uses binary symplectic arithmetic, not Monte
Carlo, a restricted list of faults, or adversarial sampling. Reports give exact
scenario counts, fault-order minimum histograms, failing-scenario counts,
stratum minima, and a counterexample with original omission IDs and input Pauli.
`one_dropped_cx` and `three_dropped_cx` summarize mandatory checks and affect
passing. The checker streams one omission scenario at a time; it does not
allocate a fault-scenario-by-Pauli array or retain all faulted circuits. Memory
does not grow with the number of omission subsets. `peak_rss_bytes` reports the
evaluator process's measured peak resident memory, not a solver resource gate.

The new requirement isolates structural sensitivity to missing entanglers under
hardware/compiler omissions: even with three omissions a low-weight Pauli must
spread strictly beyond two sites. It is not a model of arbitrary physical noise,
nor a claim that gate-loss robustness is an assumption/theorem of the source paper.
This is generation 3, the second and final ratchet. No ideal threshold, native
budget, gate alphabet, or mean constraint has been tightened in either ratchet.
There will be no further ratchet after this generation, regardless of outcome.

## Interpreting a block as an Omega building block

The source motivation is the rapid local error randomization/spreading and
inverse symmetry conditions on Omega in Proctor et al., arXiv:2112.09853v2,
"Randomized mirror circuits." This construction benchmark is not a reproduction
of their experiments or their infidelity formula. Its stronger worst-case
low-weight support objectives are a finite design certificate, not proof of an
approximate unitary design or the full distributional/noise assumptions of MRB.

Choosing C or C-inverse with equal probability gives inverse-symmetric block
support. Independent uniform local Clifford layers on both ends additionally
randomize local axes; their inversion swaps the two identically distributed
end layers. Such local dressing only permutes low-weight inputs and preserves
output supports, so these exhaustive weight guarantees persist. External
dressing is a possible downstream use, not hidden free entanglers inside the
submitted block. This finite-support certificate alone does not establish
rapid global mixing of arbitrary-weight errors under repeated Omega sampling.
