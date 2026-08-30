# Private evaluator operations

Run from the concept directory:

```
python3 -I evaluator/evaluate.py attempts/<id> --report attempts/<id>/grade_report.json
```

A direct path to `design.json` also works. The checker uses only the fixed private
target and manifest; it never executes submitted code or imports from a
submission directory. It reads at most 16385 bytes from a regular nonsymlink
file. Ordinary invalid submissions produce a JSON failure report with exit zero;
evaluator configuration errors return exit two. CLI misuse also returns nonzero.
Use an isolated Python invocation as shown, with a trusted interpreter and
standard library, rather than inheriting participant-controlled Python settings.

`python3 -B evaluator/hidden/run_authoring.py` freezes once if necessary, runs
independent arithmetic and adversarial checker tests, then scores three bounded
local-search runs. It does not launch agents. `freeze_target.py` refuses to
overwrite any existing target or witness. The manifest timestamp precedes every
baseline and fresh attempt. Do not regenerate the target during the tournament.

Only `participant/` and an initially empty per-attempt output directory may be
visible to a fresh agent. Keep this directory, `adversary/`, and root private
metadata out of that allowlist. The planted witness must remain private even
after it passes. `hidden/author_audit.json`, `hidden/planted_report.json`, and
`../adversary/AUDIT.md` provide authoring evidence without printing its entries.
