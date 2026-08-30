# Pending generation 1 — not active

This directory holds empirical diagnostics and a proposed ratchet for parent review.
The active task is not overwritten and no fresh agent is launched. The previous
fresh-v2 solver is privileged adversarial-search evidence only, archived at
`../../champions/generation_1/solve.py`. It is never shipped to a tested agent.
The pending participant receives the original public damped baseline, and the
new improvement target is anchored to a measurement of that public baseline.
