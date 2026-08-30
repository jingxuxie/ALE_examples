# Private concept selection ledger

Paper seed: Milsted, Haegeman, Osborne, arXiv:1302.5582, particularly the variational optimization, excitation masses, local occupation truncation and finite-entanglement scaling sections. Created before the first tournament, 2026-08-28.

Eight candidates were considered before building the maximum of three:

1. **A: finite bosonic MPS optimization across phase/conditioning families. Selected (concept_1).** The optimization gap is measurable through independently contracted tensor energies. Tight resources, metastable branches and nonuniform wells obstruct a single fixed sweep recipe. Private expensive solves can calibrate targets without being participant assets.
2. **C: multiscale critical-vacuum MPS construction. Selected (concept_2).** Construct one small, symmetric, primitive tensor matching energy and two inequivalent correlation channels over two decades of distance. A good local variational energy alone is insufficient. Exact Ising observables make the witness checker independent of any tensor solution. The Ising model is the paper's universality calibration, not a claim to simulate continuum phi4 exactly.
3. **D: low-cutoff to converged excitation-gap prediction. Selected (concept_3).** High-cutoff parity-resolved simulations provide private labels. Tunnelling, crossover and weak coupling have different cutoff behavior, making extrapolation harder than copying one formula. Public training and holdouts use the same documented physics.
4. **B: occupation-tail cutoff certificate falsification. Not built.** Tiny omitted occupation does not control relative tunnelling gaps. Initially attractive but likely collapses to a scalar double-well parameter sweep; the stronger useful issue is retained in the prediction families instead.
5. **F: evoMPS near-singular transfer pseudoinverse repair. Not built.** Real upstream issues concern poor conditioning and nullspace handling. A narrowly framed version risks being one standard projected Krylov solve; a broad port risks testing dependency archaeology rather than research capability.
6. **E: adaptive critical-coupling experiment allocation. Not built.** Finite-entanglement and lattice-cutoff bias make query allocation interesting, but a synthetic response surface would inject too much generator-specific modeling. Real MPS oracle calls would be costly and noisy to certify within this build.
7. **B: negative tangent excitation above a locally converged vacuum. Not built.** A symmetry-fixed saddle can make this trivial. Requiring a strict local minimum and globally lower branch would be meaningful but needs a substantially more complex trustworthy Hessian checker.
8. **C: low-bond real-time soliton scattering witness. Not built.** Scientifically rich, but a robust finite-time many-body target would require more expensive state preparation and boundary-error certification than the selected stationary witness.
9. **D: spectral-density reconstruction from Euclidean correlators. Not built.** An inverse problem with genuine hardness, but an ill-posed label convention could dominate the benchmark. The selected excitation gaps admit direct residual and cutoff checks.

Only concepts 1–3 are built. No task is retained merely for equation count, implementation size, or reproducing an upstream package. A failed agent does not by itself establish achievability; absent a passing private artifact the label must remain `hard_open_candidate`.

## Primary sources inspected

- https://arxiv.org/abs/1302.5582 and https://arxiv.org/pdf/1302.5582
- https://github.com/amilsted/evoMPS (author-maintained implementation), its issues and commit history
- https://arxiv.org/abs/1907.08603 (transfer-spectrum refinement of finite-entanglement scaling)
- Pfeuty, *Annals of Physics* 57 (1970), DOI 10.1016/0003-4916(70)90270-8, https://www.math.ucdavis.edu/~bxn/pfeuty1970.pdf
- https://arxiv.org/abs/quant-ph/0202162 (two-site Ising observables; normalization independently checked)

The older same-paper task in `tasks/...1302_5582` was inspected as generation-time context only. Its status records a 100-point reference and a 600-second gpt-5.6-sol timeout without the required module. That result is not evidence about this one-hour ultima-alpha tournament. The older task combined operator construction, periodic tangent contractions, prescribed extrapolation fits, and planning; these new concepts instead score research artifacts and numerical behavior. It and all other previous submissions are excluded from every participant allowlist.
