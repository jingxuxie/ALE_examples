#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>
#include "setorder.h"

class PythonRandom {
    std::array<uint32_t,624> state;
    int offset;
public:
    void seed(uint64_t number) {
        std::vector<uint32_t> keys = {uint32_t(number)};
        if (number>>32) keys.push_back(uint32_t(number>>32));
        seed_words(keys);
    }
    void seed_words(const std::vector<uint32_t>& keys) {
        state[0] = 19650218U;
        for (int index = 1; index < 624; ++index) state[index] = 1812433253U * (state[index-1] ^ (state[index-1] >> 30)) + index;
        int key_count = keys.size();
        int index = 1, key = 0;
        for (int count = std::max(624,key_count); count; --count) {
            state[index] = (state[index] ^ ((state[index-1] ^ (state[index-1] >> 30)) * 1664525U)) + keys[key] + key;
            ++index; ++key;
            if (index >= 624) { state[0] = state[623]; index = 1; }
            if (key >= key_count) key = 0;
        }
        for (int count = 623; count; --count) {
            state[index] = (state[index] ^ ((state[index-1] ^ (state[index-1] >> 30)) * 1566083941U)) - index;
            ++index;
            if (index >= 624) { state[0] = state[623]; index = 1; }
        }
        state[0] = 0x80000000U;
        offset = 624;
    }
    uint32_t next() {
        if (offset >= 624) {
            for (int index = 0; index < 624; ++index) {
                uint32_t mixed = (state[index] & 0x80000000U) | (state[(index+1)%624] & 0x7fffffffU);
                state[index] = state[(index+397)%624] ^ (mixed >> 1) ^ ((mixed & 1) ? 0x9908b0dfU : 0U);
            }
            offset = 0;
        }
        uint32_t value = state[offset++];
        value ^= value >> 11;
        value ^= (value << 7) & 0x9d2c5680U;
        value ^= (value << 15) & 0xefc60000U;
        return value ^ (value >> 18);
    }
    int below(int limit) {
        int bits = 32 - __builtin_clz(limit);
        uint32_t value;
        do { value = next() >> (32-bits); } while (value >= uint32_t(limit));
        return value;
    }
};

