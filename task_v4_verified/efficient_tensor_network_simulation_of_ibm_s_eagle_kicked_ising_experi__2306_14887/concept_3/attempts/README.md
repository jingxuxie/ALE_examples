# Generation-1 attempt boundary

`baseline_nominal/` is the deterministic public weak baseline, not a fresh
agent attempt. It includes its artifact and independent evaluator result.
The generation-0 first-tournament score and metadata remain unchanged.
Its raw `v_1`, `frozen_v_1`, and raw model log have been quarantined under
`adversary/generation_1/tournament_0_raw/`; the prior winner also remains
archived in `champions/generation_1/`. Those are generation-private.
Only the fresh `v_2/` directory may be exposed alongside `participant/`.
Main owns the v2 launch, logging, and final hardness status. No tested agent
has yet run against this stronger ratchet in this builder session.
