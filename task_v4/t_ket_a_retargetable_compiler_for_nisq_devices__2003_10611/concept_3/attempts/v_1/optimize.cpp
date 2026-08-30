#define SEARCH_LIBRARY
#include "search.cpp"
#include <unordered_map>

bool beam_enabled = false;
bool remote_enabled = false;

struct BeamNode {
    State state;
    std::array<int, 5> moves{};
    int length = 0;
    double score = 0;
};

bool escape_beam(State& state, const Case& instance, double parity_weight, double root_weight, double depth_weight) {
    BeamNode root;
    root.state = state;
    root.state.front.clear();
    root.state.back.clear();
    double initial_value = evaluate(state, instance, parity_weight, root_weight) + depth_weight * depth_cost(state, instance);
    std::vector<BeamNode> beam{root};
    std::unordered_set<uint64_t> visited{fingerprint(state, instance)};
    int directions = instance.directed.size();
    for (int depth = 0; depth < 5; ++depth) {
        std::vector<BeamNode> next;
        for (const auto& parent : beam)
            for (int move = 0; move < 2 * directions; ++move) {
                BeamNode candidate = parent;
                apply(candidate.state, instance, move % directions, move >= directions, false);
                uint64_t hash = fingerprint(candidate.state, instance);
                if (!visited.insert(hash).second) continue;
                candidate.moves[depth] = move;
                candidate.length = depth + 1;
                candidate.score = evaluate(candidate.state, instance, parity_weight, root_weight)
                    + depth_weight * depth_cost(candidate.state, instance) + 0.08 * candidate.length;
                next.push_back(std::move(candidate));
            }
        if (next.empty()) return false;
        int width = std::min(20, int(next.size()));
        std::partial_sort(next.begin(), next.begin() + width, next.end(), [](const auto& first, const auto& second) { return first.score < second.score; });
        if (next.front().score < initial_value - 0.1) {
            for (int index = 0; index <= depth; ++index) {
                int move = next.front().moves[index];
                apply(state, instance, move % directions, move >= directions);
            }
            return true;
        }
        next.resize(width);
        beam = std::move(next);
    }
    return false;
}

bool commute(Gate first, Gate second) {
    if (first.first < 0) return second.first < 0 || first.second != second.second;
    if (second.first < 0) return first.second != second.second;
    return first.first != second.second && second.first != first.second;
}

int direction_for(const Case& instance, int control, int target) {
    for (int direction = 0; direction < int(instance.directed.size()); ++direction)
        if (instance.directed[direction] == Gate{control, target}) return direction;
    std::abort();
}

std::vector<Gate> tree_edges(const Case& instance, Mask support, int root, Mask active) {
    std::array<int, 20> parent;
    parent.fill(-1);
    std::vector<int> order{root};
    parent[root] = root;
    for (int position = 0; position < int(order.size()); ++position) {
        int vertex = order[position];
        auto neighbors = instance.adjacent[vertex];
        std::shuffle(neighbors.begin(), neighbors.end(), random_engine);
        for (int neighbor : neighbors)
            if ((active & (1u << neighbor)) && parent[neighbor] < 0) {
                parent[neighbor] = vertex;
                order.push_back(neighbor);
            }
    }
    Mask needed = support;
    std::vector<Gate> result;
    for (int position = int(order.size()) - 1; position > 0; --position) {
        int vertex = order[position];
        if (needed & (1u << vertex)) {
            result.push_back({parent[vertex], vertex});
            needed |= 1u << parent[vertex];
        }
    }
    return result;
}

std::vector<Gate> parity_tree(const Case& instance, Mask support, int root = -1, bool force_root = false) {
    Mask active = support | (force_root ? (1u << root) : 0);
    int optimum = instance.steiner[active];
    while (weight(active) < optimum) {
        std::vector<int> possible;
        for (int wire = 0; wire < instance.size; ++wire)
            if (!(active & (1u << wire)) && instance.steiner[active | (1u << wire)] == optimum) possible.push_back(wire);
        active |= 1u << possible[random_engine() % possible.size()];
    }
    if (root < 0 || !(active & (1u << root))) {
        std::vector<int> roots;
        for (int wire = 0; wire < instance.size; ++wire) if (active & (1u << wire)) roots.push_back(wire);
        root = roots[random_engine() % roots.size()];
    }
    return tree_edges(instance, support, root, active);
}

