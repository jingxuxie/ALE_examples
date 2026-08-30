# Privileged champion storage

`builder/witness.json` is a generation-time feasibility witness, not a fresh-agent
attempt. Its independently recomputed result is in `builder/evaluation.json`.
Do not expose this directory, generation attempts, or evaluator resources to
the fresh solver. Hardness remains unmeasured until the main runner tests it.
