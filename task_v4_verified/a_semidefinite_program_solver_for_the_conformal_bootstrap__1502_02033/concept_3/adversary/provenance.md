# Exact low-rank half-line positivity

Seed: https://arxiv.org/abs/1502.02033 section 2.2, theorem 2.1 and its preceding
positive-Gram formulation. The certificate here is a rational factor form of that
identity. Section 2.6 motivates exact checks for boundary and precision loss.

These are generated polynomial-matrix programs, not claimed to be measured
3d Ising conformal blocks. The fixed instances have endpoint faces, a moving
polynomial nullspace, and nontrivial rational scale separation. The constraints
ask for compact low-rank exact certificates, not a general SDP implementation.
All row bases are accepted. Rational orthogonal changes of factor basis are
allowed. Bounds of 2048 bits are representation safety limits, far larger than
the planted witnesses. The task contains no secret coefficients to guess.

Private planted factors certify achievability; they are never mounted for a
fresh agent. No reference algorithm for recovering those factors is provided.
