# Private generation-one champion search

Run from the repository root:

```
OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 python \
  tasks_v4/bootstrapping_the_o_n_archipelago__1504_07997/concept_1/adversary/champion_search_1/search.py
```

The search imports the existing exact-PSD generator's `make_case`, frozen scorer,
and existing high-precision `conditioned_fit` validator without modifying them.
It generates 48 new-seed cases: eight per existing family, cycling the original
variants 0, 1 and 2. No coefficient magnitudes, gap ranges, dimensions, atom
counts, precision requirements, or acceptance thresholds are extended. This is
an empirical fresh-data search, not a new task or static code review.

Every case must first pass planted-spectrum scoring and the original 270-digit
moment reconstruction: full column rank, condition number below 1e100, recovered
weight relative error below 1e-60, PSD spot checks, degree/count/gap checks, and
the original 240-significant-digit RHS. Explicit input-bound checks are added.

The actual frozen `champions/generation_1/output/solve.py` is then executed through
Main's unchanged `authoring/sandbox.py`, with a separate private scratch directory,
30-second wall limit, 1 GiB address space and one CPU per case. Six independent
workers use distinct CPU affinities. The champion sees only its submission,
participant assets, scratch and JSON stdin; witnesses stay outside the sandbox.
Nonperfect outcomes are automatically repeated in a second isolated invocation.

`search_manifest.json` records seeds, parameters and source hashes. Each `cases/`
directory contains exact input, private witness, validation, champion stdout,
stderr, score and hashes. `results.json` summarizes family means, minimum case
score, runtimes and conditioning; `counterexamples.json` contains only validated
nonperfect cases and their repeats. A failure to validate generated data does not
count against the champion. The original 18-case suite's 240-second total cap is
not misapplied to this 48-case exploratory run.

Protected-file hashes cover participant assets, current evaluator/generator,
manifest, status, champion entry points and shared sandbox. Only this new private
adversary directory is written. No agents are launched, no current tasks are
ratcheted, and no status is changed. An empty counterexample set supports only
the stated search scope, not a proof that every admissible case is solved.