void gather(State& state, const Case& instance, Mask support, const std::vector<Gate>& tree, bool backward, bool column = false) {
    for (auto [parent, child] : tree) {
        if (!(support & (1u << parent))) {
            int control = column ? child : parent;
            int target = column ? parent : child;
            apply(state, instance, direction_for(instance, control, target), backward);
            support ^= 1u << parent;
        }
    }
    for (auto [parent, child] : tree) {
        if (support & (1u << child)) {
            int control = column ? parent : child;
            int target = column ? child : parent;
            apply(state, instance, direction_for(instance, control, target), backward);
            support ^= 1u << child;
        }
    }
}

void complete_parities(State& state, const Case& instance, double parity_weight, double root_weight, double depth_weight) {
    while (state.remaining) {
        State best;
        double best_cost = 1e100;
        int minimum = 100;
        for (uint64_t pending = state.remaining; pending; pending &= pending - 1) {
            int index = __builtin_ctzll(pending);
            minimum = std::min({minimum, int(instance.cost[state.forward_parities[index]]), int(instance.cost[state.backward_parities[index]])});
        }
        for (uint64_t pending = state.remaining; pending; pending &= pending - 1) {
            int index = __builtin_ctzll(pending);
            for (int side = 0; side < 2; ++side) {
                Mask support = side ? state.backward_parities[index] : state.forward_parities[index];
                if (instance.cost[support] > minimum + 2) continue;
                for (int repeat = 0; repeat < 3; ++repeat) {
                    State candidate = state;
                    gather(candidate, instance, support, parity_tree(instance, support), side);
                    double value = evaluate(candidate, instance, parity_weight, root_weight)
                        + depth_weight * depth_cost(candidate, instance) + 0.5 * (candidate.front.size() + candidate.back.size()) + uniform();
                    if (value < best_cost) { best_cost = value; best = candidate; }
                }
            }
        }
        state = best;
    }
}

bool noncut(const Case& instance, Mask active, int root) {
    active &= ~(1u << root);
    if (!active) return true;
    Mask reached = active & -active, frontier = reached;
    while (frontier) {
        int vertex = __builtin_ctz(frontier);
        frontier &= frontier - 1;
        for (int neighbor : instance.adjacent[vertex])
            if ((active & (1u << neighbor)) && !(reached & (1u << neighbor))) {
                reached |= 1u << neighbor;
                frontier |= 1u << neighbor;
            }
    }
    return reached == active;
}

void remote_reduce(State& state, const Case& instance, double root_weight) {
    for (int step = 0; step < instance.size * 4; ++step) {
        double original = evaluate(state, instance, 0, root_weight), record = 0.01;
        int chosen_control = -1, chosen_target = -1, chosen_side = -1;
        for (int side = 0; side < 2; ++side)
            for (int control = 0; control < instance.size; ++control)
                for (int target = 0; target < instance.size; ++target) {
                    if (control == target) continue;
                    State next = state;
                    auto& matrix = side ? next.inverse : next.matrix;
                    auto& inverse = side ? next.matrix : next.inverse;
                    for (int row = 0; row < instance.size; ++row)
                        if (matrix[row] & (1u << target)) matrix[row] ^= 1u << control;
                    inverse[target] ^= inverse[control];
                    double gain = (original - evaluate(next, instance, 0, root_weight)) / std::pow(instance.remote[control][target].size(), 0.8);
                    gain += 0.01 * uniform();
                    if (gain > record) { record = gain; chosen_control = control; chosen_target = target; chosen_side = side; }
                }
        if (chosen_control < 0) break;
        for (auto [control, target] : instance.remote[chosen_control][chosen_target])
            apply(state, instance, direction_for(instance, control, target), chosen_side);
    }
}

