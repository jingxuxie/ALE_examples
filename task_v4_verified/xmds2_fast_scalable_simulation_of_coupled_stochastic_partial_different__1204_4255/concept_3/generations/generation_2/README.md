# concept_3 generation 2 — ratchet 1

Release only `participant/`. Keep evaluator, references, authoring, attempts,
adversary, champions, provenance and freeze records organizer-side. The original
root generation is untouched. `PROVENANCE.md` records the verified failure clusters.

Run from this generation directory:

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
/usr/bin/python3 -I -B participant/workspace/smoke.py --artifact participant/baseline/control.json
/usr/bin/python3 -I -B evaluator/evaluate.py --artifact participant/baseline/control.json --output attempts/baseline_evaluation.json
/usr/bin/python3 -I -B authoring/validate.py
```

For fresh trials, require the exact artifact filename `control.json` in the
assigned output directory. The smoke command writes no cache by default;
`--cache-dir` and `--output`, when provided, must name writable output locations.
The trusted scorer reads JSON only and uses included, organizer-generated
reference caches. Run it with isolated Python imports and read-only trusted files.
Exit 0 means valid, not passed; inspect both JSON booleans.

This stage is frozen and ready for the main worker to archive/promote and trial.
No fresh agent is launched here, and no generation-2 passing solution is known.
