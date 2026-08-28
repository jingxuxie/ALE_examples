# Repaired junction service

Run with the documented single-request interface:

```sh
python attempt/solve.py --input REQUEST.json --output RESULT.json
```

The service uses the supplied compatibility adapter and vendored runtime in
`participant/workspace`. All repairs are contained in this submission.

`repaired_zigzag.py` retains the historical Hamiltonian templates, coordinates,
region slices, flood-fill seeds, fill order, and interface hopping assignments.
It corrects the outer-edge predicate to select sites outside the region and
unites the normal-side top and bottom interfaces for the barrier region.

`solve.py` computes excitation energies using sparse shift-invert eigenvalues,
checks the requested momentum grid and both endpoints, and refines local
minima inside the Brillouin-zone interval. It returns the minimum energy, not
the minimizing momentum. The momentum-dependent matrix is assembled from its
constant, cosine, and sine components, retaining the wrapped unit-cell phase.

The upstream BSD-3-Clause license is retained in `LICENSE.txt`.

Validation covered the supplied example, twelve finite/periodic straight and
zigzag barrier configurations, four independently minimized dense spectra,
and an endpoint minimum. Sparse and dense gap results agreed within 6e-14 meV.
A large periodic request using 65 initial grid points completed in 5.92 seconds
with approximately 111 MiB peak resident memory in the supplied environment.
