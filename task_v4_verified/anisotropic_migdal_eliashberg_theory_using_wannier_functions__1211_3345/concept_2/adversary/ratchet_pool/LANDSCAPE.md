# Private pool search landscape

Target 1.12 throughout. Only independently passing witnesses are retained. No fresh model was tested.

| Instance | Retained | Audited ratio | High clusters | Paired restart target rate |
|---|---:|---:|---:|---:|
| rough_broad | True | 1.122177328496 | 1 | 1.000 |
| rough_assortative | True | 1.127347452119 | 1 | 1.000 |
| two_hot_groups | False | 1.044537694938 | 2 | 0.000 |
| three_group_frustration | False | 1.036629130074 | 2 | 0.000 |
| balanced_hubs | False | 1.074664109490 | 1 | 0.000 |
| spectral_crossing | False | 1.078095370986 | 2 | 0.000 |
| broad_two_channels | False | 1.078805888429 | 1 | 0.000 |
| near_degenerate_groups | False | 1.036600364289 | 1 | 0.000 |

Clusters are separated by 0.025 K among endpoints reaching the directional-stationarity criterion on the 64-frequency search grid; listed temperatures and search ratios use 96 frequencies. Final scores use all required families/refinements and the independent audit. These observations do not certify local or global optimality.

The parent must test an actual fresh solution's search before choosing a ratchet. An alternative instance, an unobserved optimum, or a low scout hit rate alone is not a genuine model failure.
