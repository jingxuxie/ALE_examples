# Experimental controls and corrections

- Exactly four substantive fresh CLI sessions are launched, all with
  `ultima-alpha`, xhigh effort, read-only participant packages, empty writable
  attempt directories, and 3,600-second limits. The supplied allowlist runner
  is used without changing its permission policy. Research/validation helpers
  are authoring agents, not additional pilot models or concepts.
- An initial log prefix, `Reading additional input from stdin...`, was
  temporarily mistaken for a stalled launcher. The repair script's guard
  found that inference had already begun and refused to stop or restart
  anything. The original sessions continued. Later launches explicitly close
  stdin. This is not a failed pilot or task-difficulty observation.
- Submitted programs run under a separate bubblewrap sandbox: system runtime
  files and the participant tree are read-only, only the submission directory
  and an empty temporary filesystem are writable, the private tree is absent,
  and networking is disabled. `sandbox_validation.json` tests actual denial
  of a private-file read and a network connection, as well as permitted task
  access. The author is privileged; the submitted process is not.
- Namespace construction was initially included in elapsed time. The retained
  `reports/ewoc_pilot_initial_timing.json` records that initial measurement.
  An author-controlled marker emitted immediately before exec now excludes
  grader sandbox setup, while retaining the submitted entrypoint's Python
  startup, compilation, parsing, calculation, and output time. EWOC was
  rescored without changing its submission. The extra setup grace does not
  earn credit: actual execution exceeding the stated job budget still fails.
- Evaluation uses one pinned CPU and a 3 GiB address-space limit. Controller
  runs are serialized by `benchmark.lock`. The supplementary resolution
  search uses a different single CPU, 381, for both measured implementations.
  Reference programs are single-threaded; original stored reference timings
  include their own startup and I/O and are not claimed to be optimal.
- Accuracy is normalized by the reference's actual nonzero L1 mass, with an
  absolute-error convention only for an exactly zero reference. An early
  1e-12 denominator floor was removed to preserve scale invariance for tiny
  weighted observables. All already-scored nonzero reference blocks exceeded
  that floor, so the correction does not change those pilot outcomes. The
  equivalent inverse-power score expression also avoids overflow for grossly
  incorrect predictions. No acceptance threshold was tightened.
- The supplementary resolution search records evaluator-file hash drift
  during that numerical-meter correction. It found no meaningful failure;
  the observations are retained as a bounded diagnostic, not silently
  presented as a frozen-version certification or a ratchet.
- Runtime is externally measured; a submission's claims do not earn score.
  `peak_child_rss_kb` is the child-resource high-water mark within the evaluator
  process and can include compilation or an earlier case. It is a conservative
  resource diagnostic, not a precise attribution to one numerical kernel.
- Public package hashes at launch and at audit match. No later correlator
  module, git history, expected histogram, or labeled development set is in
  a participant directory. Each public sample has three unlabeled jets.
- The full 100,000-jet case is a throughput test on the complete release asset.
  It intentionally overlaps the stratified pools and is not represented as
  independent generalization data. Pool and reserved heldout stratum case
  IDs are disjoint; extra diagnostic queries reuse only inspected pool jets.
- The resolved agent also performs self-tests with extreme floating-point
  momenta and exponents. Those self-tests are not hidden physical cases and
  are not used as evidence of task hardness or of reference validity.
- Stored-reference replay scores are distinguished from independent
  mathematical validation. The projector, resolved, and EWOC validators use
  separate small-case oracles; the ensemble validator checks global moment,
  energy-conservation, and contact-free identities on the actual stored data.
