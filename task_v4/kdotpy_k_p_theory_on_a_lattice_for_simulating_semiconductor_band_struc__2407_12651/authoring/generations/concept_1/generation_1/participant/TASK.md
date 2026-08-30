# Robust band atlas

Improve the supplied baseline for selecting a shared rank-two band-subspace
atlas on a periodic momentum grid under an acquisition budget. The selection
must have the requested determinant-bundle Chern number in every uncertainty
scenario. Minimize the worst-scenario normalized loss plus its weighted mean;
energy agreement, subspace overlap, dispersion and Berry-flux fidelity matter.

Submit a directory containing `solve.py`, runnable as
`python3 solve.py --input CASE_DIRECTORY --output OUTPUT_JSON`.
Return only `{"choices": [integer_candidate_index, ...]}`. Each hidden case is a
fresh, isolated invocation with 90 seconds, four CPU threads, and 2 GiB address
space. NumPy/SciPy and the read-only `workspace` utilities are available; no
network or persistent cross-case state is available.

Acceptance requires every case feasible, no case worse than baseline,
at least 12% family-balanced relative loss reduction and at least 8% mean
reduction in each family. Exact optima are neither required nor rewarded.
See `workspace/SCHEMA.md`, `workspace/policy.json`, the public inputs, and
`baseline/solve.py`. Frames are arbitrary local bases: no global smooth gauge
or individual-band labeling is required.
