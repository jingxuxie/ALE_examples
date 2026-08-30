# Native-CX linear synthesis

Construct exact, hardware-native reversible circuits for four specified Boolean
linear transformations. Optimize both native CX count and duration-weighted
depth on the supplied sparse devices.

- **Assets:** `input/instances.json` contains every target matrix, native directed
  CX instruction and duration, and fixed acceptance caps. `input/FORMAT.md` and
  `input/SCORING.md` define the complete contract.
- **Deliverable:** one `solution.json` in your designated output directory,
  containing an ordered list of `[control, target]` CX pairs for each named target.
  No executable, external file reference or submitted schedule is accepted.
- **Witness conditions:** all four transformations must be exact on all inputs,
  use only their native instructions, and meet **both** caps independently.
  Qubit labels are fixed; no ancillas or free input/output permutations exist.
  Partial scores are diagnostic, never a passing submission.
- **Tools:** `python workspace/checker.py /path/to/solution.json` checks an artifact.
  `baseline/solve.py` supplies a runnable exact but unoptimized starting point.
  `input/RESOURCES.md` records scientific provenance and runtime resources.

Only the participant package and your assigned output directory are task assets.
Use local computation; no quantum hardware or network service is required. The
evaluator reads the JSON witness and never executes your synthesis program.
