# concept_3: organizer handoff

Mode C / WITNESS-DESIGN. **Expose only `participant/`** to contestant workers.
Everything else, including this README, certificates, seeds and authoring source,
is private and must be excluded from participant filesystem mounts and logs.
`evaluator/hidden/certificate_index.json` indexes the hidden feasibility assets;
their implementation and data remain in `evaluator/private/`.

Run from this concept directory:

```bash
python participant/baseline/run.py --output attempts/baseline.json
python -I evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline_score.json
python -I evaluator/evaluate.py --submission evaluator/private/certificates.json --output evaluator/private/witness_score.json
OPENBLAS_NUM_THREADS=1 python evaluator/private/audit.py
python adversary/check_fail_closed.py
```

`evaluate.py` accepts `--submission PATH` or a positional path, and optional
`--output`/`--report PATH`. Reports include `core`, `worst_fidelity`, `pass`,
`reason`, `runtime_seconds`, and per-case results. CLI exit 0 means pass; exit 1
means fail. Python API: `evaluate(submission_path) -> dict`.

The evaluator executes only a trusted private worker, in isolated Python with
a clean environment, 20-second wall limit, 12-second CPU limit, and 2-GiB
address-space cap. The worker verifies private simulator/target hashes and reads
bounded JSON data only. Never mount evaluator files writable by contestants.
The trusted runner chooses the submission path. Public checker edits cannot
change private scores. Enforce participant search resources separately.

All-case threshold `0.999999999`, caps 14/18/20, and public assets are frozen in
`evaluator/private/frozen_manifest.json`. Do not regenerate after launch.
The private seed/generator is authoring evidence only. There is no requirement to
recover the planted sequence: any legal matching circuit passes. No global
minimality or exhaustive hardness claim is made. No other concept is a dependency.

Scientific sources checked on 2026-08-28: Rubin and DePrince,
arXiv:2106.06850v3; official pdaggerq `set_unitary_cc(True)` documentation
(anti-Hermitian excitors, noncommuting UCC/BCH); Evangelista, Chan, Scuseria,
arXiv:1910.10130 (disentangled UCC). Finite-cap feasibility is proved here by
the certificates, not inferred from the papers' general parameterization results.

```text
https://arxiv.org/abs/2106.06850v3
https://github.com/edeprince3/pdaggerq
https://arxiv.org/abs/1910.10130
```
