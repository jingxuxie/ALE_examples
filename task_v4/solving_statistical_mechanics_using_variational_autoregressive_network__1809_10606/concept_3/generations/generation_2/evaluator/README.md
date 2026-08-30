# Trusted evaluation and deployment

Use `python -I evaluate.py --submission DIR --output ORGANIZER_SCORE.json`.
`DIR/predictions.npz` is the only submission input. An artifact path is also
accepted. Valid-but-below-target submissions exit zero with `passed=false`;
malformed submissions exit 2. Always read the JSON `passed` field.

The private reference is `hidden/labels.npz`; `hidden/scoring.json` binds
family membership. `hidden/model.npz` is retained
for organizer reproducibility only. All private files and parent directory have
restricted permissions, but filesystem mode bits are NOT isolation from a
same-UID participant. Mount/allowlist only the participant subtree and a fresh
output directory; keep all organizer files outside the participant namespace.

The scorer validates bounded ZIP/NPY headers before constructing fixed-shape
numeric arrays. It rejects pickles without loading them, nonfinite/zero/negative
probabilities, wrong IDs, duplicate or extra ZIP members, oversized payloads,
non-regular files, and final symlinks. The runner owns the submission's parent
directory and must not replace it with a symlink or expose organizer paths.
Launch in isolated Python mode to avoid module shadowing by participant files.
Enforce a 15-second/512-MiB evaluator cap separately; no participant compute
resource claims are inferred from an NPZ artifact.

Every valid report includes `core_score = 1/(1+mean_forward_kl)`,
`worst_family_score = 1/(1+worst_family_mean_kl)`, and
`runtime_resource_score = 1-artifact_bytes/65536`. Invalid reports contain all
three fields set to zero. These convenience scores do not replace the fixed
physical-metric pass gates. The resource score measures artifact size only,
not elapsed execution time or memory use. The launcher separately enforces
four-core affinity and an 8-GiB per-process address-space limit.

Reference generation uses positive normalized transfer messages at width eight;
independent full enumeration checks on tiny graphs and an independent dense
transfer calculation on the real material are recorded in `adversary/validation.json`.
These are numerical finite-instance references, not formal interval certificates.
Recorded residuals must remain far below the scoring tolerances.

This generation uses all 48 preregistered cold queries and the unchanged quality
targets. The full 9,600-draw public-data-fitted replay is the baseline; it is not
bitwise identical to the original champion fit. Its original-query replay error
and cold-response controls are retained in the private adversarial audit.

Controls and freeze are implemented in the enclosing paper directory's
`authoring/finish_concept3_generation2.py`. A frozen package is not regenerated
automatically. Participant data, targets, evaluator, and private labels are hashed
before any fresh launch. The builder never launches participant agents.
