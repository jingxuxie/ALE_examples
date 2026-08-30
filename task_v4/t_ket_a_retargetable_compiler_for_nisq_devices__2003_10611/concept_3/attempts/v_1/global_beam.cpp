#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <unordered_map>

struct History { int previous, move; };
struct Entry {
    State state;
    double value;
    int history, move;
};

int main(int argc, char** argv) {
    int chosen = argc > 1 ? std::stoi(argv[1]) : 2;
    int width = argc > 2 ? std::stoi(argv[2]) : 512;
    int seconds = argc > 3 ? std::stoi(argv[3]) : 600;
    int seed = argc > 4 ? std::stoi(argv[4]) : 431;
    std::string prefix = argc > 5 ? argv[5] : "global_";
    random_engine.seed(seed);
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
        int directions = instance.directed.size();
        for (int attempt = 0; std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds; ++attempt) {
            phase_bonus = 1 + 8 * uniform();
            matrix_weight = 0.5 + uniform();
            steiner_weight = 0.2 + 0.8 * uniform();
            double parity_weight = 0.5 + 2.0 * uniform(), root_weight = 0.3 + 1.2 * uniform(), depth_weight = 0.2 + 2.0 * uniform();
            std::vector<Entry> beam{{initial(instance), 0, -1, -1}};
            std::vector<History> history;
            std::unordered_map<uint64_t, double> closed;
            double minimum = 1e100;
            int stale = 0;
            for (int step = 0; step < 2 * instance.count_budget; ++step) {
                std::vector<Entry> candidates;
                std::unordered_map<uint64_t, int> indexes;
                candidates.reserve(beam.size() * directions);
                for (const auto& parent : beam) {
                    for (int move = 0; move < 2 * directions; ++move) {
                        Entry candidate = parent;
                        apply(candidate.state, instance, move % directions, move >= directions, false);
                        candidate.value = evaluate(candidate.state, instance, parity_weight, root_weight) + depth_weight * depth_cost(candidate.state, instance);
                        candidate.move = move;
                        uint64_t hash = fingerprint(candidate.state, instance);
                        auto previous = closed.find(hash);
                        if (previous != closed.end() && previous->second <= candidate.value + 1e-8) continue;
                        auto found = indexes.find(hash);
                        if (found == indexes.end()) {
                            indexes[hash] = candidates.size();
                            candidates.push_back(std::move(candidate));
                        } else if (candidate.value < candidates[found->second].value) candidates[found->second] = std::move(candidate);
                    }
                }
                int keep = std::min(width, int(candidates.size()));
                if (!keep) break;
                std::partial_sort(candidates.begin(), candidates.begin() + keep, candidates.end(), [](const auto& first, const auto& second) { return first.value < second.value; });
                candidates.resize(keep);
                beam = std::move(candidates);
                for (auto& entry : beam) {
                    closed[fingerprint(entry.state, instance)] = entry.value;
                    history.push_back({entry.history, entry.move});
                    entry.history = history.size() - 1;
                    if (finished(entry.state, instance)) {
                        std::vector<int> moves;
                        for (int index = entry.history; index >= 0; index = history[index].previous) moves.push_back(history[index].move);
                        State reconstructed = initial(instance);
                        for (auto iterator = moves.rbegin(); iterator != moves.rend(); ++iterator)
                            apply(reconstructed, instance, *iterator % directions, *iterator >= directions);
                        auto gates = normalize(instance, circuit(reconstructed));
                        double score = objective(instance, gates);
                        if (score < record) {
                            record = score;
                            save(instance, gates, prefix);
                            std::cout << "FOUND " << instance.name << " attempt " << attempt << " step " << step << " count " << gates.size() << " depth " << get_depth(gates, instance.size) << std::endl;
                        }
                    }
                }
                if (step % 10 == 0 && step >= 30) {
                    std::vector<int> moves;
                    for (int index = beam.front().history; index >= 0; index = history[index].previous) moves.push_back(history[index].move);
                    State reconstructed = initial(instance);
                    for (auto iterator = moves.rbegin(); iterator != moves.rend(); ++iterator)
                        apply(reconstructed, instance, *iterator % directions, *iterator >= directions);
                    complete_parities(reconstructed, instance, parity_weight, root_weight, depth_weight);
                    complete_linear(reconstructed, instance, root_weight, depth_weight);
                    auto gates = normalize(instance, circuit(reconstructed));
                    double score = objective(instance, gates);
                    if (score < record) {
                        record = score;
                        save(instance, gates, prefix);
                        std::cout << "COMPLETE " << instance.name << " attempt " << attempt << " step " << step << " count " << gates.size() << " depth " << get_depth(gates, instance.size) << std::endl;
                    }
                }
                double value = evaluate(beam.front().state, instance, parity_weight, root_weight);
                if (value < minimum - 0.1) { minimum = value; stale = 0; } else ++stale;
                if (step % 20 == 0) std::cout << "progress " << attempt << ' ' << step << " cost " << value << " remaining " << __builtin_popcountll(beam.front().state.remaining) << std::endl;
                if (stale > 60 || std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() > seconds) break;
            }
        }
    }
}
