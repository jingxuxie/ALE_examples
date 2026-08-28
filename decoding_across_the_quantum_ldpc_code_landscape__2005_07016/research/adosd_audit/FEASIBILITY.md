# MBP+ADOSD bounded source-feasibility audit

## Verdict

**Worth a source-based pilot02 adapter experiment; not a drop-in or a verified
stronger reference yet.** Both unmodified official programs compile on Linux.
Pilot02's existing physical generators and full joint priors fit the GF(4)
model naturally, without a new task or frame simplification. However, the
published Pauli initializer only accepts a scalar homogeneous channel, and
both executables are compile-time-configured Monte Carlo simulators. No
native-on-pilot02 accuracy or timing comparison has been performed.

## Exact provenance and build

- Repository: https://github.com/cylai-nycu/MBP_ADOSD
- Pinned commit: `094149da7c6147704b544636baf6937f688d01f9`
- Commit time: `2026-02-20T17:16:07+08:00`; message: `Update BPOSD.c`.
- Paper: https://arxiv.org/abs/2412.21118v4, revised February 21, 2026.
- No AGENTS.md instructions were found in the new source tree. No tracked
  source file was changed. Repository license is GPL-3.0.

Built executables are `research/adosd_audit/bin/adosd_dem` and `adosd_pauli`.
The tracked `.exe` files are Windows PE binaries; these are fresh Linux builds.
Dependencies: GCC 11.4.0, libc and libm; no external decoding library is needed.
Use the following from either native source directory (`ADOSD/ldpcQaun` or
`ADOSD_DEM/ldpcQuan`), choosing an output path in the audit directory:

```
gcc -O2 -Wall BPOSD.c bp_dec/bp_dec.c bp_dec/bp_llr.c \
  lib_rand/splitmix64.c lib_rand/lib_rand.c lib_rand/xoshiro256starstar.c \
  lib_math/fast_math.c OSD/OSD.c -lm -o /absolute/audit/bin/adosd_variant
```

The supplied DEM Makefile omits `-lm`; our Linux builds explicitly add it.
Measured builds: DEM 1.31 s wall / 1.23 s CPU; Pauli 1.04 s wall / 1.02 s CPU.
Numerous compiler warnings are preserved in `logs/*_build.log`; this is not a
warning-clean or sanitizer-validated build.

Each official executable was run for a bounded eight seconds, using symlinked
official code data and private `Results/` directories. DEM loaded N=1945,
M=400, one logical row and 1945 priors; Pauli loaded the [[144,12,12]] BB code,
132 checks and 156 normalizer rows. Both loaded successfully and were stopped
with timeout exit 124. Neither run produced a completed Monte Carlo result
before the bound. This establishes build/data-loading feasibility, not a
performance or decoding-quality claim. See `smoke.json` and `logs/*_smoke.log`.

## Exact pilot02 mapping and API

Use **physical coordinates directly**, retaining the existing mission:

1. Source check matrix `A4 = gx + 2*gz`: labels are I=0, X=1, Z=2, Y=3.
2. Source priors are `pauli_probs[:, [0,1,3,2]]`, converting task order
   `[I,X,Y,Z]` into native `[I,X,Z,Y]`. Do not factor them into marginals.
3. Input syndrome rows are unchanged. The provided physical generators already
   incorporate `frame` and `permutation`; no second frame transform is needed.
4. Native output label `q` maps to `correction_x=q&1`, `correction_z=(q>>1)&1`.

Exported the real 882-qubit, 882-check, 64-shot calibration fixture as
`case02.physical_A4.txt`, `case02.priors_IXZY.txt`, and `case02.syndromes.txt`.
Twelve random Pauli-vector checks confirm exact agreement between the native
anticommutation encoding and the task's symplectic pairing. This is a format
check, not decoder validation. Provenance is in `format_mapping.json`.

Matrix loading uses padded nonbinary alist: N M, maximum column/row weights,
column weights, row weights, then column and row `(1-based index, Pauli label)`
pairs. The native `PATH_Gs` file is a **normalizer**, not the task's gx/gz
stabilizers again. It is used by the simulation driver to score logical errors;
the decoder core below only requires A and syndrome, not hidden logical labels.

Callable C interfaces in `ADOSD/ldpcQaun`:

- `load_A_GFQ(FILE*, a_matrix_GFQ*)`, `alloc_QBPC(a_matrix_GFQ*, QBP_Ctl*)`.
- `Qbp_init20(QBP_Ctl*, GFQ_t* syndrome, a_matrix_GFQ*, double p_ch, double afp)`.
- One iteration: `Qbp_dec20(bp,A)` (parallel) or `Qbp_dec24(bp,A)` (serial).
- `initOSD(OSD*)`, `load_A_OSD(OSD*,FILE*)`, `free_OSD(OSD*)`.
- `post_decodeOSDfull(OSD*, const uint8_t* syndrome, const double** posterior,
  const uint8_t* lastFor, uint32_t max_iter)` returns Pauli labels.
