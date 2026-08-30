#include <z3++.h>
#include <algorithm>
#include <chrono>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

struct Gate {
    std::vector<int> references;
    std::vector<z3::expr> left;
    std::vector<z3::expr> right;
    int depth;
    int branch;
};

z3::expr parity(z3::context& context, const std::vector<z3::expr>& terms) {
    z3::expr value = context.bool_val(false);
    for (const auto& term : terms) value = value ^ term;
    return value;
}

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    int width, count;
    input >> width >> count;
    std::vector<int> masks(count), table(1 << width);
    for (auto& mask : masks) input >> mask;
    for (auto& value : table) input >> value;
    z3::context context;
    z3::solver solver(context);
    z3::params parameters(context);
    parameters.set("timeout", 1000000u);
    parameters.set("random_seed", 7u);
    parameters.set("anf", true);
    parameters.set("anf.exlin", true);
    parameters.set("cut.xor", true);
    solver.set(parameters);
    std::vector<Gate> gates;
    auto add_gate = [&](int depth, int branch) {
        Gate gate{{}, {}, {}, depth, branch};
        for (int reference = 0; reference <= width; ++reference) gate.references.push_back(reference);
        for (int previous = 0; previous < static_cast<int>(gates.size()); ++previous) {
            if (gates[previous].depth == depth - 1) gate.references.push_back(width + 1 + previous);
        }
        int index = gates.size();
        for (int reference : gate.references) {
            gate.left.push_back(context.bool_const(("l_" + std::to_string(index) + "_" + std::to_string(reference)).c_str()));
            gate.right.push_back(context.bool_const(("r_" + std::to_string(index) + "_" + std::to_string(reference)).c_str()));
        }
        z3::expr ordered = context.bool_val(false);
        for (int offset = 0; offset < static_cast<int>(gate.references.size()); ++offset) ordered = (!gate.left[offset] && gate.right[offset]) || ((gate.left[offset] == gate.right[offset]) && ordered);
        solver.add(ordered);
        if (depth < 4 && !gates.empty() && gates.back().depth == depth) {
            z3::expr increasing = context.bool_val(true);
            for (int offset = 0; offset < static_cast<int>(gate.references.size()); ++offset) increasing = (!gates.back().left[offset] && gate.left[offset]) || ((gates.back().left[offset] == gate.left[offset]) && increasing);
            solver.add(increasing);
        }
        gates.push_back(gate);
    };
    for (int depth = 1; depth <= 4; ++depth) for (int repeat = 0; repeat < count + 1; ++repeat) add_gate(depth, -1);
    std::vector<bool> used(1 << width, false);
    auto add_row = [&](int address) {
        if (used[address]) return;
        used[address] = true;
        std::vector<z3::expr> values;
        values.push_back(context.bool_val(true));
        for (int bit = 0; bit < width; ++bit) values.push_back(context.bool_val(address >> bit & 1));
        for (int index = 0; index < static_cast<int>(gates.size()); ++index) {
            const auto& gate = gates[index];
            std::vector<z3::expr> left, right;
            for (int offset = 0; offset < static_cast<int>(gate.references.size()); ++offset) {
                left.push_back(gate.left[offset] && values[gate.references[offset]]);
                right.push_back(gate.right[offset] && values[gate.references[offset]]);
            }
            z3::expr result = context.bool_const(("v_" + std::to_string(address) + "_" + std::to_string(index)).c_str());
            solver.add(result == (parity(context, left) && parity(context, right)));
            values.push_back(result);
        }
        for (int bit = 0; bit < count; ++bit) {
            int expected = (table[address] >> bit & 1) ^ (__builtin_popcount(address & masks[bit]) & 1);
            solver.add((values[width + 1 + 3 * (count + 1) + count] ^ values[width + 1 + 3 * (count + 1) + bit]) == context.bool_val(expected));
        }
    };
    std::vector<int> addresses(1 << width);
    std::iota(addresses.begin(), addresses.end(), 0);
    std::mt19937 generator(123);
    std::shuffle(addresses.begin(), addresses.end(), generator);
    for (int offset = 0; offset < 8; ++offset) add_row(addresses[offset]);
    for (int iteration = 0; iteration < 100; ++iteration) {
        auto started = std::chrono::steady_clock::now();
        auto status = solver.check();
        std::cerr << "iteration " << iteration << " status " << status << " rows " << std::count(used.begin(), used.end(), true) << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
        if (status != z3::sat) break;
        auto model = solver.get_model();
        std::vector<std::vector<int>> lefts, rights;
        for (const auto& gate : gates) {
            std::vector<int> left, right;
            for (int offset = 0; offset < static_cast<int>(gate.references.size()); ++offset) {
                if (model.eval(gate.left[offset], true).is_true()) left.push_back(gate.references[offset]);
                if (model.eval(gate.right[offset], true).is_true()) right.push_back(gate.references[offset]);
            }
            lefts.push_back(left);
            rights.push_back(right);
        }
        std::vector<int> errors;
        for (int address : addresses) {
            std::vector<int> values{1};
            for (int bit = 0; bit < width; ++bit) values.push_back(address >> bit & 1);
            for (int index = 0; index < static_cast<int>(gates.size()); ++index) {
                int left = 0, right = 0;
                for (int reference : lefts[index]) left ^= values[reference];
                for (int reference : rights[index]) right ^= values[reference];
                values.push_back(left & right);
            }
            int actual = 0;
            for (int bit = 0; bit < count; ++bit) actual |= (values[width + 1 + 3 * (count + 1) + count] ^ values[width + 1 + 3 * (count + 1) + bit] ^ (__builtin_popcount(address & masks[bit]) & 1)) << bit;
            if (actual != table[address]) errors.push_back(address);
        }
        std::cerr << "errors " << errors.size() << std::endl;
        if (errors.empty()) {
            std::ofstream output(argv[2]);
            output << "{\"gates\":[";
            for (int index = 0; index < static_cast<int>(gates.size()); ++index) {
                if (index) output << ',';
                output << "{\"left\":[";
                for (int offset = 0; offset < static_cast<int>(lefts[index].size()); ++offset) { if (offset) output << ','; output << lefts[index][offset]; }
                output << "],\"right\":[";
                for (int offset = 0; offset < static_cast<int>(rights[index].size()); ++offset) { if (offset) output << ','; output << rights[index][offset]; }
                output << "]}";
            }
            output << "]}";
            break;
        }
        for (int offset = 0; offset < std::min(2, static_cast<int>(errors.size())); ++offset) add_row(errors[offset]);
    }
}
