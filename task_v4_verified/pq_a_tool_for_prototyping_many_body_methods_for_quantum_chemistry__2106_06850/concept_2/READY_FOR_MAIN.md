# Concept 2 is ready for a fresh participant launch

**Freeze generation: population-witness-v1.** Only the `participant/` subtree is
participant-visible. Copy it to an isolated fresh workspace and run the full
one-hour ultima-alpha attempt. Do not expose this file, `evaluator/`, private
calibration data, root `status.json`, or any other concept files. This worker
does not spawn agents.

The target is fixed: symmetrized unrelaxed lambda 1-RDM real-orbital population
violation >= 0.02, on the prescribed 3-fermion/6-orbital Hamiltonian domain,
subject to all documented endpoint and 64-step path constraints.

An independently verified **private calibration witness** has violation
0.02500000000093, energy error 0.00008000000038, squared ground fidelity
0.9999998974432, exact gap 0.1284723166, HF minimum curvature 0.5478399103,
Jacobian condition 80.0000000007, and minimum path fidelity 0.9963663615.
At 64 continuation steps its maximum amplitude displacement is 0.2287628913,
below the fixed 0.25 bound. The 128-step private audit agrees.

The participant oracle passed two-electron CCSD=FCI energy/RDM/EOM checks,
finite-difference lambda and Hessian checks, and exact-state RDM positivity.
An independent full-Fock-space/expm implementation agrees on the witness.
The official JSON evaluator is complete. Its 44-case malformed/security audit
passes, including symlinks to private witnesses and paths outside the declared
submission directory. No threshold changes are permitted during fresh attempts.

Suggested output: `submission.json`. Official invocation from `concept_2`:
`python -I evaluator/evaluate.py /absolute/attempt/submission.json --submission-dir /absolute/attempt --output report.json`.

The public baseline is `participant/baseline/run.sh`. No privileged witness is
embedded in the participant files. `freeze.json` records their SHA-256 digests.
The 100,000-draw baseline finds zero positive admissible population violations;
its official score is zero. The private witness survives all 12 perturbation
checks, with minimum score 0.02496451327. Fresh-agent difficulty remains unmeasured
until the main session completes its independent one-hour replicates.
