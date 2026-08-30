#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <memory>

struct GroupCache {
    struct Distances { std::vector<uint8_t> depth, count; };
    int size;
    std::vector<Gate> generators;
    std::vector<std::vector<Gate>> actions;
    std::vector<unsigned> matrices;
    std::vector<int> indexes;
    std::vector<std::vector<int>> transitions;
    std::vector<std::vector<int>> tags;
    std::array<int, 16> tag_index{};
    std::unordered_map<int, Distances> distances;
    GroupCache(int number, const std::vector<Gate>& edges, bool layer_mode = false) : size(number), indexes(1 << (number * number), -1) {
        for (auto [first, second] : edges) { generators.push_back({first, second}); generators.push_back({second, first}); }
        for (auto gate : generators) actions.push_back({gate});
        if (layer_mode)
            for (int first = 0; first < int(generators.size()); ++first)
                for (int second = first + 1; second < int(generators.size()); ++second) {
                    auto first_gate = generators[first], second_gate = generators[second];
                    Mask endpoints = (1u << first_gate.first) | (1u << first_gate.second) | (1u << second_gate.first) | (1u << second_gate.second);
                    if (weight(endpoints) == 4) actions.push_back({first_gate, second_gate});
                }
        int tag = 0;
        for (int mask = 1; mask < (1 << size); ++mask)
            if (weight(mask) != 1) tag_index[mask] = 1 << tag++;
        unsigned identity = 0;
        for (int wire = 0; wire < size; ++wire) identity |= (1u << wire) << (size * wire);
        matrices.push_back(identity);
        indexes[identity] = 0;
        for (int position = 0; position < int(matrices.size()); ++position) {
            unsigned matrix = matrices[position];
            std::vector<int> outgoing, parity_tags;
            for (const auto& action : actions) {
                unsigned next = matrix;
                int seen = 0;
                for (auto [control, target] : action) {
                    next ^= (((next >> (size * control)) & ((1u << size) - 1)) << (size * target));
                    seen |= tag_index[(next >> (size * target)) & ((1u << size) - 1)];
                }
                if (indexes[next] < 0) { indexes[next] = matrices.size(); matrices.push_back(next); }
                outgoing.push_back(indexes[next]);
                parity_tags.push_back(seen);
            }
            transitions.push_back(std::move(outgoing));
            tags.push_back(std::move(parity_tags));
        }
    }
    std::vector<Gate> synthesize(unsigned target, int needed) {
        int obligation_count = weight(needed);
        if (obligation_count > 3) return {};
        int group_size = matrices.size(), subsets = 1 << obligation_count;
        std::array<int, 2048> compress{};
        int bit = 0;
        for (int mask = needed; mask; mask &= mask - 1) compress[mask & -mask] = 1 << bit++;
        for (int mask = 1; mask < 2048; ++mask) compress[mask] = compress[mask & (mask - 1)] | compress[mask & -mask];
        auto found = distances.find(needed);
        if (found == distances.end()) {
            std::vector<uint8_t> distance(group_size * subsets, 255);
            std::vector<uint8_t> counts(group_size * subsets, 255);
            std::vector<int> queue{0};
            distance[0] = 0;
            counts[0] = 0;
            for (int position = 0; position < int(queue.size()); ++position) {
                int state = queue[position], matrix = state % group_size, seen = state / group_size;
                for (int direction = 0; direction < int(actions.size()); ++direction) {
                    int next_seen = seen | compress[tags[matrix][direction]];
                    int next = next_seen * group_size + transitions[matrix][direction];
                    if (distance[next] == 255) {
                        distance[next] = distance[state] + 1;
                        counts[next] = counts[state] + actions[direction].size();
                        queue.push_back(next);
                    } else if (distance[next] == distance[state] + 1)
                        counts[next] = std::min(int(counts[next]), int(counts[state] + actions[direction].size()));
                }
            }
            found = distances.emplace(needed, Distances{std::move(distance), std::move(counts)}).first;
        }
        const auto& distance = found->second.depth;
        const auto& counts = found->second.count;
        int state = (subsets - 1) * group_size + indexes[target];
        if (distance[state] == 255) return {};
        std::vector<Gate> result;
        while (state) {
            int matrix = state % group_size, seen = state / group_size;
            std::vector<std::pair<int, int>> choices;
            for (int direction = 0; direction < int(actions.size()); ++direction) {
                int previous_matrix = transitions[matrix][direction];
                int added = compress[tags[previous_matrix][direction]];
                if ((seen | added) != seen) continue;
                for (int removed = added;; removed = (removed - 1) & added) {
                    int previous = (seen ^ removed) * group_size + previous_matrix;
                    if (distance[previous] + 1 == distance[state] && counts[previous] + actions[direction].size() == counts[state]) choices.push_back({previous, direction});
                    if (!removed) break;
                }
            }
            if (choices.empty()) std::abort();
            auto [previous, direction] = choices[random_engine() % choices.size()];
            for (auto gate : actions[direction]) result.push_back(gate);
            state = previous;
        }
        std::reverse(result.begin(), result.end());
        return result;
    }
};

