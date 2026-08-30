# Evaluating a static witness

From the package root:

```
OPENBLAS_NUM_THREADS=1 python concept_2/evaluator/evaluate.py /path/to/submission --output /path/to/report.json
```

The submission is a directory containing `answer.json`, or the JSON file itself.
No submitted code is executed. The evaluator checks rank-one/PSD structure by
the OPE-vector representation, the support count, the common low-state OPE
coefficient, coefficient bounds, trace budget and every supplied moment.
Its locked data and checker are not participant-writable. The public checker
has the same numerical contract, and is not imported during private grading.

Core score is the fraction of valid certificates. Worst-family score is the
minimum of the four family fractions. Passing requires both scores to equal
one. Static-artifact runtime score is one for a processed, well-formed suite;
the report also records checking time. No residual is compared with a hidden
reference output. Private planted witnesses demonstrate achievability but are
not used by the evaluator.

`adversary/validate.py` independently evaluates planted sums at 70 decimal
digits and checks rejection of six malformed or incorrect variants. The
maximum independently computed scaled planted residual is below `3e-15`,
versus a `2e-8` acceptance limit. Candidate blocks are finite, column-normalized
leading radial partial waves, not a certification of a full CFT spectrum.
