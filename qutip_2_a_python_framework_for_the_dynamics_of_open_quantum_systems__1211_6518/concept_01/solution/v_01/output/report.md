# Qualification report

The release candidate separates prescribed-collapse evolution from static
Redfield and periodic spectral-bath models. The latter two cannot be validated
by trace or positivity alone. A local Hermitian collapse approximation is the
controlled ablation: it deliberately keeps the old noise assumption while
fixing amplitude and representation handling. Production and refined use the
same physical model at different numerical resolutions. Results are generated
by the three commands/configurations in the submitted campaign.

The initial inspection identified three distinct sources of discrepancy:
time-dependent collapse amplitudes were applied as rates; the process adapter
used row-vectorization while the interface specified column-vectorization; and
the spectral branches substituted bare local operators for frequency-resolved
noise. Running the baseline produces physical-looking traces despite these
defects. The repair therefore did not use positive density matrices as its
sole acceptance criterion. After each repair, independent analytic limits and
the public experiment suite were rerun. The private qualification also checks
the Redfield tensor by an independently indexed contraction, and the driven
closed-system Floquet trajectory against direct integration.

Static Redfield retains the requested secular or nonsecular terms, including
interference at degeneracy. Periodic spectral evolution includes sidebands,
diagonal dephasing and laboratory micromotion, starting at the actual absolute
initial time. The explicit-collapse branch acts with sparse operators on
density matrices or a block of channel basis operators, rather than building a
dense dimension-to-the-fourth Liouvillian. Discontinuous controls are integrated
in separate intervals; narrow pulses constrain the integration mesh.

The final first-observable comparisons in results.csv and ablation.csv expose
the cost of local-noise assumptions. The linked claims.json comparisons are
only convergence checks, not independent accuracy labels. In particular,
agreement of production and refined does not establish that their physical
approximation is valid for a finite-memory environment. The contract specifies
a Markov approximation even for filtered spectra. Nonsecular Redfield is not
projected to positivity; doing so would conceal a limitation of that model.

The oscillator cutoff study in scaling.csv measures computational cost and
boundary occupation. A low boundary population supports cutoff adequacy for
this experiment but is not a uniform error certificate. Floquet reduction is
valuable at long physical times; sparse direct action is appropriate for the
large resonator. There is no claim that one backend is uniformly fastest or
that local and microscopic dissipation must disagree in every regime.
