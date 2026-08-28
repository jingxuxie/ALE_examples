# Activation ratchet 1: author-only protocol

## Counterexample and anti-compression decision

The initial short-chain task was solved, including its entire held-out pool.
The original N=2048 source-scale prototype is a prospective extension, not a
retroactive failure of the frozen N=6–40 contract. The immutable initial solver
times out at 90 seconds while native GNEB/sparse-HTST validates a reference.
Warm localized continuation is privileged authoring input, not a claim of an
equal cold-start global-search comparison.

This ratchet is not justified by replacing one dense eigensolver alone:

1. A private diagnostic replaces the dense steps by mathematically equivalent
   structured linear algebra, leaving search initialization unchanged. It still
   times out while following highly unstable coherent candidates, involving
   hundreds of negative modes instead of a localized index-one mechanism.
2. For the same long chain, the unchanged 45- and 65-image localized paths miss
   the positive nucleation barrier entirely and return no candidate before any
   eigensolve. The 97-image path resolves it. This is spatial path resolution,
   not a tighter residual tolerance or an eigensolver defect.
3. Correct localized saddles can be found while the unchanged endpoint-relaxation
   iteration limit fails the full-chain basin check. Longer relaxation verifies
   both branches. Thus search, scalable curvature, and connectivity require
   different changes or decisions. Short coherent controls prevent simply
   discarding coherent reversal everywhere.

The exact observations, intermediate failures, successful diagnostic repairs,
source hashes and scientific caveats are preserved in
`authoring/activation_scale_probe/exploration` at the task root. The diagnostic
repairs are not distributed to the fresh participant. The public baseline is
the byte-identical successful original submission, without outputs, scratch
files, private references or attempt logs. The public long example is the
inspected counterexample, but all scored ratchet inputs have freshly selected
parameters; none are merely copies with new identifiers.

A fixed specialized composite solver may still solve every case. A generic
dense solver is empirically defeated at the intended length, and several
independent components remain. This passes the provisional anti-compression
screen only; it does not establish difficulty until a new isolated model fails
substantively. If that model solves the new scope, reject rather than claim
that the older timeout proves frontier hardness.

## Reference and evaluation

Native reference generation and source-level certification live under
`native_reference_build/`, `reference/`, and `challenge_pool/`. They retain the
same open-chain exchange/tensor-anisotropy/uniform-field Hamiltonian and outputs.
The source reference can use expensive precomputation and trusted continuation;
the participant cannot access either. Native rotated-anisotropy Hessian defects
must not be used as ground truth.

`evaluator.py` preserves every original physical loss, normalization, ablation
weight, output requirement and execution limit. Only its dependency path and
independent Hessian implementation change: `numerics.py` computes the exact
general block-banded tangent Hessian, including arbitrary symmetric onsite
tensors, instead of allocating a dense matrix. `dense_oracle.py` and `audit.py`
cross-check the banded implementation against the original independent dense
and finite-difference oracles, including rotated nonplanar random states.

The weak calibration anchor remains ordinary relaxation, not the provided
improved baseline. Strong reference replay is explicitly a stored-output
oracle permitted by the task-authoring protocol, not an online solver claim.
Source-native accuracy, inertia, residual and downhill connectivity checks are
separate from that replay. Both saddle-only and fluctuation-only ablations
must score below .70; the strong anchor must exceed .90 before a model launch.

From this ratchet directory, use the supplied runtime:

```
PYTHONPATH=participant/workspace/vendor OPENBLAS_NUM_THREADS=1 python private/audit.py
PYTHONPATH=participant/workspace/vendor OPENBLAS_NUM_THREADS=1 python private/evaluator.py --submission private/strong_submission --split initial --output private/strong_scores.json
```

Submission evaluation uses the local copy of `isolated.py`, not an authoring
directory import. It requires bubblewrap privileges and refuses unsandboxed
fallback. Participants see only their own read-only participant directory and
empty writable attempt directory, apart from standard runtime resources.
