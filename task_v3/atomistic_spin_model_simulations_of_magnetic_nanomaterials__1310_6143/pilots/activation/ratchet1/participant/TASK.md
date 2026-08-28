# Scalable magnetic transition states

Extend the supplied transition-state solver to long, heterogeneous magnetic
chains. Recover the lowest index-one saddle connecting the supplied minima,
its activation barrier, and the complete harmonic fluctuation data within the
execution budget.

The baseline is accurate on short chains but is not reliable on long chains.
Coherent reversal, localized boundary nucleation, and soft-interface reversal
must share one implementation. Both transition search and fluctuation analysis
are scored; an unconverged or disconnected saddle is not a solution.

Implement `solve.py CASE.json OUTPUT.npz` in your submission directory.
Use `input/FORMAT.md` for the physical and execution contract. The workspace
contains the baseline, energy utilities, and numerical dependencies. Inputs are
examples without reference answers; hidden cases use independently chosen
parameters and lengths up to 4,096 spins.
