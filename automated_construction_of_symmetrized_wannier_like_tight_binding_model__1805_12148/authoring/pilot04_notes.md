# Pilot 04: gauge-resolved effective physics

## Pre-build anti-compression decision

Can one fixed general solver handle every case? A full-space eigensolver alone cannot recover symmetry corepresentations or the orbital magnetic tensor. A uniform group average cannot implement remote-band Löwdin reduction. There are independently scored intertwiner, cubic reduction, and magnetic-response bottlenecks; a high-quality implementation can of course combine them, but not collapse them into one numerical kernel. The full 600–800-band author datasets are retained rather than replaced by toy models. No difficulty claim is accepted until isolated pilots run.

## Public/private gap

The starting capability is the target paper's full-space interpolation/Taylor expansion, represented by a projection-only export adapter. The absence of target-band reduction in the associated software is independently recorded in TBmodels issue #114. This is an adapted pre-capability interface, **not** a claim that the small adapter is an untouched historical TBmodels commit. The missing standard-basis reduction and orbital magnetic response are provided privately by the adjacent VASP2KP release 1.1.5 at commit `db38afc28eee209710c75388e1474c1bccde21b2`. The official `_numeric_kp.py`, `_transform_matrix.py` and `_read_data.py` are used unchanged behind an author-only loader. This avoids inventing a strong solution from scratch.

The input data are the author's `Example/Bi2Se3` and `Example/1H-TMD/{MoSe2,MoTe2,WTe2}` matrix exports. The upstream tree also contains files not needed for this benchmark (including VASP inputs); none of those are copied into the participant package. Only numerical matrix arrays are distributed to participants.

Gauge choices, Cartesian frame rotations, reference-energy shifts and complete-doublet selections are physically equivalent or source-grounded changes, with provenance retained in the manifest. They do not add random numerical faults. Evaluators transform precomputed raw-reference tensors by the submitted admissible `U`, so residual gauge ambiguity is not an artificial failure criterion.

Author-environment compatibility: the host's user-installed Numba requires a newer NumPy than the system interpreter provides. The official routine silently catches that import failure and falls back to Python. Reference generation therefore uses an isolated NumPy 1.26.4 / SciPy 1.11.4 / Numba 0.59.1 / llvmlite 0.42.0 stack and explicitly verifies the Numba import. No numerical source formula is changed. The WTe2 eigenvalue file contains more entries than the exported momentum matrices; the adapter retains exactly the full exported momentum-band range, rather than passing nonexistent matrix rows to the source routine. All supplied remote momentum bands are retained.

References:
- https://github.com/Z2PackDev/TBmodels/issues/114
- https://arxiv.org/abs/1805.12148
- https://arxiv.org/abs/2312.08729
- https://github.com/zjwang11/VASP2KP/tree/db38afc28eee209710c75388e1474c1bccde21b2
