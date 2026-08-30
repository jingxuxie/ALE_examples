# Champion–challenger generation 1

Both original isolated ultima-alpha attempts passed contract v1. Generation 0 is archived under `generations/generation_0/`; the selected artifact and its original construction files are under `champions/generation_1/`. Selection used the actual normalized observable errors: v_1 was better than v_2 in all three original families, not just their tied capped score of one.

The private challenge search evaluates 6144 correlations: all three Pauli channels at every integer separation 1–2048, for the same infinite-chain Hamiltonian. It does not change the physical state, the critical point, or ground-truth convention. `champion_1_broad_sweep.json` records the complete profile.

Failure clusters:

- **Finite correlation-length cutoff:** order error grows from 0.268% at 128 to 35.4% at 512 and 72.7% at 1024, despite energy excess only 3.12e-6. Its transfer correlation length is about 495.
- **Unequal spectral resolution between operators:** connected density already exceeds 10% error at distance 71 and reaches 52.6% at 256. The y channel, absent from the old score but belonging to the same exact two-site density matrix, reaches 40.5% at 128.

New disclosed contract v2 keeps the same Hamiltonian, bond cap, canonical and symmetry conditions, energy tolerance and construction budget. It extends xx to 1024, zz-connected to 256, and includes yy through 128, with tolerances 2.5%, 10%, and 10%. The champion tensor alone is the new runnable public baseline; previous source code and session logs remain private. All evaluated distances are disclosed, and this is a new generation, not a retroactive rescore of v1 attempts.

No passing v2 tensor is known at target freeze. Feasibility at finite distance is not proved by the exact infinite-bond ground state. A failed fresh generation will therefore be `hard_open_candidate` unless a genuine private tensor also passes v2.
