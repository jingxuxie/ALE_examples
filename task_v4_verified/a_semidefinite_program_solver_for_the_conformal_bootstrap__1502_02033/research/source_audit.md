# Private source cross-check

The main session rechecked the original paper's full HTML, Theorem 2.1, the
half-line Gram representation, section 3.3's scaling/basis discussion, and the
damped-rational prefactor in Appendix A. The exact rational row caps in concept
3 are benchmark construction constraints, not a claim made by the paper about
all bootstrap matrices.

The follow-up https://arxiv.org/abs/2509.14307 has a journal revision dated May
26, 2026 (v2). The generation worker used its September 17, 2025 v1; the main
session also checked v2. The robust shared-prefactor task is an independently
defined finite-degree objective, not a reproduction of the follow-up formula.

Official SDPB Changelog.md, version 3.1.0, links the sampling changes to PR #255
and the spectrum rewrite to PR #274. The official source at commit 4554801 and
the merged PR metadata are preserved in sources/ solely for provenance. The
screening task is independently authored and is not a claim that SDPB's solver
or MPSolve emits false PSD certificates.

All these artifacts remain outside participant exports and fresh-agent mounts.