std::pair<int, std::vector<int>> canonical_subset(const Case& instance, Mask support) {
    std::vector<int> vertices;
    std::array<std::vector<int>, 20> neighbors;
    for (int wire = 0; wire < instance.size; ++wire) if (support & (1u << wire)) {
        vertices.push_back(wire);
        for (int neighbor : instance.adjacent[wire]) if (support & (1u << neighbor)) neighbors[wire].push_back(neighbor);
    }
    int size = vertices.size(), edge_count = 0;
    for (int vertex : vertices) edge_count += neighbors[vertex].size();
    edge_count /= 2;
    if (size == 3) {
        int center = vertices[0];
        for (int vertex : vertices) if (neighbors[vertex].size() == 2) center = vertex;
        return {0, {center, neighbors[center][0], neighbors[center][1]}};
    }
    if (edge_count == 3) {
        for (int vertex : vertices) if (neighbors[vertex].size() == 3)
            return {1, {vertex, neighbors[vertex][0], neighbors[vertex][1], neighbors[vertex][2]}};
        int start = vertices[0];
        for (int vertex : vertices) if (neighbors[vertex].size() == 1) { start = vertex; break; }
        std::vector<int> order{start};
        while (order.size() < 4) {
            for (int neighbor : neighbors[order.back()])
                if (std::find(order.begin(), order.end(), neighbor) == order.end()) { order.push_back(neighbor); break; }
        }
        return {2, order};
    }
    std::vector<int> order{vertices[0]};
    while (order.size() < 4) {
        for (int neighbor : neighbors[order.back()])
            if (std::find(order.begin(), order.end(), neighbor) == order.end()) { order.push_back(neighbor); break; }
    }
    return {3, order};
}

double profile_score(const Case& instance, const std::vector<Gate>& gates) {
    std::array<int, 20> clocks{}, loads{};
    for (auto [control, target] : gates) {
        clocks[control] = clocks[target] = 1 + std::max(clocks[control], clocks[target]);
        ++loads[control];
        ++loads[target];
    }
    int depth = *std::max_element(clocks.begin(), clocks.end());
    double spread = 0;
    for (int wire = 0; wire < instance.size; ++wire) spread += std::exp((clocks[wire] - depth) * 0.5);
    return std::max(double(depth) / instance.depth_budget, double(gates.size()) / instance.count_budget)
        + 0.001 * std::log(spread) + 0.0001 * *std::max_element(loads.begin(), loads.end()) / instance.depth_budget
        + 0.00001 * gates.size() / instance.count_budget;
}

