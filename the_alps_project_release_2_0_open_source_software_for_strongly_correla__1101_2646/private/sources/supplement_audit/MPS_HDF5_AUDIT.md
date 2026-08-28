# Author Hubbard-ladder HDF5 audit: NO-GO for fresh within-c03 heldouts

**Verdict:** this archive supplies seven numerical approximations to **one** Hamiltonian in **one** particle/spin sector, not independently varied physical cases. It contains **no full MPS checkpoints**. It does not reopen a scientifically valid, archive-backed ratchet within the frozen c03 concept. This is a bounded conclusion about this artifact, not proof that all conceivable within-contract instances are easy.

## Exact source and scope

- Figshare v1 DOI: `10.6084/m9.figshare.1092509.v1`; metadata: <https://api.figshare.com/v2/articles/1092509>; file 1578993: <https://ndownloader.figshare.com/files/1578993>.
- Local archive: `mps_author_examples.tar.gz`, **23,595,405 bytes**. MD5 `d7d9b53925d11813cc712b88a8dc2f3e` matches the supplied metadata. SHA256: `edc7307a0c32eeb160a698384a511ae9bdc62ea3a0bf34c384d5a87fe30779bd`.
- Inspected all seven `author_data/examples/hubbard_ladder/results/sim.task{1..7}.out.h5` read-only, their input XML, and the corresponding output XML. Full file hashes, metadata, observable paths/shapes, aligned comparisons, and archive inventory are in `mps_hdf5_audit.json`.
- Primary paper: <https://arxiv.org/html/1407.0872v2>, Sec. 3.2, Eq. 18, Figs. 5–7 and Appendix C. Local author sources: `author_data/examples/hubbard_ladder/parms.py:4`, `author_data/examples/hubbard_ladder/mymodel.xml:65`, `author_data/examples/hubbard_ladder/pairfield_trend.py:65`, and `author_data/examples/README:17`.

## Physical coverage and stored observables

Every HDF5 `/parameters` group specifies `MODEL=fermion Hubbard`, `LATTICE=open ladder`, `L=96`, `t=1`, `t'=1`, `U=8`, `Nup_total=Ndown_total=84`, and `symmetry=2u1`. The 192 local-density labels run from `(0,0)` through `(95,1)`: **96 rungs / 192 spinful-fermion sites**, 168 particles, filling 0.875, total Sz=0. The uniform Hamiltonian is `H = -sum_<ij>,sigma (cdag_i,sigma c_j,sigma + h.c.) + 8 sum_i n_i,up n_i,down`, as in the paper's Eq. 18. The physical signature is identical across all seven files; changing numerical/administrative parameters are listed in JSON. No second particle or spin sector, excitation energy, or sector-gap reference is present.

Under `/spectrum/results/NAME/mean/value`:

| NAME | Stored values per file |
|---|---:|
| `Energy`, `Energy^2`, `EnergyVariance` | One scalar each |
| `Local density up`, `Local density down` | 192 each |
| `pair field 1` through `pair field 4` | 17,955 labeled four-point values each |
| `dens corr up-up`, `up-down`, `down-up`, `down-down` | 18,336 labeled distinct-site pairs each |
| `neff` | 17,955 values, **chi3600 only**; operator meaning not established, not used |

The four pair channels yield the author's unnormalized singlet combination `D = p1-p2-p3+p4`; 4,560 stored positions are rung–rung pairs. The spin-resolved density means and correlations permit connected charge correlations by subtracting the product of total local means. Density sums independently reproduce 84 particles per spin to floating-point precision. The iteration groups contain optimization diagnostics, not further eigenstates.

## Actual numerical convergence evidence

Values below come directly from `/spectrum/results/Energy/mean/value` and `/spectrum/results/EnergyVariance/mean/value` (total energy, **not** energy per particle):

| chi / task | Energy | Energy variance |
|---|---:|---:|
| 800 / 1 | -121.88902712340811 | 0.215495711174 |
| 1200 / 2 | -121.90883909107764 | 0.112978229776 |
| 1600 / 3 | -121.91686887821197 | 0.0710325828386 |
| 2000 / 4 | -121.92093214797217 | 0.0485499092174 |
| 2800 / 5 | -121.92474888228035 | 0.0263144236997 |
| 3200 / 6 | -121.92571745229968 | 0.0203521405383 |
| 3600 / 7 | -121.92639075453428 | 0.0160935515360 |

From chi3200 to chi3600, total energy decreases **0.000673302234603**, or **3.50678247189e-6 per site** / **4.00775139644e-6 per particle**. Energy variance is still nonzero. From chi2800 to chi3600 the decrease is **0.00164187225393**. No rigorous error bound or exact-reference certification follows from these differences.

