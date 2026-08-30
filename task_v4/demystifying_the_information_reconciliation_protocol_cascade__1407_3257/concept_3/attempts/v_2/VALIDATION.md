# Submission

`policy.py` is self-contained and uses only the Python standard library. It
requires no data files, generated assets, or persistent state at evaluation.

The policy uses one coordinate from each doublet to obtain echo-membership
parities, discovers root neighborhoods, and compares the two-triangle and
six-cycle neighborhood models. It estimates contamination from root samples,
selects informative excitation sources, and Huffman-decodes trusted echo sites.
Once the second neighborhood is selected, spare queries refine ambiguous echoes.

## Validation

- Official public development harness: **32/36 correct**, no protocol failures.
- Worst public mechanism/contamination cell: **2/4 correct**.
- Additional synthetic development episodes: **41/45 correct**. These episodes
  were generated from the public simulator and used during policy comparison;
  they are not hidden evaluation episodes or a certification set.
- Explicit resource test on nine public high-contamination episodes: **9/9
  protocol/resource-valid** with an eight-second CPU limit and 512 MiB address
  limit. Peak child RSS was 34,544 KiB.
- Python compilation succeeds; the submission is below the 128 KiB size limit.

The requested 171/180 overall and 18/20 per-cell hidden accuracy target is **not
established**. Development performance does not meet that accuracy level.

`dev_score.json` and `resource_score.json` contain the final public reports.
Investigation scripts, experimental variants, and logs are under `investigation/`;
none is a runtime dependency of the submitted policy.
