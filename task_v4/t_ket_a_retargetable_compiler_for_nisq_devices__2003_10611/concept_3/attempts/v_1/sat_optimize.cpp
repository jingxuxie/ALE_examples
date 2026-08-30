#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <z3++.h>

std::vector<Gate> solve_window(const Case& instance, int depth, int count_bound, int timeout) {
    z3::context context;
    z3::solver solver(context);
    solver.set("timeout", unsigned(timeout));
    solver.set("random_seed", unsigned(random_engine()));
    std::vector<z3::expr_vector> rows, gates;
    for (int layer = 0; layer <= depth; ++layer) {
        rows.emplace_back(context);
        for (int wire = 0; wire < instance.size; ++wire)
            rows.back().push_back(context.bv_const(("r_" + std::to_string(layer) + "_" + std::to_string(wire)).c_str(), instance.size));
    }
    for (int wire = 0; wire < instance.size; ++wire) {
        solver.add(rows.front()[wire] == context.bv_val(1u << wire, instance.size));
        solver.add(rows.back()[wire] == context.bv_val(instance.targets[wire], instance.size));
    }
    z3::expr_vector all_gates(context);
    for (int layer = 0; layer < depth; ++layer) {
        gates.emplace_back(context);
        for (int direction = 0; direction < int(instance.directed.size()); ++direction) {
            gates.back().push_back(context.bool_const(("g_" + std::to_string(layer) + "_" + std::to_string(direction)).c_str()));
            all_gates.push_back(gates.back()[direction]);
        }
        for (int wire = 0; wire < instance.size; ++wire) {
            z3::expr_vector touching(context);
            z3::expr value = rows[layer][wire];
            for (int direction = 0; direction < int(instance.directed.size()); ++direction) {
                auto [control, target] = instance.directed[direction];
                if (control == wire || target == wire) touching.push_back(gates.back()[direction]);
                if (target == wire) value = z3::ite(gates.back()[direction], rows[layer][wire] ^ rows[layer][control], value);
            }
            solver.add(z3::atmost(touching, 1));
            solver.add(rows[layer + 1][wire] == value);
        }
    }
    solver.add(z3::atmost(all_gates, count_bound));
    for (auto mask : instance.parities) {
        z3::expr_vector occurrences(context);
        for (int layer = 0; layer <= depth; ++layer)
            for (int wire = 0; wire < instance.size; ++wire)
                occurrences.push_back(rows[layer][wire] == context.bv_val(mask, instance.size));
        solver.add(z3::mk_or(occurrences));
    }
    if (solver.check() != z3::sat) return {};
    auto model = solver.get_model();
    std::vector<Gate> result;
    for (int layer = 0; layer < depth; ++layer)
        for (int direction = 0; direction < int(instance.directed.size()); ++direction)
            if (model.eval(gates[layer][direction]).is_true()) result.push_back(instance.directed[direction]);
    return result;
}

int main(int argc, char** argv) {
    int chosen = argc > 1 ? std::stoi(argv[1]) : 4;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 600;
    std::string source = argc > 3 ? argv[3] : "annealed_";
    std::string prefix = argc > 4 ? argv[4] : "satopt_";
    int timeout = argc > 5 ? std::stoi(argv[5]) : 500;
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
        auto best = load(source + instance.name + ".txt");
        if (best.empty()) return 1;
        double record = objective(instance, best);
        Case segment = instance;
        auto start = std::chrono::steady_clock::now();
        int successes = 0;
        for (int attempt = 0; std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds; ++attempt) {
            std::vector<std::pair<int, Gate>> layered;
            std::array<int, 20> clocks{};
            for (auto gate : best) {
                int level = 1 + std::max(clocks[gate.first], clocks[gate.second]);
                clocks[gate.first] = clocks[gate.second] = level;
                layered.push_back({level, gate});
            }
            std::stable_sort(layered.begin(), layered.end(), [](const auto& first, const auto& second) { return first.first < second.first; });
            for (int index = 0; index < int(best.size()); ++index) best[index] = layered[index].second;
            int full_depth = layered.back().first;
            int length = 4 + random_engine() % 7;
            int level = 1 + random_engine() % (full_depth - length + 1);
            int first = 0, last = 0;
            while (first < int(layered.size()) && layered[first].first < level) ++first;
            last = first;
            while (last < int(layered.size()) && layered[last].first < level + length) ++last;
            local_case(segment, instance, best, first, last);
            auto replacement = solve_window(segment, length - 1, last - first + 2, timeout);
            if (!replacement.empty()) {
                ++successes;
                auto candidate = replacement;
                candidate.insert(candidate.begin(), best.begin(), best.begin() + first);
                candidate.insert(candidate.end(), best.begin() + last, best.end());
                candidate = normalize(instance, candidate);
                double score = objective(instance, candidate);
                if (score <= record + 1e-8) {
                    best = candidate;
                    record = score;
                    save(instance, best, prefix);
                    std::cout << instance.name << " attempt " << attempt << " count " << best.size() << " depth " << get_depth(best, instance.size) << std::endl;
                }
            }
            if (attempt % 20 == 0) std::cout << "progress " << attempt << ' ' << successes << std::endl;
        }
        save(instance, best, prefix);
    }
}
