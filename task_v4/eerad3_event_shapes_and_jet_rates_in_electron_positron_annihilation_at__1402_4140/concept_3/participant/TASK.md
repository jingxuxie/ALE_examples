# Repair EERAD3's unresolved momentum mapping

Repair the supplied, source-native numerical kernel for a five-to-three
antenna momentum map. It must remain reliable for valid massless
centre-of-mass events, including soft and multiple-collinear limits,
without sacrificing ordinary-event accuracy or production throughput.

Preserve the physical map, positive-energy mass shells, conservation,
spectator identity, mapped invariant bookkeeping, and valid rotations.
Do not replace the map with a different clustering prescription or
special-case the examples. Precision and computational cost both matter.

Edit the Fortran kernel in `workspace/`. The exact ABI, domain, build,
public examples, numerical tolerances, and resource contract are in
`input/INTERFACE.md`. Submit the workspace, not a report or executable.
