# Pilot 03: analog quantum memory

## Written before implementation and data generation

This is a bounded research pilot, not a claim to reproduce the paper's published
thresholds. The participant must infer a physically consistent error history
from continuous, noisy repeated parity measurements. The decoder backend is not
the scientific target: soft readout likelihoods and coupled space/time syndrome
constraints are. All implementation, generated data, reports and attempts stay
inside `pilots/03_analog_memory`.

## Anti-compression requirements

- Do not reduce the benchmark to a small independent `[H I]` decoding example.
  Use an actual lifted-product instance supplied by MQT and a periodic
  three-dimensional toric code with local cube metachecks, multiple noisy rounds,
  an exact final boundary, and accumulated data errors.
- Score final logical recovery and intermediate syndrome reconstruction
  independently. Require the reported syndrome history to arise from the
  submitted data increments; check every metacheck and the exact final boundary.
  Logical equivalence, not agreement with a particular reference correction,
  defines successful final recovery.
- Include independently generated hard-readout and no-time ablations privately.
  A weak baseline must not use hidden truth or analog magnitudes. The official
  soft multiround reference must have genuine measurable headroom over the weak
  baseline; record raw statistics and all tuning on the pilot split only.
- Normalize continuously as `(quality - weak) / (reference - weak)`, with no
  clipping at zero or one. Invalid submissions receive a separately documented
  finite failure score. Report each core metric, each code family, runtimes,
  reference/weak anchors, and the minimum family score. Do not reward exact
  matching of reference outputs or compress multiple bottlenecks into one LER.
- No large labeled public development corpus. Public input is a small unlabeled
  schema example; private pilot/challenge/holdout use disjoint RNG seeds. Fresh
  challenge regeneration must be possible after the participant attempt is
  frozen, without changing the task or evaluation contract.
- Do not give the participant a paper, analog source implementation, decoding formulas,
  reference outputs, error histories, private seed manifest, or scoring anchors.
  The mission and complete NPZ schema are sufficient. A trivial executable
  starter is permitted; it must not implement the reference method.

The main agent later authorized reuse of pilot01's original binary prestate.
The builder stages that unchanged 2020 native BP+OSD source snapshot and the
generic minimum-sum Python helper, recording file hashes in `prestate.json`.
This intentionally removes base-BP implementation as the task's main obstacle;
it does not supply analog likelihood construction or temporal/meta integration.
The upstream license is preserved. The user supplied its attribution through
the other agent; this sidecar does not redo that repository's history research.

## Primary provenance

- Berent, Hillmann, Eisert, Wille, Roffe, *Analog information decoding of bosonic
  quantum LDPC codes*, arXiv:2311.01328v2 (2024-06-10), PRX Quantum 5, 020349.
  https://arxiv.org/abs/2311.01328
  https://doi.org/10.1103/PRXQuantum.5.020349
- Author implementation: https://github.com/munich-quantum-toolkit/qecc
  Local read-only source: `research/sources/qecc` relative to the paper root.
  Relevant modules are `analog_information_decoding/simulators/` and
  `analog_information_decoding/utils/`. The builder records the actual Git SHA
  and SHA256 of every imported upstream file and source matrix in its manifest.
- Lifted-product parity checks: official MQT
  `src/mqt/qecc/codes/instances/lifted_product/lp_l=16_hx.npz` and `_hz.npz`.
  Three-dimensional toric boundary matrices are generated from a periodic cubical
  cell complex, with independently checked chain identities and GF(2) ranks.
  This is the same topological family discussed in the source paper, not a
  downloaded experimental dataset or a claim that every matrix is supplied by
  MQT. Use explicit source attribution for this distinction.
- The source paper's numerical model is phenomenological. This pilot likewise
  does not claim circuit-level cat physics, measured IQ traces, or fault-tolerant
  logical gates. A final ideal boundary is supplied explicitly in the input.
- Numerical dependencies come from the main agent's private `research/vendor`.
  Record observed versions, rather than assuming the vendor directory name is
  authoritative. The evaluator must not add author reference code to the
  participant import path.

## Reference and readiness policy

Import the official multiround construction/likelihood functions without loading
unrelated Qiskit functionality. Document any interface adapter separately from
the upstream algorithm; do not silently repair or call a different implementation
official. Precompute actual reference and baseline predictions before launch.
The current upstream analog example is not the runnable contract: it references
missing logical-operator files and has interface drift. Use inspected module APIs
and derive/verify logical operators from the supplied check matrices instead.

The evaluator launches `solve.py --input CASE.npz --output ANSWER.npz` once per
case using the main agent's verified `research/isolation.py::run_submission`.
Bwrap exposes only the submission, public participant directory, staged case,
output directory and system runtime. It does not expose private files, the
source clone, labels or other pilots. Actual evaluator calls require the main
agent's escalated execution environment. No model agent is launched by this
builder. Private replay submissions are author-only fixtures for checking the
0/1 anchors through this same isolated protocol, not participant solutions.

The history core excludes the final row, because that exact syndrome is already
provided. All histories still have to satisfy their final boundary. Malformed
outputs get zero raw quality in both cores; normalization is unchanged and can
therefore produce negative scores. Reference timings use `time.process_time`.
Submission algorithm cost is `user_seconds + system_seconds`, not host-jittery
wall time. The limit is 120 CPU seconds per case with a 360-second wall safety
timeout; CPU and wall timings are reported separately.

## Bounded execution

After inspection of the original 16-shot pilot, the user required a genuinely
strong raw reference rather than a normalization-only anchor. The final initial
corpora therefore use 128 independent shots per case and require reference
logical accuracy strictly above 0.9 in every case, with Wilson intervals recorded.
Only physical data/readout noise was reduced: all code sizes and round counts
remain unchanged, including both 544-qubit lifted-product cases with 3 and 5
noisy rounds. Earlier small-corpus logs are retained as superseded calibration.
Holdout generation is now reserved until initial-attempt inspection: old files
are unused, the evaluator rejects an unmarked holdout, and a future explicit
`--split holdout --fresh` is required. No all-splits build command remains.

During the first larger challenge build, the unmodified finite-prior boundary
produced a fault in the ideal terminal interval. Generation stopped; no failing
shot was discarded or resampled. The revised author adapter conditions the
official multiround problem exactly by removing its known-zero terminal data
and measurement columns, expanding the returned vector into the original source
layout, and checking that it satisfies the full source matrix equation. This
preserves the official graph, likelihood conversion, decoding algorithm and
window convention while enforcing this task's declared perfect boundary. Both
soft reference and hard-window ablation use the same projection. All splits must
be regenerated after this interface correction. This is explicitly an adapter,
not a claim that upstream already implements a hard terminal constraint.

Start with a small number of cases and at most a few hundred shots per private
split. Keep source matrices sparse while constructing the multiround reference.
Reference output, ground truth, checksums and parameter/seed manifests remain
private. Runtime limits apply equally per case; timeouts count as failures, not
dropped shots. Report observed execution times rather than promising real-time
hardware operation.
