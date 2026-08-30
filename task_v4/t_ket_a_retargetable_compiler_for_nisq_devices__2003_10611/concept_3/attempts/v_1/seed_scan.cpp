#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

struct PythonRandom {
    uint32_t state[624];
    int position;
    void seed(uint32_t value) {
        state[0] = 19650218u;
        for (int index = 1; index < 624; ++index) state[index] = 1812433253u * (state[index - 1] ^ (state[index - 1] >> 30)) + index;
        int index = 1;
        for (int count = 0; count < 624; ++count) {
            state[index] = (state[index] ^ ((state[index - 1] ^ (state[index - 1] >> 30)) * 1664525u)) + value;
            if (++index >= 624) { state[0] = state[623]; index = 1; }
        }
        for (int count = 0; count < 623; ++count) {
            state[index] = (state[index] ^ ((state[index - 1] ^ (state[index - 1] >> 30)) * 1566083941u)) - index;
            if (++index >= 624) { state[0] = state[623]; index = 1; }
        }
        state[0] = 0x80000000u;
        position = 624;
    }
    uint32_t next() {
        if (position == 624) {
            for (int index = 0; index < 624; ++index) {
                uint32_t value = (state[index] & 0x80000000u) | (state[(index + 1) % 624] & 0x7fffffffu);
                state[index] = state[(index + 397) % 624] ^ (value >> 1) ^ ((value & 1) ? 0x9908b0dfu : 0);
            }
            position = 0;
        }
        uint32_t value = state[position++];
        value ^= value >> 11;
        value ^= (value << 7) & 0x9d2c5680u;
        value ^= (value << 15) & 0xefc60000u;
        return value ^ (value >> 18);
    }
    int below(int bound) {
        int bits = 32 - __builtin_clz(bound);
        int value;
        do { value = next() >> (32 - bits); } while (value >= bound);
        return value;
    }
    double random() { uint32_t first = next() >> 5, second = next() >> 6; return (first * 67108864.0 + second) / 9007199254740992.0; }
};