int main(int argc, char** argv) {
    int chosen = argc > 1 ? std::stoi(argv[1]) : 4;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 600;
    std::string source = argc > 3 ? argv[3] : "macroopt_";
    std::string prefix = argc > 4 ? argv[4] : "group_";
    random_engine.seed(argc > 5 ? std::stoull(argv[5]) : 4892);
    bool layer_mode = argc > 6 ? std::stoi(argv[6]) : false;
    double temperature = argc > 7 ? std::stod(argv[7]) : 0;
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
        std::vector<std::unique_ptr<GroupCache>> groups;
        groups.push_back(std::make_unique<GroupCache>(3, std::vector<Gate>{{0, 1}, {0, 2}}, layer_mode));
        groups.push_back(std::make_unique<GroupCache>(4, std::vector<Gate>{{0, 1}, {0, 2}, {0, 3}}, layer_mode));
        groups.push_back(std::make_unique<GroupCache>(4, std::vector<Gate>{{0, 1}, {1, 2}, {2, 3}}, layer_mode));
        groups.push_back(std::make_unique<GroupCache>(4, std::vector<Gate>{{0, 1}, {1, 2}, {2, 3}, {3, 0}}, layer_mode));
        auto current = load(source + instance.name + ".txt");
        if (current.empty()) return 1;
        auto best = current;
        auto ranking = [&](const std::vector<Gate>& gates) { return temperature ? profile_score(instance, gates) : objective(instance, gates); };
        double record = ranking(best);
        Case segment = instance;
        auto start_time = std::chrono::steady_clock::now();
        for (int attempt = 0; std::chrono::duration<double>(std::chrono::steady_clock::now() - start_time).count() < seconds; ++attempt) {
            if (temperature > 4 && attempt % 10000 == 0) {
                current = best;
                int position = random_engine() % current.size();
                auto gate = current[position];
                Gate reverse{gate.second, gate.first};
                current.erase(current.begin() + position);
                std::vector<Gate> expansion{reverse, gate, reverse, gate, reverse};
                current.insert(current.begin() + position, expansion.begin(), expansion.end());
            }
            int first = random_engine() % current.size();
            auto initial_gate = current[first];
            Mask support = (1u << initial_gate.first) | (1u << initial_gate.second);
            int local_size = uniform() < 0.2 ? 3 : 4;
            while (weight(support) < local_size) {
                Mask choices = 0;
                for (int wire = 0; wire < instance.size; ++wire) if (support & (1u << wire))
                    for (int neighbor : instance.adjacent[wire]) choices |= 1u << neighbor;
                choices &= ~support;
                std::vector<int> options;
                for (int wire = 0; wire < instance.size; ++wire) if (choices & (1u << wire)) options.push_back(wire);
                support |= 1u << options[random_engine() % options.size()];
            }
            auto [topology, wires] = canonical_subset(instance, support);
            std::vector<int> selected;
            std::vector<Gate> barriers;
            for (int index = first; index < std::min(int(current.size()), first + 100); ++index) {
                auto gate = current[index];
                Mask endpoints = (1u << gate.first) | (1u << gate.second);
                bool eligible = (endpoints & support) == endpoints;
                if (eligible) for (auto barrier : barriers) if (!commute(gate, barrier)) { eligible = false; break; }
                if (eligible) selected.push_back(index);
                else if (endpoints & support) barriers.push_back(gate);
                if (selected.size() >= 20 || barriers.size() >= 20) break;
            }
            if (selected.size() < 2) continue;
            auto pulled = std::vector<Gate>(current.begin(), current.begin() + first);
            for (int index : selected) pulled.push_back(current[index]);
            int chosen_position = 0;
            for (int index = first; index < int(current.size()); ++index) {
                if (chosen_position < int(selected.size()) && selected[chosen_position] == index) ++chosen_position;
                else pulled.push_back(current[index]);
            }
            local_case(segment, instance, pulled, first, first + selected.size());
            int needed = 0;
            bool possible = true;
            for (auto parity : segment.parities) {
                if (parity & ~support) { possible = false; break; }
                int compressed = 0;
                for (int local = 0; local < local_size; ++local) if (parity & (1u << wires[local])) compressed |= 1 << local;
                needed |= groups[topology]->tag_index[compressed];
            }
            if (!possible || weight(needed) > 3) continue;
            unsigned target = 0;
            for (int row = 0; row < local_size; ++row)
                for (int column = 0; column < local_size; ++column)
                    if (segment.targets[wires[row]] & (1u << wires[column])) target |= 1u << (local_size * row + column);
            auto replacement = groups[topology]->synthesize(target, needed);
            if (replacement.size() > selected.size() + (layer_mode ? 4 : 1)) continue;
            std::vector<Gate> candidate(pulled.begin(), pulled.begin() + first);
            for (auto [control, target_wire] : replacement) candidate.push_back({wires[control], wires[target_wire]});
            candidate.insert(candidate.end(), pulled.begin() + first + selected.size(), pulled.end());
            candidate = normalize(instance, candidate);
            double score = ranking(candidate);
            if (score < record) {
                record = score;
                best = candidate;
                save(instance, best, prefix);
                std::cout << instance.name << ' ' << attempt << " count " << best.size() << " depth " << get_depth(best, instance.size) << std::endl;
            }
            if (score < record + (temperature ? 6.1 : 1.1) / instance.depth_budget && candidate.size() <= best.size() + (temperature ? 30 : 8)
                && uniform() < 0.25 * std::exp((ranking(current) - score) * instance.depth_budget / std::max(0.1, temperature))) current = candidate;
            if (score < ranking(current)) current = candidate;
            if (attempt % (temperature ? 20000 : 1000) == 0) current = best;
        }
        save(instance, best, prefix);
    }
}
