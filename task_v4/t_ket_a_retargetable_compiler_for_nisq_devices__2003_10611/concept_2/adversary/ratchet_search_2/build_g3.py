import hashlib
import json
import subprocess
from pathlib import Path


OUTPUT = Path(__file__).resolve().parent
CONCEPT = OUTPUT.parents[1]
SOURCE = CONCEPT / "adversary/generation_2"
DESTINATION = CONCEPT / "adversary/generation_3"


ALL_PROGRAM = '''


def suffix_route_all(gates, count, edges, initial, prune=True):
    setting = {"name": "embedding-prefix", "horizon": 16, "decay": 0.9,
               "tie": "ascending", "mode": "weighted"}
    best = route(gates, count, edges, initial, setting)
    neighbors, distances = graph_data(count, edges)
    for cutoff in range(0, len(gates), 4):
        prefix = route(gates[:cutoff], count, edges, initial, setting)
        if prune and prefix["swaps"] >= best["swaps"]:
            continue
        candidates = embeddings(gates[cutoff:], count, neighbors, distances, prefix["final_mapping"])
        for target in candidates:
            hop_sum = sum(distances[prefix["final_mapping"][wire]][target[wire]] for wire in range(count))
            if prune and prefix["swaps"] + (hop_sum + 1) // 2 >= best["swaps"]:
                continue
            planned = token_plan(prefix["final_mapping"], target, neighbors, distances, edges)
            swaps = prefix["swaps"] + len(planned)
            if swaps >= best["swaps"]:
                continue
            operations = prefix["route"] + [["swap", first, second] for first, second in planned]
            operations += [["gate", index, target[gates[index][0]], target[gates[index][1]]]
                           for index in range(cutoff, len(gates))]
            best = {"swaps": swaps, "native_2q": len(gates) + 3 * swaps, "route": operations,
                    "final_mapping": target, "fallback_swaps": prefix["fallback_swaps"],
                    "embedding_cutoff": cutoff}
    return best
'''


FORMAT_TAIL = '''## Robustness, costs, and scores

The 62 policies returned by `router.settings()` are fixed and public:

- Original 18: 16 weighted settings with horizons 2/4/8/16, factors 0.5/0.9,
  ascending/seeded ties; two horizon-8 lexicographic settings with ascending/descending ties.
- Six long-horizon weighted settings: `(horizon,factor)` is `(64,0.97)`,
  `(200,0.97)`, or `(200,1.0)`, each with ascending/seeded ties.
- The retained suffix-embedding policy examines cuts `(0,4,8,12,16,24)` below the gate count.
- 36 future-emphasis weighted settings: horizons `(4,8,16,32,64,200)` crossed
  with factors `(1.1,1.5,2.0)` and ties `(ascending,seeded)`.
- One all-program suffix-embedding policy examines `range(0,len(gates),4)`.

The source field `decay` is the geometric factor. Values above one emphasize
more distant future layers; they are not decaying weights. Seeded edge ordering
uses Python `random.Random(1729)`. The six relabelings are exactly
`router.relabelings(16)`: identity, physical-11, physical-29, logical-47,
joint-71, and joint-103. All 62 policies run in each family, for 372 portfolio
routes per valid witness. The minimum-cost policy wins independently in each family.

A relabeling consistently changes hardware edges, logical demands, initial
placement, reference operations, and final placement. It never grants optimized
initial placement. Every reference and every portfolio route is independently replayed.

### Public embedding bounds

Both embedding policies use the same helpers and pay for all physical transitions.
The prefix and incumbent routes use weighted horizon 16, factor 0.9, ascending ties.
Each suffix embedding search permits at most 12,000 recursive visits and stops
after 16 complete embeddings; it orders the found embeddings by total initial-to-target
hop distance and returns at most four. The source specifies deterministic degree,
already-mapped-neighbor, displacement, and node-ID ordering.

Each mapping transition obtains a legal spanning-tree token plan and then runs a
bounded token search of at most 2,500 expanded states, using priority
`cost+0.75*sumHopDistances`. Tree roots are the distinct values among node 0,
node 15, and the lowest-ID maximum-degree node. The exact tree construction,
leaf ordering, candidate edges, and token-search branch bounds are in `embedding.py`.
These are fixed computational limits, not hidden data or submitted costs.

Only the new all-program policy adds two safe cuts: skip a boundary if its prefix
SWAP count already meets/exceeds the incumbent; skip a mapping if
`prefix_swaps+ceil(sumHopDistances/2)` meets/exceeds the incumbent. One SWAP can
reduce the total token distance by at most two, so neither cut removes an improving
route. The old suffix policy, its boundaries, and its bounds remain unchanged.

### Scores

Let `W` be reference SWAPs, `P` a family's minimum portfolio SWAPs, and `G` the
demand count. Define `R=P/W`, `N=(G+3*P)/(G+3*W)`, and `D=P-W`.
Its score is `max(0,min(1,(R-1)/1.5,(N-1)/0.35,D/16))`.
`core_score` is the mean family score. `worst_family_score` and `resource_score`
are the minimum. `valid` means all format, regularity, and route checks passed.
`passed` additionally requires `R>=2.5`, `N>=1.35`, and `D>=16` in every family.
Invalid submissions have zero scores. The checker reports counts, ratios, and
the winning setting; it never accepts a claimed cost.

Evaluator CLI: `python -I -B evaluator/evaluate.py --solution-dir SOLUTION_DIR`.
Optional `--output-dir DIR` also writes `DIR/result.json`.
Python API: `evaluate(solution_dir, output_dir=None) -> dict`.
'''


