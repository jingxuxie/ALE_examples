# Bounded champion-2 revalidation

Decision: keep A solved; do not build another ratchet from these measurements.

- Exactly five requested two-case batches were rerun, each with the unchanged 20-second wall/CPU contract, shared evaluation mutex, and CPU188.
- Case013 is the only repeat-confirmed positive quality example. Its best measured champion cost is 618.3893588717926 versus a validated private witness cost of 615.2283433647366: 0.5111691302% additional reduction. The repeat champion cost is 624.158420578231; using that weaker run alone would inflate the apparent gap to approximately1.43%.
- Case023's original approximately1.05377% observation remains unconfirmed: its batch timed out on the one authorized repeat. It is neither disproved nor a robust quality counterexample.
- Previously timed-out batches07/09 timed out again. Batch10 passed in18.444875 seconds and its two cases have negative quality gaps. These are batch-level deadline observations, not individual scientific failures or proven diagnoses of contention.
- The expansion condition was not met. No additional physical instances or participant generation were created. The sibling targeted_expansion directory records the closed gate only; its code's unused generation path was not exercised.
- Original reports, frozen generation sources, and the promoted champion manifest match their stored hashes. All scored witness costs are independently recomputed using the original trusted evaluator. No submission code is imported by trusted analysis.

Machine-readable decision, cost crossovers, physical provenance, and limitations: decision.json. Exact preserved input copies, captured sandbox outputs, reports and commands: batch_06, batch_07, batch_09, batch_10, batch_11 and summary.json.

The original diagnostic baseline denominators are not benchmark references; reported diagnostic passed flags must not be interpreted as a new ratchet evaluation. The remaining0.51117% robust observation cannot justify a1% aggregate target and has almost no margin above0.5%.
