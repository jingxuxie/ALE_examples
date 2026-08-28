# Frozen ratchet reference calibration

All three preregistered reference gates pass: True. Full-calibration validation passes: True.
No cases were dropped, selected, or resampled after outcomes. No public, case, source-mask, physics, or evaluator files were changed. No confirmation attempt/transcript was accessed.

| Case | Warm baseline R (meV) | Source R (meV) | Source minus baseline | Baseline/source scores | Gate |
|---|---|---|---|---|---|
| lower_offset | 0.1574704276140209 | 0.18123113806431923 | 0.023760710450298317 | {'weak': 0.0, 'strong': 1.0} | True |
| central_offset | 0.14450285280828795 | 0.18555146174772658 | 0.041048608939438624 | {'weak': 0.0, 'strong': 1.0} | True |
| high_density | 0.13407905783652552 | 0.1679890973949691 | 0.03391003955844357 | {'weak': 0.0, 'strong': 1.0} | True |

## Full scenario metrics

| Case | Design | Scenario (mu, EZ), meV | Full-51 gap (meV) | Q | Scenario seconds |
|---|---|---|---|---|---|
| lower_offset | weak | (10.2, 0.74) | 0.154809628850 | -1 | 199.57 |
| lower_offset | weak | (12.0, 1.08) | 0.184694602956 | -1 | 174.25 |
| lower_offset | weak | (14.4, 1.32) | 0.151329583469 | -1 | 191.33 |
| lower_offset | strong | (10.2, 0.74) | 0.156740199426 | -1 | 314.55 |
| lower_offset | strong | (12.0, 1.08) | 0.230372375218 | -1 | 308.39 |
| lower_offset | strong | (14.4, 1.32) | 0.230053655463 | -1 | 297.41 |
| central_offset | weak | (10.7, 0.78) | 0.164562685946 | -1 | 194.27 |
| central_offset | weak | (12.8, 1.15) | 0.198493103759 | -1 | 185.95 |
| central_offset | weak | (14.8, 1.41) | 0.125990331786 | -1 | 181.62 |
| central_offset | strong | (10.7, 0.78) | 0.167161127044 | -1 | 293.46 |
| central_offset | strong | (12.8, 1.15) | 0.230159113666 | -1 | 320.03 |
| central_offset | strong | (14.8, 1.41) | 0.214505148646 | -1 | 248.60 |
| high_density | weak | (10.9, 0.7) | 0.147160125983 | -1 | 198.42 |
| high_density | weak | (13.2, 1.02) | 0.205772697121 | -1 | 196.65 |
| high_density | weak | (14.9, 1.46) | 0.112885380979 | -1 | 177.25 |
| high_density | strong | (10.9, 0.7) | 0.145188970517 | -1 | 299.01 |
| high_density | strong | (13.2, 1.02) | 0.223297366964 | -1 | 332.70 |
| high_density | strong | (14.9, 1.46) | 0.203881335338 | -1 | 235.76 |

Numerical wall time: 531.67 / 900 seconds. CPU sets: lower 64–69, central 72–77, high-density 80–85; three workers per case and one BLAS thread.
Resource checks: {"all_affinities_match": true, "all_observed_worker_threads_one": true, "max_sampled_worker_rss_kib": 256040, "samples": 18, "worker_observations": 150}.

R = 0.5 mean(gaps) + 0.5 min(gaps). All gaps use the unchanged 25,608-DOF forward evaluator, full 51 momenta, and an independent Pfaffian Q. The weak reference is the previously achieved frozen public baseline, not the original zigzag.

The score check applies the unchanged evaluator to stored full-resolution anchor measurements; it is not a second numerical evaluation or a fresh solver run. Incomplete measurements are not physical failures. Any failed reference gate is grounds for rejection, not case substitution.

Full raw calibration/measurement files remain alongside this report; unchanged CLI outputs and logs are in ../reference_runs/. Detailed checks are in full_calibration_validation.json and reference_score_check.json.
