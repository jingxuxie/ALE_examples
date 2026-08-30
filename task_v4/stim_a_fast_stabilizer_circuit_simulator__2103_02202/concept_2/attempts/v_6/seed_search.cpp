#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <numeric>
#include <vector>

struct PythonRandom {
    std::array<uint32_t, 624> state;
    int position = 624;

    explicit PythonRandom(uint64_t seed) {
        state[0] = 19650218;
        for (int index = 1; index < 624; ++index) state[index] = 1812433253U * (state[index-1] ^ (state[index-1] >> 30)) + index;
        uint32_t keys[2] = {uint32_t(seed), uint32_t(seed >> 32)};
        int key_count = keys[1] ? 2 : 1;
        int index = 1;
        int key_index = 0;
        for (int remaining = 624; remaining; --remaining) {
            state[index] = (state[index] ^ ((state[index-1] ^ (state[index-1] >> 30)) * 1664525U)) + keys[key_index] + key_index;
            ++index;
            ++key_index;
            if (index >= 624) { state[0] = state[623]; index = 1; }
            if (key_index >= key_count) key_index = 0;
        }
        for (int remaining = 623; remaining; --remaining) {
            state[index] = (state[index] ^ ((state[index-1] ^ (state[index-1] >> 30)) * 1566083941U)) - index;
            if (++index >= 624) { state[0] = state[623]; index = 1; }
        }
        state[0] = 0x80000000;
    }

    uint32_t next() {
        if (position == 624) {
            for (int index = 0; index < 624; ++index) {
                uint32_t mixed = (state[index] & 0x80000000) | (state[(index+1)%624] & 0x7fffffff);
                state[index] = state[(index+397)%624] ^ (mixed >> 1) ^ ((mixed & 1) ? 0x9908b0df : 0);
            }
            position = 0;
        }
        uint32_t result = state[position++];
        result ^= result >> 11;
        result ^= (result << 7) & 0x9d2c5680;
        result ^= (result << 15) & 0xefc60000;
        return result ^ (result >> 18);
    }

    uint32_t below(uint32_t bound) {
        int bits = 32 - __builtin_clz(bound);
        uint32_t result;
        do { result = next() >> (32-bits); } while (result >= bound);
        return result;
    }

    void advance(int amount) {
        for (int iteration = 0; iteration < amount; ++iteration) next();
    }
};

uint64_t columns[512][3];
int observable[512];
bool success = false;

void found(const std::vector<int>& support, uint64_t seed, int offset, int mode) {
    uint64_t syndrome[3] = {};
    int logical = 0;
    for (int fault : support) {
        for (int word = 0; word < 3; ++word) syndrome[word] ^= columns[fault][word];
        logical ^= observable[fault];
    }
    if (syndrome[0] || syndrome[1] || syndrome[2] || !logical) return;
    success = true;
    std::ofstream output("seed_witness.json");
    output << "{\"faults\": [";
    for (size_t index = 0; index < support.size(); ++index) {
        if (index) output << ", ";
        output << support[index];
    }
    output << "]}\n";
    std::cerr << "FOUND seed=" << seed << " offset=" << offset << " mode=" << mode << " weight=" << support.size() << '\n';
}

void sample(PythonRandom random, uint64_t seed, int offset, int mode) {
    std::array<uint64_t, 8> chosen = {};
    std::array<int, 512> pool;
    if (mode >= 2) std::iota(pool.begin(), pool.end(), 0);
    std::vector<int> support;
    uint64_t low = 0;
    if (mode == 1) { support.push_back(511); low = columns[511][0]; }
    for (int count = 0; support.size() < 36; ++count) {
        int selected;
        if (mode <= 1) {
            do { selected = random.below(mode ? 511 : 512); } while ((chosen[selected >> 6] >> (selected & 63)) & 1);
            chosen[selected >> 6] |= uint64_t(1) << (selected & 63);
        } else {
            int position = random.below(512 - count);
            selected = pool[position];
            pool[position] = pool[511 - count];
        }
        support.push_back(selected);
        low ^= columns[selected][0];
        if (!low) found(support, seed, offset, mode);
    }
}

int main(int argc, char** argv) {
    uint64_t begin = argc > 1 ? std::strtoull(argv[1], nullptr, 0) : 0;
    uint64_t end = argc > 2 ? std::strtoull(argv[2], nullptr, 0) : 1000000;
    int level = argc > 3 ? std::atoi(argv[3]) : 0;
    std::ifstream input("columns.txt");
    for (int fault = 0; fault < 512; ++fault) input >> std::hex >> columns[fault][0] >> columns[fault][1] >> columns[fault][2] >> observable[fault];
    if (!input) return 2;
    if (level == -1) {
        PythonRandom random(begin);
        for (int index = 0; index < 10; ++index) std::cout << random.next() << '\n';
        return 0;
    }
    auto start = std::chrono::steady_clock::now();
    for (uint64_t seed = begin; seed < end && !success; ++seed) {
        PythonRandom random(seed);
        sample(random, seed, 0, 0);
        sample(random, seed, 0, 1);
        sample(random, seed, 0, 2);
        if (level >= 1) {
            random.advance(3066);
            sample(random, seed, 3066, 0);
            sample(random, seed, 3066, 1);
            random.advance(6);
            sample(random, seed, 3072, 0);
            sample(random, seed, 3072, 1);
            sample(random, seed, 3072, 2);
            random.advance(512);
            sample(random, seed, 3584, 0);
            sample(random, seed, 3584, 2);
        }
        if ((seed & 262143) == 0) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            std::cerr << "seed=" << seed << " seconds=" << elapsed << '\n';
        }
    }
    return success ? 0 : 1;
}
