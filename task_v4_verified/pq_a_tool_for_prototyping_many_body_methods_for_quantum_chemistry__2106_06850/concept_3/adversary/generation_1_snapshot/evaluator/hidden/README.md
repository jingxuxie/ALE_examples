# Hidden certificate index

Organizer-only assets. `certificate_index.json` indexes the actual frozen
certificates, target vectors, integrity manifest, witness score, and independent
dense audit in the adjacent `../private/` directory. Both directories must remain
outside participant mounts. Paths in the index are relative to this directory.
The evaluator uses the trusted `../private/` implementation; the index does not
introduce another scoring policy or any extra hidden target cases.
