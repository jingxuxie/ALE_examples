# Private generation-two benchmark

Only this directory and the adjacent generation_2_packet are writable outputs of
this ratchet worker. The completed first champion is read from champions/generation_1;
no unfinished attempt or archived answer is used by any solver process.

`source_provenance.json` records exact archived source/binary hashes. Algorithm
bodies are unchanged. Only the old absolute import path and single-case loading
index are adapted. The supplied public simulator's loader is adapted for one
case and gate caps through 32; its algebra/scoring remain unchanged. Only the
listed source files and beam3/model.so binaries enter `runtime/`. No archived
input, solution, reverse sequence, private certificate, generator, or seed enters it.

Each job runs in a new network/PID/user namespace using bubblewrap outside the
parent sandbox. Its mounts are limited to system libraries, the read-only sanitized
runtime, one read-only public target, and its own writable output directory.
Neither /home nor /srv nor the task/pool/benchmark parent is mounted. System
/etc/alternatives and the loader cache are included only for BLAS resolution.

Broad: three original public controls plus 18 candidates, each with a 60-second
upper-bound portfolio allocation: beam3 (width 256, branches 40, entropy 0.1,
four buckets), continuous least-squares/discrete refinement, and two-gate bridges
(30/20/10 seconds, less startup overhead). Solved cases stop early. Refine seeds
are newly computed public greedy circuits or fresh beam circuits, never archived
circuits. Bridges consume fresh beam prefixes. The original bridge algorithm
uses its own width-2000 continuation unchanged.

Deep: three broad-failure finalists, each with an additional 300 seconds:
beam3 width 1000/branches 80 (140 seconds), the original refinement (100 seconds),
and bridges (60 seconds), with each run's own broad output available as a warm
start. Original controls use exactly the same broad configuration as new cases.
Phase allocation, measured times, timeouts, logs, support traces, independently
rescored legal output circuits and infrastructure health are all retained.
No full-one-hour failure claim is made; future fresh participants receive an hour.

Selection requires both N=4/6, one case at each depth 24/28/32, healthy probes,
and continued failure in every deeper probe. The broad ordering minimizes the
largest best fidelity, then the sum. Saturated-support/full-Schmidt-rank planted
suffix diagnostics are interpreted alongside observations, not used as a hidden
acceptance rule or fed to the solver. Scientific feasibility comes from private
certificates and independent exponential audits, not a hardness assertion.

`prepare.py` creates immutable input/runtime copies; `run_benchmark.py` runs and
scores the portfolio; `build_packet.py` creates and validates the separate staging
packet after the benchmark completes. `generation_2_packet/READY_FOR_MAIN` is the
handoff signal. Nothing promotes or edits the active generation-one packet.
