# Private, unfrozen continuation hypothesis

This is NOT a task generation, threshold freeze, or instruction for either running agent.

A scientifically coherent additional condition is: retain the original nominal
targets exactly, and require the 338 explicitly declared noise-budget-preserving
local 2% profiles to certify gap >= 0.90, opposite posterior >= 0.84, and
syndrome probability >= 0.000017 throughout global scales [0.95,1.05].
The profile list comprises 82 row/column/quadrant/patch fields and two seeded
families of 128 fields each. A future task would have to publish the profile
construction, seed, and certificate. No claim is made for all local fields.

The existing private known witness certifies 0.9358544332,
0.849647667782, and 1.73977264598e-05, respectively;
local guard score 1.02339567411. Its original nominal pass is retained.
No additional optimized nominal witness was needed or created.

The strongest observed genuine instability is erosion of the weight-gap
margin, not loss of entropy inversion: at 5% local calibration the exact
gap falls to 0.814943376968 while the opposite posterior is 0.886996248818.
Even 2% perturbations violate the original pointwise gap target for some
profiles. No sampled posterior or mass target failure was found; their
certificate failures must not be misrepresented as physical failures.

Test the actual champion before selecting any continuation. This condition
may not reject a strong champion; difficulty is unmeasured. The known design
certifies basic inversion for all 677 tested profiles, so this sidecar is
evidence of calibration-margin fragility, not wholesale decoder failure.

## Reproduction from concept_2

```bash
OPENBLAS_NUM_THREADS=1 /usr/bin/python3 -B adversary/stress.py /path/to/witness.json
/usr/bin/python3 -B adversary/test_stress.py
```

Use distinct `--output adversary/<name>.json --summary adversary/<name>.md`
for a champion replay; `--skip-independent` is exploration-only and explicitly
disables the generic-DP checks. The audit and candidate recorder are regressions
for the saved known-witness report, not arbitrary champion reports.
