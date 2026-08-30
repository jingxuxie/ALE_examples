# Bounded ratchet construction

All creator writes are confined to this generation directory. Original
concept-one participant, evaluator and status artifacts remain untouched.

`build_data.py` selects exactly 320 L14 records from the original private
broad bank for `evaluator/hidden/test.jsonl`, without exposing the source
bank to participants. It copies the two original public L10/L12 data
files as auxiliary training, then independently samples and simulates
320 new L14 training and 160 new L14 validation records. Up to sixteen
creator workers run with one BLAS thread each. Checkpoints permit safe
resumption without resampling completed work. A completed manifest
prevents accidental regeneration.

The public descriptor/ExtraTrees implementation is refitted with the
new L14 training and both old public splits. No prior fresh solving
code or trained artifact is used. Main's private size-transfer controls
are copied here solely as ratchet provenance, never under participant.
Generation-two thresholds remain 0.035 overall and 0.050 worst family.
If the starter already meets both on new public validation, report that
to main rather than changing thresholds. Main performs official isolated
scoring, freezes commitments and launches any fresh agent.

`finalize_package.py` independently shuffles hidden records and assigns
neutral IDs before recording readiness. The private source-to-final ID
receipt stays in authoring; neither it nor prior fresh code/models is
included in participant assets. The complete split-symmetry check is
independent of record order and is preserved by this final shuffle.
