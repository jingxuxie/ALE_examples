# t|ket> hardness-discovery package

The selected task is **concept 3: native parity-walk synthesis**, classified as `hard_verified_achievable` after two isolated fresh trials fail the grid depth constraints and private exact circuits pass all six cases.

- Participant export: `concept_3/participant/`
- Participant task: `concept_3/participant/TASK.md`
- Runnable weak baseline: `concept_3/participant/baseline/synthesize.py`
- Exact evaluator: `concept_3/evaluator/evaluate.py`
- Empirical report: `REPORT.md`
- Machine-readable final decisions: `status.json` and each concept's `status.json`
- Isolation, execution commands, and audit caveats: `authoring/REPRODUCE.md`
- Source provenance and the eight-concept shortlist: `authoring/sources.md` and `authoring/concepts.md`

The other built concepts remain available for reproduction. Their final participant/evaluator versions are `concept_1/adversary/generation_2/` and `concept_2/adversary/generation_3/`. Original versions, champion snapshots, adversarial searches, and immutable fresh-attempt artifacts are preserved rather than overwritten.

Only a concept version's **participant directory** may be exported to a tested agent, together with a new empty writable output directory. Never expose this package root, evaluators, hidden data, private certificates, authoring files, champions, or earlier attempts. The full package is the privileged scoring/authoring environment, not the participant workspace.
