# Operator-only hardness-discovery package

Deploy only one `concept_N/participant/` plus an initially empty writable output
directory to a tested agent. Do not expose evaluators, attempts, champions,
adversarial searches, research files, or archived generations.

`research/run_attempt.py concept_N --attempt N --generation N` invokes the
requested allowlisted runner with ultima-alpha, a sanitized runtime, read-only
participant assets, and a one-hour deadline. It refuses nonempty fresh outputs.
The default attempt and generation are both 1.

After the attempt supervisor finishes, the canonical scoring command is
`python research/score_attempt.py concept_N --attempt N`. It checks attempt
integrity and requires a regular submitted artifact before invoking the frozen
evaluator. Interpolation execution is separately sandboxed with bubblewrap;
CPU is measured by a protected direct-parent supervisor. The data-only scorers
can also be invoked directly on trusted regular JSON files for scientific
controls. Dependency/build details are in `research/environment.json`.

Each concept's `status.json` records its target, validation and empirical
decision. The final root `status.json` and `REPORT.md` identify the retained task.
Earlier solved generations are preserved under `adversary/generation_N_packet/`
and matching champions under `champions/generation_N/`; they are not supplied
to later fresh agents. A score for an old generation must use its archived
evaluator, which the canonical scoring command selects automatically.

The exact-certificate concept has private passing artifacts, not a supplied
reference recovery algorithm. An almost-exact identity is not an exact witness.
