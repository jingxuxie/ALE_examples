# Concept 1: invalid first target and independent recalibration

Generation 1 required 12% overall and 8% worst-family gain. During its first isolated attempt, a parallel private headroom audit proved upper bounds of 7.305952% and 5.989040%, respectively. Sparse marginal relaxations, exact dyadic dual certificates, independent Fraction arithmetic, exhaustive small-case checks, and arbitrary atlas embeddings support these bounds. See concept_1/adversary/headroom.

The controller stopped this attempt after 1324 seconds and classifies generation 1 as **invalid**, never as empirical hardness. Its frozen participant and evaluator are preserved under authoring/generations/concept_1/generation_1, and its launch/output remain in attempts/v_1 and attempts/v_1_evidence.

Generation 2 uses the same objective, cases, baseline, and resource limit, but fixes meaningful achievable-range targets of 7.0% overall and 5.7% worst-family gain. These exceed the independently observed 6.775%/5.333% private heuristic gains while lying below the certified upper bounds. Passing attainability remains unknown until a solution actually passes. These revised targets are declared before a completely new isolated attempt; the old attempt is not relabeled against the new targets.

This is an evaluator-calibration correction, not a champion ratchet. The invalid attempt provides no evidence of capability failure. Only generation-2-or-later valid-task attempts may support retention.
