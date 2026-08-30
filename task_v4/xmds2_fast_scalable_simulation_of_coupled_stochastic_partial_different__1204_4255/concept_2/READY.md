# Ready for main promotion

This self-contained staged package is sealed before any fresh generation-three trial. It is the final allowed generation. Do not expose private adversary or evaluator material to participants.

From this directory:

```
/usr/bin/python3 -B participant/baseline/search.py --output attempts/baseline.json
/usr/bin/python3 -B evaluator/evaluate.py --submission attempts/baseline.json --output attempts/baseline.evaluation.json
/usr/bin/python3 -B evaluator/test_contract.py
/usr/bin/python3 -B adversary/test_controls.py
```

Baseline copies the old official champion and should yield valid=true, passed=false, scores zero, reason certified_family_threshold_failure. A fresh submission uses the same evaluator command with its own JSON path. Internal wall/CPU limits are 1500/900 seconds; set the outer watchdog to at least 1650 seconds. --exhaustive optionally disables threshold pruning but never changes the score or reference requirements.

Exact target: all 69 explicit members, all three late observations t/T=0.75,0.875,1, conservative density gap >=0.30, certificate <=1e-4, tail <=0.02, mass drift <=2e-5 and energy drift <=2e-4; all unchanged full reference checks must resolve. Generation-three status is pending_tournament; no fresh launches by the generator.
