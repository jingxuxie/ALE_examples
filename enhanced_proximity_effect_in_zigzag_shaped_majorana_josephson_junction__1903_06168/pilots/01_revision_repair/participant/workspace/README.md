# Starting workspace

`upstream/zigzag.py` is an unmodified snapshot from commit
`a04132fedb8cbd5cf7a1365428015cefab047538` of basnijholt/zigzag-majoranas.
Attribution and the upstream BSD-3-Clause terms are retained in
`upstream/LICENSE.txt`. That license file is carried from a later licensed
revision; the starting revision itself did not contain a license file.

`solve.py` is a runnable but numerically unrepaired baseline:

```sh
python participant/workspace/solve.py --input participant/input/example.json --output attempt/example_result.json
```

For a submission in `attempt/solve.py`, add `participant/workspace` to the Python
import path, import `protocol.main`, and call it with the path to your repaired
snapshot. Alternatively replace the service. Keep all submitted changes under
`attempt/`; the evaluator does not transplant edits from this workspace.

The adapter supplies current execution compatibility, not scientific repairs:
`grid_spacing` is translated to `grid`; Kwant's symbolic printer receives its
missing `sin`/`cos`/`exp` function mappings for SymPy 1.12; the two unused
historical system arguments are supplied when required; and SciPy sparse
shift-invert replaces the unavailable MUMPS backend. These fixes are already
provided and are not intended obstacles. The source is otherwise loaded intact.

`geometry.py`, `hamiltonian.py`, and `protocol.py` are author-added service layers,
not separately recovered upstream modules. The region predicates, templates,
assembly, and gap estimator remain in the historical source.

The compact vendored archive contains Kwant 1.5.0 and tinyarray 1.2.5, including
their license metadata, without tests or bytecode. It is decoded to a temporary
directory beside the result and removed at exit. No installation or network is
needed. System dependencies: Python 3.10, NumPy, SciPy, and SymPy. Adaptive,
pfapack, and MUMPS are not used. `vendor/MANIFEST.json` lists the archive contents
and checksum. The native bundle is Linux x86_64 / CPython 3.10 specific.
