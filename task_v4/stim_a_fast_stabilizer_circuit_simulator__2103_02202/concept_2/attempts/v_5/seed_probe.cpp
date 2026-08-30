#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <vector>

struct PythonRandom {
    uint32_t state[624];
    int position = 624;

    explicit PythonRandom(uint32_t seed) {
        state[0] = 19650218;
        for (int index = 1; index < 624; ++index) state[index] = 1812433253U * (state[index - 1] ^ (state[index - 1] >> 30)) + index;
        int index = 1;
        for (int iteration = 0; iteration < 624; ++iteration) {
            state[index] = (state[index] ^ ((state[index - 1] ^ (state[index - 1] >> 30)) * 1664525U)) + seed;
            if (++index == 624) {
                state[0] = state[623];
                index = 1;
            }
        }
        for (int iteration = 0; iteration < 623; ++iteration) {
            state[index] = (state[index] ^ ((state[index - 1] ^ (state[index - 1] >> 30)) * 1566083941U)) - index;
            if (++index == 624) {
                state[0] = state[623];
                index = 1;
            }
        }
        state[0] = 0x80000000U;
    }

    uint32_t next() {
        if (position == 624) {
            for (int index = 0; index < 624; ++index) {
                uint32_t joined = (state[index] & 0x80000000U) | (state[(index + 1) % 624] & 0x7fffffffU);
                state[index] = state[(index + 397) % 624] ^ (joined >> 1) ^ ((joined & 1) ? 0x9908b0dfU : 0);
            }
            position = 0;
        }
        uint32_t value = state[position++];
        value ^= value >> 11;
        value ^= (value << 7) & 0x9d2c5680U;
        value ^= (value << 15) & 0xefc60000U;
        value ^= value >> 18;
        return value;
    }
};

int main(int argc, char** argv) {
    uint32_t first_seed = argc > 1 ? std::strtoul(argv[1], nullptr, 10) : 0;
    uint32_t last_seed = argc > 2 ? std::strtoul(argv[2], nullptr, 10) : 1000000;
    int histogram_mode = argc > 3 ? std::atoi(argv[3]) : 0;
    std::ifstream input("columns.txt");
    int weights[512];
    int target_histogram[193] = {};
    for (int fault = 0; fault < 512; ++fault) {
        uint64_t words[3];
        int observable;
        input >> std::hex >> words[0] >> words[1] >> words[2] >> observable;
        weights[fault] = __builtin_popcountll(words[0]) + __builtin_popcountll(words[1]) + __builtin_popcountll(words[2]);
        ++target_histogram[weights[fault]];
    }
    if (!input) return 2;
    auto started = std::chrono::steady_clock::now();
    PythonRandom test(928331);
    std::cerr << "self test";
    for (int index = 0; index < 6; ++index) std::cerr << ' ' << test.next();
    std::cerr << '\n';
    for (uint32_t seed = first_seed; seed < last_seed; ++seed) {
        PythonRandom generator(seed);
        if (histogram_mode) {
            int histogram[193] = {};
            int excess = 0;
            for (int fault = 0; fault < 512 && excess <= 1; ++fault) {
                int weight = 0;
                for (int word = 0; word < 6; ++word) weight += __builtin_popcount(generator.next());
                if (++histogram[weight] > target_histogram[weight]) ++excess;
            }
            if (excess <= 1) std::cout << "HISTOGRAM seed=" << seed << " excess=" << excess << std::endl;
        } else {
            std::array<uint32_t, 160> values;
            for (auto& value : values) value = generator.next();
            for (int gap = 0; gap <= 5; ++gap) {
                int mismatches = 0;
                for (int fault = 0; fault < 12 && mismatches <= 1; ++fault) {
                    int weight = 0;
                    for (int word = 0; word < 6; ++word) weight += __builtin_popcount(values[fault * (6 + gap) + word]);
                    if (weight != weights[fault]) ++mismatches;
                }
                if (mismatches <= 1) std::cout << "ORDERED seed=" << seed << " gap=" << gap << " mismatches=" << mismatches << std::endl;
            }
            for (int observable_mode = 0; observable_mode < 3; ++observable_mode) {
                int position = 0;
                int mismatches = 0;
                for (int fault = 0; fault < 8 && position + 7 < 160 && mismatches <= 1; ++fault) {
                    while (position + 7 < 160 && (values[position + 6] >> 31)) position += 7;
                    if (position + 7 >= 160) { mismatches = 2; break; }
                    int weight = 0;
                    for (int word = 0; word < 6; ++word) weight += __builtin_popcount(values[position++]);
                    ++position;
                    if (weight != weights[fault]) ++mismatches;
                    if (observable_mode == 1) ++position;
                    if (observable_mode == 2) {
                        while (position < 160 && (values[position] >> 31)) ++position;
                        ++position;
                    }
                }
                if (mismatches <= 1) std::cout << "REJECTION seed=" << seed << " observable=" << observable_mode << " mismatches=" << mismatches << std::endl;
            }
        }
        if ((seed & 262143) == 0) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
            std::cerr << "progress seed=" << seed << " elapsed=" << elapsed << '\n';
        }
    }
}
