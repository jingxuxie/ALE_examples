# Correlation-aware logical-class list decoder

`submission.py` exports the required `Decoder`. It loads the adjacent,
precompiled `decoder.so` in-process; evaluation needs neither compilation nor
subprocesses, threads, training files, or network access. `decoder.cpp` is the
complete native source. Rebuild during development with `make`.

## Method

The decoder uses the full supplied Bernoulli mechanism matrix, not graphlike
marginals. Thus Y, spatial pairs, temporal bursts, overlapping events and XOR
cancellations remain coupled exactly as specified by the public model.

1. Damped, layered sum-product belief propagation supplies mechanism
   reliabilities. A converged unperturbed solution is the inexpensive fast path.
2. Otherwise, bit-packed reliability-ordered Gaussian elimination constructs a
   syndrome-consistent affine space. The list includes every single free-variable
   flip and pairs among 40 promising nullspace generators.
3. Up to four likelihood-improving recenterings expand the search beyond the
   initial order-two neighborhood. Deterministic syndrome-seeded channel
   perturbations supply additional reliability bases: eight for single-round
   models and two for the larger memory models. Perturbations guide search only;
   all candidate weights use the original model probabilities.
4. Distinct mechanism configurations are deduplicated across lists using 64-bit
   configuration fingerprints. Their probabilities are summed within each of the
   **16 joint logical classes**, and the largest accumulated class mass wins.
   This is a truncated class-posterior approximation, not exact maximum
   likelihood, independent bit voting, or simply minimum-weight selection.

The native implementation has bounded iterations and list sizes. Its only
per-shot randomness is a deterministic function of the syndrome; predictions
are invariant to shot ordering, batch boundaries, and previous calls. Inputs are
not modified. No calibration labels or precomputed shot predictions are loaded.

## Checks

From the participant directory, run the supplied public check:

```sh
/usr/bin/python3 input/run_public.py --submission "$OUTPUT_DIR/submission.py"
```

An additional public-model sampling harness is in `experiments/evaluate.py`.
Set `P` to the participant directory, prepend `$P/input/runtime:$P/input:$P`
to `PYTHONPATH`, and run it with `/usr/bin/python3`. `--check-contract` checks
empty batches, noncontiguous inputs, row equivariance, split batches, and input
immutability. Generated-sample results are development validation, not results
on the evaluator's hidden holdout.

## Validation results

The final fixed configuration obtains:

| Sample | Shots | Baseline failures | Candidate failures | Reduction |
| --- | ---: | ---: | ---: | ---: |
| Supplied calibration | 3,072 | 389 | 43 | 88.95% |
| Fresh independent draws, seed 95173027 | 12,288 | 1,507 | 165 | 89.05% |

All three noise families improve. The fresh-sample paired 95% confidence
interval for the absolute improvement is **10.34–11.50 percentage points**.
These draws were generated after selecting the final configuration.

`public_report.json` and `validation_report.json` contain per-model results.
`experiments/worker_resources.txt` records external process resource accounting
for the supplied worker, with its 180 CPU-second and 6 GiB limits enabled.
External accounting reports **105.89 CPU seconds**, **215.85 seconds wall
time**, and **76.2 MiB peak resident memory**, including worker imports and
initialization. The process exits successfully under the resource limits.
The worker processes two separate 1,024-shot batches per model; its predictions
are checked against the single-batch predictions.

To reproduce the independent validation from this directory:

```sh
export P=/absolute/path/to/participant
export PYTHONPATH="$P/input/runtime:$P/input:$P"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
/usr/bin/python3 experiments/evaluate.py --shots 2048 --seed 95173027 --output final_independent --check-contract
/usr/bin/python3 experiments/worker_check.py --prepare
/usr/bin/time -v -o experiments/worker_resources.txt /usr/bin/python3 "$P/input/worker.py" experiments/worker_request.json experiments/worker_response.json
/usr/bin/python3 experiments/worker_check.py
```
