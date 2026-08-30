# Joint compression of fermionic simulation representations

Improve the supplied compiler's coefficient cost by jointly choosing orbital
and auxiliary bases without changing the fermionic Hamiltonian.

Assets: public Hamiltonians, a runnable spectral-candidate baseline, the exact
cost function, a public scorer, and the executable contract in `input/FORMAT.md`.

Place a self-contained `solver.py` and any supporting files in the output
directory. It must implement `python3 solver.py REQUEST.json RESPONSE.json`.

The target is at least **25% aggregate cost reduction** from the supplied
baseline and at least **10% reduction in every family** on unseen instances.
Every transformation must satisfy the stated validity conditions.

Development time is one hour. Hidden inference is limited to 180 seconds total,
one CPU, and 2 GiB. Scoring measures aggregate reduction, worst-family
reduction, validity, and runtime. No internet access is available.