void complete_linear(State& state, const Case& instance, double root_weight, double depth_weight) {
    if (remote_enabled) remote_reduce(state, instance, root_weight);
    Mask active = (1u << instance.size) - 1;
    while (weight(active) > 1) {
        State best;
        double best_cost = 1e100;
        int choice = -1;
        for (int root = 0; root < instance.size; ++root) {
            if (!(active & (1u << root)) || !noncut(instance, active, root)) continue;
            State candidate = state;
            Mask support = 0;
            for (int wire = 0; wire < instance.size; ++wire)
                if (candidate.matrix[wire] & (1u << root)) support |= 1u << wire;
            gather(candidate, instance, support, tree_edges(instance, support, root, active), true, true);
            support = candidate.matrix[root];
            gather(candidate, instance, support, tree_edges(instance, support, root, active), false);
            double value = evaluate(candidate, instance, 0, root_weight)
                + depth_weight * depth_cost(candidate, instance) + 1.0 * (candidate.front.size() + candidate.back.size()) + 2.0 * uniform();
            if (value < best_cost) { best_cost = value; choice = root; best = candidate; }
        }
        state = best;
        active &= ~(1u << choice);
    }
}

std::vector<Gate> normalize(const Case& instance, const std::vector<Gate>& gates) {
    std::array<Mask, 20> rows{};
    std::unordered_map<Mask, std::vector<Gate>> occurrences;
    for (auto parity : instance.parities) occurrences[parity] = {};
    for (int wire = 0; wire < instance.size; ++wire) {
        rows[wire] = 1u << wire;
        if (occurrences.count(rows[wire])) occurrences[rows[wire]].push_back({-1, wire});
    }
    for (int index = 0; index < int(gates.size()); ++index) {
        auto gate = gates[index];
        rows[gate.second] ^= rows[gate.first];
        auto found = occurrences.find(rows[gate.second]);
        if (found != occurrences.end()) found->second.push_back({index, gate.second});
    }
    std::vector<std::vector<int>> events(gates.size() + 1);
    for (const auto& [parity, places] : occurrences) {
        if (places.empty()) std::abort();
        auto [index, wire] = places[random_engine() % places.size()];
        events[index + 1].push_back(wire);
    }
    std::vector<Gate> nodes;
    for (int wire : events[0]) nodes.push_back({-1, wire});
    for (int index = 0; index < int(gates.size()); ++index) {
        auto gate = gates[index];
        nodes.push_back(gate);
        for (int wire : events[index + 1]) nodes.push_back({-1, wire});
    }
    bool changed = true;
    while (changed) {
        changed = false;
        for (int first = 0; first < int(nodes.size()) && !changed; ++first) {
            if (nodes[first].first < 0) continue;
            for (int second = first + 1; second < int(nodes.size()); ++second) {
                if (nodes[first] == nodes[second]) {
                    nodes.erase(nodes.begin() + second);
                    nodes.erase(nodes.begin() + first);
                    changed = true;
                    break;
                }
                if (!commute(nodes[first], nodes[second])) break;
            }
        }
    }
    std::vector<std::vector<int>> successors(nodes.size());
    std::vector<int> degree(nodes.size()), critical(nodes.size());
    for (int first = 0; first < int(nodes.size()); ++first)
        for (int second = first + 1; second < int(nodes.size()); ++second)
            if (!commute(nodes[first], nodes[second])) {
                successors[first].push_back(second);
                ++degree[second];
            }
    for (int index = int(nodes.size()) - 1; index >= 0; --index) {
        for (int child : successors[index]) critical[index] = std::max(critical[index], critical[child]);
        critical[index] += nodes[index].first >= 0;
    }
    std::vector<int> ready;
    for (int index = 0; index < int(nodes.size()); ++index) if (!degree[index]) ready.push_back(index);
    std::vector<Gate> output;
    while (!ready.empty()) {
        bool phases = true;
        while (phases) {
            phases = false;
            for (int index = 0; index < int(ready.size()); ++index)
                if (nodes[ready[index]].first < 0) {
                    int finished = ready[index];
                    ready.erase(ready.begin() + index);
                    for (int child : successors[finished]) if (!--degree[child]) ready.push_back(child);
                    phases = true;
                    break;
                }
        }
        std::vector<std::pair<double, int>> ranked;
        for (int index : ready) ranked.push_back({critical[index] + 3.0 * uniform(), index});
        std::sort(ranked.rbegin(), ranked.rend());
        Mask used = 0;
        for (auto [priority, index] : ranked) {
            auto gate = nodes[index];
            Mask endpoints = (1u << gate.first) | (1u << gate.second);
            if (used & endpoints) continue;
            used |= endpoints;
            output.push_back(gate);
            ready.erase(std::find(ready.begin(), ready.end(), index));
            for (int child : successors[index]) if (!--degree[child]) ready.push_back(child);
        }
    }
    return output;
}

