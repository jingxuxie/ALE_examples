# Champion 1 audit (sidecar only)

This is a generation-time audit, not a participant agent launch. No original
participant, evaluator, hidden corpus, or status file is modified. All new
artifacts stay under this directory. Original target v1 remains solved if the
reported result reproduces; a new generation is never applied retroactively.

Initial static finding: `attempts/v_1/predict.py` uses only physical parameters
and IDs. It does not consume training labels, low-cutoff spectra, or helper
files. It projects each 80-Fock-state onsite Hamiltonian onto eight even and
eight odd eigenstates, absorbs the diagonal bond contribution onsite, then
diagonalizes the coupled parity blocks. For L=2/3 these have 128/2048 states.
This is an efficient legitimate direct simulation, not a hidden-label lookup.

Round 1 is fixed before fresh results: three independent IID 72-case batches
and two independent edge-enriched 72-case batches, each balanced over the
original six families. Edges lie inside the published domain. All 360 cases
must pass the original teacher admission criteria; no predictor-performance
filtering is allowed. Seeds and certificates remain private sidecar artifacts.

Runs use the original trusted bubblewrap/seccomp bootstrap and original
resource limits, never an unrestricted predictor import. Only a source-identical
copy of `predict.py`, public assets, current features, and fresh output/scratch
are staged. Fresh labels/certificates and all host paths remain outside. Runtime
measurements use self `getrusage` in the trusted bootstrap's `finally` block,
not a timer supplied by the predictor. Launcher `wait4` usage is recorded
separately: on this host it does not include the numerical solver. Initial
launcher-only reports are explicitly superseded under `pre_profile_results/`.

At most two further, explicitly NEW-generation proposals may be examined after
Round 1. Merely making v1 reject a new schema/length does not demonstrate a hard
problem; generic direct-solver controls are required. Inhomogeneity alone at
L=2/3 does not remove the efficient onsite-basis mechanism.

Commands (from this sidecar; `-B` prevents writes to original bytecode caches):

```text
OPENBLAS_NUM_THREADS=1 python -B generate_fresh.py --workers 4
python -B benchmark.py --watch
```

Benchmark execution may require approved escalation out of a nested outer
sandbox. Every predictor still runs inside bubblewrap, with no unsafe fallback.
