#define OPTIMIZE_LIBRARY
#include "optimize.cpp"

std::vector<int> matching(const Case& instance, const std::vector<double>& scores, double noise, double bonus) {
    std::array<int, 20> color;
    color.fill(-1);
    color[0] = 0;
    std::vector<int> queue{0}, left, right;
    for (int position = 0; position < int(queue.size()); ++position)
        for (int neighbor : instance.adjacent[queue[position]])
            if (color[neighbor] < 0) { color[neighbor] = 1 - color[queue[position]]; queue.push_back(neighbor); }
    for (int wire = 0; wire < instance.size; ++wire) (color[wire] ? right : left).push_back(wire);
    if (right.size() > left.size()) std::swap(left, right);
    std::array<int, 20> right_index;
    right_index.fill(-1);
    for (int index = 0; index < int(right.size()); ++index) right_index[right[index]] = index;
    std::array<std::array<double, 20>, 20> weights{};
    std::array<std::array<int, 20>, 20> directions{};
    for (int direction = 0; direction < int(instance.directed.size()); direction += 2) {
        auto [first, second] = instance.directed[direction];
        int choice = scores[direction] + noise * uniform() > scores[direction + 1] + noise * uniform() ? direction : direction + 1;
        weights[first][second] = weights[second][first] = scores[choice] + bonus + noise * (uniform() - 0.5);
        directions[first][second] = directions[second][first] = choice;
    }
    int states = 1 << right.size();
    std::vector<double> table((left.size() + 1) * states);
    std::vector<int> choices(left.size() * states, -1);
    for (int position = int(left.size()) - 1; position >= 0; --position) {
        int vertex = left[position];
        for (int mask = 0; mask < states; ++mask) {
            double best = table[(position + 1) * states + mask];
            int choice = -1;
            for (int neighbor : instance.adjacent[vertex]) {
                int bit = right_index[neighbor];
                if (mask & (1 << bit)) continue;
                double score = weights[vertex][neighbor] + table[(position + 1) * states + (mask | (1 << bit))];
                if (score > best) { best = score; choice = neighbor; }
            }
            table[position * states + mask] = best;
            choices[position * states + mask] = choice;
        }
    }
    std::vector<int> result;
    int mask = 0;
    for (int position = 0; position < int(left.size()); ++position) {
        int choice = choices[position * states + mask];
        if (choice >= 0) {
            mask |= 1 << right_index[choice];
            result.push_back(directions[left[position]][choice]);
        }
    }
    return result;
}

void layer_walk(State& state, const Case& instance, double parity_weight, double root_weight, double depth_weight, double noise) {
    double best_value = evaluate(state, instance, parity_weight, root_weight);
    State best = state;
    int stale = 0;
    std::unordered_set<uint64_t> visited;
    for (int layer = 0; layer < 2 * instance.depth_budget; ++layer) {
        if (finished(state, instance)) return;
        double initial_value = evaluate(state, instance, parity_weight, root_weight);
        State chosen;
        double chosen_value = 1e100;
        for (int side = 0; side < 2; ++side) {
            std::vector<double> scores;
            for (int direction = 0; direction < int(instance.directed.size()); ++direction) {
                State candidate = state;
                apply(candidate, instance, direction, side, false);
                scores.push_back(initial_value - evaluate(candidate, instance, parity_weight, root_weight));
            }
            for (int attempt = 0; attempt < 12; ++attempt) {
                auto moves = matching(instance, scores, attempt ? noise : 0, attempt ? 0.5 * noise : 0);
                if (moves.empty()) continue;
                State candidate = state;
                for (int direction : moves) apply(candidate, instance, direction, side);
                if (visited.count(fingerprint(candidate, instance))) continue;
                double value = evaluate(candidate, instance, parity_weight, root_weight) + depth_weight * depth_cost(candidate, instance)
                    + 0.1 * (candidate.front.size() + candidate.back.size());
                if (value < chosen_value) { chosen_value = value; chosen = std::move(candidate); }
            }
        }
        if (chosen_value == 1e100) break;
        state = std::move(chosen);
        visited.insert(fingerprint(state, instance));
        double value = evaluate(state, instance, parity_weight, root_weight);
        if (value < best_value - 0.1) { best = state; best_value = value; stale = 0; } else ++stale;
        if (stale > 3) break;
    }
    state = best;
    complete_parities(state, instance, parity_weight, root_weight, depth_weight);
    complete_linear(state, instance, root_weight, depth_weight);
}

int main(int argc, char** argv) {
    std::ifstream input("instances.txt");
    int case_count;
    input >> case_count;
    int chosen = argc > 1 ? std::stoi(argv[1]) : 0;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 120;
    random_engine.seed(argc > 3 ? std::stoull(argv[3]) : 712);
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
        double best_score = 1e100;
        for (int attempt = 0; std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds; ++attempt) {
            phase_bonus = std::pow(2.0, 5.0 * uniform());
            matrix_weight = 0.3 + 1.7 * uniform();
            steiner_weight = uniform();
            State state = initial(instance);
            double parity_weight = 0.2 + 3.0 * uniform(), root_weight = 0.1 + 1.4 * uniform(), depth_weight = 0.05 + 2.0 * uniform();
            layer_walk(state, instance, parity_weight, root_weight, depth_weight, 1.0 + 8.0 * uniform());
            auto candidate = normalize(instance, circuit(state));
            double score = objective(instance, candidate);
            if (score < best_score) {
                best_score = score;
                save(instance, candidate, "layers_");
                std::cout << instance.name << " attempt " << attempt << " count " << candidate.size() << " depth " << get_depth(candidate, instance.size) << " score " << score << std::endl;
            }
        }
    }
}
