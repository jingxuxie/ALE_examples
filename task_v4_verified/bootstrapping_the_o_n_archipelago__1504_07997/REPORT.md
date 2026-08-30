# Hardness-discovery report

| Concept | Mode | Baseline core | Fresh core / worst | Status |
|---|---|---:|---:|---|
| concept_1: Extremal mixed-matrix spectrum recovery | A | 24.34% | 100.00% / 100.00% | solved |
| concept_2: Sparse rank-one mixed-OPE completion | C | 0.00% | 87.50% / 50.00% | hard_verified_achievable |
| concept_3: Active radial spectroscopy | E | 83.42% | 96.68% / 95.82% | solved |

Witness fresh-generation core history: 100.00% → 100.00% → 87.50%.
Champion private scores (core / worst): spectrum recovery 100.00% / 100.00%; active design 96.87% / 96.19%. The previous witness champion solves its own generation but passes 0/8 final-generation replay cases.
Ratchet generations: 0 / 2 / 0 (concepts 1 / 2 / 3).
Counterexample searches: 0/48 for spectrum recovery; 0 meaningful failures across 384 active-design cases; 32 and 40 witness screening cases, followed by eight confirmed failures of each preceding champion replay.
Solvability: demonstrated for all three final tasks; the witness task has independently verified private certificates.
Final status: `hard_verified_achievable`.
Substantive capability: Joint discrete-support recovery for sparse rank-one mixed-OPE matrices with limited, spin-aliased radial probes. After 3562.6 seconds the fresh agent validates 7/8 cases, but one spin-alias case retains a 3.6871e-7 scaled moment residual against the fixed 2e-8 tolerance (18.44 times too large), leaving worst-family validity at 50%. A scan of all 76 saved JSON certificates finds no hidden passing completion; independent 70-digit arithmetic confirms the failure. All eight private certificates pass, with maximum independently checked residual 2.46e-15.
