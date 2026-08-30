# Active radial spectroscopy

## Mission
Build a sequential experiment policy for a **reduced** two-channel positive
radial spectral measure. Infer the lowest state's exponent, log spectral gap,
log OPE-strength proxy, and projective OPE mixing angle from at most **72 noisy
scalar oracle calls**. The two low states and positive matrix tail are unknown.
This is not full 3d crossing, CFT reconstruction, or a current-central-charge task.
Paper seed: *Bootstrapping the O(N) Archipelago*, arXiv:1504.07997.

## Assets and entrypoint
- `input/CONTRACT.md`: exact model, distributions, JSONL protocol, limits, scoring.
- `input/target.json`: authoritative frozen success thresholds.
- `input/model.py`, `input/protocol.py`, `input/sample.py`: public simulator,
  validators, and reproducible labeled training samples.
- `baseline/policy.py`: runnable weak baseline; `workspace/policy.py`: starter.
- Submit a directory containing **`policy.py`**. It reads stdin and writes flushed
  JSONL to stdout; diagnostics belong on stderr. Each instance starts a new process.
- `import radial_public` locates public inputs under the tournament wrapper,
  including when it clears environment variables and uses scratch as cwd.

## Objectives and resources
Meet the frozen parameter-error and interval-calibration thresholds across all
six public families. Robust loss weights the worst family; every case must obey
the contract. No case truth or score is returned during interaction.

One CPU core, **45 seconds per instance**, 15 seconds between messages, 2 GiB
address-space limit under the supplied tournament wrapper. Python, numpy, scipy,
mpmath, and standard library are available; no cvxpy. Participant/submission
files are read-only during evaluation; only scratch is writable. Do not access
hidden evaluator material, other submissions, parent memory, or the network.

Operational achievability is **unknown**; no reference solution is supplied.
