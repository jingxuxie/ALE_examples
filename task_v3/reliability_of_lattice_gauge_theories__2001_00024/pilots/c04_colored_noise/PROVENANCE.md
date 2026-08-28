# Pre-implementation provenance and scope

Recorded 2026-08-27 local, before implementation and precomputation.

## Primary sources reviewed

- Jad C. Halimeh and Philipp Hauke, *Reliability of lattice gauge theories*,
  arXiv:2001.00024v1. The Z2 matter/link Hamiltonian, Gauss constraints, coherent
  errors, energetic protection, and comparison of physical observables motivate
  the task. Main-text Eqs. (1), (2), (7) are the model anchors.
  Source: https://arxiv.org/pdf/2001.00024
- Bhavik Kumar, Philipp Hauke, and Jad C. Halimeh, *Suppression of 1/f noise in
  quantum simulators of gauge theories*, arXiv:2210.06489v1. **The actual full
  12-page PDF**, including Appendices A--C, was consulted, not a short abstract
  or an assumed four-page version. Frequency-dependent suppression and the
  frequency-resolved secular dissipator in Appendix B, Eqs. (B1)--(B3), are the
  formalism anchors. We do NOT ask participants to guess secular cutoffs from
  the main-text Redfield tensor, Eq. (7).
  Source: https://arxiv.org/pdf/2210.06489
- arXiv:2403.14656 was identified as optional context only. It supplies no
  equations, numerical labels, or claims of verification for this pilot.

## What is and is not a reproduction

`private/reference/` will contain a new benchmark-author reimplementation of the
follow-up's frequency-resolved **fully secular** formalism. It is **not official
author code**, not a QuTiP reproduction, and not a claim to reproduce a paper
figure or the nonsecular Redfield tensor. Reference outputs will be actually
computed from that implementation and frozen with hashes and runtimes.

The benchmark explicitly extends the source setting: regularized infrared spectra
and white floors, finite-band noisy calibration and model selection, correlated
baths, a link-basis Hadamard rotation, a three-site periodic ring, finite actuator
menus, and known quadratic crosstalk. These are author-designed modeling choices,
not empirical data or claims made by the cited authors. `participant/input/protocol.md`
is authoritative for every mathematical convention. No external paper is needed
to solve the task. Existing unrelated source archives are not copied or credited
as a colored-noise reference.

## Validity boundaries

This is a defined weak-coupling Markov/secular effective model, not an exact
simulation of long-memory classical 1/f trajectories. The infrared cutoff makes
zero-frequency rates finite. Equal-frequency transitions remain coherent within
each channel; distinct frequencies are fully secularized even if nearly spaced.
Exact degeneracy is handled with spectral projectors. No thermal detailed balance
or Lamb shift is inferred: the spectrum is two-sided, even, and includes the
coupling strength. The model does not establish experimental validity of the
Markov approximation near arbitrarily small splittings. Small exact systems are
intentional: inference, correct rates, and experimental decisions are the target.
