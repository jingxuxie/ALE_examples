# Starting code and input provenance

`bulk.py` adapts the convention-2 `Model.hamilton` Fourier sum and eigenvalue evaluation from the public pre-supercell revision of TBmodels, commit `ab24b723e4b35dd08d86aa098a5cadeacab96e83`:

<https://github.com/Z2PackDev/TBmodels/blob/ab24b723e4b35dd08d86aa098a5cadeacab96e83/tbmodels/_tb_model.py>

The historical source stored one conjugate half; the NPZ contract instead contains both directions, so the adapter must not add another Hermitian conjugate. This is an honest capability-level starting point, not a claim that the complete historical package lacked every transport interface. No later geometry or transport implementation is included here.

Real-material input data come from the official TBmodels examples/tests. Their hopping amplitudes are retained without fitting, randomization, or range truncation. Finite crystal cuts and additional real onsite gates define the devices specified in each input. The bundled numerical data are provided for this computation, not as experimental device predictions.

The upstream Apache-2.0 license is retained as `LICENSE.TBmodels.txt`. The modified Fourier adapter uses the explicit full-Hamiltonian NPZ convention described above; it is not an unmodified historical module.
