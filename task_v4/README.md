# task_v4 — ten randomly sampled tasks

This collection replaces the previous verified-achievable-only selection with
**one uniform random sample without replacement from all 210 `tasks_v4`
folders**. No outcome, topic, report-completeness, or prior-inclusion filter was
used, and the draw was not repeated to reach a status quota.

The seed, complete sampling population, original status hashes, and draw order
are in [SAMPLE.json](SAMPLE.json). [verify_sample.py](verify_sample.py) replays
the draw with the recorded Python algorithm.

## Distribution at sampling

| Saved status | All 210 folders | Random sample of 10 |
| --- | ---: | ---: |
| `hard_open_candidate` | 156 | 5 |
| `rejected` | 22 | 1 |
| `hard_verified_achievable` | 21 | 3 |
| `missing_or_unreadable_status` | 8 | 1 |
| `complete` | 1 | 0 |
| `selected_task` | 1 | 0 |
| `tournament_in_progress` | 1 | 0 |

The actual draw is **5 hard-open, 3 verified-achievable, 1 rejected, and 1
without a final status**. The population's verified-achievable proportion gives
an expected count of one in a sample of ten, but a uniform random sample does
not enforce that count. No task was substituted to make the table look closer
to the population proportions.

## Sample in draw order

| Draw | Topic | Review entry | Status at draw |
| ---: | --- | --- | --- |
| 1 | EERAD3 event shapes and jet rates | [Report](eerad3_event_shapes_and_jet_rates_in_electron_positron_annihilation_at__1402_4140/FINAL_REPORT.md) | [`rejected`](eerad3_event_shapes_and_jet_rates_in_electron_positron_annihilation_at__1402_4140/status.json) |
| 2 | Fault-tolerant honeycomb memory | [Report](a_fault_tolerant_honeycomb_memory__2108_10457/REPORT.md) | [`hard_open_candidate`](a_fault_tolerant_honeycomb_memory__2108_10457/status.json) |
| 3 | Retargetable quantum compilation (tket) | [Report](t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/REPORT.md) | [`hard_verified_achievable`](t_ket_a_retargetable_compiler_for_nisq_devices__2003_10611/status.json) |
| 4 | Sparse-blossom error correction | [Report](sparse_blossom_correcting_a_million_errors_per_core_second_with_minimu__2303_15933/REPORT.md) | [`hard_open_candidate`](sparse_blossom_correcting_a_million_errors_per_core_second_with_minimu__2303_15933/status.json) |
| 5 | Mirror-circuit randomized benchmarking | [Report](scalable_randomized_benchmarking_of_quantum_computers_using_mirror_cir__2112_09853/FINAL_REPORT.md) | [`hard_open_candidate`](scalable_randomized_benchmarking_of_quantum_computers_using_mirror_cir__2112_09853/status.json) |
| 6 | Semiconductor band structure (kdotpy) | [Snapshot note; no final report](kdotpy_k_p_theory_on_a_lattice_for_simulating_semiconductor_band_struc__2407_12651/REVIEW_SNAPSHOT.md) | No final status |
| 7 | Quantum-processor characterization (pyGSTi) | [Report](probing_quantum_processor_performance_with_pygsti__2002_12476/REPORT.md) | [`hard_open_candidate`](probing_quantum_processor_performance_with_pygsti__2002_12476/status.json) |
| 8 | Stabilizer quantum error correction (Stim) | [Report](stim_a_fast_stabilizer_circuit_simulator__2103_02202/FINAL_REPORT.md) | [`hard_verified_achievable`](stim_a_fast_stabilizer_circuit_simulator__2103_02202/status.json) |
| 9 | NLO energy-energy correlations | [Report](numerical_evaluation_of_the_analytic_nlo_energy_energy_correlation__1801_03219/FINAL_REPORT.md) | [`hard_verified_achievable`](numerical_evaluation_of_the_analytic_nlo_energy_energy_correlation__1801_03219/status.json) |
| 10 | Electron-phonon transport and superconductivity (EPW) | [Report](epw_electron_phonon_coupling_transport_and_superconducting_properties__1604_03525/FINAL_REPORT.md) | [`hard_open_candidate`](epw_electron_phonon_coupling_transport_and_superconducting_properties__1604_03525/status.json) |

The kdotpy folder has no top-level final report or status file. Its existing
concepts and authoring work are included, not replaced with a completed task.
Reports for other folders explain their selected concepts and current
versions; not every concept in an archive shares its folder's final status.

## Review and reproduction

These are **reviewer-only archives**, including solutions, private witnesses,
hidden cases, and attempt transcripts. Give a blind participant only its chosen
participant assets, never the whole archive.

See the [publication notes](PUBLICATION_V4.md) for sampling semantics, explicit
exclusions, integrity checks, and large-data restoration. The
[manifest](PUBLICATION_MANIFEST_V4.json) records artifact hashes and capture
provenance; paths are relative to this folder. Saved scientific outcomes are
not rerun or independently certified by this publication process.

The former curated collection remains in Git history at `7cf6509`. The earlier
[task_v2](../task_v2/README.md) and [task_v3](../task_v3/README.md) collections are
unchanged. Return to the [repository index](../README.md).
