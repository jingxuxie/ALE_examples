# Generation-only source inspection

- Paper: arXiv:1407.3257v2, retrieved August 28, 2026, saved as `sources/paper.html`.
- Follow-up repository: `brunorijsman/cascade-cpp`, inspected HEAD `8240cab83831` (February 22, 2025), plus the eight retrieved recent commits in `sources/commits.json`.
- Its algorithm configuration is saved in `sources/algorithm.cpp`; this is not exposed to participants.
- Issue inventory `sources/issues.json` contains two usage/build questions and no substantive correctness patch. The repository's documentation describes its earlier Python implementation, improved C++ validation, and comparison studies. No author supplement or author source repository was identified in the inspected material.
- Earlier local Cascade package was inspected. Its previous reference passed but the 600-second pilot did not submit. Neither outcome is counted as new empirical hardness evidence.

The chosen tasks extend the paper's tradeoffs among disclosed parities,
communication, finite-frame failures, and shuffle/confirmation design. They
are not reproductions of the paper's numerical tables. In particular, concept 2
is an explicitly synthetic fixed-interleaver deployment audit with a privately
constructed sparse residual trap; it is not a refutation of the paper's random
channel results. All privileged artifacts remain outside `participant/`.
