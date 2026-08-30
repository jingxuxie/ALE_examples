#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <mutex>
#include <omp.h>

bool numpy_mode = false;

std::array<uint32_t, 624> python_state(uint32_t seed) {
    std::array<uint32_t, 624> state;
    state[0] = numpy_mode ? seed : 19650218;
    for (int index = 1; index < 624; ++index) state[index] = 1812433253u * (state[index - 1] ^ (state[index - 1] >> 30)) + index;
    if (numpy_mode) return state;
    int index = 1;
    for (int count = 0; count < 624; ++count) {
        state[index] = (state[index] ^ ((state[index - 1] ^ (state[index - 1] >> 30)) * 1664525u)) + seed;
        ++index;
        if (index >= 624) { state[0] = state[623]; index = 1; }
    }
    for (int count = 0; count < 623; ++count) {
        state[index] = (state[index] ^ ((state[index - 1] ^ (state[index - 1] >> 30)) * 1566083941u)) - index;
        ++index;
        if (index >= 624) { state[0] = state[623]; index = 1; }
    }
    state[0] = 0x80000000u;
    return state;
}

std::array<uint32_t, 624> next_block(std::array<uint32_t, 624>& state) {
    for (int position = 0; position < 624; ++position) {
        uint32_t word = (state[position] & 0x80000000u) | (state[(position + 1) % 624] & 0x7fffffffu);
        state[position] = state[(position + 397) % 624] ^ (word >> 1) ^ ((word & 1) ? 0x9908b0dfu : 0);
    }
    auto output = state;
    for (auto& word : output) {
        word ^= word >> 11;
        word ^= (word << 7) & 0x9d2c5680u;
        word ^= (word << 15) & 0xefc60000u;
        word ^= word >> 18;
    }
    return output;
}

int main(int argc, char** argv) {
    uint32_t begin = argc > 1 ? std::stoul(argv[1]) : 0;
    uint32_t end = argc > 2 ? std::stoul(argv[2]) : 30000000;
    int seconds = argc > 3 ? std::stoi(argv[3]) : 400;
    int blocks = argc > 4 ? std::stoi(argv[4]) : 1;
    numpy_mode = argc > 5;
    auto test_state = python_state(760142);
    auto test = next_block(test_state);
    std::cout << "test";
    for (int index = 0; index < 8; ++index) std::cout << ' ' << test[index];
    std::cout << std::endl;
    std::array<uint32_t, 8> target;
    std::ifstream input("tail.txt");
    for (auto& value : target) input >> value;
    std::array<uint32_t, 8> prefix;
    std::ifstream prefix_input("prefix.txt");
    for (auto& value : prefix) prefix_input >> value;
    omp_set_num_threads(128);
    std::atomic<bool> found{false}, stopped{false};
    std::atomic<uint64_t> completed{0};
    std::mutex output_mutex;
    auto start = std::chrono::steady_clock::now();
    #pragma omp parallel for schedule(dynamic, 1000)
    for (uint64_t seed = begin; seed < end; ++seed) {
        if (found || stopped) continue;
        auto state = python_state(seed);
        for (int block_index = 0; block_index < blocks; ++block_index) {
        auto random = next_block(state);
        for (int offset = 0; offset < 612; ++offset) {
            uint32_t first_value = numpy_mode ? random[offset] & 8191 : random[offset] >> 18;
            bool sample = first_value == prefix[0];
            if (first_value != target[0] && !sample) continue;
            const auto& pattern = sample ? prefix : target;
            int position = offset + 1;
            int matched = 1;
            while (matched < 8 && position < 624) {
                uint32_t value = numpy_mode ? random[position++] & 8191 : random[position++] >> 19;
                if (value >= uint32_t(8192 - matched)) continue;
                if (value != pattern[matched]) break;
                ++matched;
            }
            if (matched == 8) {
                std::lock_guard<std::mutex> lock(output_mutex);
                int global_offset = block_index * 624 + offset;
                std::cout << "FOUND SEED " << seed << " OFFSET " << global_offset << " SAMPLE " << sample << std::endl;
                std::ofstream result("seed_found.txt");
                result << seed << ' ' << global_offset << ' ' << (int(sample) + 2 * numpy_mode) << '\n';
                found = true;
            }
        }
        }
        uint64_t count = ++completed;
        if (count % 1000000 == 0) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            std::lock_guard<std::mutex> lock(output_mutex);
            std::cout << "completed " << count << " time " << elapsed << " seed " << seed << std::endl;
            if (elapsed > seconds) stopped = true;
        }
    }
}
