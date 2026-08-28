# Author-only provenance

Snapshots and local histories, rather than an assumption about the newest
release, determine every artifact boundary.

| Artifact | Primary source | Local evidence |
|---|---|---|
| Target paper | https://arxiv.org/abs/2406.08577, v2 | `paper.html` |
| Original implementation | https://github.com/abudhraj/FastEEC | `FastEEC/.git`, tag 0.1 `54e6886` |
| Fractional continuation | https://arxiv.org/abs/2409.12235, v2 | `nu_paper.html`, tag 0.2 `54811e2` |
| Projected resolved follow-up | https://arxiv.org/abs/2410.16368 | tag 0.3 `5dbac32`, `eec_angles.cc` |
| Multidimensional resolved implementation | https://github.com/samcaf/ResolvedEnergyCorrelators | complete history, commit `0736fc3c24d00f1ea7d08b8ea3c62ccd84f7b10e` |
| Subjet observable follow-up | https://arxiv.org/abs/2501.17218 | adjacent repository `write/src/ewocs.cc` and utility modules |
| Releases | https://api.github.com/repos/abudhraj/FastEEC/releases | `releases.json` |
| Issue audit | https://api.github.com/repos/abudhraj/FastEEC/issues?state=all&per_page=100 | `issues.json`, empty response |
| Pull-request audit | https://api.github.com/repos/abudhraj/FastEEC/pulls?state=all&per_page=100 | `pulls.json`, empty response |
| Adjacent issue/PR/release audit | GitHub API for samcaf/ResolvedEnergyCorrelators | `adjacent_issues.json`, `adjacent_pulls.json`, `adjacent_releases.json`, all empty responses |
| Real data | https://github.com/abudhraj/FastEEC/releases/download/0.3/data.txt | `cms100k.txt`, checksum and measured multiplicities in `data_audit.json` |
| Build dependency | https://fastjet.fr/repo/fastjet-3.4.3.tar.gz | tarball, source, configure/build/install logs, static library |

The four-mode integer and fractional private programs retain their official
mathematics. Only output precision is raised to 17 digits in copied drivers;
original sources remain unchanged. The original clustering is **pt_scheme**,
not E_scheme. The EWOC adapter intentionally uses E_scheme, as its source does.
This distinction was checked before the first substantive pilot attempts.

The resolved and EWOC adapters remove Pythia/event-generation and plotting
dependencies. Their mathematical kernels come from the adjacent implementation;
interface and histogram presentation choices are specified publicly. The
resolved adapter's exact bin aggregation is an author optimization, not a claim
that its C++ file was distributed by the paper authors. Independent validators
are retained beside the adapters.

The original Mathematica notebook and `test_4pt*.out` files concern integer
four-point plotting. They are not a released small-nu scaling-fit solution.
No hidden detector-unfolding ground truth, unpublished author fitter, or
unobserved bug-fix pull request is claimed.

Deeper adjacent-history inspection did find actual committed fixes:
`37308dba92540c6d0e8fdb2afa0004b64a7dd5ca` changes several writer denominators
from vector jet pt to scalar constituent pt; `720b1a67dcacfcf24bf8caae51babb2355a696a8`
fixes the `RE3C.h` ratio-histogram constructor. These are documented candidate-A
gaps, not extra pilots or alleged unpublished implementations.

The raw dataset has no supplied constituent masses or particle identities.
Spherical-geometry jobs reinterpret the supplied positive massless four-vectors
under a declared measure; they are not represented as newly acquired ee data.
Momentum rescalings and azimuthal rotations are exactly specified kinematic
families, not a trained simulator or labeled hidden development set.

All downstream code copies retain their existing licenses. No git metadata,
later solution-bearing module, or expected numerical histogram is provided in
participant directories.
