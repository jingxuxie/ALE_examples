# Runnable starting point

From this directory, run `python solve.py --input ../input/sample_01.json --output result.json`. It is a weak, deterministic Python translation, **not** an unmodified ALPS binary or a snapshot of the 2011 release. NumPy is its only nonstandard dependency. The task interface, packing, quadrature weights, round-trip diagnostic, and coefficient normalization are adapter code.

The excerpts in `historical/` are exact functions extracted from official pre-fix source files, with their existing source notices retained. They are evidence for the starting arithmetic, not complete compilation units. `SOURCE_MAP.json` gives the exact parent revisions, source paths, original line numbers, and file/excerpt hashes. No later implementation or expected answers are included here.

The AFM band loop and signed Legendre accumulation retain the pre-fix indexing and sign arithmetic. The backward Fourier routine retains its old conditional, but the **matrix-entry interface is an extension**: historical concrete Fourier constructors restricted production use to one site. Do not infer production matrix support from the bare base-class routine. The contract, not a historical zero-tail shortcut, defines the mathematical behavior for active off-diagonal channels.

The supplied measure replaces ALPS DOS-file parsing and numerical integration machinery; measurement matrices replace configuration sampling. HDF5, solver selection, and external-process handoffs are intentionally outside this numerical task. All samples are unlabeled inputs, not regression answers.
