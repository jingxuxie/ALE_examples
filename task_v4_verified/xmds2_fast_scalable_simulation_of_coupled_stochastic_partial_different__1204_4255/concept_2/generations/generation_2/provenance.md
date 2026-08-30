# Source and ratchet provenance

The model, fourth-order interaction-picture Fourier-Galerkin simulator, and temporal/spatial/DOP853 reference checks are unchanged from generation 1. Source paper: `https://arxiv.org/abs/1204.4255v2`. Official repository: `https://github.com/GrahamDennis/xpdeint`. Documentation: `https://xmds.sourceforge.net/reference_elements.html#error-check`. Source file fingerprints and tested dependency versions are recorded in `provenance.json`.

The source-native connection remains the full-step/half-step comparison in `xpdeint/Features/ErrorCheck.tmpl`, exact linear interaction-picture dynamics, and the documentation distinction between an error estimate and proof. The stochastic-specific upstream warning is not misrepresented as a deterministic-NLSE bug claim. This is an independently written challenge workflow, not a patched or executed XMDS implementation.

Generation 2 changes only the public finite robustness design, supplies the previous verified champion as baseline, adds guard-only screening and expands the explicit evaluation budget. The complete audit rationale and numerical evidence are in `RATCHET.md` and `evaluator/hidden/ratchet_evidence.json`. No source URLs or publication claims are needed in participant instructions.
