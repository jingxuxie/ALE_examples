import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
AUTHOR = ROOT / "author"
CONCEPTS = ["weighted", "fractional", "resolved", "ewoc"]


def read(path):
    return json.loads(path.read_text())


def main():
    rows = []
    for kind in CONCEPTS:
        pilot = read(AUTHOR / "reports" / (kind + "_pilot.json"))
        pool = read(AUTHOR / "reports" / (kind + "_pilot_pool.json"))
        strong = read(AUTHOR / "reports" / (kind + "_reference_all.json"))
        run = read(AUTHOR / "runs" / (kind + "_pilot.json"))
        scale_case = next(case for case in pilot["cases"] if case["id"] == "pilot_full_sample_scale")
        if min(pilot["mean_core_score"], pilot["worst_family_score"], pool["mean_core_score"], pool["worst_family_score"]) < 0.90:
            raise RuntimeError(kind + " needs substantive counterexample/ratchet analysis; do not publish a blanket rejection")
        if strong["worst_family_score"] <= 0.90:
            raise RuntimeError(kind + " reference gate failed")
        rows.append({"concept": kind, "pilot_core_accuracy": pilot["mean_core_score"], "pilot_mean_score": pilot["mean_score"], "pilot_worst_family": pilot["worst_family_score"], "pool_core_accuracy": pool["mean_core_score"], "pool_mean_score": pool["mean_score"], "pool_worst_family": pool["worst_family_score"], "reference_mean_score": strong["mean_score"], "reference_worst_family": strong["worst_family_score"], "agent_wall_seconds": run["wall_seconds"], "agent_timed_out": run["timed_out"], "submission_exists": run["submission_exists"], "pilot_cases": len(pilot["cases"]), "pool_cases": len(pool["cases"]), "full_sample_reference_seconds": scale_case["reference_wall_seconds"], "full_sample_submission_seconds": scale_case["wall_seconds"], "full_sample_child_high_water_mib": scale_case["peak_child_rss_kb"] / 1024})
    additional = read(AUTHOR / "reports" / "ewoc_pilot_pool_pool_radius_transition.json")
    if additional["worst_family_score"] < 0.90:
        raise RuntimeError("The extra EWOC family needs analysis")
    packages = read(AUTHOR / "package_audit.json")
    ensemble = read(AUTHOR / "ensemble_validation.json")
    isolation = read(AUTHOR / "sandbox_validation.json")
    if not packages["passed"] or not ensemble["passed"] or not all(isolation.values()):
        raise RuntimeError("An integrity gate failed")
    ranking = sorted(rows, key=lambda row: (row["pilot_worst_family"], row["pilot_core_accuracy"]))
    pair = [row["concept"] for row in ranking[:2]]
    decision = {
        "status": "rejected", "accepted_task": None,
        "reason": "All four fresh agents solve their core tasks robustly, including worst families; no source-grounded substantive failure region was confirmed. None meets the required fresh score below 0.70 with a central component unsolved.",
        "pilot_model": "ultima-alpha", "pilot_effort": "xhigh", "pilot_time_limit_seconds": 3600,
        "concepts_built": 4, "fresh_attempts": 4, "ratchets_created": 0, "second_fresh_confirmation_attempts": 0,
        "initial_difficulty_ranking": [row["concept"] for row in ranking],
        "lowest_scoring_pair_reviewed": pair, "retained_for_ratchet": [],
        "confirmation_scores": None,
        "confirmation_not_run_reason": "The protocol rejects a solved concept without a meaningful counterexample; no eligible ratcheted concept existed.",
        "scores": rows,
        "supplementary_ewoc_transition": {key: additional[key] for key in ["mean_core_score", "mean_score", "worst_family_score"]},
        "supplementary_weighted_resolution_report": "author/resolution_search/report.json",
        "scope_limit": "This rejects the four tested concepts under this budget, not every possible task derived from the paper. Candidate A's adjacent fixes and the data/model-inference candidates were not separately piloted.",
    }
    (ROOT / "selection.json").write_text(json.dumps(decision, indent=2))
    table = "\n".join(f"| {row['concept']} | {row['pilot_core_accuracy']:.6f} | {row['pilot_mean_score']:.6f} | {row['pilot_worst_family']:.6f} | {row['agent_wall_seconds']/60:.2f} |" for row in rows)
    pool_table = "\n".join(f"| {row['concept']} | {row['pool_cases']} | {row['pool_core_accuracy']:.6f} | {row['pool_mean_score']:.6f} | {row['pool_worst_family']:.6f} |" for row in rows)
    reference_table = "\n".join(f"| {row['concept']} | {row['reference_mean_score']:.6f} | {row['reference_worst_family']:.6f} |" for row in rows)
    scale_table = "\n".join(f"| {row['concept']} | {row['full_sample_reference_seconds']:.2f} | {row['full_sample_submission_seconds']:.2f} | {row['full_sample_child_high_water_mib']:.1f} |" for row in rows)
    report = f"""# FastEEC frontier-hard task search — rejection report

## Decision

**No task is accepted or promoted to a production participant package.** Four
source-gap concepts were built and tested with isolated `ultima-alpha` agents.
Every submitted solution passes the core outcome robustly, including its worst
tested family. No confirmed scientific counterexample justifies a ratchet.
In particular, no task meets the required fresh-agent score below 0.70 with a
central technical component remaining unsolved.

This is a rejection of these four tested concepts, not a proof that no harder
task can ever be obtained from the paper. Complete decision data is in
`selection.json`; all pilots, attempts, references, and search evidence remain.

## Candidate directions and artifact boundaries

The full eight-direction ledger, including each starting artifact, private
artifact, outcome, shortcut, failure regime, independent bottlenecks, and check,
is `author/CANDIDATES.md`. Primary sources and pinned histories are recorded in
`author/SOURCES.md`.

| Direction | Candidate gap | Disposition |
|---|---|---|
| A: pre/post fix | Original validation-string delta is trivial; adjacent commits repair scalar normalization and a ratio-histogram constructor | Verified adjacent gaps; not a fifth pilot |
| B: follow-up | Integer-only v0.1 to v0.2 signed continuous-order projected correlators | Built `fractional` |
| C: realistic scale | Missing official weighted and kT modules at high integer order | Built `weighted` |
| D: physical transfer | Finite-radius massive subjets, pp versus spherical geometry | Built `ewoc` |
| E: real-data discrepancy | Small-nu scaling/model mismatch, fit-window and mixing uncertainty | No independently released fitting oracle verified; not built |
| F: integration | Joint three-/four-particle geometry, contacts, and nonlinear phi-local weights | Built `resolved` |
| G: ablation | Angle/pT-dependent resolution and accuracy/cost calibration | Candidate only; angle-adaptive source implementation not released |
| H: correctness/performance | Later anchor-centered projection is not the old diameter observable | Audited semantic trap; not a fifth one-kernel pilot |

The public starts contain only the original unit-weight C/A module, its reader,
its license, a local FastJet dependency, an incomplete contact-only baseline,
and three unlabeled sample jets. Later solution-bearing modules and git history
remain private. The four TASK.md missions are concise and do not name the paper.
Definitions needed for a complete task live in public interface contracts.

The resolved prototype was expanded to the later code's nonlinear-weight branch
**before its first fresh attempt**. This is not counted as a ratchet or a second
concept. No production task was constructed before the pilot tournament.

## Fresh-agent tournament

All four use the supplied allowlist runner, model `ultima-alpha`, xhigh effort,
a fresh empty attempt directory, a read-only participant directory, and a
one-hour wall limit. They cannot access another attempt or the author/private
tree. Full launch records and transcripts are under `author/runs/`.

| Concept | Mean core accuracy | Mean accuracy × runtime | Worst family | Agent minutes |
|---|---:|---:|---:|---:|
{table}

Each pilot includes ordinary, high-multiplicity, sparse, and momentum/azimuth
shifted cases, plus a complete 100,000-jet throughput case. Family reporting also
separates technical branches and their intersections with data strata. A failed
central branch is not averaged away. Original sources and all submitted programs
are retained for inspecting completeness rather than inferring it from a score.

The initial lowest-scoring pair reviewed for retention is **{pair[0]} and
{pair[1]}**, ordered first by worst-family score and then by mean core accuracy.
Neither qualifies as a hard survivor. The other solved controls also receive
challenge-pool checks rather than being discarded merely by prediction.

## Counterexample search

| Concept | Pool cases | Mean core accuracy | Mean accuracy × runtime | Worst family |
|---|---:|---:|---:|---:|
{pool_table}

Searches and root-cause conclusions:

- **Weighted:** twenty supplementary single-query probes examine near-exact
  low-order CA/kT evaluation, genuine high-multiplicity CMS jets, and finer
  angular axes. All completed numerical comparisons agree at roundoff.
  The hardest observed eight-jet N=3 case has overlapping reference and
  submission timing ranges, not a confirmed inefficiency region. N=4 coverage
  in this bounded supplementary search is partial. See
  `author/resolution_search/report.json`; no extrapolated timeout is invented.
- **Fractional:** real-data pools cover subunit and superunit orders, integer
  collapse, odd caps, rare multiplicities, and transformed frames. The exact
  clique/intersection construction remains accurate. No cancellation or
  cap-bookkeeping failure is found.
- **Resolved:** the pool additionally changes the azimuth partition and
  nonlinear exponents in mixed requests. This changes the phi-local statistic,
  not merely its presentation, and cannot be repaired by rebinning a fixed
  public histogram. Its results are included in the table.
- **EWOC:** an additional radius-transition case exercises all six supported
  geometry/algorithm combinations, from nearly resolved constituents to massive
  diagonal contacts. Core accuracy is {additional['mean_core_score']:.6f} and
  worst-family score is {additional['worst_family_score']:.6f}; see
  `author/reports/ewoc_pilot_pool_pool_radius_transition.json`.

There is therefore **no substantive failure cluster to focus on**. Observed
roundoff, startup effects, and overlapping short-run timing ranges are not
scientific counterexamples. No random edge cases, extra rows, stricter accuracy
thresholds, or out-of-contract input regime is used to manufacture hardness.

## Universal shortcuts actually discovered

- The weighted agent evaluates ordered moments using clique generating
  functions, true-twin compression, complete-graph sums, complement components,
  and memoized recursion, reusing geometry and moments across queries.
- The fractional agent sums signed subset weights through maximal cliques and
  their intersections. A clique's cross-child weight is a difference of three
  powers; collected intersection coefficients give the entire diameter-bin
  cumulative. This is exact for the specified capped observable and avoids the
  later reference's cardinality-expanded subset implementation.
- The resolved solution integrates ordered geometry, contact conventions, and
  conditional finite differences into a cached numerical engine. The actual
  code and final claims are retained in its attempt rather than assuming that
  a projected marginal determines a joint distribution.
- The EWOC solution uses the provided standard clustering primitives followed
  by exact ordered-pair accumulation. That generic integration handles every
  tested physical branch.

The pre-build anti-compression ledger admitted scale plus multiple independent
components. These experiments show that admission was insufficient to establish
frontier hardness: the fresh agents compress or integrate those components
successfully. A private solution gap alone is not evidence of a hard task.

## Realistic scale and private-reference checks

The complete release asset contains **100,000 jets, 4,330,905 constituents**, a
median multiplicity of **41**, and a maximum of **139**. Constituents are not
truncated. The full-asset case is explicitly a throughput test, not independent
heldout generalization; it overlaps the statistical strata. Public sample IDs,
pool IDs, and reserved heldout stratum IDs are recorded in manifests.

| Complete 100,000-jet case | Reference seconds | Submission seconds | Child high-water MiB |
|---|---:|---:|---:|
{scale_table}

The full-asset queries are explicitly: weighted N=7, kappa=2, CA f=8;
fractional nu=0.35 with cap 8; linear resolved order 3; and pp anti-kT mass
EWOC with radius 0.15. Higher fractional caps and joint order 4 are evaluated
on separate untruncated, multiplicity-stratified ensembles, not claimed to
have been run over the complete asset. Their source multiplicities and query
counts are in each private manifest. Memory is the conservative child
high-water diagnostic described in `author/INFRASTRUCTURE.md`.

On the actual 139-constituent jet 7165, exact N=7 multiset enumeration requires
230,826,830,520 multisets and does not finish within the measured 15-second run.
The official finite-resolution f8 computation finishes in approximately 0.128
seconds, but **it is an approximation, not the same exact full-particle target**.
Naive dense fractional full-jet subset storage would need 2^142 bytes. This
demonstrates source-contribution scale, not failure of the submitted graph
solvers. See `author/direct_scale.json`.

| Stored-reference replay | Mean score | Worst family |
|---|---:|---:|
{reference_table}

Replay is not offered as independent proof of correctness. Separate checks are:

- Projectors: 392 actual runs and 1,829 checks; maximum small-fixture absolute
  error 3.07e-15, using independent ordered tuples and subset inclusion-exclusion.
- Resolved: 78 baseline plus 390 weighted checks, including 312 non-unit cases;
  maximum cell error 1.11e-15.
- EWOC: 135 checks, including 24 independent seeded comparisons; maximum
  absolute bin error 2.78e-16.
- Actual stored ensembles: {ensemble['checks']} independent identity/positivity
  checks pass; maximum relative identity error
  {ensemble['max_relative_identity_error']:.3g}.
- Public-snapshot, missing-solution-module, and actual sandbox denial checks pass.

The fractional target is the declared finite-resolution compatibility measure,
not an exact uncompressed jet correlator. Non-unit resolved weights reproduce
the source's binned statistic and are not claimed to be a normalized analytic
continuation. Spherical jobs are declared kinematic reinterpretations, not newly
acquired ee data. No detector-unfolded truth or unpublished fitting code is
invented.

## Ratchets and final confirmation

**Ratchets: zero. Second fresh confirmation attempts: zero. Confirmation scores:
not applicable.** The protocol requires rejecting a solved concept when no
meaningful counterexample is found. There is consequently no eligible ratcheted
concept to send to a second fresh agent. An unchanged replay is not mislabeled
as a second-model test, and a new task is not invented after the four-concept cap.

The reference and public-completeness gates pass, but the decisive fresh-failure
and unsolved-central-component gates fail for every concept. No task is retained.

## Reproduction and audit locations

- Candidate and provenance ledgers: `author/CANDIDATES.md`, `author/SOURCES.md`.
- Complete minimal pilots: `pilots/<concept>/participant`, `private`, `attempt`.
- Launches and immutable public hashes: `author/runs/` and `author/package_audit.json`.
- Numerical scores and per-case errors/timing: `author/reports/`.
- Reference construction: `author/build_pilots.py`, `author/build_scale.py`,
  `author/extend_resolved.py`, `author/expand_pool.py`.
- Independent validators: `author/validate_projectors.py`,
  `author/validate_resolved.py`, `author/validate_ewoc.py`,
  `author/validate_ensembles.py`.
- Isolation, setup-time correction, numerical-meter correction, and probe
  version-drift details: `author/INFRASTRUCTURE.md`.

Example reevaluation from this task root:

```sh
python author/evaluate_attempt.py --kind fractional --split pool
```

The evaluator requires Linux bubblewrap/user namespaces and the supplied Python
environment. It compares against stored private outputs; it does not recompute
expensive physical references during participant grading.
"""
    (ROOT / "REPORT.md").write_text(report)
    (ROOT / "README.md").write_text("# Search completed: no task accepted\n\nAll four fresh-agent pilots solve their tested source gaps robustly. No qualifying counterexample or ratchet remains.\n\nSee `REPORT.md` for the full experiment and `selection.json` for the machine-readable rejection. `pilots/` contains research prototypes, not accepted frontier-hard tasks.\n")
    print(json.dumps({"status": decision["status"], "ranking": decision["initial_difficulty_ranking"], "reviewed_pair": pair, "report": str(ROOT / "REPORT.md")}, indent=2))


if __name__ == "__main__":
    main()
