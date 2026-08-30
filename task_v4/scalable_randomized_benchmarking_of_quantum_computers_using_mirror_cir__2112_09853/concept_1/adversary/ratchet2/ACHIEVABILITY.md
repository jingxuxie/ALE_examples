# Generation-two private achievability demonstrated

The frozen pair-only generation-two contract is unchanged: original global mean, native inverse-pair overlaps 28800 and 1920, bias at least 0.0239, residual at most 0.004, and end signal at least 0.005.

`../generation_2_winning_witness.json` is now an independently verified **integer passing witness**. Its bias is 0.023941729474725837, maximum residual 0.0038068677015571373, fitted infidelity 0.019521165410505484, and depth-256 signal 0.006524824077090089. All original integer constraints pass; the split overlaps are exactly 28800 and 1920.

`achievability.json` is the current status. The earlier hard_open labels in `SELECTED_CONTRACT.md`, `selected_recommendation.json`, and historical checker output describe the status before this private search. No scientific target or public contract was changed to obtain the witness.

The search used only the previously saved private continuous pair-only candidates. A small LP branch-and-bound problem rounds a candidate while preserving every original integer linear equality. Bounded transportation moves repair the two native-family quadratic overlaps separately. The search source, actual run, witness hashes, and selected-checker acceptance are retained in this directory. No v2 attempt was read.

`generation2_full_independent_trace.json` includes all 129 polarizations and the independent probability-convolution cross-check. Its nested original-verifier accepted flag is false solely because that old verifier uses 0.0244; it is not the generation-two acceptance decision. `integer_winner_independent_verification.json` records the correct frozen generation-two decision, passed=true.

Main should validate `../generation_2_winning_witness.json` with its frozen evaluator. Keep every artifact and all search source private. This does not imply the fresh participant has solved v2, and no generation-three recommendation is made.
