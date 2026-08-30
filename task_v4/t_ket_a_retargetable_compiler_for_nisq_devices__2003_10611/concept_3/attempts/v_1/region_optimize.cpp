#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <z3++.h>

std::vector<Gate> region_solve(const Case& instance, int depth, int bound, int timeout) {
    z3::context context;
    z3::solver solver(context, "QF_BV");
    solver.set("timeout", unsigned(timeout));
    std::vector<z3::expr_vector> rows, choices;
    for (int layer = 0; layer <= depth; ++layer) {
        rows.emplace_back(context);
        for (int wire = 0; wire < instance.size; ++wire) rows.back().push_back(context.bv_const(("r" + std::to_string(layer) + "_" + std::to_string(wire)).c_str(), instance.size));
    }
    for (int wire = 0; wire < instance.size; ++wire) {
        solver.add(rows.front()[wire] == context.bv_val(1u << wire, instance.size));
        solver.add(rows.back()[wire] == context.bv_val(instance.targets[wire], instance.size));
    }
    z3::expr_vector all(context);
    for (int layer = 0; layer < depth; ++layer) {
        choices.emplace_back(context);
        for (int direction = 0; direction < int(instance.directed.size()); ++direction) {
            choices.back().push_back(context.bool_const(("g" + std::to_string(layer) + "_" + std::to_string(direction)).c_str()));
            all.push_back(choices.back()[direction]);
        }
        for (int wire = 0; wire < instance.size; ++wire) {
            z3::expr value = rows[layer][wire];
            z3::expr_vector touching(context);
            for (int direction = 0; direction < int(instance.directed.size()); ++direction) {
                auto [control, target] = instance.directed[direction];
                if (wire == control || wire == target) touching.push_back(choices.back()[direction]);
                if (wire == target) value = z3::ite(choices.back()[direction], rows[layer][target] ^ rows[layer][control], value);
            }
            solver.add(z3::atmost(touching, 1));
            solver.add(rows[layer + 1][wire] == value);
        }
    }
    solver.add(z3::atmost(all, bound));
    for (auto parity : instance.parities) {
        z3::expr_vector places(context);
        for (int layer = 0; layer <= depth; ++layer)
            for (int wire = 0; wire < instance.size; ++wire) places.push_back(rows[layer][wire] == context.bv_val(parity, instance.size));
        solver.add(z3::mk_or(places));
    }
    if (solver.check() != z3::sat) return {};
    auto model = solver.get_model();
    std::vector<Gate> result;
    for (int layer = 0; layer < depth; ++layer)
        for (int direction = 0; direction < int(instance.directed.size()); ++direction)
            if (model.eval(choices[layer][direction]).is_true()) result.push_back(instance.directed[direction]);
    return result;
}

