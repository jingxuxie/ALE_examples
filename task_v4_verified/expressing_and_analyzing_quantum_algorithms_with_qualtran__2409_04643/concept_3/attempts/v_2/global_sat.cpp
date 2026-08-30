#include <z3++.h>
#include <algorithm>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

using namespace z3;

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    int width, outputs;
    input >> width >> outputs;
    int rows = 1 << width;
    std::vector<int> table(rows);
    for (auto& value : table) input >> value;
    std::vector<unsigned> output_affine;
    std::stringstream masks(argv[2]);
    std::string item;
    while (std::getline(masks, item, ',')) output_affine.push_back(std::stoul(item));
    int base = argc > 3 ? std::stoi(argv[3]) : 6;
    int seed = argc > 4 ? std::stoi(argv[4]) : 1;
    int seconds = argc > 5 ? std::stoi(argv[5]) : 1200;
    int initial_rows = argc > 6 ? std::stoi(argv[6]) : rows;
    bool polynomial = argc > 7 && std::stoi(argv[7]);
    context ctx;
    solver solve(ctx, "QF_FD");
    params settings(ctx);
    settings.set("timeout", unsigned(seconds * 1000));
    settings.set("random_seed", unsigned(seed));
    settings.set("anf", true);
    settings.set("anf.exlin", true);
    settings.set("anf.delay", 0U);
    settings.set("cut.xor", true);
    solve.set(settings);
    std::vector<int> previous(base, 0);
    for (int gate = 0; gate < outputs; ++gate) previous.push_back(base);
    for (int gate = 0; gate < outputs; ++gate) previous.push_back(base + outputs);
    int final_start = base + 2 * outputs;
    for (int gate = 0; gate < 2 * outputs; ++gate) previous.push_back(final_start);
    int gate_count = previous.size();
    std::vector<expr> left_masks, right_masks;
    for (int gate = 0; gate < gate_count; ++gate) {
        int size = width + 1 + previous[gate];
        left_masks.push_back(ctx.bv_const(("left_" + std::to_string(gate)).c_str(), size));
        right_masks.push_back(ctx.bv_const(("right_" + std::to_string(gate)).c_str(), size));
        solve.add(ult(left_masks.back(), right_masks.back()));
        solve.add(left_masks.back() != ctx.bv_val(0, size));
        if (gate < final_start) {
            solve.add(left_masks.back().extract(0, 0) == ctx.bv_val(0, 1));
            solve.add(right_masks.back().extract(0, 0) == ctx.bv_val(0, 1));
            for (int pivot = 1; pivot < size; ++pivot) {
                expr highest = left_masks.back().extract(pivot, pivot) == ctx.bv_val(1, 1);
                if (pivot + 1 < size) highest = highest && (left_masks.back().extract(size - 1, pivot + 1) == ctx.bv_val(0, size - pivot - 1));
                solve.add(implies(highest, right_masks.back().extract(pivot, pivot) == ctx.bv_val(0, 1)));
            }
        }
        if (gate > 0 && previous[gate] == previous[gate - 1] && (gate < final_start || (gate - final_start) % 2 == 1)) {
            solve.add(ule(left_masks[gate - 1], left_masks[gate]));
        }
    }
    std::vector<int> addresses(rows);
    std::vector<std::vector<expr>> quadratic;
    if (polynomial) {
        for (int gate = 0; gate < base; ++gate) {
            quadratic.emplace_back();
            for (int first = 1; first <= width; ++first) for (int second = first; second <= width; ++second) {
                expr coefficient = ctx.bool_const(("quadratic_" + std::to_string(gate) + "_" + std::to_string(first) + "_" + std::to_string(second)).c_str());
                expr first_left = left_masks[gate].extract(first, first) == ctx.bv_val(1, 1);
                expr first_right = right_masks[gate].extract(first, first) == ctx.bv_val(1, 1);
                expr second_left = left_masks[gate].extract(second, second) == ctx.bv_val(1, 1);
                expr second_right = right_masks[gate].extract(second, second) == ctx.bv_val(1, 1);
                solve.add(coefficient == (first == second ? first_left && first_right : (first_left && second_right) ^ (first_right && second_left)));
                quadratic.back().push_back(coefficient);
            }
        }
    }
    std::iota(addresses.begin(), addresses.end(), 0);
    std::mt19937 random(seed);
    std::shuffle(addresses.begin(), addresses.end(), random);
    auto add_row = [&](int address) {
        std::vector<expr> values;
        values.push_back(ctx.bool_val(true));
        for (int bit = 0; bit < width; ++bit) values.push_back(ctx.bool_val((address >> bit) & 1));
        for (int gate = 0; gate < gate_count; ++gate) {
            expr left = ctx.bool_val(false), right = ctx.bool_val(false);
            if (polynomial && gate < base) {
                int index = 0;
                for (int first = 1; first <= width; ++first) for (int second = first; second <= width; ++second) {
                    if (((address >> (first - 1)) & 1) && ((address >> (second - 1)) & 1)) left = left ^ quadratic[gate][index];
                    ++index;
                }
                right = ctx.bool_val(true);
            } else {
                for (int reference = 0; reference < width + 1 + previous[gate]; ++reference) {
                    left = left ^ ((left_masks[gate].extract(reference, reference) == ctx.bv_val(1, 1)) && values[reference]);
                    right = right ^ ((right_masks[gate].extract(reference, reference) == ctx.bv_val(1, 1)) && values[reference]);
                }
            }
            expr value = ctx.bool_const(("value_" + std::to_string(address) + "_" + std::to_string(gate)).c_str());
            solve.add(value == (left && right));
            values.push_back(value);
        }
        for (int bit = 0; bit < outputs; ++bit) {
            bool expected = ((table[address] >> bit) & 1) ^ (__builtin_parity(unsigned(address) & output_affine[bit]));
            solve.add((values[width + 1 + final_start + 2 * bit] ^ values[width + 1 + final_start + 2 * bit + 1]) == ctx.bool_val(expected));
        }
    };
    std::vector<bool> used(rows);
    for (int row = 0; row < initial_rows; ++row) {
        add_row(addresses[row]);
        used[addresses[row]] = true;
    }
    std::cerr << "gates " << gate_count << " rows " << initial_rows << std::endl;
    for (int iteration = 0; ; ++iteration) {
        std::cerr << "check " << iteration << std::endl;
        auto result = solve.check();
        if (result != sat) { std::cerr << result << " " << solve.reason_unknown() << std::endl; return 1; }
        auto model = solve.get_model();
        std::vector<unsigned long long> left_values, right_values;
        for (int gate = 0; gate < gate_count; ++gate) {
            left_values.push_back(model.eval(left_masks[gate], true).get_numeral_uint64());
            right_values.push_back(model.eval(right_masks[gate], true).get_numeral_uint64());
        }
        std::vector<int> failed;
        for (int address : addresses) {
            unsigned long long values = (static_cast<unsigned long long>(address) << 1) | 1;
            for (int gate = 0; gate < gate_count; ++gate) {
                unsigned long long value = __builtin_parityll(left_values[gate] & values) & __builtin_parityll(right_values[gate] & values);
                values |= value << (width + 1 + gate);
            }
            bool wrong = false;
            for (int bit = 0; bit < outputs; ++bit) {
                int actual = ((values >> (width + 1 + final_start + 2 * bit)) ^ (values >> (width + 2 + final_start + 2 * bit)) ^ __builtin_parity(unsigned(address) & output_affine[bit])) & 1;
                wrong |= actual != ((table[address] >> bit) & 1);
            }
            if (wrong) failed.push_back(address);
        }
        std::cerr << "errors " << failed.size() << std::endl;
        if (failed.empty()) {
            std::cout << "{\"id\":\"reconvergent_" << width << "\",\"gates\":[";
            auto expression = [&](unsigned long long mask) {
                std::cout << "[";
                bool comma = false;
                for (int reference = 0; reference < width + 1 + gate_count; ++reference) if ((mask >> reference) & 1) { std::cout << (comma ? "," : "") << reference; comma = true; }
                std::cout << "]";
            };
            for (int gate = 0; gate < gate_count; ++gate) {
                std::cout << (gate ? "," : "") << "{\"left\":"; expression(left_values[gate]); std::cout << ",\"right\":"; expression(right_values[gate]); std::cout << "}";
            }
            std::cout << "],\"outputs\":[";
            for (int bit = 0; bit < outputs; ++bit) {
                if (bit) std::cout << ",";
                expression((static_cast<unsigned long long>(output_affine[bit]) << 1) | (1ULL << (width + 1 + final_start + 2 * bit)) | (1ULL << (width + 2 + final_start + 2 * bit)));
            }
            std::cout << "]}" << std::endl;
            return 0;
        }
        int count = 0;
        for (int address : failed) if (!used[address]) { add_row(address); used[address] = true; if (++count == 32) break; }
    }
}
