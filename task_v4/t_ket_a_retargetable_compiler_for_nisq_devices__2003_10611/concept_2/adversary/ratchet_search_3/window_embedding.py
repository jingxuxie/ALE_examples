from embedding import embeddings, token_plan
from router import graph_data, route, settings as frozen_settings
from validation import replay


def window_route(gates, count, edges, initial, prefix_portfolio=False):
    setting = {"name": "window-prefix-tail", "horizon": 16, "decay": 0.9,
               "tie": "ascending", "mode": "weighted"}
    best = route(gates, count, edges, initial, setting)
    measured = replay(gates, count, edges, best["route"], best["final_mapping"], initial)
    assert measured["swaps"] == best["swaps"]
    statistics = {"baseline_routes_replayed": 1, "prefix_routes": 0,
                  "prefix_setting_routes_replayed": 0, "degree_bound_prunes": 0,
                  "window_pairs_considered": 0, "prefix_bound_prunes": 0,
                  "embedding_searches": 0, "candidate_layouts": 0,
                  "distance_bound_prunes": 0, "token_plans": 0,
                  "plan_bound_prunes": 0, "tail_routes": 0,
                  "assembled_routes_replayed": 0, "improvements": []}
    neighbors, distances = graph_data(count, edges)
    prefixes = {}
    for trim in range(1, min(8, len(gates) - 1) + 1):
        end = len(gates) - trim
        for cutoff in range(0, end, 4):
            statistics["window_pairs_considered"] += 1
            logical_neighbors = [set() for _ in range(count)]
            for first, second in gates[cutoff:end]:
                logical_neighbors[first].add(second)
                logical_neighbors[second].add(first)
            if max(map(len, logical_neighbors)) > max(map(len, neighbors)):
                statistics["degree_bound_prunes"] += 1
                continue
            if cutoff not in prefixes:
                variants = frozen_settings() if prefix_portfolio else [setting]
                routed_prefixes = []
                for variant in variants:
                    candidate = route(gates[:cutoff], count, edges, initial, variant)
                    measured = replay(gates[:cutoff], count, edges, candidate["route"],
                                      candidate["final_mapping"], initial)
                    assert measured["swaps"] == candidate["swaps"]
                    statistics["prefix_setting_routes_replayed"] += 1
                    candidate["prefix_setting"] = variant["name"]
                    routed_prefixes.append(candidate)
                prefixes[cutoff] = min(routed_prefixes, key=lambda candidate: candidate["swaps"])
                statistics["prefix_routes"] += 1
            prefix = prefixes[cutoff]
            if prefix["swaps"] >= best["swaps"]:
                statistics["prefix_bound_prunes"] += 1
                continue
            statistics["embedding_searches"] += 1
            candidates = embeddings(gates[cutoff:end], count, neighbors, distances, prefix["final_mapping"])
            statistics["candidate_layouts"] += len(candidates)
            for target in candidates:
                hop_sum = sum(distances[prefix["final_mapping"][wire]][target[wire]] for wire in range(count))
                if prefix["swaps"] + (hop_sum + 1) // 2 >= best["swaps"]:
                    statistics["distance_bound_prunes"] += 1
                    continue
                planned = token_plan(prefix["final_mapping"], target, neighbors, distances, edges)
                statistics["token_plans"] += 1
                if prefix["swaps"] + len(planned) >= best["swaps"]:
                    statistics["plan_bound_prunes"] += 1
                    continue
                tail = route(gates[end:], count, edges, target, setting)
                statistics["tail_routes"] += 1
                operations = prefix["route"] + [["swap", first, second] for first, second in planned]
                operations += [["gate", index, target[gates[index][0]], target[gates[index][1]]]
                               for index in range(cutoff, end)]
                for operation in tail["route"]:
                    if operation[0] == "gate":
                        operations.append(["gate", operation[1] + end, operation[2], operation[3]])
                    else:
                        operations.append(operation[:])
                measured = replay(gates, count, edges, operations, tail["final_mapping"], initial)
                statistics["assembled_routes_replayed"] += 1
                swaps = prefix["swaps"] + len(planned) + tail["swaps"]
                assert measured["swaps"] == swaps
                if swaps >= best["swaps"]:
                    continue
                detail = {"cutoff": cutoff, "tail_trim": trim, "prefix_swaps": prefix["swaps"],
                          "prefix_setting": prefix["prefix_setting"],
                          "layout_swaps": len(planned), "tail_swaps": tail["swaps"], "swaps": swaps}
                statistics["improvements"].append(detail)
                best = {"swaps": swaps, "native_2q": len(gates) + 3 * swaps,
                        "route": operations, "final_mapping": tail["final_mapping"],
                        "fallback_swaps": prefix["fallback_swaps"] + tail["fallback_swaps"],
                        "window": detail}
    best["search_statistics"] = statistics
    return best
