# Catalogue interface

Each NPZ contains `source`, `target` (unique undirected edge endpoints), `channels` (edge by phonon-branch nonnegative symmetric conductances), `mixing` (temperature by branch positive coefficients), `velocities` (state by three Cartesian drives), `probes` (state by collision-dissipation probes), `positions` (state by three reduced coordinates), `budget` (scalar integer), and `temperatures` (K).

At temperature index t, edge conductance is `channels @ mixing[t]`. These detailed-balance conductances define a weighted graph Laplacian L. All states have equal quadrature weight. The connected constant mode is the only null mode; drives and probes have zero mean. Units and an overall conductivity prefactor cancel from every relative diagnostic. Physical phonon thermal factors are included in `mixing`; no occupations need to be reconstructed. Graph diagonals represent rates, not self-scattering events.

The output NPZ contains one-dimensional `indices` (distinct integer indices into input edges) and `multipliers` (finite real numbers in [0, 1e9]). The number of retained edges must not exceed `budget`; no new edges are allowed. All phonon channels on an event share its multiplier. The graph must remain connected. Extra keys are ignored.

`workspace/physics.py` is the authoritative public definition of physical diagnostics and per-case score. For every temperature it compares degree relative RMS, the relative conductivity-tensor operator error, and the maximum relative dissipation error over the supplied probes. The case error is the maximum of these diagnostics over temperatures; case score is `100*exp(-error/0.05)`. Overall score is the unweighted case mean and worst-family score is the minimum family mean. The target is fixed in TASK.md.

Development and hidden cases have 72–168 states, 3–5 phonon branches, 5–7 temperatures, 12–24 probes, and event budgets between 6 and 9 times the number of states. No hidden family identifiers, seeds, or expected outputs are required by the solver.
