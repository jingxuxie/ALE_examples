# Witness JSON, version 1

The output directory must contain a regular, non-symlink file `witness.json`,
at most 131072 bytes, encoded as UTF-8 JSON. The object has exactly these keys:

| Key | Type and shape | Meaning |
| --- | --- | --- |
| `schema_version` | integer 1 | Schema identifier |
| `bonds` | list of 32 integers, each -1 or +1 | Torus couplings in the order below |
| `beta` | finite real JSON number in [1,3] | Inverse temperature |
| `order` | permutation of integers 0 through 15 | Physical site at each autoregressive position |
| `weights` | 16 lists of 16 finite real JSON numbers | Matrix in autoregressive-position coordinates |
| `pattern` | list of 16 integers, each -1 or +1 | Sector center in physical-site coordinates |
| `radius` | integer 2, 3, or 4 | Hamming radius |

Booleans are not numbers or integers for this interface. Duplicate keys, unknown
keys, missing keys, NaN, Infinity, strings standing for numbers, and ragged arrays
are invalid. Diagonal and upper-triangular weights must be exactly zero. Each
row's L1 norm must not exceed ln(9999). There is no bias or mixture parameter.

Site `(row,column)` is `4*row+column`, with coordinates taken modulo 4. For
each site in increasing site order, append its rightward bond and then its
downward bond. Thus `bonds[2*site]` joins `(row,column)` to `(row,column+1)`;
`bonds[2*site+1]` joins `(row,column)` to `(row+1,column)`. These are 32 distinct
undirected bonds. Every elementary square is counted once, indexed by its
upper-left site, including squares crossing a periodic boundary.

Structural validity checks the schema, topology constraints, beta, and weights.
The entropy, KL, variance, gradient, energy, and sector gates determine success,
not structural validity. See `MATH.md` for the exact quantities and scoring.
