# PRIVATE contingency candidate search

Date: August 28, 2026. This directory is a private sidecar, not an installed generation.
Main reported that generation1 fresh v2 passed officially with score 1.0; main owns
archival, historical-method screening, input-reader changes, and any promotion.
Nothing here installs a task or changes an active test. No participant, attempt,
champion, evaluator, status, shared-runner, or other-task file was edited. No
participant/attempt/champion code was inspected. No fresh agent was launched.

**Structural hardness is hypothesized, not empirically proven until a fresh
attempt.** These certificates demonstrate source-native feasibility, substantial
operator entanglement, and complete local causal mixing. They do not prove a
minimum CNOT count, exclude a more compact circuit, or establish inverse-search
difficulty. No lookup-failure experiment or solver attempt was run. Main's planned
gen0 analytic-gradient topology-portfolio screen can provide only explicitly
limited historical-method evidence, not a replay of the unavailable v2 method.

## Ready paths

Paths in this report are relative to this private directory.

- `pool/inputs/n8_m80_01.json`: 8 qubits, exactly 80 CNOT + 168 U3 in its witness.
- `pool/witnesses/n8_m80_01.json`: corresponding private native gate list.
- `pool/statistics/n8_m80_01.json`: full causal certificate and all-cut statistics.
- `first_candidate_audit.json`: immediate independent dense and direct-commutator audit.
- `pool/inputs/n8_m72_03.json`: qualified 8-qubit alternative, 72 CNOT + 152 U3.
- `pool/inputs/n7_m60_01.json`: qualified 7-qubit alternative, 60 CNOT + 127 U3.
- `pool/metadata.json`: all eight certificates, seeds, hashes, exact budgets,
  qualification decisions, dependency versions, and resource measurements.
- `verification.json`: independent serialized-artifact verification for all eight.
- `input_reader_audit.json`: all eight pass the updated 8-MiB input reader,
  1-MiB witness reader, and current scoring kernel without invoking a runner.

The first 8q/80 candidate has middle-cut effective rank 88.5551 out of 256,
participation and tail statistics in its certificate, 15.1055% squared Schmidt
weight beyond rank 64, and needs rank 157 to retain 99% of that weight. Its
smallest normalized middle-cut coefficient is 5.99636e-5; its minimum across
all 127 bipartitions is 2.24218e-5. It therefore has substantial spectral weight
beyond a small-rank approximation, not merely algebraic full rank supported
by numerical dust. Its minimum normalized squared Pauli commutator is 0.708099;
the conservative lower bound for arbitrary pairs of real unit Bloch axes is
0.518313. These are measured structural facts, not a hardness result.

## Bounded sample and outcomes

Exactly eight dense candidates were examined: three 8q/80, three 8q/72, and two
7q/60. Five pass all fixed structural thresholds. Three are retained as rejected
diagnostics; **do not treat a valid witness as structural qualification**. There
was no angle resampling or extra dense search after seeing the results. Topology
proposals before each one-shot angle draw are recorded separately.

| Candidate | Structural qualification | Middle effective rank(s) | Minimum all-cut normalized coefficient | Minimum Pauli squared commutator | Minimum arbitrary-axis Gram eigenvalue |
| --- | --- | --- | --- | --- | --- |
| n8_m80_01 | Pass | 88.5551 / 256 | 2.24218e-5 | 0.708099 | 0.518313 |
| n8_m80_02 | Pass | 66.9268 / 256 | 1.32148e-5 | 0.747611 | 0.444090 |
| n8_m80_03 | Reject | 66.4013 / 256 | 4.80583e-6 | 0.553886 | 0.426748 |
| n8_m72_01 | Reject | 58.0105 / 256 | 2.00428e-5 | 0.538287 | 0.302059 |
| n8_m72_02 | Reject | 48.8711 / 256 | 1.17633e-5 | 0.447860 | 0.349572 |
| n8_m72_03 | Pass | 76.4367 / 256 | 1.24390e-5 | 0.625885 | 0.284051 |
| n7_m60_01 | Pass | 39.7602, 43.7285 / 64 | 0.0346833 | 0.772583 | 0.646975 |
| n7_m60_02 | Pass | 41.1480, 45.1456 / 64 | 0.0332300 | 0.595173 | 0.261028 |

The two rejected 8q/72 cases miss the predeclared middle-cut effective-rank
fraction floor of 0.25. The rejected 8q/80 case misses the 1e-5 smallest-coefficient
floor on the noncontiguous bipartition {1,3,4,6}|{0,2,5,7}. Its chain cuts alone
would not expose that weakness. All eight nevertheless have full numerical rank
at both stated rank tolerances and all eight have complete causal mixing.

