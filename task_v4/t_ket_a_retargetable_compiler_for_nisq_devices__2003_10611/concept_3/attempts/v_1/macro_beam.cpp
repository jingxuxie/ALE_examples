#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <unordered_map>

struct MacroEntry { State state; double score; };

int main(int argc, char** argv) {
    int chosen = argc > 1 ? std::stoi(argv[1]) : 2;
    int width = argc > 2 ? std::stoi(argv[2]) : 256;
    int seconds = argc > 3 ? std::stoi(argv[3]) : 600;
    random_engine.seed(argc > 4 ? std::stoull(argv[4]) : 1752);
    std::string prefix = argc > 5 ? argv[5] : "macro_";
    bool compact_mode = argc > 6 ? std::stoi(argv[6]) : false;
    remote_enabled = argc > 7 ? std::stoi(argv[7]) : false;
    bool joint_mode = argc > 8 ? std::stoi(argv[8]) : false;
    std::ifstream input("instances.txt");
    int case_count;
    input >> case_count;
    for (int case_index = 0; case_index < case_count; ++case_index) {
        Case instance;
        input >> instance.name >> instance.size >> instance.edge_count >> instance.parity_count >> instance.count_budget >> instance.depth_budget;
        instance.edges.resize(instance.edge_count);
        instance.targets.resize(instance.size);
        instance.parities.resize(instance.parity_count);
        for (auto& edge : instance.edges) input >> edge.first >> edge.second;
        for (auto& mask : instance.targets) input >> mask;
        for (auto& mask : instance.parities) input >> mask;
        if (case_index != chosen) continue;
        instance.prepare();
        auto start = std::chrono::steady_clock::now();
        double record = 1e100;
        int count_record = 100000;
        for (int attempt = 0; std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds; ++attempt) {
            phase_bonus = 0.5 + 4.0 * uniform();
            matrix_weight = 0.2 + 0.8 * uniform();
            steiner_weight = 0.5 + 0.5 * uniform();
            double parity_weight = 0.4 + uniform(), root_weight = 0.2 + uniform(), depth_weight = 0.4 + 3.0 * uniform();
            double gate_weight = 0.5 + uniform();
            if (compact_mode) { depth_weight = 0.02 + 0.4 * uniform(); gate_weight = 1.0 + 1.5 * uniform(); }
            int slack = uniform() < 0.5 ? 0 : 1;
            std::vector<MacroEntry> beam{{initial(instance), 0}};
            std::unordered_map<uint64_t, double> closed;
            for (int step = 0; step < (joint_mode ? 3 * (instance.parity_count + instance.size) : instance.parity_count); ++step) {
                std::vector<MacroEntry> candidates;
                std::unordered_map<uint64_t, int> indexes;
                for (const auto& parent : beam) {
                    if (!parent.state.remaining) {
                        for (int repeat = 0; repeat < 3; ++repeat) {
                            State state = parent.state;
                            complete_linear(state, instance, root_weight, depth_weight);
                            auto gates = normalize(instance, circuit(state));
                            double score = objective(instance, gates);
                            if (int(gates.size()) < count_record) {
                                count_record = gates.size();
                                save(instance, gates, prefix + "compact_");
                                std::cout << "COMPACT " << instance.name << " count " << gates.size() << " depth " << get_depth(gates, instance.size) << std::endl;
                            }
                            if (score < record) {
                                record = score;
                                save(instance, gates, prefix);
                                std::cout << instance.name << " attempt " << attempt << " step " << step << " count " << gates.size() << " depth " << get_depth(gates, instance.size) << std::endl;
                            }
                        }
                        if (!joint_mode || finished(parent.state, instance)) continue;
                    }
                    int minimum = 100;
                    for (uint64_t pending = parent.state.remaining; pending; pending &= pending - 1) {
                        int index = __builtin_ctzll(pending);
                        minimum = std::min({minimum, int(instance.cost[parent.state.forward_parities[index]]), int(instance.cost[parent.state.backward_parities[index]])});
                    }
                    if (joint_mode)
                        for (int side = 0; side < 2; ++side)
                            for (int root = 0; root < instance.size; ++root) {
                                Mask support = side ? parent.state.inverse[root] : parent.state.matrix[root];
                                if (support == (1u << root)) continue;
                                int cost = 2 * instance.steiner[support | (1u << root)] - weight(support) - 1;
                                minimum = std::min(minimum, cost);
                            }
                    for (uint64_t pending = parent.state.remaining; pending; pending &= pending - 1) {
                        int index = __builtin_ctzll(pending);
                        for (int side = 0; side < 2; ++side) {
                            Mask support = side ? parent.state.backward_parities[index] : parent.state.forward_parities[index];
                            if (instance.cost[support] > minimum + slack) continue;
                            for (int root = 0; root < instance.size; ++root) {
                                if (!(support & (1u << root))) continue;
                                MacroEntry candidate = parent;
                                gather(candidate.state, instance, support, parity_tree(instance, support, root), side);
                                candidate.score = evaluate(candidate.state, instance, parity_weight, root_weight) + depth_weight * depth_cost(candidate.state, instance)
                                    + gate_weight * (candidate.state.front.size() + candidate.state.back.size());
                                uint64_t hash = fingerprint(candidate.state, instance);
                                auto previous = closed.find(hash);
                                if (previous != closed.end() && previous->second <= candidate.score + 1e-8) continue;
                                auto found = indexes.find(hash);
                                if (found == indexes.end()) {
                                    indexes[hash] = candidates.size();
                                    candidates.push_back(std::move(candidate));
                                } else if (candidate.score < candidates[found->second].score) candidates[found->second] = std::move(candidate);
                            }
                        }
                    }
                    if (joint_mode) {
                        for (int side = 0; side < 2; ++side)
                            for (int root = 0; root < instance.size; ++root) {
                                Mask support = side ? parent.state.inverse[root] : parent.state.matrix[root];
                                if (support == (1u << root)) continue;
                                int cost = 2 * instance.steiner[support | (1u << root)] - weight(support) - 1;
                                if (cost > minimum + slack + 1) continue;
                                MacroEntry candidate = parent;
                                gather(candidate.state, instance, support, parity_tree(instance, support, root, true), side);
                                candidate.score = evaluate(candidate.state, instance, parity_weight, root_weight) + depth_weight * depth_cost(candidate.state, instance)
                                    + gate_weight * (candidate.state.front.size() + candidate.state.back.size());
                                uint64_t hash = fingerprint(candidate.state, instance);
                                auto previous = closed.find(hash);
                                if (previous != closed.end() && previous->second <= candidate.score + 1e-8) continue;
                                auto found = indexes.find(hash);
                                if (found == indexes.end()) { indexes[hash] = candidates.size(); candidates.push_back(std::move(candidate)); }
                                else if (candidate.score < candidates[found->second].score) candidates[found->second] = std::move(candidate);
                            }
                    }
                }
                if (candidates.empty()) break;
                int keep = std::min(width, int(candidates.size()));
                std::partial_sort(candidates.begin(), candidates.begin() + keep, candidates.end(), [](const auto& first, const auto& second) { return first.score < second.score; });
                candidates.resize(keep);
                beam = std::move(candidates);
                if (joint_mode) for (const auto& entry : beam) closed[fingerprint(entry.state, instance)] = entry.score;
                if (step % 5 == 0) std::cout << "progress " << attempt << ' ' << step << ' ' << __builtin_popcountll(beam.front().state.remaining) << ' ' << beam.front().score << std::endl;
                if (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() > seconds) break;
            }
            for (int index = 0; index < std::min(20, int(beam.size())); ++index) {
                State state = beam[index].state;
                complete_parities(state, instance, parity_weight, root_weight, depth_weight);
                complete_linear(state, instance, root_weight, depth_weight);
                auto gates = normalize(instance, circuit(state));
                double score = objective(instance, gates);
                if (int(gates.size()) < count_record) {
                    count_record = gates.size();
                    save(instance, gates, prefix + "compact_");
                    std::cout << "COMPACT " << instance.name << " count " << gates.size() << " depth " << get_depth(gates, instance.size) << std::endl;
                }
                if (score < record) {
                    record = score;
                    save(instance, gates, prefix);
                    std::cout << instance.name << " attempt " << attempt << " FINAL count " << gates.size() << " depth " << get_depth(gates, instance.size) << std::endl;
                }
            }
        }
    }
}
