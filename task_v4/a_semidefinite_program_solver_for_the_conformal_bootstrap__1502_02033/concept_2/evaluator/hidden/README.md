# Private validation controls

`control_report.json` records the pre-launch negative and positive controls.
The immutable guard and exact checker live one directory above and are pinned
by `frozen_manifest.json`. None of evaluator/ is mounted for a tested agent.
