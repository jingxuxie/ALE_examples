# Scientific seed and controls

Seed: ALF collaboration, arXiv:2012.11914v2, release 2.0, finite-temperature
auxiliary-field weights, the sign problem, symmetric time decomposition and
Hubbard models. The benchmark uses the standard real two-state spin-channel
Hubbard-Stratonovich specialization, fully specified in the public contract;
it is not an exact port of ALF's default four-state generalized decoupling.

Inspected official later source at commit
f81b5cbc74b098b3910cc22e6d31b918be1e1223, especially
Prog/Hamiltonians/Hamiltonian_Hubbard_Plain_Vanilla_smod.F90, and the changes
in logarithmic global-update ratios documented by official PR603. Current
source, changelog and issue records are stored in the root research directory.

The sign-free screening claim is explicitly an in-house hypothesis for this
benchmark; it is not attributed to the paper or ALF developers. Rare signs in
a finite-step, doped Hubbard ensemble are a physical counterexample search,
not a numerical-overflow attack.

Private initial random search found a negative field at beta=3, U=4, mu=1,
24 time slices after 768 draws, then at beta=2 and 16 slices after 401664
draws. The beta=2 field passes independent 65/95-digit certification at all
three perturbations. The same field has positive weight at half filling,
providing a particle-hole-symmetry control. This is checker validation, not
a passing solution to the beta=1.6 task.

Target beta=1.6 and the three publicly declared perturbations are frozen
before the first fresh attempt. A privileged continuation search may
demonstrate achievability after that freeze without changing the target.

## Champion ratchet

The first ultima-alpha submission passed the original beta=1.6 task. Its
search found the witness in about 2.08 seconds of numerical work. A private
1,632-case beta/chemical-potential sweep found 1,533 parameter points at which
that fixed witness was positive. The actual champion search, not merely its
fixed field, found new signs at beta=0.85 in 40.48 seconds and beta=0.80 in
109.06 seconds, but no sign at beta=0.75 in its 120-second screening probe.
The second generation freezes beta=0.75 and supplies both the old witness
and its search implementation, with only path plumbing adapted for portability.

Additional privileged continuation and portfolio work independently verifies
a robust witness at beta=0.786. A nominal beta=0.785 candidate does not pass
the perturbation stencil. Continuation, dual objectives, continuous relaxation,
binary rounding and 597,504 structured block candidates do not produce a
beta=0.75 witness. These are finite search results, not nonexistence proofs.

An additional primary-source check inspected Iazzi, Soluyanov and Troyer,
arXiv:1410.8535, on the geometric origin of auxiliary-field negative signs and
their survival of precision/smoothing checks. It does not establish feasibility
or infeasibility for this benchmark's specific beta=0.75 finite-step window.
https://arxiv.org/abs/1410.8535