Chain ranks are `[4,16,64,256,64,16,4]` for every 8q case and
`[4,16,64,64,16,4]` for every 7q case. The full certificates cover **every**
nontrivial bipartition, modulo complementation: 127 per 8q case and 63 per 7q
case, not merely contiguous chain cuts. Effective-rank fractions and tail
weights are recorded for all cuts; full singular spectra are stored on chain
cuts without duplicating the target matrices.

## Construction and thresholds

Only current-kernel-native U3 and bidirectionally oriented nearest-neighbor CNOT
gates are used, with little-endian qubits and first-listed-first-applied ordering.
An initial U3 on every qubit is followed by two endpoint U3 gates after every
CNOT, giving **exactly `max_u3 = 2*max_cnot+n`**, with no slack.

The nonperiodic schedules are randomized connected rounds with extra interior
crossings and randomly permuted near-balanced edge orientations. Every edge
occurs in every temporal quarter; consecutive CNOTs never use the same edge.
Counts by edge are `[8,10,12,12,10,8]`, `[8,10,12,12,12,10,8]`, and
`[9,11,13,14,13,11,9]` for 7q/60, 8q/72, and 8q/80 respectively. Generic
undirected dependency cones must saturate in both temporal directions by 80%
of the schedule. This topology test is only a necessary screening proxy; the
dense Heisenberg tests certify actual nonvanishing influence.

For n8_m80_01 all sources reach all sites by CNOT 33 forward and 35 in reverse,
well before its 80th CNOT. Complete actual Pauli/axis mixing is checked separately.
All sampled U3 angles are finite and moderate: cos(theta/2)^2 is uniform on
[0.1,0.9], while phi and lambda have independently random signs and magnitudes
uniform on [0.25,pi-0.25]. These are conditioned random angles, not unconditioned
Haar samples. The minimum phase-invariant normalized U3-to-identity distance
across the pool is 0.339382; dense targets have distance at least 1.40581 from
identity. There are no deliberately tiny identity-like gates or target matrices.

Predeclared structural acceptance thresholds, unchanged after sampling:

- Full Schmidt rank at absolute singular-value tolerance 1e-10 and relative
  tolerance 1e-6, on every bipartition.
- Smallest normalized Schmidt coefficient at least 1e-5 on every bipartition.
- Effective-rank fraction at least 0.75, 0.50, 0.35, and 0.25 for maximum ranks
  4, 16, 64, and 256 respectively.
- Every Pauli squared commutator at least 0.08 and every site-pair 9x9 real
  commutator-Gram minimum eigenvalue at least 0.04, in both directions.

## Meaning of the statistics

For each bipartition A|B, realign the unitary as `(out_A,in_A)|(out_B,in_B)`.
With dimension `d=2**n`, normalize its singular values as `sigma=s/sqrt(d)`.
The probabilities are `p=sigma**2` normalized to sum to one. Effective rank is
`exp2(-sum(p*log2(p)))`; participation rank is `1/sum(p**2)`. Certificates also
record 99%-weight rank, tails beyond ranks 4/16/64 and half maximum rank,
condition number, and minimum normalized coefficient.

For both `U P_i Udag` and `Udag P_i U`, the tested causal quantity is
`C[i,j,a,b] = ||[evolved(P_i^a),P_j^b]||_F**2/(2*d)` for all sites i,j and
all nine pairs of Pauli axes a,b. The normalization gives 0 for a commuting
pair and 2 for an anticommuting pair of unitary Paulis. This includes same-site
pairs, both endpoint directions, and every interior pair. There are 1,152
evaluations per 8q case, 882 per 7q case, and 8,676 over this pool.

For each site pair the nine commutators also form a real 9x9 Gram matrix with
entries `Re(vdot(C_ab,C_cd))/(2*d)`. For arbitrary unit real Bloch axes x,y,
the corresponding squared commutator equals
`(x tensor y)^T G (x tensor y) >= lambda_min(G)`, since `||x tensor y||=1`.
Consequently a positive certified minimum rules out vanishing commutators
even for arbitrary normalized traceless single-qubit Hermitian observables,
not just the chosen Pauli basis. Identity components are necessarily excluded;
identity always commutes. The reverse-direction data obey the transpose
relation and are checked explicitly, not claimed as independent evidence.

Background terminology: Paolo Zanardi, *Entanglement of Quantum Evolutions*,
arXiv:quant-ph/0010074; *Operator Spreading and the Emergence of Dissipative
Hydrodynamics under Unitary Evolution with Conservation Laws*, Physical Review X
8, 031057. These are conceptual background only; they make no hardness claim
about the private candidates. All candidate numbers in this report come from
the local computations and certificates, not those papers.

## Independent verification and precision

