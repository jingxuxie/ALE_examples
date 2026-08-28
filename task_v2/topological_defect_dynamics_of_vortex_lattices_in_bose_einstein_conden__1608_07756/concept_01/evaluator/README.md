# Private pilot evaluator

Run `python evaluate.py --submission PATH --output PATH` with numerical library
thread counts set to one. `hidden/truth` contains dt=0.0005 propagation and
independent observable recomputation. The submitted system is rerun on five
physical/domain families with randomized identifiers and asset names. No grading
code, target states, or manuscript is participant-visible.

Each family receives continuous field/density (42%), signed-core (15%),
coordination/order (18%), and kinetic/physical (25%) accuracy, discounted for
inconsistent raw diagnostics or result tables. Core score is 70% mean plus 30%
worst family. Overall score is 85% core + 10% continuous runtime utility + 5%
evidence. Core, rather than presentation, governs the hardness classification.

The physical contract fixes observable conventions, not a preferred solver.
The finite-grid reference is checked against an independent DOP853 Hamiltonian
integration and timestep halving. Counts near mesh degeneracies are scored
continuously, not through brittle exact equality. Initial states are GPE
reconstructions, not a toy point-lattice generator or claimed author data.

The five families are: rapidly rotating circular bulk, nonrotating isolated-core
healing, a driven rectangular elliptic trap, multiply connected annular current,
and two separated material domains. Mere changes of seed/size do not define any
family. Shared propagation alone cannot satisfy independent signed-topology,
material-boundary, and energy-partition measurements. The empirical screen may
still reject this combined workflow as ordinary coding.

Evidence audit checks the submitted primary run by rerunning it, table/raw-record
consistency, genuine numerical/method ablations, claims' numerical comparisons,
and valid figure assets. Scientific interpretation and timeout attribution also
receive a separate private transcript/report audit; PNG aesthetics are ignored.
