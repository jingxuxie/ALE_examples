# Generation 2: efficient active detector calibration

This is a separate, pre-fresh generation. Do not replace or edit the original
concept's participant/evaluator. The main builder owns root status and fresh
promotion. No fresh agent has been launched by this generation's builder.

Participant allowlist: this directory's `participant/` read-only, plus the
launcher's single writable attempt directory, with the main runner's `:minimal`
runtime. Do not include `adversary/`, `evaluator/`, sibling attempts, or this
private README in a fresh participant's allowlist.

Runtime is `/usr/bin/python3`. NumPy and SciPy are installed under
`/usr/lib/python3/dist-packages`; numerical dependencies need `/usr`, `/lib`,
and `/lib64` where present. The hidden evaluator also uses `/usr/bin/bwrap` and
the explicitly permitted `/bin` and `/etc`. No pip, sklearn, torch, or network
service is required. The original authenticated supervisor is retained.

From an escalation-capable parent, set `GEN` to this generation's absolute path:

```
/usr/bin/python3 "$GEN/evaluator/evaluate.py" --submission "$GEN/attempts/v_1" --output "$GEN/attempts/v_1_result.json" -- /usr/bin/python3 /submission/solution.py
```

The exact submission leaf must already exist. Only it is mounted writable at
`/submission`; the evaluator never imports its code. The generation's public
tree is mounted read-only at `/participant`. Private fixture rates and seeds
remain in the parent. Budget, query validation, signed actual-worker CPU usage,
and both accuracy thresholds are mandatory. Startup gets 300 seconds and each
episode a separate 900-second watchdog; neither is a 120-second wall cutoff.

The public developer command in `participant/TASK.md` deliberately uses the
actual launcher-provided writable path and an ordinary subprocess tester. It
does not assume evaluator-only mount aliases or start nested bwrap.

See `adversary/BUILD_REPORT.md` for validation, controls, limitations, and
target chronology. `evaluator/hidden/freeze.json` fixes targets and private
fixtures; `evaluator/hidden/package_manifest.json` records final package hashes.
Private portfolio files are not fresh champions. `champions/` is reserved for
main's future actual fresh promotions.
