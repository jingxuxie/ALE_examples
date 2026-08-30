#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

struct PythonMT {
    std::array<uint32_t, 624> state;
    int index = 624;
    explicit PythonMT(uint32_t seed) {
        state[0] = 19650218U;
        for (int offset = 1; offset < 624; ++offset) state[offset] = 1812433253U * (state[offset - 1] ^ (state[offset - 1] >> 30)) + offset;
        int offset = 1;
        for (int count = 0; count < 624; ++count) {
            state[offset] = (state[offset] ^ ((state[offset - 1] ^ (state[offset - 1] >> 30)) * 1664525U)) + seed;
            if (++offset >= 624) { state[0] = state[623]; offset = 1; }
        }
        for (int count = 0; count < 623; ++count) {
            state[offset] = (state[offset] ^ ((state[offset - 1] ^ (state[offset - 1] >> 30)) * 1566083941U)) - offset;
            if (++offset >= 624) { state[0] = state[623]; offset = 1; }
        }
        state[0] = 0x80000000U;
    }
    uint32_t next() {
        if (index == 624) {
            for (int offset = 0; offset < 624; ++offset) {
                uint32_t value = (state[offset] & 0x80000000U) | (state[(offset + 1) % 624] & 0x7fffffffU);
                state[offset] = state[(offset + 397) % 624] ^ (value >> 1) ^ ((value & 1) ? 0x9908b0dfU : 0);
            }
            index = 0;
        }
        uint32_t value = state[index++];
        value ^= value >> 11;
        value ^= (value << 7) & 0x9d2c5680U;
        value ^= (value << 15) & 0xefc60000U;
        value ^= value >> 18;
        return value;
    }
};

int main(int argc, char** argv) {
    std::string path = argv[1];
    int first_seed = std::stoi(argv[2]);
    int last_seed = std::stoi(argv[3]);
    int offsets = std::stoi(argv[4]);
    std::array<std::array<int, 20>, 10> targets;
    std::array<std::vector<int>, 8192> first_matches;
    std::ifstream input(path + "/shuffle_targets.txt");
    for (int target = 0; target < 10; ++target) {
        for (int offset = 0; offset < 20; ++offset) input >> targets[target][offset];
        first_matches[targets[target][0]].push_back(target);
    }
    PythonMT test(760142);
    std::cout << "MT TEST";
    for (int count = 0; count < 5; ++count) std::cout << ' ' << test.next();
    std::cout << std::endl;
    std::vector<uint32_t> words(offsets + 100);
    auto started = std::chrono::steady_clock::now();
    for (int seed = first_seed; seed < last_seed; ++seed) {
        PythonMT generator(seed);
        for (auto& word : words) word = generator.next();
        for (int start = 0; start < offsets; ++start) {
            int first = words[start] >> 18;
            if (first >= 8192 || first_matches[first].empty()) continue;
            for (int target_index : first_matches[first]) {
                const auto& target = targets[target_index];
                std::array<int, 20> keys, values;
                int cursor = start;
                int matches = 0;
                for (int offset = 0; offset < 20; ++offset) {
                    int position = 8192;
                    while (position >= 8192 - offset) position = words[cursor++] >> (offset == 0 ? 18 : 19);
                    int value = position;
                    int replacement = 8191 - offset;
                    for (int previous = offset - 1; previous >= 0; --previous) {
                        if (keys[previous] == position) { value = values[previous]; break; }
                    }
                    for (int previous = offset - 1; previous >= 0; --previous) {
                        if (keys[previous] == 8191 - offset) { replacement = values[previous]; break; }
                    }
                    keys[offset] = position;
                    values[offset] = replacement;
                    matches += value == target[offset];
                    if (offset == 3 && matches < 3) break;
                }
                if (matches < 17) continue;
                std::cout << "FOUND " << seed << ' ' << start << ' ' << target_index << ' ' << matches << std::endl;
                std::ofstream output(path + "/seed_match.json");
                output << "{\"seed\":" << seed << ",\"offset\":" << start << ",\"pass\":" << target_index / 2 + 1 << ",\"method\":\"" << (target_index % 2 ? "sample" : "shuffle") << "\"}\n";
                return 0;
            }
        }
        if ((seed - first_seed) % 10000 == 0) std::cout << "progress " << seed << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
    }
}
