# Evaluator audits

Tests here exercise numerical invariants, branch traps, parser validation, timeout
handling, and filesystem/process separation. They are builder-only assets.

## Final audit: 19/19 pass

Run from the concept root with one-thread environment variables:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m unittest discover -s adversary -p 'test_*.py' -v
```

Eight numerical tests cover FFT versus direct summation, folded versus full
signed frequencies, the analytic Jacobian, energy rescaling, the exact normal
state, global gauge symmetry, tiny nonzero normal-state impostors, and deleting
a weak induced gap. The tiny-gap impostor has acceptable residuals and positive
relative signs but fails the private branch-distance gate. Per-patch normalization
also rejects dropping the smallest gap despite a gap ratio near 1.87e7.

Eleven security tests cover malformed/object/complex/nonfinite arrays; shape
headers before allocation; archive expansion limits; extra archive members;
file and submission-root symlinks; hard-linked output; private canary reads;
sockets; fork and thread creation; forged stderr CPU timers; absence of trusted
scoring modules in the candidate; output-to-private symlink replay; and CPU/wall
timeouts. Some tests deliberately group related failure modes.

The initial shared-harness audit revealed that denying fork/vfork syscalls alone
did not prevent Python fork or threads using clone. No root file was changed.
The concept-local child adapter stacks a clone/clone3 deny filter on the shared
harness, and the repeated audit confirms both calls are denied. The parent also
uses descriptor-relative, no-follow submission copying and rejects output paths
before opening their NPZ content. Final results are in `../attempts/all_tests.log`.

The 71-file prelaunch seal was checked after scoring: every hash matched.
This is a focused local audit, not a claim of universal sandbox correctness.
