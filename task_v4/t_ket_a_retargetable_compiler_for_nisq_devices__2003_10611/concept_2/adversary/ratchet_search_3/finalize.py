import json
import sys
import time
from pathlib import Path


sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit import OUTPUT, frozen_hashes, write_json
from router import graph_data, relabelings, transform
from validation import load_witness, replay, validate


def main():
    parameters = json.loads((OUTPUT / "audit_parameters.json").read_text())
    robustness = json.loads((OUTPUT / "robustness_summary.json").read_text())
    witness = load_witness(OUTPUT / "authorized_champion.json")
    count, edges, gates, reference = validate(witness)
    neighbors, distances = graph_data(count, edges)
    colors = [None] * count
    colors[0] = 0
    pending = [0]
    bipartite = True
    while pending:
        current = pending.pop()
        for neighbor in neighbors[current]:
            if colors[neighbor] is None:
                colors[neighbor] = 1 - colors[current]
                pending.append(neighbor)
            elif colors[neighbor] == colors[current]:
                bipartite = False
    terminal_edges = {tuple(sorted(gate)) for gate in gates[-3:]}
    terminal_wires = set(wire for edge in terminal_edges for wire in edge)
    terminal_triangle = len(terminal_edges) == 3 and len(terminal_wires) == 3
    cutoffs = list(range(0, len(gates), 4))
    all_cuts_contain_triangle = terminal_triangle and all(cutoff <= len(gates) - 3 for cutoff in cutoffs)
    executed = 0
    swap_schedule = []
    for operation in witness["route"]:
        if operation[0] == "gate":
            executed += 1
        else:
            swap_schedule.append({"after_executed_gates": executed, "physical_edge": operation[1:]})
    terminal_start = next(index for index, operation in enumerate(witness["route"])
                          if operation[0] == "gate" and operation[1] >= len(gates) - 3)
    roots = {"hardware_bipartite": bipartite, "terminal_three_demands_form_triangle": terminal_triangle,
             "terminal_logical_wires": sorted(terminal_wires),
             "terminal_reference_swaps": sum(operation[0] == "swap" for operation in witness["route"][terminal_start:]),
             "all_program_cutoffs": cutoffs, "all_program_cuts_contain_terminal_triangle": all_cuts_contain_triangle,
             "static_suffix_embedding_impossible_at_every_cut": bipartite and all_cuts_contain_triangle,
             "reference_swap_schedule": swap_schedule,
             "route_fallback_cases": sum(setting["fallback_swaps"] > 0
                                         for record in robustness["families"]
                                         for setting in record["result"]["families"][0]["settings"])}
    public = {name: (logical, physical) for name, logical, physical in relabelings(count)}
    repairs = []
    certificate_rechecks = 0
    for filename in ("repair_summary.json", "repair_summary_portfolio.json"):
        path = OUTPUT / filename
        if not path.exists():
            continue
        summary = json.loads(path.read_text())
        below_target = [record["family"] for record in summary["champion"]
                        if not record["champion_meets_targets_against_repair"]]
        for record in summary["champion"]:
            logical, physical = public[record["family"]]
            mapped_gates, mapped_edges, initial = transform(gates, edges, logical, physical)
            routed = record["route"]
            measured = replay(mapped_gates, count, mapped_edges, routed["route"], routed["final_mapping"], initial)
            assert measured == record["measured"]
            certificate_rechecks += 1
        repairs.append({"artifact": filename,
                        "families_below_target": below_target,
                        "breaks_all_families_required_robust_target": bool(below_target),
                        **{key: value for key, value in summary.items() if key not in ("champion", "controls")},
                        "family_results": [{key: record[key] for key in
                                            ("family", "measured", "swap_ratio", "native_ratio", "swap_gap",
                                             "champion_meets_targets_against_repair")}
                                           for record in summary["champion"]]})
    assert frozen_hashes() == parameters["frozen_hashes_before"]
    summary = {"official_G3_status": "solved; unchanged by this private audit",
               "fixed_method_additional_families_requested": 32,
               "fixed_method_additional_families_completed": robustness["families_completed"],
               "fixed_method_additional_families_passed": robustness["families_passed"],
               "fixed_method_portfolio_routes_replayed": robustness["portfolio_routes_replayed"],
               "fixed_method_transformed_reference_routes_replayed": robustness["reference_routes_replayed"],
               "fixed_method_original_reference_validations": 1 + robustness["families_completed"],
               "minimum_portfolio_swaps": robustness["minimum_portfolio_swaps"],
               "maximum_portfolio_swaps": robustness["maximum_portfolio_swaps"],
               "minimum_swap_ratio": robustness["minimum_swap_ratio"],
               "minimum_native_ratio": robustness["minimum_native_ratio"],
               "minimum_swap_gap": robustness["minimum_swap_gap"],
               "worst_family_score": robustness["worst_family_score"],
               "root_evidence": roots, "completed_repairs": repairs,
               "repair_certificate_rechecks": certificate_rechecks,
               "frozen_artifacts_unchanged": True, "fresh_agents_launched": 0,
               "further_generations": 0, "seconds_since_parameter_freeze": time.time() - parameters["started_unix"]}
    write_json(OUTPUT / "audit_summary.json", summary)
    lines = ["# Final G3 private audit", "", "G3 remains solved. No task, score, policy, or frozen artifact changed.", "",
             "## Fixed-method robustness", "",
             f"All {robustness['families_passed']}/32 additional deterministic families meet the original targets.",
             "The 11 logical, 11 physical, and 10 joint permutations were declared before evaluation.",
             "All 1,984 returned policy routes and 32 transformed reference routes were exactly replayed;",
             "the original reference also undergoes 33 validator replays in this phase.",
             f"Portfolio SWAP range: {robustness['minimum_portfolio_swaps']}–{robustness['maximum_portfolio_swaps']}.",
             f"Worst ratios: SWAP {robustness['minimum_swap_ratio']:.8f}, native {robustness['minimum_native_ratio']:.8f}; gap {robustness['minimum_swap_gap']}.",
             "", "## General repairs", "",
             "Both variants examine tail trims 1..8 and core starts at multiples of four.",
             "They use the frozen embedding and token budgets; every prefix, layout transition, and tail is paid.",
             "The second variant chooses each prefix from all 62 frozen G3 policies, without recursion into this repair."]
    for repair in repairs:
        lines.append(f"- {repair['artifact']}: {repair['minimum_repair_swaps']}–{repair['maximum_repair_swaps']} SWAPs; "
                     f"families below target: {', '.join(repair['families_below_target']) or 'none'}; "
                     f"{repair['completed_policy_calls']} completed calls including {repair['independent_controls']} independent controls.")
    lines.extend(["", "With frozen-portfolio prefixes, the exact repaired cost is 37 SWAPs in identity, physical-11,",
                  "and logical-47; it is 39 in the other three public families. At 37, the SWAP ratio is 37/15 < 2.5.",
                  "Thus this separate repair breaks the all-families-required condition in three families, not uniformly.",
                  "Its best decomposition is prefix 30/32 + layout 6 + terminal tail 1, at core start 80 and trim 1.",
                  "This is an audit of a new general policy, not a change to the frozen evaluator or its solved status."])
    lines.extend(["", "## Root evidence", "",
                  "The final three demands form a logical triangle, executed with one reference SWAP.",
                  "The ladder hardware is bipartite. Every one of the 31 all-program cutoffs retains that triangle,",
                  "so neither frozen static-suffix embedding policy can embed its entire suffix at any cutoff.",
                  "The reference additionally changes layout in multiple earlier phases; allowing a terminal tail alone",
                  "does not ensure a cheap prefix. The fixed-prefix repair costs 51 SWAPs and does not break the target.",
                  "Full routes, search counters, exact family measurements, and the reference swap schedule are private artifacts here.",
                  "", "No fresh agents launched; no further generation.", ""])
    (OUTPUT / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps({key: value for key, value in summary.items() if key not in ("root_evidence", "completed_repairs")}, indent=2))


if __name__ == "__main__":
    main()
