# Scientific provenance and resources

This is a synthetic synthesis benchmark, not a reproduction of a measured
device's calibration or of numeric results in a paper.

1. Javadi-Abhari et al., *Quantum computing with Qiskit*, arXiv:2405.08810v3
   (June 19, 2024), section II's third design principle, “Balance between
   portability and hardware optimization” (HTML heading II.0.3; also referred to
   as II.3), motivates targeting native instructions and their durations.
   Section III.1, “Circuits”, describes specialized representations of Boolean
   linear functions. Here the high-level object is an invertible GF(2) matrix;
   the output must be a resource-limited native CX realization.
   Source: `https://arxiv.org/html/2405.08810v3`.
2. Official Qiskit source, `qiskit/synthesis/linear/cnot_synth.py` on the
   `stable/1.0` branch, provides `synth_cnot_count_full_pmh`, an all-to-all linear
   reversible synthesis interface. The neighboring `linear_depth_lnn.py` provides
   `synth_cnot_depth_line_kms` for a line. Those connectivity assumptions are
   different from this benchmark's irregular weighted devices. They are relevant
   algorithmic resources, not turnkey guarantees of meeting the supplied caps.
   Sources:
   `https://github.com/Qiskit/qiskit/blob/stable/1.0/qiskit/synthesis/linear/cnot_synth.py`
   and
   `https://github.com/Qiskit/qiskit/blob/stable/1.0/qiskit/synthesis/linear/linear_depth_lnn.py`.
3. Official API documentation for that release family:
   `https://quantum.cloud.ibm.com/docs/en/api/qiskit/1.0/synthesis`.

The source linkage is hardware-aware synthesis of Boolean linear functions; the
four matrices, graphs, durations and numerical caps are benchmark-authored.
No implementation from Qiskit is vendored, and Qiskit is not a runtime dependency.
These notes make the paper connection self-contained; opening the links is not
required to complete the task.

The baseline and checker use Python 3.10+ standard-library modules only. NumPy,
SciPy and NetworkX are available in the build environment. Qiskit, OR-Tools and
Z3 are not preinstalled and are not required. No installation, GPU, remote
backend, credentials, external files or quantum circuit execution is needed for
verification. You may use any synthesis algorithm within the surrounding run's
resource and access rules.
