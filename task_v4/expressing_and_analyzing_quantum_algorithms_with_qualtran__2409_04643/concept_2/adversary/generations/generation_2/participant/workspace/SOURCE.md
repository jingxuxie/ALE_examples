# Supplied method provenance

The numerical method is extracted from the official quantumlib/Qualtran source,
commit 096a2d009059faee0cfae462c3d59cb055300eb9:

- qualtran/bloqs/qsp/fft_qsp.py: fft_complementary_polynomial
- qualtran/bloqs/qsp/generalized_qsp.py: qsp_phase_factors
- qualtran/bloqs/basic_gates/su2_rotation.py: rotation_matrix

The extraction removes package/type dependencies and adds a separate read-only
phase-guard diagnostic. The arithmetic and return values of the tested methods
are preserved. The original code is copyright Google LLC and provided under
Apache License 2.0; see LICENSE.qualtran. Checker and witness-domain definitions
are benchmark-specific. The complete repository and authoring diagnostics are
not supplied.
