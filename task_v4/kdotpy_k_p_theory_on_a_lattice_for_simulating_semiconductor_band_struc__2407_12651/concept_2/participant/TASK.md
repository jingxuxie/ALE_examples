# A false spectral-window convergence certificate

Audit a convergence heuristic used when only a few eigenstates of a lattice semiconductor model are retained: agreement of the lowest-band integrated Berry response at three successive spectral-window sizes is taken as evidence of convergence.

The supplied six-orbital, finite-range model and diagnostic in `workspace/` define a spin-resolved reduced model, not a material-calibrated Kane calculation. `input/contract.json` specifies the admissible parameters, response convention, and fixed witness thresholds. `baseline/solve.py` emits a runnable starting design.

Construct a genuinely hybridized counterexample with a resolved nonzero plateau, substantial omitted response, and an isolated topological target band. Save `witness.json` containing `{"parameters": [25 finite numbers]}` in the output directory. The checker recomputes all quantities; reported numerical claims are ignored.

The witness must pass nominal, axial, and simultaneous manufacturing-perturbation audits, spectral and momentum convergence checks, and coupling requirements. Perturbations affect the first 21 coefficients by up to 0.02; 256 frozen held-out interior probes and 1,296 corner probes supplement the 42 axis probes. The corner audit covers all 512 mass/offset, 16 dispersion, and 256 hybridization corners, plus 512 held-out simultaneous corners; exact coordinate families are in the contract. The perturbation box and all response thresholds are unchanged. These distinguish missing spectral weight from a gap closure, decoupled spectator trick, accidental cancellation at one calibration, or underresolved quadrature. This falsifies the supplied heuristic, not a theorem asserted by kdotpy.

You have one hour, four CPU threads, NumPy/SciPy, and no network. Write only in the designated output directory. Validation scores plateau consistency, response error, nontrivial coupling, spectral isolation, and robustness; all contract conditions are necessary for a valid witness.
