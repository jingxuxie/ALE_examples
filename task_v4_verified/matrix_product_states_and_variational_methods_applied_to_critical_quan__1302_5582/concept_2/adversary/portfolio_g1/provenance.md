# Privileged ratchet-v2 achievability portfolio

Date: 2026-08-28. This directory is the only write scope for this sidecar.

The permitted sources are the current `concept_2/participant/`, its trusted
evaluator, and this sidecar's earlier `concept_2/adversary/portfolio/` sources
and tensors. No `attempts/` or champion construction code has been accessed.
The original v1 evidence and the v2 contract, targets, and status files are
not modified. This is a generation-side solvability audit, not a participant
attempt. A claim of achievability requires an actual `state.npz` passing the
unchanged official v2 evaluator.

## Numerical method

The real parity-block row-isometry parameterization, stationary density solve,
and old private warm-start tensors come from this sidecar's prior portfolio.
The v2 implementation independently adds the y-spin channel, compresses the
real symmetric even transfer sector, and evaluates every required integer
distance by differentiable dyadic matrix powers. It fits actual finite-bond
MPS contractions, not a replacement ground-state correlation formula.

The frozen evaluator supplies only the public target definitions and the
independent final checker. The optimizer's contraction and gradient validation
is recorded in `derivative_validation.json`.

## Primary-source provenance carried forward

These sources were inspected during the preceding generation research and are
recorded more fully in the read-only prior `portfolio/provenance.md`:

- Milsted, Haegeman, Osborne, arXiv:1302.5582v3:
  https://arxiv.org/abs/1302.5582v3
- Primary evoMPS source revision inspected:
  https://github.com/amilsted/evoMPS/tree/86caa3cdda1e815d96513702b1f50d6fbac471b5
- Stojevic et al., conformal data and finite-entanglement scaling:
  https://arxiv.org/abs/1401.7654
- Vanhecke et al., transfer-spectrum scaling:
  https://arxiv.org/abs/1907.08603
- Zauner-Stauber et al., VUMPS:
  https://arxiv.org/abs/1701.07035
- Exact XY MPS truncation study:
  https://arxiv.org/abs/1411.2607

No upstream solver code was copied for this new optimizer, and no new web
sources are needed for the local frozen-contract audit.

## Completed audit

The D=24 artifact selected from the direct seed-17 warm-start strategy passes
the actual official v2 evaluator, its public checker, and a complex parity-block
unitary gauge audit. The curriculum strategy also passes from that same earlier
private tensor. Full scores, unchanged input hashes, construction timing, and
the artifact SHA-256 are retained in `portfolio_results.json`; construction
details and frozen-bound margins are summarized in `README.md`.

This proves achievability under the specified v2 tolerances, not optimality of
the tensor or feasibility of a stricter future ratchet. No longer-distance
or new-target search was initiated.
