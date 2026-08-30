This initial private sweep is invalid and must not inform scientific targets.
`np.empty_like(labels)` inherited Fortran order from sparse-generated labels;
the native decoder requires row-major output buffers. The sweep was rejected
before any regime selection or new-generation freeze. The corrected sweep uses
an explicit C-contiguous `(shots, 4)` allocation, binary-output validation, and
byte-for-byte checks against the promoted Python API. Corpus labels, correlated
baseline reports, and original task artifacts were unaffected.
