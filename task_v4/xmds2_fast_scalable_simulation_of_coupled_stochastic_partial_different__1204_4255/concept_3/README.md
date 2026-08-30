# concept_3 generation 2 — ratchet 1

Release only `participant/`. Keep evaluator, references, authoring, attempts,
adversary, champions, provenance and freeze records organizer-side. The original
generation is archived under `generations/generation_1/`. `PROVENANCE.md` records the verified failure clusters.

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

This frozen generation is `hard_verified_achievable`: both final fresh controls
fail the fidelity target, while an independently reproduced private control passes.
The saved-output fairness audit also finds no passing pre-cutoff alternative.
See `status.json` and `adversary/alternate_output_audit/conclusion.json` for evidence.
