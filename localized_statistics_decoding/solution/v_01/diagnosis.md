# Diagnosis and repair

The starter assigns a crossing mechanism to one region and discards its effect
on other regions, treats missing detector observations as zeros, chooses a
single affine representative without summing degeneracies, and uses the prior
mode weights separately for each shot. Its probability adapter therefore does
not compute the specified probability model, even when a correction happens to
match a syndrome. Detectorless mechanisms are also omitted from its hypotheses.

Commands executed from the task root, with OPENBLAS_NUM_THREADS=1:

```
python participant/v_01/software/solve.py --input participant/v_01/input/validation.json --output authoring/starter_validation.json
python participant/v_01/software/validate.py --expected participant/v_01/input/validation_expected.json --actual authoring/starter_validation.json
python solution/v_01/solve.py --input authoring/reference_input.json --output authoring/reference_output.json
python authoring/finalize_reference.py
```

The starter's mean logical total-variation errors were 0.565585 and 0.672160 on
the two public validation cases. Mean query absolute errors were 0.149828 and
0.174180; log-evidence errors were 26.510523 and 73.115252. The repaired
implementation reproduces the public target distributions. It also agrees with
an independent full-fault enumeration on three microcases to maximum absolute
error 1.78e-15 across evidence, mode weights, logical probabilities, and queries.
The complete eight-case reference run took 0.99 seconds on this host.

The replacement maintains affine solution spaces within each hardware region,
retains crossing fault variables, sums internal mechanism probabilities, and
contracts the resulting boundary-factor network. Character-valued factors
carry joint logical information and parity queries without treating observables
as independent. Per-mode batch evidence determines a single posterior mode
mixture for all shots. Missing checks are removed before binary factorization.
Zero and one probabilities are supported without taking their logarithms.

The method is exact on the stated workloads. Its limitation is exponential
growth with regional nullity and boundary contraction width, not total fault
count. The validation includes rank dependencies, non-tree boundary networks,
joint logical degeneracy, silent mechanisms, missing observations, and changing
probability support; it does not claim scalable exact inference on arbitrary
high-width detector networks.
