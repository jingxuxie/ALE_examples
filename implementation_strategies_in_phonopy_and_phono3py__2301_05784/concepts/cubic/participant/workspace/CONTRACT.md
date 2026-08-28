# Interface and mathematical contract

`python solve.py INPUT.npz OUTPUT.npz` reads and writes NumPy NPZ archives without
pickle. All indices are zero-based. Let `T` be the triplet count, `P` the primitive
atom count, `S` the supercell atom count, and `B=3*P`. Real arrays are float64,
complex arrays complex128, and index arrays int64. No case identifier or target
answers are present in an input.

## Input fields

| Field | Shape | Meaning |
|---|---|---|
| `fc3` | `(P,S,S,3,3,3)` or `(S,S,S,3,3,3)` | Compact or full real third-order force constants, eV/angstrom^3. The last axes are Cartesian x,y,z in atom order. |
| `p2s_map` | `(P,)` | Supercell representative of each primitive atom. |
| `s2p_map` | `(S,)` | Representative **supercell index**, not dense primitive index; its values belong to `p2s_map`. |
| `shortest_vectors` | `(V,3)` | All tied shortest supercell-image displacement vectors in fractional **primitive** coordinates. |
| `multiplicities` | `(S,P,2)` | `[count,offset]`; vectors from representative primitive atom `a` to supercell atom `s` occupy `[offset:offset+count]`. Counts are positive. |
| `primitive_lattice` | `(3,3)` | Primitive lattice vectors as rows, angstrom. |
| `primitive_positions` | `(P,3)` | Fractional primitive positions in the same atom order as the maps. |
| `supercell_lattice` | `(3,3)` | Supercell lattice vectors as rows, angstrom. |
| `supercell_positions` | `(S,3)` | Fractional supercell positions. |
| `masses` | `(P,)` | Positive atomic masses, atomic mass units. |
| `qpoints` | `(T,3,3)` | Three fractional reciprocal-primitive wavevectors per triplet. Their sum is an integer reciprocal vector `G`; wavevectors need not be commensurate with the supercell or folded into a Brillouin zone. |
| `frequencies` | `(T,3,B)` | Signed phonon frequencies in THz; unstable frequencies can be negative. |
| `eigenvectors` | `(T,3,B,B)` | Unit-normalized eigenvectors as **columns**; row `3*a+alpha` is atom `a`, Cartesian component `alpha`. These are supplied, not to be recomputed. |
| `cutoff_frequency` | `()` | Nonnegative frequency cutoff in THz. |

The force constants obey atom/Cartesian permutation and supercell translation
symmetry up to numerical precision. Compact row `a` denotes full row
`p2s_map[a]`; do not assume representatives are consecutive. Different storage
layouts represent the same physics. The shortest-vector multiplicity average is
part of the definition, including at noncommensurate wavevectors.

## Reciprocal tensor

For primitive atom `a`, supercell atom `s`, and wavevector `q`, define

\[
 h_{as}(q)=\frac{1}{m_{sa}}\sum_{v\in V_{sa}}\exp(2\pi i\,q\cdot v),
 \qquad p_a(G)=\exp(2\pi i\,G\cdot(\tau_a-\tau_0)).
\]

Here `V_sa` is exactly the vector slice specified by `multiplicities[s,a]`,
`m_sa` is its count, and `tau` is `primitive_positions`. No Cartesian conversion
or extra factor of `2*pi` is applied to the supplied fractional vectors.
Let `Phi[a,s,u,alpha,beta,gamma]` denote compact force constants (or the
representative row of full force constants). The single-origin tensor is

\[
 F^{abc}_{\alpha\beta\gamma}(q_0,q_1,q_2)=p_a(G)
 \sum_{s:\,s2p[s]=p2s[b]}\sum_{u:\,s2p[u]=p2s[c]}
 \Phi^{asu}_{\alpha\beta\gamma}\,h_{as}(q_1)h_{au}(q_2).
\]

The required tensor, in the original atom/Cartesian order, is

\[
 C^{abc}_{\alpha\beta\gamma}(q_0,q_1,q_2)=\frac{1}{3}\left[
 F^{abc}_{\alpha\beta\gamma}(q_0,q_1,q_2)+
 F^{bac}_{\beta\alpha\gamma}(q_1,q_0,q_2)+
 F^{cba}_{\gamma\beta\alpha}(q_2,q_1,q_0)\right].
\]

This is a complex **amplitude** average, before taking squared magnitudes. It
is not an average of three strengths. The reference phase is relative to atom
zero, not an absolute-coordinate phase. Momentum conservation includes `G != 0`.

## Mode coupling

For all ordered band triples `(mu,nu,xi)`, define

\[
 A_{\mu\nu\xi}=\sum_{abc\alpha\beta\gamma}
 \frac{C^{abc}_{\alpha\beta\gamma}
 e^{(0)}_{a\alpha,\mu}e^{(1)}_{b\beta,\nu}e^{(2)}_{c\gamma,\xi}}
 {\sqrt{M_aM_bM_c}}.
\]

There is **no complex conjugation** of the supplied eigenvectors. The required
strength is `abs(A)**2 / (f[0,mu]*f[1,nu]*f[2,xi])` if **each** of the three
frequencies is strictly greater than `cutoff_frequency`, and exactly zero
otherwise. Equality to the cutoff is excluded. Do not take absolute values of
negative frequencies. This is the reduced squared three-phonon matrix element,
in `(eV/angstrom^3)^2/(amu^3*THz^3)`: no hbar, mesh-size, Bose occupation,
energy-conservation delta, degeneracy, or SI conversion factor is included.
It is the physical mass/eigenvector/frequency contraction, not a Cartesian norm.

## Output fields and scoring

| Field | Shape | Type |
|---|---|---|
| `reciprocal_fc3` | `(T,P,P,P,3,3,3)` | complex128, `C` in the order defined above |
| `coupling_strength` | `(T,B,B,B)` | float64, ordered band triples, finite and nonnegative |

Both fields are required. Scores are separate, continuous functions of numerical
error relative to a measured single-origin baseline error; that baseline scores
0.5 and the reference scores 1.0 in each component. Errors are normalized per
triplet, so a large-amplitude triplet cannot conceal errors on other triplets.
There is no binary accuracy threshold. Invalid shape, nonfinite values, a
missing field, or a non-real/negative strength invalidates that component.
Only the submission directory, public participant files, and the current input
are made available during scoring; the reference implementation is not public.
