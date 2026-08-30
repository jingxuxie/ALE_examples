# Resource-bounded portfolio submission

Self-contained online packaging of the existing portfolio strategy. It reads
only the supplied input directory and imports only its local engine/catalog
reader plus standard Python, NumPy, and SciPy environment dependencies.

The planner recomputes the public 32-trial baseline online as its incumbent,
then tries up to 256 diversified trials with the original portfolio seed.
All search shares a 44-second cooperative deadline, leaving startup margin
under the unchanged authoritative 60-second per-fleet allowance. No private
policies, fleet identifiers, hidden answers, or cross-instance cache are embedded.

The engine is the public baseline algorithm with only a cooperative deadline
added. Candidate design choices, case ordering, and ambiguity-prior weights
are varied exactly as in the existing offline portfolio. Offline baseline
policy loading is replaced by online computation of the same baseline.

Run with `/usr/bin/python3 solve.py --input INPUT_DIRECTORY --output OUTPUT_JSON`.
Only an authoritative passing evaluation establishes online achievability.