bool walk(const Case& instance, State& state, int maximum_steps, double parity_weight, double root_weight, double depth_weight, double noise) {
    std::unordered_set<uint64_t> visited;
    visited.insert(fingerprint(state, instance));
    int stale = 0;
    double best_cost = evaluate(state, instance, parity_weight, root_weight);
    State best_state = state;
    for (int step = 0; step < maximum_steps; ++step) {
        if (finished(state, instance)) return true;
        double choice_cost = 1e100;
        int choice = -1;
        bool choice_back = false;
        double old_depth_cost = depth_cost(state, instance);
        for (int side = 0; side < 2; ++side)
            for (int direction = 0; direction < int(instance.directed.size()); ++direction) {
                State next = state;
                apply(next, instance, direction, side, false);
                uint64_t hash = fingerprint(next, instance);
                if (visited.count(hash)) continue;
                double value = evaluate(next, instance, parity_weight, root_weight)
                    + depth_weight * (depth_cost(next, instance) - old_depth_cost) + noise * uniform();
                if (value < choice_cost) { choice_cost = value; choice = direction; choice_back = side; }
            }
        if (choice == -1) return false;
        apply(state, instance, choice, choice_back);
        visited.insert(fingerprint(state, instance));
        double current = evaluate(state, instance, parity_weight, root_weight);
        if (current + 0.1 < best_cost) { best_cost = current; stale = 0; best_state = state; } else ++stale;
        if (stale > 8) {
            if (beam_enabled) {
                state = best_state;
                if (escape_beam(state, instance, parity_weight, root_weight, depth_weight)) {
                    best_cost = evaluate(state, instance, parity_weight, root_weight);
                    best_state = state;
                    stale = 0;
                    visited.insert(fingerprint(state, instance));
                    continue;
                }
            }
            complete_parities(state, instance, parity_weight, root_weight, depth_weight);
            complete_linear(state, instance, root_weight, depth_weight);
            return finished(state, instance);
        }
    }
    return finished(state, instance);
}

double objective(const Case& instance, const std::vector<Gate>& gates) {
    double count = double(gates.size()) / instance.count_budget;
    double depth = double(get_depth(gates, instance.size)) / instance.depth_budget;
    return std::max(count, depth) + 0.001 * (count + depth);
}

std::vector<Gate> load(const std::string& path) {
    std::ifstream input(path);
    std::vector<Gate> result;
    int control, target;
    while (input >> control >> target) result.push_back({control, target});
    return result;
}

void local_case(Case& segment, const Case& instance, const std::vector<Gate>& gates, int first, int last) {
    std::array<Mask, 20> rows{}, before{};
    std::unordered_set<Mask> outside;
    for (int wire = 0; wire < instance.size; ++wire) outside.insert(rows[wire] = 1u << wire);
    for (int index = 0; index < first; ++index) {
        auto [control, target] = gates[index];
        outside.insert(rows[target] ^= rows[control]);
    }
    before = rows;
    for (int index = first; index < last; ++index) rows[gates[index].second] ^= rows[gates[index].first];
    auto after = rows;
    for (auto mask : rows) if (mask) outside.insert(mask);
    for (int index = last; index < int(gates.size()); ++index) outside.insert(rows[gates[index].second] ^= rows[gates[index].first]);
    auto inverse = invert(before, instance.size);
    for (int wire = 0; wire < instance.size; ++wire) segment.targets[wire] = multiply(after[wire], inverse);
    segment.parities.clear();
    for (auto parity : instance.parities)
        if (!outside.count(parity)) segment.parities.push_back(multiply(parity, inverse));
    segment.parity_count = segment.parities.size();
}

