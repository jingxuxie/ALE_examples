import os

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "BLIS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[variable] = "1"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time

import continue_search as engine

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


def save(name, document):
    path = HERE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")


def main():
    until = datetime.datetime.fromisoformat("2026-08-28T22:43:42+00:00")
    while datetime.datetime.now(datetime.timezone.utc) < until:
        ready = all((HERE / name).exists() and "finished_utc" in load(name) for name in ("adaptive/run.json", "two_root/run.json", "extension/run.json"))
        if ready:
            break
        time.sleep(1)
    candidates = []
    for prefix in ("best", "adaptive/best", "two_root/best", "extension/best"):
        if (HERE / prefix / "official_report.json").exists():
            candidates.append((load(prefix + "/official_report.json")["core_score"], prefix))
    unused, selected = max(candidates)
    save("final_best/witness.json", load(selected + "/witness.json"))
    official = engine.official(HERE / "final_best")
    stages = {}
    trials = []
    for prefix, state_name in (("static", "run.json"), ("adaptive", "adaptive/run.json"), ("two_root", "two_root/run.json"), ("extension", "extension/run.json")):
        if (HERE / state_name).exists():
            stages[prefix] = load(state_name)
        trial_name = "trials.json" if prefix == "static" else prefix + "/trials.json"
        if (HERE / trial_name).exists():
            trials.extend(dict(row, stage=prefix) for row in load(trial_name))
    static_jobs = list((HERE / "trials").glob("*/job.json"))
    completed_static = {row["trial_id"] for row in trials if row["stage"] == "static" and "score" in row}
    interrupted = [int(path.parent.name) for path in static_jobs if int(path.parent.name) not in completed_static]
    save("static_termination.json", {"requested_stop_utc": "2026-08-28T22:31:36+00:00", "exit_code": 130,
                                     "reason": "intentional portfolio pivot to two-root cluster construction",
                                     "completed_trials_retained": len(completed_static), "interrupted_or_unfinalized_trial_ids": sorted(interrupted),
                                     "note": "Completed witnesses and official best reports remain preserved; interrupted jobs retain their input JSON but may not retain an in-flight optimized iterate."})
    release = json.loads((engine.ROOT / "adversary/release_manifest.json").read_text())
    frozen_changes = [name for name, digest in release["sha256"].items() if hashlib.sha256((engine.ROOT / name).read_bytes()).hexdigest() != digest]
    provenance = load("source_provenance.json")
    original_changes = [name for name, row in provenance.items() if hashlib.sha256((engine.ROOT / "attempts/v_2" / Path(name).name).read_bytes()).hexdigest() != row["original_sha256"]]
    copies_exact = all(row["sha256"] == row["original_sha256"] for row in provenance.values())
    metrics = official["metrics"]
    now = datetime.datetime.now(datetime.timezone.utc)
    counted_search_start = datetime.datetime.fromtimestamp((HERE / "continue_search.py").stat().st_mtime, datetime.timezone.utc) - datetime.timedelta(seconds=5)
    completed_search_stages = [datetime.datetime.fromisoformat(stage["finished_utc"]) for stage in stages.values() if "finished_utc" in stage]
    search_upper_bound = (max(completed_search_stages) - counted_search_start).total_seconds()
    summary = {"finished_utc": now.isoformat(), "request_started_utc": "2026-08-28T22:17:32+00:00",
               "total_elapsed_seconds": (now - datetime.datetime.fromisoformat("2026-08-28T22:17:32+00:00")).total_seconds(),
               "latest_search_deadline_utc": "2026-08-28T22:43:25+00:00", "best_source": selected,
               "counted_numerical_search_start_utc": counted_search_start.isoformat(), "numerical_search_elapsed_upper_bound_seconds": search_upper_bound,
               "numerical_search_within_20_minutes": search_upper_bound <= 1200,
               "official_passed": official["passed"], "official_valid": official["valid"], "official_evaluator_valid": official["evaluator_valid"],
               "core_score": official["core_score"], "metrics": metrics, "failing_gates": official["failing_gates"],
               "attainability": "demonstrated_after_two_fresh_failures" if official["passed"] else "unknown",
               "completed_refinements": sum("score" in row for row in trials), "trial_errors": [row for row in trials if "error" in row],
               "families": sorted({row["family"] for row in trials if "family" in row}),
               "frozen_file_changes": frozen_changes, "completed_attempt_source_changes": original_changes,
               "copied_sources_byte_identical": copies_exact, "validation": load("validation.json"),
               "spec_sha256": official["spec_sha256"], "no_ongoing_attempt_reads": True,
               "limitations": "bounded non-exhaustive local search; no claim of global infeasibility or complete coverage"}
    save("stages.json", stages)
    save("summary.json", summary)
    sources = {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest() for path in HERE.rglob("*") if path.is_file() and path.suffix in (".py", ".cpp", ".so")}
    save("source_hashes.json", {"sha256": sources, "native_build": "g++ -O3 -std=c++17 -fPIC -shared copied_v2/fast.cpp -o copied_v2/fast.so", "fast_math_enabled": False})
    verdict = "A passing exact witness demonstrates attainability after the two completed fresh failures." if official["passed"] else "No passing witness was found; general attainability remains UNKNOWN."
    lines = ["# Private post-fresh generation-3 refinement", "", verdict, "",
             f"Official score: {official['core_score']:.12g}; valid: {official['valid']}; passed: {official['passed']}. The seven scientific gates and epsilon=0.01 are unchanged.",
             f"Best source: `{selected}/witness.json`. Canonical witness: `final_best/witness.json`. Official score: `final_best/official_report.json`.", "",
             "## Exact metrics", "", "| Metric | Measured | Required |", "|---|---:|---:|",
             f"| Entropy | {metrics['entropy']:.12g} | >=3 |", f"| Reverse KL | {metrics['reverse_kl']:.12g} | >=0.4 |",
             f"| Reward variance | {metrics['reward_variance']:.12g} | <=0.05 |",
             f"| Ambient gradient infinity | {metrics['gradient_infinity']:.12g} | <=0.003 |",
             f"| Energy error/spin | {metrics['energy_error_per_spin']:.12g} | <=0.02 |",
             f"| Target sector probability | {metrics['target_sector_mass']:.12g} | >=0.35 |",
             f"| Proposal sector probability | {metrics['proposal_sector_mass']:.12g} | <=0.001 |", "",
             f"Failing gates: {', '.join(official['failing_gates']) or 'none'}. Minimum conditional probability: {metrics['minimum_binary_conditional']:.12g}.", "",
             "## Search and timing", "",
             f"The task began at 22:17:32 UTC on August 28, 2026. Source review, copying, and compilation preceded numerical search. The original conservative 22:37:00 cutoff was extended only to use the remainder of the explicitly authorized 20 minutes of search; the final hard cutoff was 22:43:25 UTC. Counting from five seconds before the numerical driver was created gives a conservative search-time upper bound of {search_upper_bound:.1f} seconds (within 20 minutes: {search_upper_bound <= 1200}). Evidence finalization completed at {now.isoformat()} ({summary['total_elapsed_seconds']:.1f} seconds of total wall time, including setup and reporting).",
             f"Completed refinements retained: {summary['completed_refinements']}. The static portfolio was intentionally interrupted at 22:31:36 UTC to allocate its cores to a distinct construction; `static_termination.json` lists {len(interrupted)} unfinalized inputs rather than treating them as completed failures.",
             "The completed v2 README and final numerical checks were read before execution. Its actual native wrapper is `search.py`; no separate `fast.py` was present. Reviewed sources were copied byte-for-byte and the numerical C++ kernel rebuilt privately without fast-math.",
             "Branches: fixed-order continuation; exact weighted logistic row refits after adjacent swaps and early insertion of formerly free spins; balanced binary-bond geometry changes; best-first compositions of successful order changes; saturated-parent reassignment; fixed-weight beta profiles; and exact two-root low-energy cluster initializations followed by unrestricted coupled row refinement.",
             "The two-root construction enumerates backbone cuts whose broken-bond cost equals the free-spin field relief. Its initial phase odds include exact conditional free-spin partition factors, rather than assigning equal probabilities to disconnected modes. This is a search initialization, not an extra scientific gate or proof of feasibility.",
             "The fixed-order v2 solve reproduced the original approximately 7.6% scientific deficit. Improvements from order changes are substantive; discrepancies at the 1e-12 level are not treated as resolution of the original failed gates.", "",
             "## Validation and integrity", "",
             f"Copied-kernel checks: {summary['validation']}. All final acceptance decisions use the unmodified official full-enumeration evaluator, not the accelerated search score.",
             f"Frozen-file changes: {frozen_changes}. Completed-v2 source changes: {original_changes}. Copied sources byte-identical: {copies_exact}.",
             f"Frozen specification SHA256: `{official['spec_sha256']}`. Exact source and binary hashes are in `source_hashes.json`; original-source comparisons are in `source_provenance.json`.",
             "No ongoing attempts were read, and no earlier generation, participant, evaluator, target, fresh submission, or main-controlled status was edited. Only this disjoint private directory was written.",
             "Seeds, initial candidates, completed trial witnesses, independent reports, official record improvements, and stopping details are retained. These bounded searches do not establish global infeasibility and do not invalidate either previously solved generation.", ""]
    text = "\n".join(lines)
    path = HERE / "REPORT.md"
    patch = "*** Begin Patch\n*** Add File: " + str(path) + "\n" + "".join("+" + line + "\n" for line in text.splitlines()) + "*** End Patch\n"
    subprocess.run(["apply_patch", patch], check=True, capture_output=True, text=True)
    manifest = {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest() for path in HERE.rglob("*") if path.is_file() and path.name != "manifest.json"}
    save("manifest.json", {"sha256": manifest})
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
