# ALE examples

Task-design and screening artifacts shared for review. The folders preserve
participant instructions where a task was built, authoring decisions, source
artifacts, known-good solutions, evaluators, and fresh-agent attempts where
available.

## Original collection (`tasks_v2`)

| Topic | Participant task or review entry | Screening record |
| --- | --- | --- |
| Localized statistics decoding | [Review guide](localized_statistics_decoding/README.md) | [Rejected: remains too easy](localized_statistics_decoding/status.json) |
| block2 | [Are the transport traces physical?](block2_a_comprehensive_open_source_framework_to_develop_and_apply_stat__2310_03920/concept_01/participant/v_01/TASK.md) | [Rejected](block2_a_comprehensive_open_source_framework_to_develop_and_apply_stat__2310_03920/status.json) |
| Bodge | [Authoring archive; no participant task built](bodge_python_package_for_efficient_tight_binding_modeling_of_supercond__2410_08758/private) | [Rejected](bodge_python_package_for_efficient_tight_binding_modeling_of_supercond__2410_08758/status.json) |
| Filter functions | [Quantum gate-sequence noise predictor](filter_function_formalism_and_software_package_to_compute_quantum_proc__2103_02403/concept_01/participant/v_01/TASK.md) | [Rejected](filter_function_formalism_and_software_package_to_compute_quantum_proc__2103_02403/status.json) |
| Hamiltonian truncation | [Rescue a finite-volume scalar-spectrum campaign](hamiltonian_truncation_study_of_the_phi_4_theory_in_two_dimensions__1412_3460/concept_01/participant/v_01/TASK.md) | [Rejected](hamiltonian_truncation_study_of_the_phi_4_theory_in_two_dimensions__1412_3460/status.json) |
| Many-body localization | [Authoring archive; no participant task built](many_body_localization_edge_in_the_random_field_heisenberg_chain__1411_0660/private) | [Rejected](many_body_localization_edge_in_the_random_field_heisenberg_chain__1411_0660/status.json) |
| Package-X | [One-loop matching and subtraction engine](package_x_2_0_a_mathematica_package_for_the_analytic_calculation_of_on__1612_00009/concept_01/participant/v_01/TASK.md) | [Rejected](package_x_2_0_a_mathematica_package_for_the_analytic_calculation_of_on__1612_00009/status.json) |
| QuTiP | [Qualify a migrated open-system dynamics service](qutip_2_a_python_framework_for_the_dynamics_of_open_quantum_systems__1211_6518/concept_01/participant/v_01/TASK.md) | [Rejected](qutip_2_a_python_framework_for_the_dynamics_of_open_quantum_systems__1211_6518/status.json) |
| SuperScreen | [Qualify the thin-film device-response pipeline](superscreen_an_open_source_package_for_simulating_the_magnetic_respons__2203_13388/concept_01/participant/v_01/TASK.md) | [Rejected](superscreen_an_open_source_package_for_simulating_the_magnetic_respons__2203_13388/status.json) |
| Tkwant | [Transient transport that looks converged](tkwant_a_software_package_for_time_dependent_quantum_transport__2009_03132/concept_01/participant/v_01/TASK.md) | [Rejected](tkwant_a_software_package_for_time_dependent_quantum_transport__2009_03132/status.json) |
| Vortex lattices | [Phase-engineered rotating superfluids, v_02](topological_defect_dynamics_of_vortex_lattices_in_bose_einstein_conden__1608_07756/concept_01/participant/v_02/TASK.md) | [Rejected](topological_defect_dynamics_of_vortex_lattices_in_bose_einstein_conden__1608_07756/status.json) |

The original collection above consists of rejected screening archives, not
accepted hard ALE tasks. Consult each original `status.json` for its reason and supporting record;
the reasons and amount of completed work vary by task.

## Additional collection (`tasks_v3`)

These are review snapshots of the saved reports and pilot artifacts. Some
tournaments were still in progress during capture; inclusion here is not an
acceptance decision or a claim that all runs have finished.

| Topic | Author's report |
| --- | --- |
| Atomistic spin models | [Report](atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/REPORT.md) |
| Symmetrized Wannier-like tight-binding models | [Final report](automated_construction_of_symmetrized_wannier_like_tight_binding_model__1805_12148/FINAL_REPORT.md) |
| Quantum LDPC code landscape | [Report](decoding_across_the_quantum_ldpc_code_landscape__2005_07016/REPORT.md) |
| Learning quantum noise | [Report](efficient_learning_of_quantum_noise__1907_13022/REPORT.md) |
| Zigzag Majorana Josephson junctions | [Report](enhanced_proximity_effect_in_zigzag_shaped_majorana_josephson_junction__1903_06168/REPORT.md) |
| FastEEC energy correlators | [Report](fasteec_fast_evaluation_of_n_point_energy_correlators__2406_08577/REPORT.md) |
| Phonopy and phono3py | [Report](implementation_strategies_in_phonopy_and_phono3py__2301_05784/REPORT.md) |
| Equivariant lattice field theory learning | [Report](learning_lattice_quantum_field_theories_with_equivariant_continuous_fl__2207_00283/REPORT.md) |
| Reliability of lattice gauge theories | [Report](reliability_of_lattice_gauge_theories__2001_00024/REPORT.md) |
| ALPS | [Report](the_alps_project_release_2_0_open_source_software_for_strongly_correla__1101_2646/REPORT.md) |

See the [tasks_v3 publication notes](PUBLICATION_V3.md) for snapshot semantics,
runtime exclusions, and restoration of losslessly packaged large data.

## Before reviewing or running

These are **author/reviewer bundles** and include solutions, hidden evaluation
data, and attempt transcripts. Do not expose an entire bundle to a blind task
participant.

These are review-oriented exports, not complete offline runtime images. The
[original publication notes](PUBLICATION.md) document the `tasks_v2` exclusions,
including its oversized frozen snapshot. The [tasks_v3 notes](PUBLICATION_V3.md)
document that collection separately: oversized scientific data is preserved
losslessly and can be restored, while installed runtime trees remain excluded.