int main(int argc, char** argv) {
    int chosen = argc > 1 ? std::stoi(argv[1]) : 2;
    int limit = argc > 2 ? std::stoi(argv[2]) : 20000;
    int offset = argc > 3 ? std::stoi(argv[3]) : 0;
    int variant_start = argc > 4 ? std::stoi(argv[4]) : 0;
    int variant_finish = argc > 5 ? std::stoi(argv[5]) : 144;
    std::ifstream input("instances.txt");
    int case_count;
    input >> case_count;
    for (int case_index = 0; case_index < case_count; ++case_index) {
        std::string name;
        int size, edge_count, parity_count, count_budget, depth_budget;
        input >> name >> size >> edge_count >> parity_count >> count_budget >> depth_budget;
        std::vector<std::pair<int, int>> edges(edge_count);
        std::vector<uint32_t> targets(size), parities(parity_count);
        for (auto& edge : edges) input >> edge.first >> edge.second;
        for (auto& mask : targets) input >> mask;
        for (auto& mask : parities) input >> mask;
        if (case_index != chosen) continue;
        std::vector<uint64_t> obligations(1 << size);
        for (int index = 0; index < parity_count; ++index) obligations[parities[index]] = 1ull << index;
        int record = 0;
        PythonRandom random;
        for (int variant = variant_start; variant < variant_finish; ++variant) {
            for (int seed = offset; seed < offset + limit; ++seed) {
                random.seed(seed);
                std::vector<uint32_t> rows(size);
                for (int wire = 0; wire < size; ++wire) rows[wire] = 1u << wire;
                auto shuffled = edges;
                std::vector<std::pair<int, int>> gates;
                uint64_t visited = 0;
                int style = variant / 72;
                int direction_style = variant % 6;
                int extras = (variant / 6) % 3;
                bool skip = (variant / 18) % 2;
                bool reset = (variant / 36) % 2;
                for (int layer = 0; layer < 60; ++layer) {
                    if (reset) shuffled = edges;
                    if (style == 2) {
                        shuffled.assign(edge_count, {-2, -2});
                    } else if (style == 3) {
                        shuffled.clear();
                        std::vector<int> vertices(size);
                        for (int wire = 0; wire < size; ++wire) vertices[wire] = wire;
                        for (int index = size - 1; index > 0; --index) std::swap(vertices[index], vertices[random.below(index + 1)]);
                        uint32_t matched = 0;
                        for (int vertex : vertices) {
                            if (matched & (1u << vertex)) continue;
                            std::vector<int> neighbors;
                            for (auto edge : edges) {
                                int neighbor = edge.first == vertex ? edge.second : edge.second == vertex ? edge.first : -1;
                                if (neighbor >= 0 && !(matched & (1u << neighbor))) neighbors.push_back(neighbor);
                            }
                            if (neighbors.empty()) continue;
                            int neighbor = neighbors[random.below(neighbors.size())];
                            matched |= (1u << vertex) | (1u << neighbor);
                            shuffled.push_back({vertex, neighbor});
                        }
                    } else if (!style) {
                        for (int index = edge_count - 1; index > 0; --index) std::swap(shuffled[index], shuffled[random.below(index + 1)]);
                    } else {
                        shuffled.clear();
                        std::vector<int> vertices(size);
                        for (int wire = 0; wire < size; ++wire) vertices[wire] = wire;
                        for (int index = size - 1; index > 0; --index) std::swap(vertices[index], vertices[random.below(index + 1)]);
                        for (int vertex : vertices) shuffled.push_back({vertex, -1});
                    }
                    uint32_t used = 0;
                    for (auto [control, target] : shuffled) {
                        if (control == -2) {
                            std::vector<std::pair<int, int>> choices;
                            for (auto edge : edges) if (!(used & ((1u << edge.first) | (1u << edge.second)))) choices.push_back(edge);
                            if (choices.empty()) break;
                            auto choice = choices[random.below(choices.size())];
                            control = choice.first;
                            target = choice.second;
                        }
                        if (target < 0) {
                            if (used & (1u << control)) continue;
                            std::vector<int> neighbors;
                            for (auto edge : edges) {
                                int neighbor = edge.first == control ? edge.second : edge.second == control ? edge.first : -1;
                                if (neighbor >= 0 && !(used & (1u << neighbor))) neighbors.push_back(neighbor);
                            }
                            if (neighbors.empty()) continue;
                            target = neighbors[random.below(neighbors.size())];
                        }
                        if (used & ((1u << control) | (1u << target))) continue;
                        if (skip && random.random() > 0.85) continue;
                        int direction = direction_style / 2;
                        bool reverse = direction == 0 ? random.random() < 0.5 : direction == 1 ? random.below(2) : random.next() >> 31;
                        if (direction_style % 2) reverse = !reverse;
                        if (reverse) std::swap(control, target);
                        rows[target] ^= rows[control];
                        used |= (1u << control) | (1u << target);
                        gates.push_back({control, target});
                        visited |= obligations[rows[target]];
                        if (extras == 1) random.random();
                        if (rows[0] == targets[0] && rows == targets) {
                            std::cout << "FOUND " << name << ' ' << variant << ' ' << seed << ' ' << gates.size() << std::endl;
                            std::ofstream output("seed_" + name + ".txt");
                            for (auto gate : gates) output << gate.first << ' ' << gate.second << '\n';
                            return 0;
                        }
                    }
                    if (extras == 2) random.below(size);
                }
                int score = __builtin_popcountll(visited);
                if (score > record) {
                    record = score;
                    std::cout << "record " << name << " variant " << variant << " seed " << seed << " hits " << score << std::endl;
                }
            }
            std::cout << "completed variant " << variant << std::endl;
        }
    }
}
