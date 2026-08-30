# Submission and development record

The artifact is `design.json`. It is a regular JSON file containing exactly the required 24 integer axis choices.

## Outcome

The requested improvement and pass target have **not** been achieved. The retained pattern is the horizontal reflection of the supplied champion. It is not a newly improved construction: exact row-space checks show that reflection preserves both the syndrome and augmented response matroids, so its population performance under independent identically distributed erasures is identical to the baseline's.

Final fresh validation with the supplied standard-library checker, seed 659187 and 10,000 supports per group (90,000 supports total), gives:

| Size | iid_28 | iid_30 | iid_32 |
| --- | ---: | ---: | ---: |
| 24 | 0.7054 | 0.6101 | 0.4825 |
| 96 | 0.9800 | 0.9391 | 0.8587 |
| 216 | 0.9991 | 0.9953 | 0.9797 |

Core score: **0.8388777778**. Worst group: **0.4825**. Mean ambiguity: **0.1975666667**.

An earlier paired check (seed 983271, 4,096 supports per group) scores the artifact at 0.8392198351 and the baseline at 0.8387586806. This small sampled difference is not evidence of a genuine improvement; the reflection equivalence rules out an IID population improvement. Neither pattern meets the 0.85 core and 0.60 minimum-group requirements.

## Search and verification

- Implemented an exact C++ GF(2) evaluator and checked its correctability and full four-logical ambiguity against the supplied Python implementation on baseline, reflected-baseline, and unrelated random patterns.
- Exhaustively enumerated all 116 perfect matchings of the 24-site colored graph and all 40,080 patterns having exactly two unmatched vertices.
- Screened over six million structured repeated or axis-permuted 12-site patterns, all baseline mutations through Hamming distance three, and numerous independent annealing restarts.
- Exhaustively classified patterns whose complete selected fault span contains at most two independent pure logical vectors: there are exactly 59, all among the perfect matchings. The two strongest are the champion and its reflection.
- Searched unrestricted patterns using exact monotone rank pruning on independently generated screening supports. A partial pattern that already permits a pure logical vector cannot become correctable by assigning more sites. Additional look-ahead detects remaining sites for which every axis necessarily fails a support.
- Completed 17 such searches: eleven at density 0.32 and six using the density mixture. One complete search reads screening supports generated directly by the supplied Python implementation.
- Checked incremental rank updates and rollback against direct elimination on all 6,561 completions of a 16-site prefix. Verified the eight color-preserving spatial symmetries using the complete response matrices, including all three sizes.

Searches use fresh draws rather than fitting the supplied finite practice set. Finite screening experiments are not a mathematical proof of population optimality or infeasibility. Full logs and research sources are retained in this directory. `search_summary.json` records screening seeds, thresholds, completion status, and independently validated candidates; its fractions concern the 24-qubit case, not the nine-group core score. Symmetry-reduced searches cover every equivalence class rather than testing every literal pattern on the same finite supports.

## Reproduction

The submission itself executes no code. For development, set `P` to the supplied participant directory and `PYTHONDONTWRITEBYTECODE=1`, then run `python prepare.py` and compile with `g++ -std=c++17 -O3 -march=native optimize.cpp -o optimize`. `python verify.py` cross-checks the evaluator; `python verify_symmetry.py` verifies the artifact's equivalence to the champion. Run `python public_supports.py` before reproducing the published-generator search. Exact search commands are recorded in `search_summary.json`. `final_validation.json` contains the complete final supplied-checker output for the artifact.
