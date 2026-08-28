# Independent two-spin directional-ensemble audit

This sidecar never changes any pilot participant, evaluator, frozen case, or
reference. Small N is an independent oracle test only; pilot tasks remain at
least 2,048 spins. No pilot/model agents are launched.

## Measure derivation

For two independent unit spins with product uniform solid-angle measure, their
relative cosine `c = s1 dot s2` is uniform on `[-1,1]`. Define
`u = |s1+s2|/2`, so `c = 2u^2-1` and `dc/2 = 2u du`. Rotational invariance makes
the total direction n uniform on the sphere and the remaining azimuth phi
uniform on `[0,2pi)`, independently of u. Thus the normalized conditional
measure at fixed n is `2u du dphi/(2pi)`, not `du dphi/(2pi)`.

Equivalently, with `e_theta=(cos(theta),0,-sin(theta))` and `e_y=(0,1,0)`,

```
n = (sin(theta),0,cos(theta))
e_phi = cos(phi)*e_theta + sin(phi)*e_y
s1 = u*n + sqrt(1-u*u)*e_phi
s2 = u*n - sqrt(1-u*u)*e_phi
```

At u=0 the total direction is undefined, but that endpoint has zero measure.
The unnormalized product measure is `4u du dphi dOmega_n`; conditioning and
normalizing yields the expression above. Label exchange corresponds to
`phi -> phi+pi`; both labeled states must be retained when onsite tensors differ.

The official pair-move acceptance contains
`(Mnew/Mold)^2 * abs(s2z_old/s2z_new)` in the constraint frame. For two equal
moments, `Mz=2u` and `s2z=u`, so this reduces to `u_new/u_old`, exactly the
additional weight needed relative to the first spin's `du dphi` proposal measure.
Deleting the M-squared factor would instead produce a nonnormalizable `du/u`
target at this N; the explicit flat-u and u-squared controls are well-defined
alternative measures, not claims to reproduce that singular erroneous sampler.

Primary method source: https://arxiv.org/abs/1006.3507, Appendix A, Eq. A11.
The actual tested implementation and its unchanged extraction hashes are in
`provenance.json`; the quadrature is independently derived, not code borrowed
from the CMC energy adapter.

## Exact oracle

For each of four unequal-diagonal-onsite, exchange/axial-bond models:

```
H = -J*(2u^2-1) - b*s1z*s2z - sum_a Q1a*s1a^2 - sum_a Q2a*s2a^2
Z(theta) = integral_0^1 2u du integral_0^(2pi) dphi/(2pi) exp(-H/T)
Delta f(theta) = -T/2 * log(Z(theta)/Z(0))
tau(theta) = <sum_i (s_i cross (-dH/ds_i))_y>/2
```

Gauss-Legendre integration in u and periodic trapezoidal integration in phi use
128x256 and 256x512 grids at every angle, with 384x768 checks at pi/4. The oracle
also verifies partition derivatives against torque and the analytic isotropic
partition `sinh(J/T)/(J/T)` for positive, negative, and zero J. The J=0 isotropic
check has `<u>=2/3`. These tests do not use native energy or torque routines.

The native binary is compiled from byte-identical private copies of the frozen
engine and extracted functions. It samples the actual neighboring two-spin
graph, with the same energy/unit adapter and constraints as the pilot. Native
block torque, moment u, and energy are compared to the direct oracle. Separate
controls use flat u, u-squared, and doubled exchange-plus-axial bond weights;
observables in the controls still use the physical, single-counted Hamiltonian.

## Statistics and decision rules

An early six-chain screen tests three angles per model. Any seven-SEM discrepancy
stops the audit and creates `STATUS.json` with FAIL. The full audit uses 33 angles
per model and twelve independently seeded chains per angle, each with 100,000
burn sweeps and 1,000,000 measured sweeps. Alternating chains also use the frozen
engine's 2,000-sweep hot-start option. Measurements and block size are unchanged
native output conventions: every five sweeps, aggregated into 10,000-sweep blocks.

SEM is the maximum of between-chain SEM and pooled block-SEM estimates after
reblocking by factors 1, 2, and 5. R-hat uses the native block means. All three
stationary observables must agree within 5.5 SEM and have R-hat below 1.05.
This is a conservative finite-sample audit threshold, not an exact coverage claim.

Native free energies are composite-Simpson integrals of independently sampled
torque at the 33 angles, reported at the 17 even-indexed angles. They are compared
against direct log-partition ratios, not against another torque integration.
The quadrature-only Simpson bias is separately reported and must be less than
0.25 of the propagated sampling SEM. It is never subtracted from native results.
Free-energy disagreement must be below 5.5 SEM. Wrong-target controls must each
be rejected by more than eight SEM in every model. Constraint/norm diagnostics
must remain below 1e-7. These checks validate these finite models; they do not
prove mixing for every large, frustrated, or near-critical pilot system.

## Reproduction and artifacts

From this directory, using only the existing read-only authoring runtime:

```
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export PYTHONPATH="$(dirname "$PWD")/python_runtime"
python prepare.py
python audit.py --workers 16
python seal.py
```

`cases.json`, `models/`, and `source/` contain all inputs. `raw/` contains blocked
native trajectories, seeds, and timings. `results/oracle.json`, `screen.json`,
and `full.json` contain detailed comparisons. `STATUS.json` is the explicit
pass/fail decision. Cached jobs are reused only for this fixed sidecar; archive
the sidecar raw/results directories before changing its definitions or source.
`MANIFEST.json` seals all inputs, source, raw chains, and results after rechecking
that the original frozen pilot source hashes still match.
