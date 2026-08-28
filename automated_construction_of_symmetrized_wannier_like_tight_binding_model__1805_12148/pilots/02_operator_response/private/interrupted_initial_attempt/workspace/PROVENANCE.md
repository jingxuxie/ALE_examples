# Starting capability

`atomic_h.py` is a small NumPy compatibility adaptation of the earlier local-orbital
Hamiltonian group-average workflow, not a verbatim historical snapshot or a
fabricated upstream bug. It handles scalar hoppings and Bloch energies only.
The connection and response stages in `solve.py` intentionally retain that
pre-capability behavior. The full real-space numeric inputs are normalized from
official first-principles Wannier data; no random Hamiltonian generator is used.

Hamiltonian workflow source: `Model.symmetrize` in
https://github.com/Z2PackDev/TBmodels/blob/39d7eb096d809137373774ef6ba337fdf36349bc/src/tbmodels/_tb_model.py .
No full operator symmetrizer or Berry-response implementation is included here.
