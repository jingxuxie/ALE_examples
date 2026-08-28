# Frontier-hard task mining report

**Final decision: reject this four-concept round. No task meets the frontier-hard acceptance gate.**

Target: *Decoding Across the Quantum LDPC Code Landscape*, arXiv:2005.07016. Four concepts were built, not four variations of one simulator. All scored attempts use the requested `ultima-alpha` model, high reasoning effort, the supplied allowlisted runner, an initially empty submission directory, and a 3,600-second wall limit. Authoring artifacts and reference implementations remain outside each participant allowlist.

## 1. Candidate directions

The complete per-candidate starting artifact, private solution artifact, outcome, shortcut, scale limitation, independent bottlenecks, and validation procedure are in `research/CANDIDATES.md`.

| Direction | Candidate gap | Privileged artifact | Disposition |
|---|---|---|---|
| A: pre/post fix | Decoder lifetime/native-memory correctness | `ldpc` 2.4.1, PR #97, original memory-leak history | Not built; a small ownership fix alone is insufficiently hard |
| B: original/follow-up | Global BP/OSD to localized sparse recovery | Official BP+LSD and on-the-fly elimination | Built as 01 |
| C: realistic scale | Long-memory overlapping-window inference | Official window decoder and commit/buffer logic | Not built in this four-concept round |
| D: physical-family transfer | Biased, correlated Pauli recovery in Clifford frames | Bias-tailored 416/882-qubit codes and correlation updates | Built as 02 |
| E: real-data discrepancy | Analog device readout, fidelity mismatch, leakage | Surface-13 analysis and neural-decoder artifacts | Not built; reproducible trained-reference/data admission gates remain |
| F: integration | Clifford extraction to detector/observable error models | Official Stim compiler and later circuit integration | Built as 04 |
| G: missing ablation | Correlation-safe, matched-channel decoder comparisons | Joint-channel and analog comparison data/scripts | Not built; proposed ablation, not a proven original-paper defect |
| H: correctness/performance | Reliable-subset reduction and approximate degeneracy | MBP+ADOSD source, pinned February 2026 implementation | Audited, not a fifth pilot; no drop-in accuracy upgrade demonstrated |
| I: additional follow-up | Analog, temporally consistent quantum-memory recovery | MQT-QECC analog decoding and augmented inference | Built as 03 |

Key pinned sources:

- Original native pre-state: `quantumgizmos/bp_osd` commit `74f86d3ef00f04bbb90a043dfef52e92a091f4d3`, July 22, 2020.
- Later decoder: `quantumgizmos/ldpc` commit `d3429964cd4ffe1abfc041c6ec8b8425cb174f40`, package 2.4.1.
- Compiler: official Stim 1.16.0.
- Additional audited source: `cylai-nycu/MBP_ADOSD` commit `094149da7c6147704b544636baf6937f688d01f9`.

The target's appended material is in its 15-page version, Appendices A–C. The source ledger links the original paper, follow-ups, repository history, PRs, data, and implementations. Publicly available later source is *privileged by filesystem isolation* here; it is not described as secret or unpublished.

## 2. Four minimal pilots

| ID | Mission | Central, independently checked requirements | Scale actually evaluated |
|---|---|---|---|
| 01 | Sparse recovery service | Syndrome validity; logical equivalence; sparse postprocessing efficiency | Up to 116,265 circuit-fault variables; HGP blocks up to 25,920 variables |
| 02 | Biased Pauli recovery | Symplectic/frame correctness; joint Pauli likelihood; logical preservation | Official 416- and 882-qubit blocks; 128 shots/profile initially, 256 in challenge |
| 03 | Analog quantum memory | Final logical recovery; consistent, accurately reconstructed intermediate history | 3D toric and 544-qubit lifted-product memories; four 128-shot cases/split |
| 04 | Circuit-to-detector compiler | Clifford propagation; detector/observable bookkeeping; probability aggregation; throughput | Initial largest HGP circuit: 242,608 fault events; extended test: 381,074 events |

