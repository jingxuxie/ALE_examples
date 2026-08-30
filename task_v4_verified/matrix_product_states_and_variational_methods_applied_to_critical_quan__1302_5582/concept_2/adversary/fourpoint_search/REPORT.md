# A genuinely new four-spin failure, without increasing distance

## Main finding

The authorized v3 tensor passes frozen v2, but its composite order-pair
covariance is wrong by about 21% for the quartet (0,96,224,256), although all
six associated two-X correlations are within 0.061% of their exact values.
This uses total span 256 and gap 128, not a longer-range extension of v2.

Define C4(a,b,c,d) = <X_a X_b X_c X_d> - <X_a X_b><X_c X_d>.
Both factors in the submitted-state subtraction are measured in the submitted
state. The exact target uses the corresponding exact pair expectations.

| Quartet | Exact C4 | Observed C4 | C4 relative error | Raw XXXX error | Worst of six pair errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| (0,16,112,128) | 5.374399318e-4 | 4.729116806e-4 | 12.0066% | 0.06250% | 0.02733% |
| (0,96,224,256) | 1.266005379e-3 | 1.000411264e-3 | 20.9789% | 0.48752% | 0.06037% |
| (0,96,160,256) | 5.011653885e-3 | 4.540304386e-3 | 9.4051% | 1.04178% | 0.03988% |
| (0,192,320,512) | 3.543854761e-3 | 2.746609335e-3 | 22.4966% | 2.25793% | 0.06543% |
| (0,192,448,512) | 8.952205616e-4 | 4.994232337e-4 | 44.2123% | 0.92333% | 0.10907% |

The broad scan contains 15,133 ordered quartets, all with total span at most
1024. It varies both interval lengths, their asymmetry, gap, and cross ratio.
The greatest raw XXXX error is about 5.95% at (0,384,512,1024), with target
0.02484316835 and observation 0.02336536761. This is useful supporting evidence,
but the short-span composite failure is the cleaner new task mechanism.
The 95.6% covariance failure at gap 768 is intentionally NOT used to justify
the proposed task, since it risks being primarily another long-range test.

## Why this is not a two-point test in disguise

An X two-point function probes one boundary-to-boundary matrix element through
the parity-odd transfer sector. A Z two-point function probes one particular
pair of boundary vectors in the even sector. A separated XX-pair covariance
instead couples length-dependent, two-X boundary vectors through the even
sector. Those matrix elements are not fixed by fitting the existing scalar
two-point curves. Here the gap is already inside the tested zz distance range.

At the span-256 example, the error remains about 20.96% after dividing out the
submitted state's own pair product and comparing the connected enhancement.
Consequently this is not simply drift of the two pair normalizations. Raw XXXX
looks much better because it is dominated by the disconnected product.

The submitted four-spin observable must be contracted from the actual tensor.
Reconstructing it from submitted two-point functions by imposing the exact
Cauchy/Wick identity would assume the property being tested and make the task
tautological. Generic variational MPS are not automatically fermionic Gaussian
ground states.

## Focused proposed addition

Retain every current v2 admissibility, energy, and two-point condition. Add the
following complete, predeclared geometry mesh rather than a cherry-picked
single worst quartet:

- left,right in {16,32,64,96}; gap in {32,64,96,128}; retain left+gap+right<=256.
- Quartet = (0,left,left+gap,left+gap+right), including both interval orderings.
- Require max relative composite-covariance error <=10% over the mesh.
- Optionally require max raw XXXX relative error <=2.5% as a consistency gate.
- Use exact lattice targets, not a continuum cross-ratio asymptotic.
- Explicitly reject unstable targets below 1e-6; the actual minimum on this
  proposed mesh is recorded in `focused_results.json` and is much larger.

`proposed_quartets.json` is a private proposal, not a modification or freezing
of participant targets. `focused_checker_score.json` evaluates it against the
authorized tensor. Achievability under this added mesh remains untested: no
optimization or new reference portfolio was run.

The mesh contains 60 quartets; 36 exceed the 10% covariance tolerance. Its
maximum covariance error is 20.9789%, while the maximum raw XXXX error is only
1.04178%. The smallest exact covariance target is 3.234640785e-4, more than 300
times the declared numerical floor. `helper_recheck.json` independently repeats
the final helper CLI evaluation, preserving the original v2 pass and rejecting
the proposed four-point condition.

## Trust and reproducibility

`fourpoint.py` is the proposed trusted helper. It implements the infinite
Cauchy determinant, finite even-N sine determinant, stable exact connected
target, and independent full-matrix MPS contractions. Its CLI can evaluate a
JSON list of quartets without changing the current evaluator:

```sh
PYTHONDONTWRITEBYTECODE=1 python fourpoint.py --state ../../attempts/v_3/state.npz --quartets proposed_quartets.json --output helper_recheck.json
```

`validation_ed.json` checks every quartet on N=6,8,10,12 periodic spin chains
using the full Pauli Hamiltonian, not a fermion implementation. `focused_results.json`
also audits selected anchors with 70-digit exact targets, dense determinants,
uncentered versus centered contractions, and a random complex parity-preserving
gauge transformation. `scan.csv` retains the complete scan; `search_results.json`
records stratified maxima and the input tensor SHA-256. `provenance.md` provides
primary sources, conventions, and the exact permitted-read scope.

The helper's authoritative covariance is the literal raw four-point contraction
minus the submitted pair product. The centered transfer result is retained as
a cross-check, not substituted as a definition: canonical form is only required
within a tolerance, so identity is not assumed to be an exactly fixed matrix
for arbitrary future submissions. On this tensor the two agree numerically.

Measured validation margins: 790 finite-chain quartets agree with full spin ED
to at most 2.276e-15 absolute error; the largest ground-state eigen-residual is
8.545e-14. Focused 70-digit targets agree with the fast exact targets to at most
6.751e-14 relative error. The complex-gauge covariance change is at most
3.039e-15 absolute, and centered versus literal subtraction differs by at most
3.999e-16 absolute. These errors are negligible against the measured deficits.
