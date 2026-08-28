# Historical source manifest

The extracted method bodies are original TBmodels code, not reimplemented
fault injections. Local namespace/import scaffolding is intentionally small.

- `import_xyz.py`: `Model.from_wannier_files`, commit
  `a93b8f805b3ade4436a89dffb209ae1d2f857dbd`, `tbmodels/_tb_model.py`.
- `import_atom.py`: the corresponding method at
  `0168836c6bb2c04ac7a9d4ac6682fca47512ea4c`.
- `historical_model.py`: selected dense construction, Fourier, supercell and
  cell-mapping methods from `24c3d2b3420d7b4b34ae15c636ea2f3685fbf02d`;
  text parser helpers from `0168836c6bb2c04ac7a9d4ac6682fca47512ea4c`.
- `dense_support.py`: adapter for the old sparse constructor interface;
  `set_sparse` and `_array_cast` are dense-only compatibility glue. They do not
  implement import or cell repairs. No later implementation is included.

The Cartesian and atom loaders are independently preserved historical API
versions. `pipeline.py` selects the appropriate legacy path and supplies the
entrypoint integration. The separate geometry input allows repairs to be
developed and evaluated independently. Original upstream license is retained.
