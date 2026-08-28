# Release-candidate incident notes

These are observations, not certified physical conclusions.

- The stationary control drifts despite no time-dependent Hamiltonian term. Reducing the time step changes less than changing the lead representation.
- The ring can produce a transient even when its preparation was intended to be stationary. Its contacts do not have the same occupation.
- Some side-branch oscillations persist after the pulse; the team is split between a numerical reflection explanation and a localized-state explanation.
- A stronger imaginary boundary can make late-time curves smoother without stabilizing their values.
- The spin and honeycomb cases make brute-force reservoir enlargement expensive. Changing a lead's internal cell basis should not change the measured central observables.
- The dimerized contact is not equivalent to a flat-band bath. We have no certified transient trace for it.

The current code's numerical defaults are provisional. These notes do not imply that exactly one bug or one common parameter change explains all observations.
