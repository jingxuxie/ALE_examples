# Private physical-search results

Generation-only reviewed-copy probes; no frozen evaluator grades or public changes.
References are achieved same-cap variational states, not certified ground energies.
The physical-gap screen is 1e-7 per site; wall-limited probes are excluded.

## Long-stage comparisons

| Cohort | Completed/valid | Gaps above screen | Largest absolute gap |
|---|---:|---:|---:|
| original | 8/8 | 0 | 2.156497203e-12 |
| proposed_same_physics_scaling_only | 12/12 | 4 | 0.002452861819 |

| Case | E40 minus reference | Gap/site | Champion CPU | Teacher CPU |
|---|---:|---:|---:|---:|
| `weak_any64-any--0.0408` | 0.002452861819 | 3.832596592e-05 | 39.723 | 70.493 |
| `weak_tilt64-any--0.0408` | 0.001392865179 | 2.176351842e-05 | 39.726 | 90.446 |
| `weak64-odd--0.0358` | 1.06585828e-05 | 1.665403563e-07 | 39.669 | 90.081 |
| `weak64-odd--0.0408` | 8.699952311e-06 | 1.359367549e-07 | 39.668 | 90.036 |
| `weak_link64-odd--0.0408` | 4.77003563e-06 | 7.453180673e-08 | 39.671 | 90.032 |
| `weak64-even--0.0408` | 8.918930021e-07 | 1.393582816e-08 | 39.661 | 90.250 |
| `proposed48-odd--0.5750` | 4.954264234e-07 | 1.032138382e-08 | 39.657 | 43.305 |
| `weak64-even--0.0358` | 4.107340601e-08 | 6.417719689e-10 | 39.664 | 90.288 |
| `proposed64-odd--0.5750` | 9.5319308e-09 | 1.489364188e-10 | 39.664 | 70.025 |
| `proposed64-even--0.5750` | 1.806121475e-09 | 2.822064804e-11 | 39.660 | 69.958 |
| `weak_profile48-any--0.0408` | 1.218829482e-10 | 2.539228087e-12 | 39.656 | 63.168 |
| `proposed48-even--0.5750` | 5.385913937e-12 | 1.122065404e-13 | 13.302 | 34.615 |
| `uniform20-odd--0.5000` | 2.156497203e-12 | 1.078248602e-13 | 3.064 | 15.988 |
| `uniform20-even--0.5000` | 1.644906433e-12 | 8.224532166e-14 | 7.542 | 14.923 |
| `uniform20-even--0.4000` | 1.310951347e-12 | 6.554756737e-14 | 6.650 | 14.857 |
| `uniform20-odd--0.4000` | 5.471179065e-13 | 2.735589533e-14 | 2.671 | 15.887 |
| `uniform20-even--0.6000` | 5.41788836e-13 | 2.70894418e-14 | 1.952 | 14.934 |
| `uniform20-even--0.7000` | 1.190159082e-13 | 5.950795412e-15 | 2.068 | 16.136 |
| `uniform20-odd--0.6000` | 9.237055565e-14 | 4.618527782e-15 | 2.048 | 14.903 |
| `uniform20-odd--0.7000` | 5.329070518e-14 | 2.664535259e-15 | 1.938 | 15.509 |

## Completed six-CPU states

Direct wait4 CPU includes interpreter/import/save cost; no bwrap certification is claimed.

| Case | Valid within limits | CPU/wall | E6 minus reference |
|---|---|---:|---:|
| `proposed64-even--0.5750` | True | 5.806 / 6.253 | 0.0004122070686 |
| `proposed64-odd--0.5750` | True | 5.858 / 6.518 | 0.002436908734 |
| `weak64-even--0.0408` | True | 5.835 / 6.273 | 0.01229641274 |
| `weak64-odd--0.0408` | True | 5.885 / 6.351 | 0.006892143378 |

Requests, states, full spectra, variances, trajectories, raw timings, and SHA256 hashes
are retained in `runs/<case>/`; `SEARCH_STATUS.json` independently remeasures final files.
