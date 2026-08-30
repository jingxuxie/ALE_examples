#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <sstream>
#include <string>
#include <vector>

struct PythonRandom {
    uint32_t state[624];
    int index = 624;
    PythonRandom(uint64_t seed) {
        state[0] = 19650218;
        for (int position = 1; position < 624; ++position)
            state[position] = 1812433253U * (state[position - 1] ^ (state[position - 1] >> 30)) + position;
        uint32_t keys[2] = {uint32_t(seed), uint32_t(seed >> 32)};
        int key_count = keys[1] ? 2 : 1;
        int position = 1, key = 0;
        for (int remaining = 624; remaining; --remaining) {
            state[position] = (state[position] ^ ((state[position - 1] ^ (state[position - 1] >> 30)) * 1664525U)) + keys[key] + key;
            ++position;
            if (++key == key_count) key = 0;
            if (position == 624) { state[0] = state[623]; position = 1; }
        }
        for (int remaining = 623; remaining; --remaining) {
            state[position] = (state[position] ^ ((state[position - 1] ^ (state[position - 1] >> 30)) * 1566083941U)) - position;
            if (++position == 624) { state[0] = state[623]; position = 1; }
        }
        state[0] = 0x80000000U;
    }
    uint32_t word() {
        if (index == 624) {
            for (int position = 0; position < 624; ++position) {
                uint32_t combined = (state[position] & 0x80000000U) | (state[(position + 1) % 624] & 0x7fffffffU);
                state[position] = state[(position + 397) % 624] ^ (combined >> 1) ^ ((combined & 1) ? 0x9908b0dfU : 0U);
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
    int below(uint32_t bound) {
        int bits = 32 - __builtin_clz(bound);
        uint32_t result;
        do { result = word() >> (32 - bits); } while (result >= bound);
        return result;
    }
    void shuffle(std::vector<int>& values) {
        for (int position = int(values.size()) - 1; position > 0; --position)
            std::swap(values[position], values[below(position + 1)]);
    }
    std::vector<int> sample(int size, int count) {
        std::vector<int> pool(size), result(count);
        std::iota(pool.begin(), pool.end(), 0);
        for (int position = 0; position < count; ++position) {
            int selected = below(size - position);
            result[position] = pool[selected];
            pool[selected] = pool[size - position - 1];
        }
        return result;
    }
};

std::array<int, 4096> expected;
std::array<int, 4096> candidate;
std::vector<int> preweights;
bool check(uint64_t seed, const std::string& method) {
    for (int lag : {2, 3, 4, 5}) {
        int sum = 0;
        for (int position = 0; position < 4096; ++position) sum += candidate[position] * candidate[(position + lag) & 4095];
        if (sum != expected[lag]) return false;
    }
    for (int lag = 6; lag <= 2048; ++lag) {
        int sum = 0;
        for (int position = 0; position < 4096; ++position) sum += candidate[position] * candidate[(position + lag) & 4095];
        if (sum != expected[lag]) return false;
    }
    std::ofstream output("design.json");
    output << "{\"schema_version\":1,\"a\":[";
    for (int position = 0; position < 4096; ++position) output << (position ? "," : "") << candidate[position];
    output << "]}\n";
    std::cout << "EXACT SEED " << seed << " METHOD " << method << std::endl;
    return true;
}

bool assignments(const std::vector<int>& occupied, PythonRandom generator, uint64_t seed, const std::string& method) {
    if (!preweights.empty()) {
        for (int sorted = 0; sorted < 2; ++sorted) {
            auto support = occupied;
            if (sorted) std::sort(support.begin(), support.end());
            candidate.fill(0);
            for (int index = 0; index < 768; ++index) candidate[support[index]] = preweights[index];
            if (check(seed, "preweights/" + method)) return true;
        }
    }
    for (int variant = 0; variant < 6; ++variant) {
        candidate.fill(0);
        auto state = generator;
        std::vector<int> weights(768, 1);
        if (variant == 0) std::fill(weights.begin(), weights.begin() + 256, 2);
        else std::fill(weights.begin() + 512, weights.end(), 2);
        if (variant == 2 || variant == 3) state.shuffle(weights);
        auto support = occupied;
        if (variant == 3 || variant == 5) std::sort(support.begin(), support.end());
        if (variant >= 4) {
            std::fill(weights.begin(), weights.end(), 1);
            for (int selected : state.sample(768, 256)) weights[selected] = 2;
        }
        for (int position = 0; position < 768; ++position) candidate[support[position]] = weights[position];
        if (check(seed, method + "/" + std::to_string(variant))) return true;
    }
    return false;
}

int main(int argc, char** argv) {
    uint64_t begin = argc > 1 ? std::stoull(argv[1]) : 0;
    uint64_t end = argc > 2 ? std::stoull(argv[2]) : 1000000;
    int modes = argc > 3 ? std::stoi(argv[3]) : 15;
    double time_limit = argc > 4 ? std::stod(argv[4]) : 1800;
    if (begin == end) {
        PythonRandom generator(begin);
        for (int count = 0; count < 8; ++count) std::cout << generator.word() << " ";
        std::cout << std::endl;
        return 0;
    }
    std::ifstream source("../../participant/input/target.json");
    std::string text((std::istreambuf_iterator<char>(source)), std::istreambuf_iterator<char>());
    auto position = text.find('[', text.find("cyclic_autocorrelation"));
    auto ending = text.find(']', position);
    std::string body = text.substr(position + 1, ending - position - 1);
    std::replace(body.begin(), body.end(), ',', ' ');
    std::istringstream numbers(body);
    for (int& value : expected) numbers >> value;
    auto started = std::chrono::steady_clock::now();
    for (uint64_t seed = begin; seed < end; ++seed) {
        if (modes & 1) {
            PythonRandom generator(seed);
            auto bars = generator.sample(3327, 767);
            std::sort(bars.begin(), bars.end());
            std::vector<int> weights(768, 1);
            std::fill(weights.begin() + 512, weights.end(), 2);
            generator.shuffle(weights);
            candidate.fill(0);
            candidate[0] = weights[0];
            for (int index = 1; index < 768; ++index) candidate[bars[index - 1] + index + 1] = weights[index];
            if (check(seed, "bars")) return 0;
        }
        for (int method = 1; method <= 8; ++method) {
            if (!(modes & (1 << method))) continue;
            PythonRandom generator(seed);
            preweights.clear();
            if (modes & 512) {
                preweights.assign(768, 1);
                std::fill(preweights.begin() + 512, preweights.end(), 2);
                generator.shuffle(preweights);
            }
            if (method == 6 || method == 7) {
                std::vector<int> occupied;
                do {
                    occupied = generator.sample(method == 6 ? 3328 : 3329, 768);
                    std::sort(occupied.begin(), occupied.end());
                    for (int rank = 0; rank < 768; ++rank) occupied[rank] += rank;
                } while (occupied[0] == 0 && occupied.back() == 4095);
                if (assignments(occupied, generator, seed, "compressed/" + std::to_string(method))) return 0;
                continue;
            }
            if (method == 8) {
                std::vector<int> order(3328);
                std::iota(order.begin(), order.end(), 0);
                generator.shuffle(order);
                int labels[] = {0, 1, 2};
                int counts[] = {2560, 512, 256};
                do {
                    candidate.fill(0);
                    int position = 0;
                    for (int index : order) {
                        int value = index < counts[labels[0]] ? labels[0] : index < counts[labels[0]] + counts[labels[1]] ? labels[1] : labels[2];
                        candidate[position++] = value;
                        if (value) ++position;
                    }
                    if (check(seed, "compressed_shuffle")) return 0;
                } while (std::next_permutation(labels, labels + 3));
                continue;
            }
            std::vector<int> order(4096), occupied;
            std::iota(order.begin(), order.end(), 0);
            if (method == 1) generator.shuffle(order);
            if (method == 3) order = generator.sample(4096, 4096);
            candidate.fill(0);
            int tree[4097], available_count = 4096;
            bool available[4096];
            std::vector<int> locations(4096);
            for (int index = 0; index < 4096; ++index) { tree[index + 1] = (index + 1) & (-index - 1); available[index] = true; locations[index] = index; }
            for (int index = 0; occupied.size() < 768; ++index) {
                int slot = method == 2 ? generator.below(4096) : order[index];
                if (method == 4) {
                    int rank = generator.below(available_count);
                    slot = 0;
                    for (int bit = 4096; bit; bit >>= 1) {
                        int next = slot + bit;
                        if (next <= 4096 && tree[next] <= rank) { slot = next; rank -= tree[next]; }
                    }
                    for (int removed : {slot, (slot + 1) & 4095, (slot + 4095) & 4095}) {
                        if (!available[removed]) continue;
                        available[removed] = false;
                        --available_count;
                        for (int update = removed + 1; update <= 4096; update += update & -update) --tree[update];
                    }
                }
                if (method == 5) {
                    slot = order[generator.below(available_count)];
                    for (int removed : {slot, (slot + 1) & 4095, (slot + 4095) & 4095}) {
                        if (!available[removed]) continue;
                        available[removed] = false;
                        int location = locations[removed];
                        order[location] = order[--available_count];
                        locations[order[location]] = location;
                    }
                }
                if (!candidate[slot] && !candidate[(slot + 1) & 4095] && !candidate[(slot + 4095) & 4095]) {
                    candidate[slot] = 1;
                    occupied.push_back(slot);
                }
            }
            if (assignments(occupied, generator, seed, std::to_string(method))) return 0;
        }
        if ((seed - begin) % 10000 == 0) {
            double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
            std::cout << "SEED " << seed << " SECONDS " << seconds << std::endl;
            if (seconds > time_limit || std::ifstream("STOP_SEARCH").good()) break;
        }
    }
    std::cout << "FINISHED" << std::endl;
}