TASK = '''# A robust routing-portfolio counterexample

Construct a regular 16-qubit circuit and an explicitly feasible cheaper SWAP route
that demonstrates substantial resource regret in the supplied routing portfolio.
This is verification mode B: a counterexample to this specified implementation,
not an approximation-theorem claim or a claim about current tket.

## Assets and interface

The read-only `input/` directory supplies the complete 62-policy router, public
checker, exact format, and method description. `baseline/witness.json` is a valid
weak example. Python's standard library is sufficient. Use only your separate
writable output directory for work and submit its static `witness.json`.
No submission code is evaluated. The authoring limit is one hour.

## Constraints

Choose a supplied sparse hardware graph. Initial placement is fixed to identity.
Use 48–200 two-qubit demands with connected interactions and moderate per-wire
coverage. Your route must execute every gate exactly once, preserve every per-wire
dependency, respect physical adjacency, and account for every SWAP. Exact schema,
regularity limits, public policy bounds, and checker commands are in `input/FORMAT.md`.

## Scoring

The checker executes all 62 policies under all six public relabelings, choosing
the cheapest policy separately in each family. Pass only if every family's
portfolio cost is at least **2.5 times your SWAP count**, at least **16 additional
SWAPs**, and at least **1.35 times your total native two-qubit count**.
Each demand costs one native two-qubit operation; a SWAP costs three.
Valid but insufficient witnesses receive partial scores, not a pass.
'''


METHOD = '''# Supplied method and scope

Primary sources:

- Sivarajah et al., *t|ket>: A Retargetable Compiler for NISQ Devices*,
  arXiv:2003.10611v3, section 7, especially 7.2.
  https://arxiv.org/html/2003.10611v3#S7.SS2
- Cowtan et al., *On the qubit routing problem*, arXiv:1902.08091v2,
  section III.3 and Appendix A. This routing paper predates the compiler paper.
  https://arxiv.org/html/1902.08091v2#S3.SS3

The papers motivate dynamic distance-based routing, finite lookahead, and
shortest-path progress. They do not establish the approximation guarantee being
falsified here. The benchmark is a transparent SWAP-only adaptation and portfolio
extension, not a bit-for-bit implementation of either paper or current tket.

## Distance-based policies

Drain all ready adjacent gates using the true per-wire dependency DAG. Build
future layers after deleting executed gates. Consider hardware edges incident to
ready-gate operands, score each resulting placement by average excess graph
distance in each layer, and combine those values geometrically or lexicographically.
Resolve ties by the specified edge ordering. Do not revisit a placement without
executing a gate. After 32 nonexecuting SWAPs, or when no unvisited candidate remains,
shortest-path route a closest ready pair and execute it. This guarantees progress.

In addition to the retained local and long-horizon settings, future-emphasis
settings use positive factors greater than one. They prioritize deeper layers
rather than discounting them. The exact 62-setting list, seeded ties, all six
relabelings, and all numeric limits are public in `FORMAT.md` and source.

## Embedding policies

Route a prefix using the fixed horizon-16/factor-0.9/ascending setting. Seek a
bounded hardware embedding of the remaining interaction graph. Physically route
tokens from the resulting prefix placement to that embedding, accounting for
every adjacent SWAP, and then execute the suffix natively. Keep the cheapest
complete feasible route found, including the ordinary routing incumbent.

The retained policy uses six early cuts. The added policy examines every fourth
gate boundary throughout the entire circuit, so its boundary range scales with
the supplied circuit rather than ending at a fixed prefix position. Both policies
use identical embedding and token-planning routines. Search visits, returned
embeddings, token expansions, and spanning-tree construction are explicitly
bounded and documented in `FORMAT.md` and `embedding.py`.

The new policy skips only candidates already unable to beat its incumbent:
prefix cost alone, or prefix cost plus the admissible half-total-hop-distance
lower bound. These are efficiency cuts, not instance-specific restrictions.

## Interpretation

The methods receive only demands, hardware, initial placement, and public settings;
they cannot read a submitted reference route or a private case library. Both sides
have the same fixed initial placement, SWAP-only operations, and free final
permutation. There is no free initial remapping. Initial-placement optimization,
CX bridges, algebraic circuit simplification, and native-gate cleanup remain out
of scope. The cheapest policy wins in each family, so retaining the older settings
prevents the enlarged portfolio from worsening its cost on any input.
'''


