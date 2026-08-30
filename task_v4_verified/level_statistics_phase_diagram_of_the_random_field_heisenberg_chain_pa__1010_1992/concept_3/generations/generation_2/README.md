# concept_3 generation 2: replication ratchet 1

This is a disjoint package. Nothing in the generation-one participant,
evaluator, status, attempts, or champions is modified. Expose only this
package's participant/ to tested agents. Keep evaluator/ and adversary/
private; never expose prior fields, solvers, witnesses, or stress cases.

The numerical discrepancy thresholds and model are unchanged. Each family
now has 32 members, with required coverage 24/32. Public calibration and
private grading use independent, fixed 128-offset banks from the same law.
The private bank is SHA-256 committed before evaluation and is verified on
every evaluator call. Public-case success does not imply acceptance.

Run `python -I -B evaluator/evaluate.py PATH/witness.json --output report.json`.
The main runner owns final freeze and launch. status.json records readiness,
the fixed criteria, commitments, existing-reference results, and any open
solvability question. This authoring run launches no fresh agents and makes
no claim about fresh-agent difficulty before independent attempts.