int main(int argc, char** argv) {
    int chosen = argc > 1 ? std::stoi(argv[1]) : 4;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 600;
    std::string source = argc > 3 ? argv[3] : "group_";
    std::string prefix = argc > 4 ? argv[4] : "region_";
    random_engine.seed(argc > 5 ? std::stoull(argv[5]) : 573);
    int timeout = argc > 6 ? std::stoi(argv[6]) : 150;
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
        auto current = load(source + instance.name + ".txt");
        if (current.empty()) return 1;
        auto best = current;
        double record = objective(instance, best);
        Case segment = instance;
        auto started = std::chrono::steady_clock::now();
        int solved = 0;
        std::unordered_map<uint64_t, std::vector<Gate>> cache;
        for (int attempt = 0; std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() < seconds; ++attempt) {
            int first = random_engine() % current.size();
            auto initial_gate = current[first];
            Mask support = (1u << initial_gate.first) | (1u << initial_gate.second);
            int local_size = uniform() < 0.3 ? 6 : 5;
            while (weight(support) < local_size) {
                std::vector<int> options;
                for (int wire = 0; wire < instance.size; ++wire) if (support & (1u << wire))
                    for (int neighbor : instance.adjacent[wire]) if (!(support & (1u << neighbor))) options.push_back(neighbor);
                support |= 1u << options[random_engine() % options.size()];
            }
            std::vector<int> wires;
            std::array<int, 20> local_index{};
            for (int wire = 0; wire < instance.size; ++wire) if (support & (1u << wire)) { local_index[wire] = wires.size(); wires.push_back(wire); }
            std::vector<int> selected;
            std::vector<Gate> barriers, local_gates;
            for (int index = first; index < std::min(int(current.size()), first + 100); ++index) {
                auto gate = current[index];
                Mask endpoints = (1u << gate.first) | (1u << gate.second);
                bool eligible = (endpoints & support) == endpoints;
                if (eligible) for (auto barrier : barriers) if (!commute(gate, barrier)) { eligible = false; break; }
                if (eligible) { selected.push_back(index); local_gates.push_back({local_index[gate.first], local_index[gate.second]}); }
                else if (endpoints & support) barriers.push_back(gate);
                if (selected.size() >= 18 || barriers.size() >= 20) break;
            }
            if (selected.size() < 4) continue;
            std::vector<Gate> pulled(current.begin(), current.begin() + first);
            for (int index : selected) pulled.push_back(current[index]);
            int position = 0;
            for (int index = first; index < int(current.size()); ++index)
                if (position < int(selected.size()) && selected[position] == index) ++position;
                else pulled.push_back(current[index]);
            local_case(segment, instance, pulled, first, first + selected.size());
            Case local;
            local.size = local_size;
            local.targets.resize(local_size);
            bool possible = true;
            for (auto parity : segment.parities) {
                if (parity & ~support) { possible = false; break; }
                Mask compressed = 0;
                for (int wire = 0; wire < local_size; ++wire) if (parity & (1u << wires[wire])) compressed |= 1u << wire;
                local.parities.push_back(compressed);
            }
            if (!possible) continue;
            for (int row = 0; row < local_size; ++row)
                for (int column = 0; column < local_size; ++column)
                    if (segment.targets[wires[row]] & (1u << wires[column])) local.targets[row] |= 1u << column;
            for (auto [control, target] : instance.edges)
                if ((support & (1u << control)) && (support & (1u << target))) {
                    local.directed.push_back({local_index[control], local_index[target]});
                    local.directed.push_back({local_index[target], local_index[control]});
                }
            int depth = std::min(8, get_depth(local_gates, local_size));
            int bound = selected.size();
            if (uniform() < 0.5) --depth; else --bound;
            if (depth < 1 || bound < 1) continue;
            uint64_t hash = depth * 100 + bound;
            for (auto row : local.targets) hash = hash * 0x100000001b3ull ^ row;
            for (auto parity : local.parities) hash = hash * 0x100000001b3ull ^ parity;
            for (auto edge : local.directed) hash = hash * 0x100000001b3ull ^ (edge.first * 10 + edge.second);
            auto found = cache.find(hash);
            if (found == cache.end()) found = cache.emplace(hash, region_solve(local, depth, bound, timeout)).first;
            if (found->second.empty()) continue;
            ++solved;
            std::vector<Gate> candidate(pulled.begin(), pulled.begin() + first);
            for (auto [control, target] : found->second) candidate.push_back({wires[control], wires[target]});
            candidate.insert(candidate.end(), pulled.begin() + first + selected.size(), pulled.end());
            candidate = normalize(instance, candidate);
            double score = objective(instance, candidate);
            if (score < record) {
                best = candidate;
                record = score;
                save(instance, best, prefix);
                std::cout << instance.name << ' ' << attempt << " count " << best.size() << " depth " << get_depth(best, instance.size) << std::endl;
            }
            if (score < objective(instance, current) || (score < record + 2.1 / instance.depth_budget && uniform() < 0.15)) current = candidate;
            if (attempt % 500 == 0) { current = best; std::cout << "progress " << attempt << ' ' << solved << std::endl; }
        }
        save(instance, best, prefix);
    }
}
