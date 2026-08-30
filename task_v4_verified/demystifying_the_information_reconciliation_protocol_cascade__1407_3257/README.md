# Cascade hardness discovery

Each `concept_N/participant/` is the complete, read-only participant release.
Everything else is generation/evaluation evidence and must not be exposed to
tested agents. In particular, concept 2 contains a private constructive witness.

`research/concepts.json` records the nine concepts considered and the three
selected verification modes. `research/SOURCE_NOTES.md` records paper,
follow-up source, change-history and earlier-pilot inspection.

`research/launch_attempt.py CONCEPT GENERATION` uses the supplied
`run_allowlisted_codex.sh`, model `ultima-alpha`, a fresh ephemeral context,
read-only participant assets, an initially empty output directory, and a
3600-second wall-time limit. It stages exact copies on local temporary storage
to reduce shared-filesystem sandbox startup overhead. The resulting submission
is copied to `concept_N/attempts/v_GENERATION/`; the adjacent `_evidence/`
directory contains the transcript, launch metadata and frozen SHA-256 manifest.
Never reuse a nonempty attempt directory.

Use `--attempt-number N` when running another independent attempt on the same
generation. The attempt number names its output directory; it does not change
the task generation. Archived `champions/generation_N/participant/` and
`evaluator/` preserve earlier solved generations for replay.

`research/isolation_audit.json` records a probe of the runner's filesystem
allowlist: both home-directory spellings of private sources, certificates and
the repository token were inaccessible; direct networking was denied. The probe
uses the installed CLI's explicit sandbox permission profile; the actual fresh
launches additionally use the supplied runner's strict configuration mode.

Concept 2 replay and baseline example, from that concept directory:

```sh
python3 participant/baseline/solve.py --input participant/input/deployment.json --output /tmp/witness.json
python3 evaluator/evaluate.py --submission /tmp/witness.json --report /tmp/score.json
python3 adversary/build_and_validate.py
```

The last command cross-checks independent implementations and verifies a
private certificate. Do not copy that certificate to a participant release.
Generation scripts and hidden suites must not be regenerated between a frozen
fresh attempt and its scoring. The per-concept `status.json` and final report
record the empirical decision, not a claim of difficulty for all agents.

Concept 1 baseline and hidden scoring, from `concept_1/`:

```sh
python3 -B participant/baseline.py --output /tmp/cascade-policy.json
python3 -B -I evaluator/evaluate.py --policy /tmp/cascade-policy.json --split hidden --jobs 8 --output /tmp/cascade-policy-score.json
```

Concept 3 hidden scoring, from `concept_3/`:

```sh
python3 -B evaluator/evaluate.py --policy participant/baseline/policy.py --jobs 8 --output /tmp/cascade-diagnosis-score.json
```

The scoring code uses Python 3.10 or newer and its standard library. Concept 3
also requires `bwrap` with working unprivileged user namespaces: its trusted
parent keeps simulator state outside the policy sandbox. Namespace startup
and cleanup are not charged to the policy interaction budget. Public
`participant/workspace/dev_evaluate.py` does not require nested sandboxing.
All submitted artifacts are interpreted or executed by these trusted
evaluators, never by an evaluator supplied by a participant.
