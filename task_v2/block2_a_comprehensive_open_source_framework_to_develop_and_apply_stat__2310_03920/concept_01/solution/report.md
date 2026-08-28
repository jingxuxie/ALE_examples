# Transport reliability study

## Diagnosis

The migrated integral path does not represent the specified Hamiltonian. Its
onsite tensor carries half the required U; scalar real hopping discards both
magnetic phases and spin mixing. It excludes the density interactions,
pairing, Zeeman and oscillator terms. Its fixed N,Sz state space is invalid
for the paired and spin-mixed contacts. More sweeps cannot repair these
representation errors. The impurity legacy and repaired energies differ by
about 0.1615 even though a much stronger refinement of the repaired development
calculation changes its ground energy by less than 1e-11. This distinguishes
physical assembly from finite-bond convergence.

## Repair and controlled experiments

The replacement assembles the explicitly ordered fermion products, including
their Hermitian conjugates, in physical site labels. Its local electronic
states and quantum sectors depend on the actual conservation law. In a parity
sector the two even states must form one degenerate block; this was caught and
fixed during independent exact verification. Oscillator spaces are retained
at the supplied cutoff and interleaved with their coupled electrons. The
time evolution is a two-site complex tensor-network sweep, with independent
ground-state sweeps and propagation settings. Every observable is constructed
from the specified physical operator, not from a stale tensor index.

The provided development study compares low-cost, production and refined
policies across five regimes. The production/refined disagreement is much
smaller than the low-cost/production disagreement in the entangled contacts.
The low-cost paired and spin-orbit trajectories visibly illustrate why a
nearly conserved norm is insufficient. Vibronic ground-state energy also
changes under preparation refinement, so not all error is a time-step error.
The ablation changes several resource controls together; it does not identify
the isolated order of a time integrator. The source data and all actual run
outputs are included. Resource scaling uses both configuration and full local
Hilbert-space size; the latter is not a prediction of tensor-network cost.

An independent sparse occupation-basis implementation checks four-site
instances from all five regimes. Ground energies and all time-resolved
observables agree within 2e-6, with substantially smaller errors in most
channels. Hidden-size refinement is also performed privately before accepting
this reference. Small-system agreement alone would not certify large-system
truncation error; that is why both checks are used.

## Interpretation and limitations

The correct regional continuity relation includes the pairing source. A
nonzero regional charge derivative need not equal a bond transport current in
a paired contact. A number-conserving state-space truncation can look stable
while eliminating this effect altogether. In nonpaired contacts total number
is conserved; Sz need not be conserved in spin-orbit contacts. Energy refers
to the post-quench Hamiltonian and is conserved only after the quench.

The reported short finite-system traces support transient transport and the
listed refinement comparisons, not an infinite-lead conductance or a true
steady-state plateau. Numerical normalization, if added by a future solver,
must not be treated as an accuracy test. Larger systems or later times can
need different bond dimensions and the present resource policy is not claimed
to be uniformly optimal beyond the documented bounded regime.
