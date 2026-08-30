#include <z3++.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    std::ifstream input("instances.txt");
    int cases;
    input >> cases;
    int chosen = argc > 1 ? std::stoi(argv[1]) : 0;
    for (int index = 0; index < cases; ++index) {
        std::string name;
        int size, edge_count, parity_count, count_budget, depth;
        input >> name >> size >> edge_count >> parity_count >> count_budget >> depth;
        std::vector<std::pair<int, int>> edges(edge_count);
        for (auto& edge : edges) input >> edge.first >> edge.second;
        std::vector<unsigned> target(size), parities(parity_count);
        for (auto& mask : target) input >> mask;
        for (auto& mask : parities) input >> mask;
        if (index != chosen) continue;
        z3::context context;
        z3::solver solver(context);
        solver.set("timeout", 1200000u);
        solver.set("random_seed", 31u);
        std::vector<z3::expr_vector> rows, gates;
        for (int layer = 0; layer <= depth; ++layer) {
            rows.emplace_back(context);
            for (int wire = 0; wire < size; ++wire)
                rows.back().push_back(context.bv_const(("r_" + std::to_string(layer) + "_" + std::to_string(wire)).c_str(), size));
        }
        for (int wire = 0; wire < size; ++wire) {
            solver.add(rows.front()[wire] == context.bv_val(1u << wire, size));
            solver.add(rows.back()[wire] == context.bv_val(target[wire], size));
        }
        z3::expr_vector all_gates(context);
        for (int layer = 0; layer < depth; ++layer) {
            gates.emplace_back(context);
            for (int direction = 0; direction < 2 * edge_count; ++direction) {
                gates.back().push_back(context.bool_const(("g_" + std::to_string(layer) + "_" + std::to_string(direction)).c_str()));
                all_gates.push_back(gates.back()[direction]);
            }
            for (int wire = 0; wire < size; ++wire) {
                z3::expr_vector touching(context);
                z3::expr value = rows[layer][wire];
                for (int direction = 0; direction < 2 * edge_count; ++direction) {
                    int control = edges[direction / 2].first;
                    int target_wire = edges[direction / 2].second;
                    if (direction % 2) std::swap(control, target_wire);
                    if (control == wire || target_wire == wire) touching.push_back(gates.back()[direction]);
                    if (target_wire == wire) value = z3::ite(gates.back()[direction], rows[layer][wire] ^ rows[layer][control], value);
                }
                solver.add(z3::atmost(touching, 1));
                solver.add(rows[layer + 1][wire] == value);
            }
        }
        solver.add(z3::atmost(all_gates, count_budget));
        for (auto mask : parities) {
            z3::expr_vector occurrences(context);
            for (int layer = 1; layer < depth; ++layer)
                for (int wire = 0; wire < size; ++wire)
                    occurrences.push_back(rows[layer][wire] == context.bv_val(mask, size));
            solver.add(z3::mk_or(occurrences));
        }
        std::cerr << "solving " << name << " depth " << depth << std::endl;
        auto status = solver.check();
        std::cerr << status << std::endl;
        if (status == z3::sat) {
            auto model = solver.get_model();
            std::ofstream output("sat_" + name + ".txt");
            for (int layer = 0; layer < depth; ++layer)
                for (int direction = 0; direction < 2 * edge_count; ++direction)
                    if (model.eval(gates[layer][direction]).is_true()) {
                        auto edge = edges[direction / 2];
                        if (direction % 2) std::swap(edge.first, edge.second);
                        output << edge.first << ' ' << edge.second << '\n';
                    }
        }
    }
}