- Fixed-order alternative: `post_decodeOSDw(OSD*, syndrome, posterior,lastFor)`.

### Required adapter work, not implemented here

- A batched supplied-syndrome driver: `int main(void)` currently samples its own
  errors and has no NPZ/file-argument API. Reuse allocations across shots.
- Correct compile-time N, M and K for each task code. Headers unconditionally
  define dimensions; simply adding `gcc -DN=882` is not a reliable override.
  Pauli OSD initializes `RankH=N-K` (398 / 858 for the two task codes), whereas
  the task can retain redundant check rows. Preserve M from the input and
  validate redundant-row handling; do not assume M=N-K.
- A per-qubit joint-prior initializer derived from `Qbp_init20`. At
  `bp_dec/bp_dec.c:605`, `GenInitBiasVec` only constructs homogeneous depolarizing
  or equal-rate independent X/Z channels. Lines 875–900 copy the same vector
  into every `bp->pn[n]` and initialize edge messages. Replace that channel
  initialization with the supplied four probabilities for each qubit, keeping
  the official BP updates/ADOSD logic unchanged. Account for `dqml_ori` if its
  optional compile-time feature is enabled. Merely replacing posterior values
  after BP, or passing one scalar error rate, is not equivalent.
- Preserve the official hard-decision stability history (`LastRun`), normalized
  four-component `bp->qn` posterior, and BP-convergence/OSD fallback behavior
  from `BPOSD.c:690` and `BPOSD.c:828`.

## Source configurations to start with

For pilot02 use the checked-in **GF(4)** branch, not independent binary sectors:
`Q=4`, `USE_GF2_DEC=0`, `LLR_BP=0`, `BY_DEC=20`, `MAX_ITER=100`, `AFP=160`,
`AFP2=0`, `AFPINC=0`, `RND_SCHE=0`, `OSDW=-2`, `RelThr=0.999995`, and default
`SORTCOMPARE=LASTFORSORT`. The driver passes `afp=100/160`. These are source
defaults, not a tuned optimum for pilot02. `OSDW=-1` and `OSDW=0` are useful
source-existing BP-only and order-zero controls, respectively.

The Pauli documentation mentions `ADOSDw`, but the checked-in Pauli C source
does **not** use that macro. `OSD.c:496` chooses order zero under its degeneracy
condition or uses `decideOSDW`; its reduction-failure fallback is order two.
Do not confuse GF(4) ADOSD with setting an unsupported `ADOSDw=4` parameter.
The documented AMBP schedule AFP=160, AFP2=30, AFPINC=-1 is a possible later
source-based comparison, not something validated or recommended for immediate
replacement on the current task budget.

For pilot01 the DEM branch exposes `Qbp_init20(..., double *p_ch, double afp)`,
so per-variable binary priors already exist. Encode nonzero H and logical rows
as Z-labelled alist entries and binary faults as X. Current defaults are
`OSDW=-2`, `ADOSDw=2`, `RelThr=0.99`, `MAX_ITER=10`, `AFP=150`, `LLR_BP=0`.
It still needs a supplied-syndrome driver, compile-time dimensions, and correct
rank handling (the driver hardcodes `RankH=M`). It is not a direct NPZ consumer.
Given pilot01's demonstrated robust solution, this audit does not recommend a
size/timing ratchet or claim that ADOSD improves it.

## Pinned source pointers

- Pauli initializer and channel restriction:
  https://github.com/cylai-nycu/MBP_ADOSD/blob/094149da7c6147704b544636baf6937f688d01f9/ADOSD/ldpcQaun/bp_dec/bp_dec.c#L605
- Pauli BP/ADOSD bridge:
  https://github.com/cylai-nycu/MBP_ADOSD/blob/094149da7c6147704b544636baf6937f688d01f9/ADOSD/ldpcQaun/BPOSD.c#L799
- Pauli adaptive order:
  https://github.com/cylai-nycu/MBP_ADOSD/blob/094149da7c6147704b544636baf6937f688d01f9/ADOSD/ldpcQaun/OSD/OSD.c#L496
- DEM binary sample/decoder path:
  https://github.com/cylai-nycu/MBP_ADOSD/blob/094149da7c6147704b544636baf6937f688d01f9/ADOSD_DEM/ldpcQuan/BPOSD.c#L237

Selection and any later reference replacement remain with the main agent.
No pilot public files, attempts, evaluators, or reference anchors were changed.