For the exact distributed `pairfield_trend.py` averaging rule, align all four channels by their coordinate labels, form `p1-p2-p3+p4`, and average shifts -5 through +5 around the center at each rung distance 1–84. This is **11 shifts**, notwithstanding the paper caption's wording of 10 pairs.

| chi | D(distance 80) | D(distance 84) |
|---|---:|---:|
| 2800 | 4.086174192854331e-5 | 3.271340416363416e-5 |
| 3200 | 4.859003086906983e-5 | 3.925385571944010e-5 |
| 3600 | 5.554501902538883e-5 | 4.516882050401808e-5 |

The chi3200→3600 differences are **12.5214% at distance 80** and **13.0952% at distance 84**, relative to the chi3600 values. Across the 84 averaged distances, absolute RMS change is **1.00976708844e-5** and maximum absolute change **2.93170746232e-5**. The modest norm-relative change (0.1346%) is dominated by shorter-distance magnitudes and must not be described as uniform relative convergence. For connected charge density over all 18,336 distinct-site pairs, maximum/RMS change is **4.42349905209e-5 / 4.71856956050e-6**. Local spin-resolved density maximum change is approximately **1.192e-4**. These are differences of existing approximations, not invented target outputs or newly tightened grading tolerances.

## Checkpoints and source-data cautions

1. **No checkpoints:** the complete archive inventory has 33 files and no `.ckp`, `.chkp`, checkpoint directory, or stored boundary/tensor files. HDF5 roots are only `parameters`, `simulation`, `spectrum`, and `version`; every dataset is parameter/version metadata or measurement/iteration output. No external or soft HDF5 link points to an omitted state. `/parameters/chkpfile` contains external author-machine strings, for example the chi3600 path `/mnt/lnec/dolfim/hubbard_ladder/run2/data/tsoptim_thin/L96Nu84Nd84/t10U8/ns16M3600.out.ckp`; that path is **not a bundled checkpoint**. The `domain_wall` and `z2_example` folders supply scripts/models only, no additional computed HDF5 references.
2. **Alignment matters:** chi3600 `pair field 4` has the same coordinate set but a different row order from channels 1–3. All reported sums and differences are coordinate-aligned. Naive row-wise addition produces wrong results.
3. **Iteration anomaly:** chi3200 `/simulation/iteration/15/results/Energy/mean/value` has 382 entries, including **282 exact zeros**, at zero-based indices 13–34 and 122–381; the same anomaly exists under `/spectrum/iteration/15`. Its terminal-array delta is **not a valid convergence diagnostic**. The cause is unestablished; no source data is repaired. Chi3600's final two sweep endpoint energies differ by approximately -2.93541e-8, but that does not erase its finite-chi correlation uncertainty.
4. **XML is not an interchangeable numerical copy:** `sim.task1.out.xml` is incomplete. At the identical first `pair field 1` coordinate, chi3600 output XML says `9.317859434228096e-12`, whereas its HDF5 says `3.443582075688774e-6`. Input XML references `mymodels.xml`, but the included file is `mymodel.xml`; seeds/sweep metadata also differ. Use the audited HDF5 metadata and values together, not a mixture. HDF5 versions are `2.0-r4204` for tasks1–6 and `2.0-r4282` for task7; this is a numerical provenance difference, not new physics.

## Fresh-heldout decision

The frozen `../../../c03_mps/participant/input/CONTRACT.md:7` permits spin-one chains, spin-half ladders, and Bose-Hubbard chains, with 32–80 total hidden sites and specified sector gaps. This **doped spinful fermion ladder at 192 sites is outside that contract**, and its one sector cannot provide the required gap targets. It is not an exact spin-half or Bose-Hubbard instance under a relabeling.

New rows, query positions, correlation channels, averaging windows, or chi values remain queries of the same Hamiltonian. Gauge-equivalent relabelings, trivial shifts/rescalings, and uncontrolled model substitutions do not create independently varied physical heldouts. Cropping a subsystem likewise does not supply the ground state of an isolated smaller system. Genuinely changing couplings, size, fields, geometry, or sector requires new validated calculations; the archive neither contains those outputs nor provides reusable MPS tensors. No expensive author reruns are assumed.

**Final disposition:** historical MPS/convergence evidence is strengthened, but **no legitimate fresh within-concept ratchet is supplied by this artifact**. Do not manufacture a counterexample or overturn the reported successful original/stress c03 results on this basis. No pilot, solver, student, agent, or evaluator was run. Only this Markdown and `mps_hdf5_audit.json` were written; all seven HDF5 source hashes remain unchanged.
