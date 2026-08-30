# Generation-2 private feasibility study

## Outcome

No accepted witness was found within the bounded study. Achievability remains unknown; no global infeasibility bound was obtained. The best private design scores **0.9852473662925599** under the unchanged full evaluator. Its only failed acceptance condition is the certified bandwidth upper bound, **0.17762036823149993**, against the frozen **0.175** target. This is a certificate shortfall, not proof that its actual worst-case bandwidth exceeds the target.

Best data-only witness: `mixed_spin/candidate_3.json`.
Full report: `mixed_spin/candidate_3_result.json`.
Witness SHA256: `5812012565418fcfcf1a7ec8dbb613538a7fed65477749bc12e556bf7976569f`.

## Independent full-checker evidence

| Quantity | Best private design |
| --- | ---: |
| Optional channels | 8 |
| Sampled worst bandwidth, 320 mesh and 25 mass/anisotropy scenarios | 0.14051460452975073 |
| Certified bandwidth upper bound | 0.17762036823149993 |
| Certified direct gap lower bound | 3.01733387875794 |
| Certified indirect gap lower bound | 3.016740886559408 |
| Certified gap12 lower bound | 3.689657428660619 |
| Full rank-one FHS Chern, ordinary and shifted grids | -1 |
| Independently anchored coupling-homotopy gap lower bound | 2.422262808098872 |
| Independent coefficient-error norm radius | 0.016410480057897376 |
| Lower-band interpolation error | 0.0021424017929772255 |
| Largest width in the evaluator's 24 manufacturing audit trials | 0.14974908589477254 |

The bandwidth certificate equals the sampled width plus twice the coefficient-error radius and twice the interpolation error. The manufacturing audit alone is not a continuum certificate. The spectral enclosure includes the full public mass, anisotropy, and coefficient uncertainty box; topology uses full four-band FHS, an independent core degree, and a gapped coupling homotopy. The report certifies gap12 as required for the upper target-band Hessian; it does not reuse a two-band-only gap assumption.

## Search and controls

All searches descend from the authorized generation-1 champion, SHA256 `0707a04e7686ffc4c3992efd425f2d23b2559123d8eed7ec192d03a8c5a50d5e`. No fresh-generation-2 files were inspected and no agents were launched.

- Initially screened all 84 triples of the nine scalar modes while retaining the champion's five optional channels. The initial SLSQP phase completed 94 local solves, including refinements. One full-checker evaluation scored zero after encountering an uncertifiable remote-band ordering/gap12 regime. Those local results do not support an infeasibility claim.
- Retried eight supports with symmetry-reduced meshes and exchanged active epigraph constraints. SLSQP remained unreliable; no positive witness resulted.
- Six sequential-linear-programming trust-region trials retained the five original channels plus three scalar modes. All saturated the existing first spin-orbit coefficient bound. This is an empirical limitation of these local trials, not a bound on the design family.
- Four final support trials retained the same five channels but used one additional spin-orbit harmonic and two scalar modes. Full-checker scores were 0.4336023734751466, 0.4001688616868187, 0.37581896235787743, and 0.9852473662925599. The strongest uses the extra spin-orbit harmonic `(2,1)` and scalar harmonics `(1,0)` and `(1,1)`; it satisfies the original eight-channel limit.
- Optimization uses full four-band eigenvectors and Hellmann-Feynman coefficient derivatives, not effective two-band spectra. With active components `z0,z1`, the coefficient-gradient observables are `(|z0|^2+|z1|^2, 2 Re(conj(z0) z1), 2 Im(conj(z0) z1), |z0|^2-|z1|^2)` multiplied by the public Fourier features.
- Per-scenario epigraph variables constrain `alpha <= E0 <= beta`, `E1 >= beta + 3.055` in the trust-region phase, and a common width. The objective includes the coefficient-error norm contribution. A sampled gap12 floor of 0.8 is an optimization guard only; the unchanged full checker supplies the actual continuum certificate.
- Optimization uses 13/17 meshes and nine mass/anisotropy scenarios. The final report is from the independent unchanged checker with finer meshes, both anisotropy signs, complete public-box enclosure, and shifted topology checks.
- Spectral gradient finite-difference error: 2.726659675822418e-9. Full epigraph Jacobian error: 4.492747729401003e-9. Reduced-grid Jacobian error: 4.582639268058131e-9. Reflection/anisotropy-sign symmetry errors were at most 5.329070518200751e-15. These are local numerical controls, not universal symbolic proofs.

The numerical wall span, from the first input record to the last search summary, was **769.074610710144 seconds**. No additional optimization is run after that last summary. Logs, intermediate designs, numerical controls, and rejected full reports remain in this private directory.

## Integrity and reproduction

Every manifest-listed frozen file was hash-verified before and after the study. Freeze ID: `00a77145dd4d7c5b1ba1a9453468a254edce5b93b58c45a0b4745c7ca161677f`. Participant assets, evaluator, targets, status, and champion files were not edited. All study writes are under `adversary/feasibility_probe/`.

From the `concept_3` directory, reproduce the best candidate's full report without modifying frozen files:

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python evaluator/evaluate.py --candidate adversary/feasibility_probe/mixed_spin/candidate_3.json --output adversary/feasibility_probe/mixed_spin/candidate_3_recheck.json
```

The initial optimizer implementation is preserved as `epigraph_initial.py`; `epigraph.py` is the later symmetry-reduced implementation. Phase-specific JSON summaries and logs distinguish these runs. The final mixed-support route provides a substantially stronger near-witness than the scalar-only route, but neither the near-witness nor these local trials settle acceptance feasibility.
