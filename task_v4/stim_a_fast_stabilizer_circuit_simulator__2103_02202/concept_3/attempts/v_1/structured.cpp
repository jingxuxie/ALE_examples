#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

struct PythonRandom {
    std::array<uint32_t, 624> state;
    int index = 624;
    void seed(uint32_t value) {
        state[0] = 19650218U;
        for (int position = 1; position < 624; position++) state[position] = 1812433253U * (state[position - 1] ^ (state[position - 1] >> 30)) + position;
        int position = 1;
        for (int count = 624; count; count--) {
            state[position] = (state[position] ^ ((state[position - 1] ^ (state[position - 1] >> 30)) * 1664525U)) + value;
            position++;
            if (position == 624) {
                state[0] = state[623];
                position = 1;
            }
        }
        for (int count = 623; count; count--) {
            state[position] = (state[position] ^ ((state[position - 1] ^ (state[position - 1] >> 30)) * 1566083941U)) - position;
            position++;
            if (position == 624) {
                state[0] = state[623];
                position = 1;
            }
        }
        state[0] = 0x80000000U;
        index = 624;
    }
    uint32_t next() {
        if (index >= 624) {
            for (int position = 0; position < 624; position++) {
                uint32_t mixed = (state[position] & 0x80000000U) | (state[(position + 1) % 624] & 0x7fffffffU);
                state[position] = state[(position + 397) % 624] ^ (mixed >> 1) ^ (mixed & 1 ? 0x9908b0dfU : 0);
            }
            index = 0;
        }
        uint32_t result = state[index++];
        result ^= result >> 11;
        result ^= (result << 7) & 0x9d2c5680U;
        result ^= (result << 15) & 0xefc60000U;
        result ^= result >> 18;
        return result;
    }
    int below(int bound) {
        int bits = 32 - __builtin_clz(bound);
        uint32_t value;
        do value = next() >> (32 - bits); while (value >= uint32_t(bound));
        return value;
    }
    bool coin(int method) {
        if (method == 0) return below(2);
        if (method == 1) return next() >> 31;
        bool result = (next() >> 31) != 0;
        next();
        return result;
    }
};

struct Gate { int name, first, second; };
std::array<std::vector<std::array<int, 2>>, 4> matchings;
std::vector<std::vector<std::string>> word_sets{
    {"", "H", "S", "HS", "SH", "HSH"},
    {"", "S", "H", "HS", "SH", "HSH"},
    {"", "H", "HS", "HSH", "S", "SH"},
    {"H", "S", "HS", "SH"},
    {"", "H", "S", "HS"},
    {"H", "S", "HS", "SH", "HSH", ""},
    {"", "H", "S", "HS", "SH", "HSH", "SHS"},
    {"H", "S", ""},
    {"H", "S"}
};

int main(int argc, char **argv) {
    int limit = argc > 1 ? std::stoi(argv[1]) : 100;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 600;
    std::vector<uint32_t> seeds{42, 12345, 1234, 1337, 2024, 2025, 2026, 123456, 1234567, 12345678, 123456789, 314159, 271828, 8675309, 0xC1FF0D, 0xC1FF0D36, 0xC1FF, 0xC11FF0D, 0x5EED, 0xC0FFEE, 0xBADC0DE, 20250308, 20250301, 20240517, 20250101, 20250403, 20250321, 20250911, 20251001, 20260101, 20260301, 20260828, 20260217, 20250217, 20250617, 424242, 31415926, 27182818};
    for (int seed = 0; seed < limit; seed++) seeds.push_back(seed);
    for (int row = 0; row < 6; row++) {
        for (int column = 0; column < 5; column++) matchings[column % 2].push_back({6 * row + column, 6 * row + column + 1});
    }
    for (int row = 0; row < 5; row++) {
        for (int column = 0; column < 6; column++) matchings[2 + row % 2].push_back({6 * row + column, 6 * row + column + 6});
    }
    std::ifstream input("target_rows.txt");
    uint64_t target_x, target_z;
    input >> target_x >> target_z;
    auto start = std::chrono::steady_clock::now();
    uint64_t tested = 0;
    for (uint32_t seed : seeds) {
        for (int rounds : {20, 18, 16, 22}) {
            for (int words = 0; words < 12; words++) {
                for (int direction = 0; direction < 5; direction++) {
                    for (int layout = 0; layout < 3; layout++) {
                        std::array<int, 4> order{0, 1, 2, 3};
                        do {
                            PythonRandom randomizer;
                            randomizer.seed(seed);
                            uint64_t xrow = 1, zrow = 0;
                            std::vector<Gate> gates;
                            auto operate = [&](int name, int first, int second = -1) {
                                gates.push_back({name, first, second});
                                if (name == 0) {
                                    if (((xrow ^ zrow) >> first) & 1) {
                                        xrow ^= 1ULL << first;
                                        zrow ^= 1ULL << first;
                                    }
                                } else if (name == 1) {
                                    if ((xrow >> first) & 1) zrow ^= 1ULL << first;
                                } else {
                                    if ((xrow >> first) & 1) xrow ^= 1ULL << second;
                                    if ((zrow >> second) & 1) zrow ^= 1ULL << first;
                                }
                            };
                            auto singles = [&]() {
                                for (int qubit = 0; qubit < 36; qubit++) {
                                    if (words < int(word_sets.size())) {
                                        const auto &options = word_sets[words];
                                        for (char name : options[randomizer.below(options.size())]) operate(name == 'H' ? 0 : 1, qubit);
                                    } else {
                                        if (randomizer.coin(words - 9)) operate(0, qubit);
                                        if (randomizer.coin(words - 9)) operate(1, qubit);
                                    }
                                }
                            };
                            for (int layer = 0; layer < rounds; layer++) {
                                if (layout != 2) singles();
                                for (auto edge : matchings[order[layer % 4]]) {
                                    bool reverse = direction < 3 ? randomizer.coin(direction) : direction == 3 ? false : layer % 2;
                                    operate(2, edge[reverse], edge[!reverse]);
                                }
                                if (layout == 2) singles();
                            }
                            if (layout == 1) singles();
                            tested++;
                            if (xrow == target_x && zrow == target_z) {
                                std::cout << "MATCH " << seed << ' ' << rounds << ' ' << words << ' ' << direction << ' ' << layout << " order ";
                                for (auto value : order) std::cout << value;
                                std::cout << std::endl;
                                std::ofstream output("structured_match.json");
                                output << '[';
                                bool separator = false;
                                for (auto gate : gates) {
                                    if (separator) output << ',';
                                    separator = true;
                                    output << "[\"" << (gate.name == 0 ? "H" : gate.name == 1 ? "S" : "CX") << "\",[" << gate.first;
                                    if (gate.name == 2) output << ',' << gate.second;
                                    output << "]]";
                                }
                                output << ']';
                                return 0;
                            }
                        } while (std::next_permutation(order.begin(), order.end()));
                    }
                }
            }
        }
        std::cout << "seed " << seed << " tested " << tested << std::endl;
        if (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() > seconds) break;
    }
}
