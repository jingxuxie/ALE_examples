# Predict the dynamical spin fraction

**Mode D — HIDDEN PREDICTION.** Learn a fast, sample-specific surrogate for the
Pal–Huse dynamical spin fraction, not an ensemble-mean phase classifier.

## Physics and target

For the supplied exact site-ordered fields, use the spin-1/2 Hamiltonian
`H = sum_j [h_j S_j^z + S_j . S_(j+1)]`, periodic boundaries, `J = 1`,
and total `Sz = 0`. Length `L` is 10 or 12. Let `D = binomial(L, L/2)` and
sort eigenstates by ascending energy. Select zero-based ranks
`D//3 <= n < (2*D)//3`: 84 states at L10, 308 at L12. Define
`M = sum_j exp(2*pi*i*j/L) S_j^z` and, following Pal–Huse Eq. (6),

`f = mean_n [1 - abs(<n|M|n>)**2 / <n|M†M|n>]`.

This is the **mean of the eigenstate ratios**, not a ratio of summed
numerators and denominators. Predict one dimensionless `f` in `[0,1]` for
each realization. Site order and resonances matter. Frozen executable
physics is provided in `workspace/physics.py`.
Source: Pal and Huse, *The many-body localization phase transition*,
Phys. Rev. B 82, 174411 (2010), arXiv:1010.1992, Eqs. (1), (3), (6).

## Public data and distribution

`input/train.jsonl` has 1,600 actual float64 exact-diagonalization records;
`input/validation.jsonl` has 320 independent labeled records. Each has
`id`, `L`, `fields`, `family`, `f`. Every split is balanced across both
lengths and four families. Training has 200 records per family/length;
validation and the hidden 320-case test each have 40 per family/length.
There is no train/test symmetry duplication.

The **complete shared sampling law** is `workspace/generators.py`:
- `iid_uniform`: independent uniform site fields.
- `ordered_blocks`: two or three contiguous, internally weakly disordered
  blocks, with detuned boundaries resembling weak transport links.
- `alternating_correlated`: staggered fields plus a long-wave correlated
  component and continuous site noise.
- `shuffled_pairs`: near-resonant field pairs shuffled onto the ring.

All bonds still have `J=1`; weak-link-like profiles do not alter couplings.
The common amplitude mixture is uniform on `[0.4,1.8]`, `[1.8,4.5]`,
`[4.5,8.0]` with probabilities `0.2,0.5,0.3`. Fields are nondegenerate.
Training/validation generator seeds are public in `input/data_checks.json`.
Hidden vectors are independent draws of this same published law, frozen
before launch from OS entropy, without a retained secret seed. There are
no hidden physical parameters: every target is determined by the exact
bare field vector. Family and amplitude are **not** inference inputs.

## Submission and limits

Place `predict.py` and any trained assets together in the submitted
workspace. The official isolated evaluator starts the program without arguments:

`python3 /submission/predict.py`

Within **60 startup seconds**, load your model and print exactly `READY`
followed by a newline, flushing stdout. Hidden fields are not mounted or
sent before readiness. The evaluator then sends one JSON line on stdin;
return one JSON line on stdout. No other stdout text is allowed. Use
stderr for diagnostics. The **3-second inference clock** starts only
after the input is delivered, and includes parsing, features, prediction,
serialization and flushing the complete response line.

Input is JSON `{"cases":[{"id":"...","L":10,"fields":[...]}]}`.
Output must be JSON `{"predictions":[{"id":"...","f":0.5}]}` with
exactly one finite numeric `[0,1]` prediction for every ID, no extra keys.
Order is arbitrary. The starter additionally reads input JSON-lines.
IDs carry no physical information. Do not infer labels from IDs.

The entire 320-case inference batch has **3 wall seconds, four CPU cores
(enforced affinity), 2,048 MiB address space**, and no network. Model
loading belongs to the separate 60-second startup allowance. `/submission` and `/participant` are
read-only; only `/tmp` and `/output` are writable. No evaluator, hidden
bank, parent workspace, or private generator is exposed. There is no
cross-evaluation persistent cache. Full test-batch ED is not the intended
solution; train a surrogate or an appropriately fast approximation.

One hour of training/probing is allowed before the timed inference call.
You may use training and validation labels, generate more samples with
the public physics/generators, and fit models. Do not access private
evaluation artifacts. A passing solution is not supplied or guaranteed.

## Scoring and starter

Fixed prelaunch targets: overall RMSE **<= 0.035** and worst-family RMSE
**<= 0.050**, both required; absolute errors use the physical `[0,1]` scale.
Targets were frozen on August 28, 2026 after public-validation calibration,
before any fresh solving attempt; they will not change during solving.
An invalid output or resource-limit failure fails regardless of accuracy.
Family RMSE pools both lengths; length metrics are diagnostic only.

The provided `workspace/predict.py` loads `baseline.pkl.gz`, a descriptor
ExtraTrees surrogate. Refit with `python3 workspace/train_baseline.py`.
The starter retains `--input input/validation_cases.json --output
predictions.json` for local file-based testing only. Official scoring
always uses the no-argument streaming protocol. The submission should
reply, flush, and exit within the inference window. Public data,
physics checks, and baseline validation metrics are under `input/`.

The final 200-tree baseline has validation RMSE **0.03895 overall / 0.04552
worst-family** and therefore does not meet the overall accuracy target.
It has an official successful inference measurement of 0.3507 seconds;
see `input/official_streaming_benchmark.json`. Earlier configurations had
intermittent timeouts; full prelaunch timing history is retained privately.
`input/streaming_benchmark.json` is a historical local, non-isolated
diagnostic, not the official timing result. All paths here are relative
to the participant directory. `baseline/` is a self-contained copy of
the finalized starter and can be passed directly to the evaluator.
An ordinary four-process full-ED control needs **33.80 inference seconds**
even with basis construction before `READY`, so it fails the 3-second cap;
its separate startup is not charged. See `input/ed_control_timing.json`.