def main():
    evidence = json.loads((OUTPUT / "probe_results.json").read_text())
    assert evidence["repair_confirmed"], "do not build speculative G3"
    assert not DESTINATION.exists(), "G3 must not be overwritten after creation"
    files = {}
    for relative in ("participant/input/router.py", "participant/input/embedding.py",
                     "participant/input/validation.py", "participant/input/benchmark.py",
                     "participant/baseline/generate.py", "participant/baseline/witness.json",
                     "participant/workspace/README.md", "evaluator/evaluate.py"):
        files[relative] = (SOURCE / relative).read_text()
    router_text = files["participant/input/router.py"]
    addition = '''    for horizon in (4, 8, 16, 32, 64, 200):
        for weight in (1.1, 1.5, 2.0):
            for tie in ("ascending", "seeded"):
                variants.append({"name": f"future-{horizon}-{weight}-{tie}", "horizon": horizon,
                                 "decay": weight, "tie": tie, "mode": "weighted"})
    variants.append({"name": "suffix-embedding-all-program", "horizon": 0, "decay": 1.0,
                     "tie": "ascending", "mode": "embedding-all-program"})
'''
    router_text = router_text.replace("    return variants\n", addition + "    return variants\n", 1)
    dispatch = '''    if setting["mode"] == "embedding-all-program":
        from embedding import suffix_route_all
        return suffix_route_all(gates, count, edges, initial)
'''
    marker = "    neighbors, distances = graph_data(count, edges)\n"
    router_text = router_text.replace(marker, dispatch + marker, 1)
    files["participant/input/router.py"] = router_text
    files["participant/input/embedding.py"] += ALL_PROGRAM
    files["participant/input/FORMAT.md"] = (SOURCE / "participant/input/FORMAT.md").read_text().split(
        "## Robustness, costs, and scores")[0] + FORMAT_TAIL
    files["participant/input/METHOD.md"] = METHOD
    files["participant/TASK.md"] = TASK
    original_test = (CONCEPT / "evaluator/hidden/test_validation.py").read_text()
    files["evaluator/hidden/test_validation.py"] = original_test.replace(
        'len(family["settings"]) == 18', 'len(family["settings"]) == 62').replace(
        "all 108 portfolio runs replayed", "all 372 portfolio runs replayed")
    files["evaluator/hidden/README.md"] = "Author-only validation and freeze evidence. Never expose this directory to participants.\n"
    files["attempts/README.md"] = "Reserved for main's final-generation fresh launch. No worker launches are permitted.\n"
    files["champions/README.md"] = "Reserved for independently checked generation-three champions.\n"
    files["adversary/README.md"] = "Private author validation, regression, and freeze evidence. Not participant assets.\n"
    files["status.json"] = json.dumps({"generation": 3, "final_generation": True,
        "maximum_generations": 3, "verification_mode": "B_COUNTEREXAMPLE",
        "status": "validating", "launch_ready": False, "date": "2026-08-28",
        "portfolio_settings": 62, "relabeling_families": 6, "policies_retained": 25,
        "policies_added": 37, "target": {"swap_ratio": 2.5, "native_ratio": 1.35, "swap_gap": 16},
        "schema_changed": False, "baseline_changed": False, "fresh_agents_launched": 0,
        "fresh_agent_owner": "main", "repair_confirmed_before_build": True,
        "participant_access": "read_only", "submission": "OUTPUT_DIR/witness.json"}, indent=2) + "\n"
    patch = ["*** Begin Patch"]
    for relative, content in files.items():
        destination = DESTINATION / relative
        patch.append(f"*** Add File: {destination.relative_to(CONCEPT)}")
        patch.extend("+" + line for line in content.splitlines())
    patch.append("*** End Patch")
    subprocess.run(["apply_patch", "\n".join(patch) + "\n"], cwd=CONCEPT, check=True)
    provenance = {"source_generation": 2, "destination_generation": 3,
                  "source_hashes": {relative: hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest()
                                    for relative in ("participant/input/router.py", "participant/input/embedding.py",
                                        "participant/input/validation.py", "participant/input/benchmark.py",
                                        "participant/baseline/witness.json", "evaluator/evaluate.py")},
                  "copied_public_assets_only": True, "private_raw_submissions_exposed": False}
    (OUTPUT / "build_provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({"built": str(DESTINATION.relative_to(CONCEPT)), "files": len(files)}))


if __name__ == "__main__":
    main()
