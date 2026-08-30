#include <z3++.h>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using namespace z3;

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    int width, outputs;
    input >> width >> outputs;
    std::vector<int> table(1 << width);
    for (auto& value : table) input >> value;
    int output_bit = std::stoi(argv[2]);
    int affine_mask = std::stoi(argv[3]);
    int seed = argc > 4 ? std::stoi(argv[4]) : 1;
    int seconds = argc > 5 ? std::stoi(argv[5]) : 600;
    context ctx;
    solver solve(ctx, "QF_FD");
    params settings(ctx);
    settings.set("timeout", unsigned(seconds * 1000));
    settings.set("random_seed", unsigned(seed));
    solve.set(settings);
    std::vector<int> previous = {0, 0, 0, 0, 4, 4, 6, 7};
    std::vector<expr> left_masks, right_masks;
    for (int gate = 0; gate < int(previous.size()); ++gate) {
        int size = width + 1 + previous[gate];
        left_masks.push_back(ctx.bv_const(("left_" + std::to_string(gate)).c_str(), size));
        right_masks.push_back(ctx.bv_const(("right_" + std::to_string(gate)).c_str(), size));
        solve.add(ult(left_masks.back(), right_masks.back()));
        solve.add(left_masks.back() != ctx.bv_val(0, size));
        if (gate < 6) {
            solve.add(left_masks.back().extract(0, 0) == ctx.bv_val(0, 1));
            solve.add(right_masks.back().extract(0, 0) == ctx.bv_val(0, 1));
            for (int pivot = 1; pivot < size; ++pivot) {
                expr highest = left_masks.back().extract(pivot, pivot) == ctx.bv_val(1, 1);
                if (pivot + 1 < size) highest = highest && (left_masks.back().extract(size - 1, pivot + 1) == ctx.bv_val(0, size - pivot - 1));
                solve.add(implies(highest, right_masks.back().extract(pivot, pivot) == ctx.bv_val(0, 1)));
            }
        }
        if (gate > 0 && previous[gate] == previous[gate - 1]) {
            solve.add(ule(left_masks[gate - 1], left_masks[gate]));
        }
    }
    std::vector<int> addresses(1 << width);
    for (int address = 0; address < (1 << width); ++address) addresses[address] = address;
    std::mt19937 random(seed);
    std::shuffle(addresses.begin(), addresses.end(), random);
    auto add_row = [&](int address) {
        std::vector<expr> values;
        values.push_back(ctx.bool_val(true));
        for (int bit = 0; bit < width; ++bit) values.push_back(ctx.bool_val((address >> bit) & 1));
        for (int gate = 0; gate < int(previous.size()); ++gate) {
            expr left = ctx.bool_val(false), right = ctx.bool_val(false);
            for (int reference = 0; reference < width + 1 + previous[gate]; ++reference) {
                left = left ^ ((left_masks[gate].extract(reference, reference) == ctx.bv_val(1, 1)) && values[reference]);
                right = right ^ ((right_masks[gate].extract(reference, reference) == ctx.bv_val(1, 1)) && values[reference]);
            }
            expr value = ctx.bool_const(("value_" + std::to_string(address) + "_" + std::to_string(gate)).c_str());
            solve.add(value == (left && right));
            values.push_back(value);
        }
        bool expected = ((table[address] >> output_bit) & 1) ^ (__builtin_parity(unsigned(address & affine_mask)));
        solve.add((values[width + 1 + 6] ^ values[width + 1 + 7]) == ctx.bool_val(expected));
    };
    int initial_rows = argc > 6 ? std::stoi(argv[6]) : 128;
    std::vector<bool> used(1 << width);
    for (int row = 0; row < initial_rows; ++row) {
        add_row(addresses[row]);
        used[addresses[row]] = true;
    }
    for (int iteration = 0; ; ++iteration) {
        std::cerr << "check " << iteration << std::endl;
        auto result = solve.check();
        if (result != sat) {
            std::cerr << result << " " << solve.reason_unknown() << std::endl;
            return 1;
        }
        auto model = solve.get_model();
        std::vector<unsigned> left_values, right_values;
        for (int gate = 0; gate < int(previous.size()); ++gate) {
            left_values.push_back(model.eval(left_masks[gate], true).get_numeral_uint());
            right_values.push_back(model.eval(right_masks[gate], true).get_numeral_uint());
        }
        std::vector<int> failed;
        for (int address : addresses) {
            unsigned values = (unsigned(address) << 1) | 1;
            for (int gate = 0; gate < int(previous.size()); ++gate) {
                unsigned value = __builtin_parity(left_values[gate] & values) & __builtin_parity(right_values[gate] & values);
                values |= value << (width + 1 + gate);
            }
            int actual = ((values >> (width + 1 + 6)) ^ (values >> (width + 1 + 7)) ^ __builtin_parity(unsigned(address & affine_mask))) & 1;
            if (actual != ((table[address] >> output_bit) & 1)) failed.push_back(address);
        }
        std::cerr << "errors " << failed.size() << std::endl;
        if (failed.empty()) {
            std::cout << "{\"left\":[";
            for (int gate = 0; gate < int(previous.size()); ++gate) std::cout << (gate ? "," : "") << left_values[gate];
            std::cout << "],\"right\":[";
            for (int gate = 0; gate < int(previous.size()); ++gate) std::cout << (gate ? "," : "") << right_values[gate];
            std::cout << "]}" << std::endl;
            return 0;
        }
        int count = 0;
        for (int address : failed) {
            if (!used[address]) {
                add_row(address);
                used[address] = true;
                if (++count == 32) break;
            }
        }
    }
}
