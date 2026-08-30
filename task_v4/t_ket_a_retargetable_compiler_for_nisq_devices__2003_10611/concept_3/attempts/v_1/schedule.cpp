#include <algorithm>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <z3++.h>

bool commute(std::pair<int, int> first, std::pair<int, int> second) {
    if (first.first < 0) return second.first < 0 || first.second != second.second;
    if (second.first < 0) return first.second != second.second;
    return first.first != second.second && second.first != first.second;
}

int main(int argc, char** argv) {
    std::string path = argv[1];
    std::ifstream input(path);
    int size, depth, count;
    input >> size >> depth >> count;
    std::vector<std::pair<int, int>> nodes(count);
    for (auto& node : nodes) input >> node.first >> node.second;
    std::vector<int> earliest(count), remaining(count);
    for (int index = 0; index < count; ++index) {
        for (int prior = 0; prior < index; ++prior)
            if (!commute(nodes[prior], nodes[index])) earliest[index] = std::max(earliest[index], earliest[prior]);
        earliest[index] += nodes[index].first >= 0;
    }
    for (int index = count - 1; index >= 0; --index)
        for (int after = index + 1; after < count; ++after)
            if (!commute(nodes[index], nodes[after])) remaining[index] = std::max(remaining[index], remaining[after] + (nodes[after].first >= 0));
    z3::context context;
    z3::solver solver(context);
    solver.set("timeout", 180000u);
    solver.set("random_seed", 612u);
    z3::expr_vector clocks(context);
    for (int index = 0; index < count; ++index) {
        clocks.push_back(context.int_const(("time_" + std::to_string(index)).c_str()));
        solver.add(clocks.back() >= earliest[index]);
        solver.add(clocks.back() <= depth - remaining[index]);
    }
    for (int first = 0; first < count; ++first)
        for (int second = first + 1; second < count; ++second)
            if (!commute(nodes[first], nodes[second]))
                solver.add(clocks[first] + (nodes[second].first >= 0) <= clocks[second]);
    for (int wire = 0; wire < size; ++wire) {
        z3::expr_vector assigned(context);
        for (int index = 0; index < count; ++index)
            if (nodes[index].first >= 0 && (nodes[index].first == wire || nodes[index].second == wire)) assigned.push_back(clocks[index]);
        solver.add(z3::distinct(assigned));
    }
    auto result = solver.check();
    std::cout << path << ' ' << result << std::endl;
    if (result == z3::sat) {
        auto model = solver.get_model();
        std::vector<std::pair<int, std::pair<int, int>>> scheduled;
        for (int index = 0; index < count; ++index)
            if (nodes[index].first >= 0) scheduled.push_back({model.eval(clocks[index]).get_numeral_int(), nodes[index]});
        std::sort(scheduled.begin(), scheduled.end());
        std::ofstream output(argv[2]);
        for (auto item : scheduled) output << item.second.first << ' ' << item.second.second << '\n';
    }
}