Each pilot has `participant/TASK.md`, `participant/input/`, `participant/workspace/`, `private/reference/`, `private/challenge_pool/`, `private/evaluator.py`, and an isolated `attempt/`. Complete interface details live separately from the concise missions. Existing native BP/OSD code is supplied where relevant, rather than withholding the already-solved 2020 workflow. Later reference modules and hidden outcomes are not supplied.

### Anti-compression and scale checks

The pre-build audits are preserved in each `private/reference/design.md`. They are hypotheses tested empirically, not hardness certificates.

- A native global BP+OSD_CS8 configuration consumed at least 588 seconds at 99.9% CPU without finishing the 12-shot HGP stage. The localized reference processed the full 192-shot batch in 3.93 CPU seconds.
- A bounded native OSD-0 run also failed to finish that HGP stage within its 120-second wall allowance. This does **not** establish that every optimized global method is slow.
- Serial BP alone recovered only 31.25% of the circuit batch, taking 142.42 CPU seconds at 30 iterations and 401.82 at 100; increasing iterations did not improve that observed accuracy. Other schedule measurements are preserved in `research/bp_schedule_baselines.json`.
- The forward per-fault compiler exhausted eight CPU seconds on realistic surface and HGP cases, while the official reference passed.
- Nevertheless, the fresh agent implemented effective specialized algorithms. A baseline failure is not evidence that a frontier model cannot solve the task.

## 3. Initial tournament

Scores below share the convention **weak = 0, strong reference = 1**, with no upper clipping. The compiler's original `score` field is in percentage units; its `mean_core` and `worst_family` aliases are normalized. The conservative reported worst branch is retained instead of averaging away a difficult case.

| Pilot | Fresh mean core | Worst family/branch | Model wall seconds | Outcome |
|---|---:|---:|---:|---|
| 01: sparse recovery | 1.068402 | 1.038122 | 2721.05 | Solved |
| 02: biased Pauli | 1.104094 | 1.000000 | 2884.82 | Solved relative to the source reference |
| 03: analog memory | 1.000744 | 1.000029 | 1986.65 | Solved |
| 04: compiler | 1.585852 | 0.820929 | 1806.58 | All semantic outputs exact; no unsolved central component |

All normalized reference audits pass at 1.0. These normalized values are not substitutes for raw reliability:

- 01 initial raw reference logical accuracies are 95.57%, 96.875%, and 100%; the submitted decoder attains 96.61%, 96.875%, and 100%.
- 03 reference and submission both recover all 512 logical frames in the initial split. History quality is independently measured.
- 02 initial raw reference accuracies are `[1.000, 0.703, 1.000, 0.891]`; challenge values are `[1.000, 0.395, 1.000, 0.555]`. In particular, the correlated-noise anchors are not represented as >90% raw-success oracles.
- 02 initial submitted accuracies are `[1.000, 0.922, 1.000, 0.984]`, with all 512 corrections syndrome-consistent.
- 04 compares semantic detector/observable mechanisms and their probabilities, not arbitrary output ordering.

Complete scored reports are in `research/scores/tournament/`; run metadata, participant before/after hashes, requested model, exact prompt, time budget, and logs are in `research/runs/tournament/`.

The requested lexicographic screening order, lower worst-family score first and then lower mean, is **04, 02, 03, 01**. Thus 04 and 02 are the provisional strongest two for counterexample inspection. All four were audited, rather than rejecting the others solely on a predicted generic shortcut. The low compiler branch is examined as a resource/semantic distinction, not automatically counted as an unsolved component.

## 4. Counterexamples and reusable solutions

### 01: no systematic private advantage found

The unchanged submitted solution scores **1.114263 mean / 1.098247 worst** on the larger challenge pool. It recovers all HGP and circuit frames, taking **1.16 / 15.27 CPU seconds**, respectively, compared with reference **5.95 / 94.53 seconds**.

On the high-rate code it succeeds on 360/384 frames versus reference 345/384. There are four reference-only successes but nineteen submission-only successes. Three reference-only wins have exactly equal correction likelihood and differ by weight-six logical operators; in the fourth, the submitted correction has *lower* negative log likelihood than the reference. These are not evidence that the reference found lower-cost corrections which the submitted search missed. Selecting only those four lucky reference outcomes would manufacture a private-answer preference rather than demonstrate a systematic capability gap.

