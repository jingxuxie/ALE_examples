# Concept 2 — Mode B: robust entropy inversion

This directory is a privileged task-builder package. Only `participant/` is
public. The task is a constrained, physically motivated counterexample search,
not package debugging or a claim to falsify the Sparse Blossom matching theorem.

The fixed local graph has 20 detectors, 39 edges, and logical distance six. A
passing artifact must certify a minimum physical-class weight advantage of
1.08 nats while the opposite logical class has posterior at least 0.85, with
syndrome probability at least 0.0000175, throughout scales [0.95,1.05]. All three
bounds include conservative between-anchor and floating-point allowances.

The native builder search, raw logs, immutable known witness, independent
certification, and audit reports belong only in `adversary/`. The participant
gets an exact fast checker, full contract, graph, and weak baseline but no
optimizer, search recipe, or strong witness. The official generic full-state
oracle is a separate implementation and does not read the known witness.

Read `status.json` for certified feasibility, scores, and freeze metadata;
`adversary/SEARCH_REPORT.md` for builder-only provenance; and
`evaluator/README.md` for the artifact-only command and isolation requirements.
Run `/usr/bin/python3 -B adversary/audit.py` for the reproducible adversarial audit.
No fresh run has occurred. Difficulty against two independent one-hour model
attempts is unmeasured; no “neither agent” claim is justified yet.
