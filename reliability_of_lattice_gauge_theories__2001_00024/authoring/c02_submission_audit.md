# Initial completed submission: execution and completeness audit

The fresh attempt ended normally after 2938.705 seconds. Public hashes are
unchanged. Its `solve` entry point performs calibration and many-body propagation;
it is not a partial scaffold or a missing-output failure.

The submitted implementation is self-contained NumPy/SciPy. It does not write
files, compile helpers, spawn processes, or read case identifiers in `solve`.
The only explicit file open is in the optional command-line entry point. Instances
have separate state and random generators. Therefore independent isolated calls
can safely run concurrently on the same immutable submitted source. Each call
still has one CPU, 6 GiB, and 3600 worker seconds; namespace startup gets 30 seconds
of grace and no additional numerical time. Raw hidden executions are stored
outside the participant/attempt allowlist.

The method combines bounded calibration fits with parity-blocked canonical MPS,
fourth-order composition, randomized SVD, and measured-cost bond adaptation. It
preserves each intact local Gauss-square term in the splitting. The private
reference instead uses existing charge-conserving tensor software and finer
steps. Neither description establishes a performance gap: actual held-out results
remain necessary. Submitted validation claims are retained separately from the
author's independent references and will not be substituted for hidden scores.
