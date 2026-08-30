# Runtime dependencies and isolation

The builder validated `/usr/bin/python3` 3.10.12, NumPy 1.21.5, SciPy 1.8.0 and
scikit-learn 0.23.2 on Linux x86_64. NumPy and SciPy are system packages;
the training baseline imports sklearn from the installed Python package roots.
**The fitted baseline's inference uses only NumPy and the standard library**:
it stores numeric kernel weights in NPZ, not sklearn pickle objects. Its
`features.py`, `solver.py`, and `model.npz` must accompany a submitted copy.
OpenFermion, PySCF, CVXPY, JAX, Torch, a compiler and network access are not needed
for the supplied baseline. No installations are performed by the evaluator.

The trusted launcher invokes the system Python with `-S` and disables `.pth` and
site startup hooks. It sets `PYTHONPATH` to the submission and installed package
roots under `/usr`, plus the current user's `.local/lib/python3.10/site-packages`
when present. This is deliberately not an arbitrary participant-controlled
Python environment. Libraries requiring subprocesses or worker threads at import
time may fail. A direct precompiled executable or shared library is permitted,
but `solver.py` remains the entrypoint; `os.execv` can replace that process.

Landlock grants read/execute only to the participant tree, submitted directory,
system runtime directories, and explicit Python package roots. Writes are only
allowed in the per-invocation scratch directory and `/dev/null`. The environment
is rebuilt, not inherited: secrets, arbitrary `PYTHONPATH`, `LD_PRELOAD`, and
startup hooks are not passed. `HUBBARD_ASSET_DIR` points to the public input tree.
The input NPZ staged in scratch contains only the five input arrays, never gaps.

Seccomp denies network, processes/threads, process inspection/signalling,
namespace changes, and affinity/resource-limit expansion. Numerical thread
environment variables are fixed to one. CPU/address-space/file limits are hard;
the trusted parent also bounds wall time, output bytes and scratch use. Sandbox
setup failure is invalid, not a fallback to unguarded execution. Linux must
provide Landlock ABI ≥1 and `libseccomp.so.2`.

This is file-content isolation, not a mount/PID namespace: some path metadata and
host identity remain visible. Runtime and submitted trees must be frozen against
concurrent outside modification. The launcher's own tiny supervisor is outside
the payload address-space limit. Aggregate scratch limits are monitored every
50 ms, not a filesystem quota. The participant release contains only this
`participant/` tree; trusted evaluator, private test, attempts and status stay out.
