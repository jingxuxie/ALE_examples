# Interface and model

## Artifact

`design.json` must be a regular, non-symlink file of at most 16 KiB. It contains
exactly `{"z_image": [24 integers]}`; duplicate keys and other types are rejected.
Entries `0=X`, `1=Y`, `2=Z` specify `C_q† Z C_q` in the original code frame.
Canonical Cliffords are `H`, `H_YZ`, and identity, respectively. The supplied
baseline is a previous optimized pattern. The `cell_coordinates` lists order the entries;
a physical coordinate `(x,y)` maps to `(x mod 8,y mod 6)` in that list.

The same static 24-site pattern tiles all three memories: 24, 96 and 216 data
qubits. Native arbitrary two-qubit Pauli-product measurements are allowed.
Clifford choices change measurement bases, not connectivity or gate count.
The circuit and logicals are conjugated; laboratory-frame phase noise is not.

## Heralded faults

Each circuit has six clean subrounds, six noisy subrounds and six clean
subrounds, with ideal reference readout. A flagged `(subround,qubit)` slot
permits an arbitrary unknown `Z` bit immediately after that subround's parity
measurements. All combinations of flagged bits must be correctable. Flags
identify possible error locations, not error values. No additional noise is
present. Clean boundaries and reference qubits are ideal verification devices.
This is not a conventional EM3 threshold or an unheralded-noise guarantee.

For each slot, supplied response columns correspond to original-frame `X`,
`Y`, and `Z`. Select the column indexed by that slot's supercell entry. Columns
pack `(syndrome << 4) | logical_action` as hexadecimal integers. The four low
bits are ordered `(X1,Z1,X2,Z2)`. For any support `E`, exact ambiguity is

`a(E) = rank_GF2([H_E; L_E]) - rank_GF2(H_E)`.

Complete correctability requires `a(E)=0`, equivalently
`ker(H_E) ⊆ ker(L_E)`. This tests every error combination, without sampling the
unknown error bits or invoking a decoder.

## Distributions, scores and assets

`input/family.json` specifies probabilities and slot conventions. The full
distribution implementation is `design_common.py:generate_supports`.
Every spacetime slot is flagged independently with probability 0.28, 0.30,
or 0.32. These are three separate density groups, named `iid_28`, `iid_30`,
and `iid_32`. The public generator reproduces the hidden distribution, not
the hidden supports. The artifact must handle all three sizes and densities.

The core score is the equally weighted average of the nine size × family
correctability fractions. The worst-family score conservatively means the
minimum of those nine groups. Mean logical ambiguity is a secondary diagnostic.
The fixed target is **core score ≥ 0.85 and every group ≥ 0.60**. Hidden evaluation
uses 4,096 supports per group, 36,864 total. The exact protocol is also published
in `input/objective.json`. Only a JSON artifact is evaluated; runtime/resource
scores are 1 for a valid bounded artifact and 0 otherwise. Evaluator wall time
is diagnostic, not an optimization objective. Development time is one hour.

- `input/scale_*.json.gz`: complete fault-response columns and slot/cell maps.
- `input/scale_*.stim`: source-derived circuits for provenance. Artificial
  `X/Y/Z_ERROR(0.001)` probes extract columns; they are not extra task noise.
- `input/practice.json`: development supports, disjoint from hidden supports.
- `check_design.py`: faithful exact practice scorer; standard library only.
- `../baseline/design.json` and `../baseline/solve.py`: the previous champion.

From the participant directory with Python 3.9+:

```
python baseline/solve.py --output /your/writable/path/design.json
python workspace/check_design.py /your/writable/path/design.json
python workspace/check_design.py /your/writable/path/design.json --seed 731 --count 96
```

`--count` is the number of generated supports per family per size. Generate
additional practice draws to assess robustness rather than memorizing the
finite supplied draws. No hidden supports or passing dense-erasure design are supplied.

Scientific sources: [original paper](https://arxiv.org/abs/2108.10457),
[official implementation](https://github.com/Strilanc/honeycomb_threshold),
[bias-tailored Floquet codes](https://arxiv.org/abs/2411.04974). This task's
heralded model and optimization objective are explicit new definitions.
