# Executable and data contract

The sibling JSON and NPZ form one device. `qualification.model.load_case` reads
them without pickle. Arrays are ordinary finite float64 values except that
`prescribed_current` uses NaN to mark an unknown current. Vertex and triangle
ordering is arbitrary; do not depend on a particular mesher numbering.

NPZ arrays:

- `points`: (N,3) global xyz coordinates; all triangle vertices share a z.
- `triangles`: (T,3) counterclockwise vertex indices.
- `region`: (N,) -1=exterior boundary, 0=free film vertex, positive=global hole
  ID plus one. All vertices in a hole share its tag, including its boundary.
- `point_film`, `triangle_film`: film membership, matching JSON `films` order.
- `lambdas`: (T,) physical elementwise material coefficients; zero inside holes.
- `drive_H`: (D,N) applied out-of-plane H, in mA/um.
- `vortex_load`: (D,N) integrated source, as described in `PHYSICS.md`.
- `prescribed_current`: (D,H) mA. A finite entry fixes that hole current; NaN
  instead fixes that hole's `target_fluxoid` entry. A finite current's fluxoid
  target is ignored.
- `target_fluxoid`: (D,H) mT*um^2, meaningful only for unknown-current entries.
- `observers`: (P,3) screening-field observation coordinates.

For `case CASE.npz RESULT.npz [--config NAME]`, write:

- `stream`: (D,N) g in mA, in the input vertex order.
- `current`: (D,T,2) J in mA/um, in the input triangle order.
- `field`: (D,P,3) screening B in mT, in the input observer order.
- `hole_current`: (D,H) mA, in global hole-ID order.
- `fluxoid`: (D,H) mT*um^2, same hole order.
- `inductance`: (H,H) pH. The no-hole case has shape (0,0), not a missing array.

The default config is evaluated on hidden inputs. Additional configs are
replayed to verify ablations. The baseline driver writes a sibling metrics
JSON with case/configuration/seconds/max_rss_mib/vertices/triangles/drives.

The development experiment driver documents the required CSV columns. Keep
those columns; additional columns are welcome. `results.csv` contains only
your chosen default, `ablation.csv` contains all configurations (including the
default), and `scaling.csv` contains one measured resource row per run.
The standard driver computes norms, kinetic-current energy, reciprocity,
linearity, and state-constraint diagnostics from the raw arrays. Those are
diagnostics, not hidden labels. On the supplied development cases, drive 3
is -0.7 times drive 2, so their responses should obey the same relation.
Do not assume that relation or four drives for arbitrary future inputs.

`claims.json` is an object with a `claims` list, with at least two quantitative
comparisons. Each comparison has `id`, `text`, `table` (`results.csv` or
`ablation.csv`), `metric`, `left`, `right`, `relation` (`lt`, `gt`, `close`), and
optionally `tolerance` (absolute tolerance for `close`). A row selector is an
object with `case`, `configuration`, and integer `drive`. The comparison must
be true for the identified table rows. Use the report for broader interpretation,
including limitations that cannot be encoded as one scalar comparison.

`run.sh` must be relocatable with its sibling `workspace`. It may use the
supplied dependencies through `ALE_RUNTIME`; evaluation sets this variable.
Evaluation runs without network access and cannot see private oracle files.