Targets are produced by the allowed authoring `dense_reference.py`, using full
Kronecker-embedded matrices and dense multiplication. They are compared with the
current evaluator kernel's row-update circuit implementation. A random private
global phase is then applied; no source topology or seed enters an input JSON.
Saved witnesses are reparsed through the kernel's capped strict JSON reader,
and saved inputs through its strict JSON parser, before current-kernel scoring.
All eight saved witnesses pass with score 1.0 and exact gate budgets.

`verify_pool.py` independently reconstructs every full dense witness again,
checks input/witness/statistics hashes, replays every private seed exactly,
audits nearest-neighbor connectivity and angles, recomputes all 888 bipartitions
and all 8,676 bidirectional commutators, and rescores the serialized artifacts.
It additionally checks 54 commutators per candidate by explicit Kronecker
embeddings and dense left/right multiplication, independently of the fast
Pauli-permutation implementation, including both endpoint directions and an
interior same-site pair. Analytic controls cover identity/CNOT/SWAP Schmidt
ranks, identity causal zeros, Pauli normalization, Y signs, and endianness.

Across the generated pool, maximum independent dense/row-update entry error is
3.77967e-16, maximum unitarity Frobenius defect is 4.07119e-14, maximum scored
phase-aligned normalized Frobenius discrepancy is 1.36622e-15, and maximum
reported infidelity is 4.88499e-15. Computation uses complex128; JSON preserves
round-trippable Python binary64 values without lossy rounding. These are
numerical certificates with explicit thresholds, not interval-arithmetic proofs.

## Reproduction, resources, and packaging

Run from this private directory. The generator refuses an existing output
directory and rejects output paths outside its own private scope. The seed is
private and must not be copied into participant-visible files.

```sh
python -B verify_pool.py
python -B generate_pool.py --workers 2 --seed "$(python -B -c 'import json; print(json.load(open("pool/metadata.json"))["master_seed"])')" --output replay
python -B verify_pool.py --pool replay --report replay_verification.json
```

The default run is exactly eight candidates with no unbounded dense rejection
loop. Seed replay in verification does not generate new target candidates.
Runtime versions were Python 3.10.12 and NumPy 1.21.5, PCG64 with per-candidate
SHA256-derived seeds. Source hashes are recorded in the manifest. Exact hashes
of regenerated floating-point matrices can depend on NumPy/BLAS/platform;
use the independent toleranced verifier rather than assuming cross-platform
bitwise matrix equality.

Generation used two local single-thread-BLAS processes, took 56.97 seconds, and
reported a maximum per-worker RSS of 79.93 MiB. No generator agents were used.
One ad-hoc standalone audit initially imported NumPy before setting thread
limits and was interrupted, only within this private directory; its capped
rerun passed. Both saved scripts set thread limits before importing NumPy.
Full independent verification is single-process and records its time and peak
RSS in `verification.json`. No dependency installation was necessary.

The first full independent verification took 92.54 seconds at 87.22 MiB peak
RSS. A final source-hash audit detected that the evaluator kernel changed
concurrently outside this sidecar while generator and dense-reference hashes
remained unchanged. Verification is rerun against the updated kernel; its report
records generation-time and verification start/end kernel hashes rather than
silently conflating the two snapshots. The initial maximum direct-commutator
and Gram-eigenvalue cross-check errors were 4.663e-15 and 2.332e-15 respectively.
The task directory is not inside a discoverable Git repository, so the changed
file inventory is filesystem-based rather than a Git diff.

Compact single-line 8q inputs are 2,754,049-2,754,834 bytes (about 2.63 MiB),
and 7q inputs are 683,811-683,957 bytes. All witnesses are 15,580-20,640 bytes.
The 8q inputs exceed the old 1-MiB `kernel.read_json` limit; the verifier confirms
that rejection separately and does not disguise it as an end-to-end runner
pass. Main has stated that it will separate an 8-MiB public-input limit from the
1-MiB witness-output limit. That integration is outside this sidecar; no kernel
or runner was changed here. Each candidate input individually fits 8 MiB;
concatenating several targets requires a separate size audit.

Changed/created files are confined to this directory: `generate_pool.py`,
`verify_pool.py`, `REPORT.md`, `search.log`, `verification.log`,
`first_candidate_audit.json`, `input_reader_audit.json`, `verification.json`, `pool/metadata.json`, and
eight files apiece in `pool/inputs/`, `pool/witnesses/`, `pool/statistics/`.
No duplicate combined dense-matrix pool is written. The generated artifacts
occupy about 18.2 MiB before any optional replay. Keep the entire directory,
including logs and this report, private; only an explicitly selected input JSON
is public-style and eligible for main's separately authorized promotion.