int main(int argc, char** argv) {
    uint64_t start = std::strtoull(argv[1], nullptr, 10);
    uint64_t stop = std::strtoull(argv[2], nullptr, 10);
    int variant = argc > 3 ? std::atoi(argv[3]) : 0;
    int support_variant = variant;
    if (variant >= 11 && variant < 16) { int mapping[] = {1,3,6,5,0}; support_variant = mapping[variant-11]; }
    if (variant >= 16) support_variant = (variant-16)%8;
    if (variant >= 32) support_variant = 100;
    bool pre_weights = (variant >= 8 && variant <= 10) || (variant >= 16 && variant < 32) || variant >= 35;
    bool skip_label = std::getenv("SKIP_LABEL");
    bool skip_initial = std::getenv("SKIP_INITIAL");
    std::vector<uint64_t> seed_list;
    std::vector<std::vector<uint32_t>> word_seeds;
    if (std::string(argv[1]) == "words") {
        std::ifstream input(argv[2]);
        int count;
        while (input>>count) {
            std::vector<uint32_t> words(count);
            for (auto& word:words) input>>word;
            word_seeds.push_back(words);
        }
        start=0;stop=word_seeds.size();
    }
    if (std::string(argv[1]) == "list") {
        std::ifstream input(argv[2]);
        uint64_t number;
        while (input >> number) seed_list.push_back(number);
        start = 0;
        stop = seed_list.size();
    }
    int label_start = std::getenv("LABEL_START") ? std::atoi(std::getenv("LABEL_START")) : 0;
    PythonRandom generator;
    std::vector<int> pool(4096), bars(767), weights(768), values(4096), positions(768), initial_weights(768), permutation(4096);
    for (uint64_t seed_index = start; seed_index < stop; ++seed_index) {
        uint64_t seed = seed_list.empty() ? seed_index : seed_list[seed_index];
        if (word_seeds.empty()) generator.seed(seed);
        else generator.seed_words(word_seeds[seed_index]);
        if (skip_initial) generator.below(4096);
        if (pre_weights) {
            std::fill(initial_weights.begin(),initial_weights.begin()+512,1);
            std::fill(initial_weights.begin()+512,initial_weights.end(),2);
            if (variant == 9 || (variant >= 24 && variant < 32) || variant == 37) std::reverse(initial_weights.begin(),initial_weights.end());
            for (int index = 767; index > 0; --index) std::swap(initial_weights[index], initial_weights[generator.below(index+1)]);
        }
        if (support_variant == 100) {
            std::array<int,4097> tree{};
            std::array<bool,4096> available;
            available.fill(true);
            for (int index=1;index<=4096;++index) tree[index]=index&-index;
            int remaining=4096;
            for (int count=0;count<768;++count) {
                int rank=generator.below(remaining)+1,position=0;
                for (int bit=4096;bit;bit>>=1) {
                    int next=position+bit;
                    if (next<=4096 && tree[next]<rank) {rank-=tree[next];position=next;}
                }
                positions[count]=position;
                for (int removed:{position,(position+4095)&4095,(position+1)&4095}) if (available[removed]) {
                    available[removed]=false;--remaining;
                    for (int index=removed+1;index<=4096;index+=index&-index) --tree[index];
                }
            }
            if (variant==33 || variant==36) std::sort(positions.begin(),positions.end());
            if (variant==34) python_set_order(positions);
        } else if (support_variant > 0) {
            std::fill(values.begin(), values.end(), 0);
            if (support_variant == 1 || support_variant == 2 || (variant >= 8 && variant <= 10)) {
                int count = 0;
                while (count < 768) {
                    int position = generator.below(4096);
                    if (values[position] || values[(position+1)&4095] || values[(position+4095)&4095]) continue;
                    positions[count++] = position;
                    values[position] = 1;
                }
            } else if (support_variant == 3 || support_variant == 4 || support_variant == 6 || support_variant == 7) {
                std::iota(pool.begin(), pool.end(), 0);
                if (support_variant == 6 || support_variant == 7) {
                    for (int index = 0; index < 4096; ++index) {
                        int selected = generator.below(4096-index);
                        permutation[index] = pool[selected];
                        pool[selected] = pool[4095-index];
                    }
                    pool = permutation;
                } else for (int index = 4095; index > 0; --index) std::swap(pool[index], pool[generator.below(index+1)]);
                int count = 0;
                for (int position : pool) {
                    if (values[(position+1)&4095] || values[(position+4095)&4095]) continue;
                    positions[count++] = position;
                    values[position] = 1;
                    if (count == 768) break;
                }
            } else {
                std::iota(pool.begin(), pool.end(), 0);
                for (int index = 0; index < 768; ++index) {
                    int selected = generator.below(3328-index);
                    positions[index] = pool[selected];
                    pool[selected] = pool[3327-index];
                }
                std::sort(positions.begin(), positions.end());
                for (int index = 0; index < 768; ++index) positions[index] += index;
            }
            if (support_variant == 2 || support_variant == 4 || support_variant == 7 || support_variant == 10) std::sort(positions.begin(), positions.end());
        } else {
        std::iota(pool.begin(), pool.end(), 0);
        for (int index = 0; index < 767; ++index) {
            int selected = generator.below(3327-index);
            bars[index] = pool[selected];
            pool[selected] = pool[3326-index];
        }
        std::sort(bars.begin(), bars.end());
        int position = 0, boundary = -1;
        for (int index = 0; index < 768; ++index) {
            positions[index] = position;
            if (index < 767) { position += bars[index] - boundary + 1; boundary = bars[index]; }
        }
        }
        if (variant >= 11 && variant < 16) python_set_order(positions);
        if (skip_label) generator.below(4096);
        PythonRandom saved = generator;
        for (int label_mode = label_start; label_mode < (pre_weights ? 1 : 12); ++label_mode) {
        generator = saved;
        std::fill(weights.begin(), weights.begin()+512, 1);
        std::fill(weights.begin()+512, weights.end(), 2);
        if (label_mode == 1 || label_mode == 4) std::reverse(weights.begin(), weights.end());
        if (label_mode < 2) for (int index = 767; index > 0; --index) std::swap(weights[index], weights[generator.below(index+1)]);
        if (label_mode == 2) {
            std::fill(weights.begin(), weights.end(), 1);
            std::iota(pool.begin(), pool.end(), 0);
            for (int index = 0; index < 256; ++index) {
                int selected = generator.below(768-index);
                weights[pool[selected]] = 2;
                pool[selected] = pool[767-index];
            }
        }
        if (label_mode == 5 || label_mode == 6) {
            std::fill(weights.begin(),weights.end(),1);
            std::iota(pool.begin(),pool.begin()+768,0);
            for (int index = 767; index > 0; --index) std::swap(pool[index],pool[generator.below(index+1)]);
            for (int index = 0; index < 256; ++index) weights[pool[label_mode == 5 ? index : 767-index]] = 2;
        }
        if (label_mode == 7) {
            std::fill(weights.begin(),weights.end(),2);
            std::iota(pool.begin(),pool.begin()+768,0);
            for (int index = 0; index < 512; ++index) {
                int selected = generator.below(768-index);
                weights[pool[selected]] = 1;
                pool[selected] = pool[767-index];
            }
        }
        if (label_mode == 8 || label_mode == 9) {
            std::fill(weights.begin(),weights.end(),label_mode == 8 ? 1 : 2);
            int remaining = label_mode == 8 ? 256 : 512;
            while (remaining) {
                int index = generator.below(768);
                if (weights[index] == (label_mode == 8 ? 1 : 2)) {
                    weights[index] = label_mode == 8 ? 2 : 1;
                    --remaining;
                }
            }
        }
        if (label_mode == 10 || label_mode == 11) {
            if (label_mode == 11) std::reverse(weights.begin(),weights.end());
            for (int index = 767; index > 0; --index) std::swap(weights[index],weights[generator.below(index+1)]);
            std::reverse(weights.begin(),weights.end());
        }
        if (pre_weights) weights = initial_weights;
        std::fill(values.begin(), values.end(), 0);
        for (int index = 0; index < 768; ++index) {
            values[positions[index]] = weights[index];
        }
        bool match = true;
        int wanted[] = {1536, 0, 259, 249, 191, 302, 279, 271, 267, 244};
        for (int lag = 2; lag < 10; ++lag) {
            int total = 0;
            for (int index = 0; index < 4096; ++index) total += values[index] * values[(index+lag)&4095];
            if (total != wanted[lag]) { match = false; break; }
        }
        if (match || (argc > 4 && seed == start)) {
            std::ofstream output("seed_candidate.json");
            output << "{\"schema_version\":1,\"a\":[";
            for (int index = 0; index < 4096; ++index) output << (index ? "," : "") << values[index];
            output << "]}\n";
            std::cout << "MATCH " << seed << " variant " << variant << " label " << label_mode << std::endl;
            return 0;
        }
        }
        if (seed % 100000 == 0) std::cout << seed << std::endl;
    }
}