#ifndef OPTIMIZE_LIBRARY
int main(int argc, char** argv) {
    std::ifstream input("instances.txt");
    int case_count;
    input >> case_count;
    int chosen = argc > 1 ? std::stoi(argv[1]) : 0;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 120;
    std::string source_prefix = argc > 3 ? argv[3] : "ordered_";
    random_engine.seed(argc > 4 ? std::stoull(argv[4]) : 31415);
    std::string output_prefix = argc > 5 ? argv[5] : "optimized_";
    bool annealing = argc > 6 ? std::stoi(argv[6]) : false;
    beam_enabled = argc > 7 ? std::stoi(argv[7]) : false;
    remote_enabled = argc > 8 ? std::stoi(argv[8]) : false;
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
        auto best = load(source_prefix + instance.name + ".txt");
        if (best.empty()) { std::cerr << "missing input\n"; return 1; }
        best = normalize(instance, best);
        double best_score = objective(instance, best);
        auto record = best;
        double record_score = best_score;
        auto start = std::chrono::steady_clock::now();
        int rounds = 0, successes = 0;
        Case segment = instance;
        while (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds) {
            int length = 5 + random_engine() % std::max(1, std::min(annealing ? 65 : 110, int(best.size()) - 4));
            int first = random_engine() % (best.size() - length + 1);
            int last = first + length;
            if (uniform() < 0.05) { first = 0; last = best.size(); length = last; }
            local_case(segment, instance, best, first, last);
            State base = initial(segment);
            for (int index = 0; index < first; ++index) {
                auto [control, target] = best[index];
                base.front_clock[control] = base.front_clock[target] = 1 + std::max(base.front_clock[control], base.front_clock[target]);
            }
            for (int index = int(best.size()) - 1; index >= last; --index) {
                auto [control, target] = best[index];
                base.back_clock[control] = base.back_clock[target] = 1 + std::max(base.back_clock[control], base.back_clock[target]);
            }
            base.front_depth = *std::max_element(base.front_clock.begin(), base.front_clock.end());
            base.back_depth = *std::max_element(base.back_clock.begin(), base.back_clock.end());
            for (int attempt = 0; attempt < 20; ++attempt) {
                State state = base;
                double parity_weight = 0.1 + 3.0 * uniform();
                double root_weight = 0.3 + 1.5 * uniform();
                double depth_weight = 0.05 + 2.5 * uniform();
                double noise = 0.05 + 1.5 * uniform();
                if (!walk(segment, state, std::max(30, 2 * length), parity_weight, root_weight, depth_weight, noise)) continue;
                ++successes;
                auto candidate = circuit(state);
                candidate.insert(candidate.begin(), best.begin(), best.begin() + first);
                candidate.insert(candidate.end(), best.begin() + last, best.end());
                candidate = normalize(instance, candidate);
                double score = objective(instance, candidate);
                bool accept = score < best_score;
                if (annealing && candidate.size() <= record.size() + 12 && score < record_score + 1.05 / instance.depth_budget)
                    accept = accept || uniform() < 0.15 * std::exp((best_score - score) * instance.depth_budget * 2);
                if (accept) {
                    best = candidate;
                    best_score = score;
                    if (score < record_score) {
                        record = best;
                        record_score = score;
                        save(instance, record, output_prefix);
                        std::cout << instance.name << " round " << rounds << " count " << record.size() << " depth " << get_depth(record, instance.size) << " score " << record_score << std::endl;
                    }
                    break;
                }
            }
            if (annealing && rounds % 100 == 0 && uniform() < 0.5) { best = record; best_score = record_score; }
            if (++rounds % 100 == 0) std::cout << "progress " << rounds << ' ' << successes << std::endl;
        }
        save(instance, record, output_prefix);
    }
    return 0;
}
#endif
