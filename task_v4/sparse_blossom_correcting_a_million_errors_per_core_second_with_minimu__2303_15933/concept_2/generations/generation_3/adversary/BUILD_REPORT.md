# Privileged construction report — open final generation

This is the final planned B generation (initial plus two ratchets). The actual
generation-two champion v1 scored 1.0104109012101703; v2 also officially passed
at 1.0104079400244192. The selected artifact is used byte-for-byte as the public
baseline. Original generation-one/two participant and evaluator files are untouched.

## Stress evidence and selected failure

The parent private `adversary/extension_stress.py` tested all twelve 2x2 detector
patches and 48 convex row/column mixing paths. Both the prior private witness and
actual generation-two champion passed these unchanged local targets. The report
does not infer a multidimensional box from those paths.

The broader deterministic probe tested every proper detector rectangle, all
row/column product fields, orientation contrast, and orientation-conditioned
fields. Representative extrema were recomputed by the independent generic
full-state DP. The actual champion has an orientation-column posterior of
0.8418515011072246 at target 0.845, and an orientation-cross gap of
0.8053940642086914 at target 0.85. These are actual exact point failures, not
certificate penalties. No syndrome-mass point failure was found in this family.

The final domain retains every previous condition and adds all 43 transparent
orientation-conditioned fields: constant, all canonical row/column signs, and
all twenty single-row/single-column product fields. Both reflections and both
amplitude signs are included. The cross family supplies a meaningful combined
position/orientation perturbation without a hidden selected direction list.
Magnitude remains 5%, expected error count is preserved, and targets are unchanged.

Forty-one fixed new anchors plus adjacent-endpoint Lipschitz cones give rigorous
continuous coverage in real arithmetic with a conservative binary64 guard. The
old certificates are unchanged. The new domain is 86 additional one-dimensional
paths, not a full box; total inference count is 5,791. Separate private/public
schedule and certificate implementations are crosschecked numerically.

## Bounded feasibility investigation

The earlier private witness also fails these stronger conditions. A bounded
242-second private local feasibility investigation completed eighteen restarts
and 77,005 batched constraint calls. Its best stricter endpoint surrogate was
0.9652626095256147. The search was stopped; no indefinite search or post-launch
threshold selection is allowed. Search sources, logs and artifacts remain in
the original private `concept_2/adversary/`, outside the participant packet.

No valid generation-three witness is known. Achievability is **unknown**, not
verified feasible and not proved impossible. This incomplete local investigation
does not exclude other rates, syndromes, or entropy structures. There is no
claim that either final fresh model must fail; difficulty is unmeasured before
the final tournament.

The saved best private candidate also fails the complete public exact checker:
core score 0.9652626095256142, extension score 0.9700646462348368, and an actual
opposite-posterior minimum 0.8432090772758045. This was not promoted, exposed, or
claimed as an independently passing witness. Its full public inference report
is private in `best_private_candidate_metrics.json`.

The official independent champion replay took 887.024658039 CPU seconds,
959.688448546 wall seconds, and 68.84375 MiB peak RSS. The nominal 900-second
allowance is not a wall watchdog and did not invalidate the artifact. Scientific
failure is exclusively from the declared calibration certificates and exact
point failures, never host load or runtime scoring.

`baseline_independent_metrics.json`, `audit_report.json`, and `freeze_report.json`
record independent exact evaluation, validation/proof checks, and the immutable
pre-launch package. Main owns final launch, champion selection, and status updates.