The solution is not merely dense Gaussian elimination: it combines efficient BP, localized sparse elimination, local cycle improvement, and budgeted ordered-statistics searches. It implements the intended difficult capability. Evidence: `research/scores/local_challenge.json` and `research/scores/local_counterexample_audit.json`.

### 02: joint-channel inference exceeds the official correlation update

The unchanged submission scores **1.293369 mean / 1.000000 worst** on the original 1,024-shot challenge pool. It succeeds on **892/1,024** frames versus reference **755/1,024**, with all corrections syndrome-consistent. CPU time is **89.88 seconds total**, at most **43.28 per case**; peak RSS is **37,492 KiB**.

| Family | Submitted raw success | Reference raw success |
|---|---:|---:|
| 416-qubit Hadamard transfer | 100.00% | 100.00% |
| 416-qubit correlated Clifford transfer | 67.97% | 39.45% |
| 882-qubit Hadamard transfer | 100.00% | 100.00% |
| 882-qubit correlated Clifford transfer | 80.47% | 55.47% |

Paired outcomes are **2 reference-only wins, 139 submission-only wins, and 130 shared failures**. Both reference-only wins are ordinary-load, near-likelihood-tie cases: one submitted correction is 0.051 nats more likely, while the other reference correction has a small 0.198-nat advantage. The latter is a genuine finite-candidate-ranking opportunity, not evidence of a missing correlation mechanism. Every submission-only win has a much larger submitted representative-likelihood advantage, between 21.62 and 95.43 nats. Representative likelihood is not claimed to equal exact logical-coset posterior mass.

The heavier-error tail is genuinely difficult, but the above-one-standard-deviation bin has **zero reference-only wins and 58 shared failures**. It is not a region where the private source solves what the participant cannot. The submitted decoder already transports complete four-state priors through frames, performs correlated BP, combines ordered-statistics candidates, and applies stabilizer-preserving descent. No systematic source advantage or missing source-existing mechanism was found. Evidence: `pilots/02_biased_pauli/private/reference/postpilot/REPORT.md`, its paired diagnostics, and `challenge_report.json`.

### 03: reusable space-time inference solves the challenge

The unchanged submission recovers **512/512 logical frames** on the original challenge pool, scoring **1.001098 mean / 1.000034 worst**. Its observed history accuracy exceeds the reference in every case. Runtime is **50.79 CPU seconds total**, at most **19.03 per case**, with peak memory about **50.3 MiB**.

It uses calibrated space-time augmentation, BP/OSD ensembles, explicit metachecks, all-pairs temporal-cancellation moves, and history refinement. No missing analog or temporal mechanism was identified. A nonspecific noise sweep was not used to manufacture a new failure claim. Evidence: `pilots/03_analog_memory/private/reference/postpilot/audit.md` and its replay report.

### 04: exact sparse reverse propagation is a universal solution here

All six initial outputs are exact. The lower small-case score reflects variable startup/output/system overhead around 4–8 ms of compilation, not a semantic failure.

Two additional, source-grounded longer-memory regimes were tested without changing the public contract or budgets:

| Regime | Fault events | Submission CPU seconds | Full official wrapper CPU seconds | Result |
|---|---:|---:|---:|---|
| Surface d=7, 512 rounds | 381,074 | 0.76 | 2.41 | Exact |
| HGP n=76, 128 rounds | 223,512 | 0.68 | 2.75 | Exact |

Both pass eight CPU seconds and 1,536 MiB. The submitted compiler already uses sparse sensitivity sets and lazy repeat traversal, avoiding the hypothesized global-bitset failure. Zero verified counterexamples were found in this audit. Evidence: `pilots/04_circuit_compiler/private/reference/postpilot/SUMMARY.md`.

## 5. Stronger-source audit, not a fifth concept

