# Scoring environment

Run `python evaluator/evaluate.py --submission PATH --report score.json` from the concept directory. The submission contains `solve.py`. `--public` evaluates the supplied examples only. Linux bubblewrap, Python 3, NumPy and SciPy are the runtime prerequisites; the core planner/checker uses only the standard library.

Each submission executes with only system runtime, the public participant tree, its own submission tree, and a temporary input/output directory mounted. Network, host process namespace, and hidden evaluator files are not available. The output is untrusted declarative JSON; the host independently checks exact symbolic equality and recomputes the trusted baseline. Symlink output artifacts are rejected.

The 30-second planner clock starts inside the initialized sandbox. Bubblewrap setup has a separate 240-second infrastructure allowance and is not charged as planning time. Address space is capped at 2 GiB and CPU affinity at one logical CPU. Every hidden case must return a valid plan. Infrastructure failure must be repaired or marked invalid, never interpreted as scientific hardness.

Before the tournament, the numerical audit compared the exact symbolic verifier's accepted plans against independent, unoptimized einsum evaluation of complete monomials. Four negative controls per public family check missing outputs, duplicates, invalid axes and insufficient memory. The private source extraction records the pinned source path and line for each primitive contraction.
