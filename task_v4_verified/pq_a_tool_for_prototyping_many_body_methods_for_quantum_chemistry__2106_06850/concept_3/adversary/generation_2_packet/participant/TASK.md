# Compact fermionic state preparation

Construct short, ordered circuits of spin-preserving fermionic single and double
excitation rotations that prepare each of three supplied correlated target states.
Choose both the excitations and their real angles. Every target is achievable
within its stated gate budget; any valid decomposition is accepted.

`input/targets.json` contains complete target vectors, reference determinants and
budgets: 24, 28 and 32 gates for the three cases. `workspace/CONTRACT.md` specifies
the exact gate convention, artifact schema and constraints; `workspace/API.md`
documents the simulator. `baseline/run.py` is a runnable starting point.

Write `submission.json` in your output directory. This is a data-only circuit
artifact, not a program. Public checking is
`python workspace/check.py --submission /absolute/path/submission.json`.
The final artifact must be at most 131072 bytes and include every case exactly
once; its programs are never executed by the evaluator.

Passing requires every gate constraint and cap to hold and squared normalized
overlap **at least 0.999999999 in every case**. The core score is worst-case
fidelity; gate counts and checking runtime are also reported. Global sign is
irrelevant. No particular circuit or globally shortest decomposition is
required.

You have one hour for development and search. Only the participant assets and
your writable output directory are available; no network or GPU is permitted.
This inverse-synthesis problem is seeded by p†q's fermionic many-body and unitary
coupled-cluster formalism, not by a requirement to reproduce its source code.