The official MBP+ADOSD C programs compile unmodified, and their Pauli representation maps correctly to the existing 882-qubit fixture. However, their Pauli initializer accepts a homogeneous scalar channel, whereas pilot02 supplies per-qubit four-state priors. A supplied-syndrome batch driver and source-based prior initializer are needed. No native-on-pilot accuracy improvement was demonstrated; no reference anchor was silently replaced. See `research/adosd_audit/FEASIBILITY.md`.

## 6. Integrity and reproducibility

- Private evaluation executes submissions in a network-isolated, restricted-filesystem container. Only participant/submission files, one sanitized input, an empty output directory, and OS runtimes are mounted. Original participant/submission paths are preserved as aliases.
- CPU time, wall time, memory, syndrome consistency, and raw correctness are reported separately. Large mount/startup jitter is not treated as algorithmic hardness.
- Initial authoring caught accidental distance-two classical constituents and explicit zeros in an official sparse logical-operator fixture. Scored corpora were regenerated and serialization audited before scoring. See `research/AUTHORING_AUDIT.md`.
- Two startup-only aborted launcher invocations are excluded from solver scores. One had reached read-only discovery commands, but neither produced a solver. Full details are preserved in `research/runs/INFRASTRUCTURE.md`; the corrected launcher closes stdin explicitly.
- The initial Pauli report-path failure occurred before decoder execution. It was repaired in the collector, not counted as a solver failure; the direct and collector replays agree exactly on quality scores.
- No held-out confirmation case is represented as fresh after having been inspected. Reserved pre-ratchet analog holdout files are blocked and unused.
- No success is inferred from an agent's self-report: the stored submitted artifacts are executed against hidden cases.
- Final integrity checks pass for all four pilots: model, one-hour limit, successful completion, complete minimal layout, report consistency, unchanged public files, and unchanged submitted artifacts. See `research/scores/final_integrity.json`.

To replay an initial score from this output directory, run the relevant `pilots/CONCEPT/private/evaluator.py` with `--submission pilots/CONCEPT/attempt --split pilot --report pilots/CONCEPT/private/reference/evaluations/replay.json` in an environment that permits the restricted `bwrap` child. The report must remain inside the pilot for evaluators with confined output paths. Use `--split challenge` for the existing challenge pools. Alternatively, `python research/evaluate_tournament.py --concept CONCEPT` reruns only that initial evaluation and collects its report. Neither procedure launches a new model or exposes private files to the submitted program.

## 7. Final gate and decision

**Accepted task: none.** All four one-hour fresh attempts finish successfully, and every initial mean core score is at least 1.0 relative to the frozen source reference. The lowest worst-branch score is 0.820929; no evaluated concept reaches the requested below-0.70 hardness gate. More importantly, the source-grounded challenge audits do not reveal a substantial source-existing capability that remains unsolved.

The compiler has a reusable exact sparse reverse-propagation solution; Pauli recovery has no reference-advantage family or error-load region; localized recovery implements the intended specialized methods; and analog memory implements both temporal and analog inference. Generic direct baselines failing at scale did not prevent the fresh agent from building these stronger solutions.

- **Concepts built:** four, within the maximum of four; nine candidate directions documented.
- **Scored fresh initial attempts:** four, all `ultima-alpha`, each below 3,600 seconds.
- **Counterexamples:** six isolated reference-only decoding wins across 01 and 02, none establishing a systematic hard region; zero semantic compiler failures in the additional regimes; no remaining analog mechanism failure.
- **Ratcheted concepts:** zero. No natural failure region justifies a source-grounded ratchet, including for the provisional strongest two.
- **Fresh ratchet holdouts:** zero. Previously reserved analog cases are not relabeled as fresh.
- **Second-model/confirmation attempts and scores:** not run / not applicable, because no concept survives counterexample eligibility. These stages are not claimed to have been executed.
- **Production task:** not created or represented as accepted. Pilot artifacts, private references, attempts, diagnostics, and logs are retained for audit.

This is a rejection of the **four concepts tested in this bounded round**, not a proof that no harder task can be derived from this paper or its follow-ups. Tightening timers, selecting lucky logical outcomes, replacing weak reference anchors without validation, or inventing a fifth concept would not satisfy the requested loop. The machine-readable decision is `selection.json`.
