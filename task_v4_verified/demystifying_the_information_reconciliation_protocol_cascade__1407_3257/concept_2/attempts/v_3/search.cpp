#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

constexpr int size = 8192;
std::array<std::array<int, 6>, size> checks;
std::array<std::array<int, 128>, 384> neighbors;
std::array<int, 384> parity;
std::array<int, 384> occupation;
std::array<int, 384> weights;
std::array<bool, size> selected;
std::mt19937 generator;
int energy;

bool peel_core(const std::vector<int>& support, const std::string& path, int seed) {
    std::array<uint32_t, 384> rows{};
    std::array<int, 384> touched;
    int touched_count = 0;
    for (size_t index = 0; index < support.size(); ++index) {
        for (int check : checks[support[index]]) {
            if (!rows[check]) touched[touched_count++] = check;
            rows[check] |= uint32_t(1) << index;
        }
    }
    std::array<int, 768> queue;
    int head = 0, tail = 0;
    for (int index = 0; index < touched_count; ++index) {
        uint32_t row = rows[touched[index]];
        if (!(row & (row - 1))) queue[tail++] = touched[index];
    }
    uint32_t active = (uint32_t(1) << support.size()) - 1;
    while (head < tail && active) {
        uint32_t row = rows[queue[head++]];
        if (!row || (row & (row - 1))) continue;
        int index = __builtin_ctz(row);
        if (!(active & row)) continue;
        active ^= row;
        for (int check : checks[support[index]]) {
            rows[check] ^= row;
            uint32_t remaining = rows[check];
            if (remaining && !(remaining & (remaining - 1))) queue[tail++] = check;
        }
    }
    int weight = __builtin_popcount(active);
    if (weight < 8 || weight > 18) return false;
    for (int index = 0; index < touched_count; ++index) if (__builtin_parity(rows[touched[index]])) return false;
    std::cout << "PEEL FOUND " << weight << std::endl;
    std::ofstream output(path + "/peeled_core_" + std::to_string(seed) + ".json");
    output << "{\"errors\":[";
    bool first = true;
    for (size_t index = 0; index < support.size(); ++index) {
        if (!(active >> index & 1)) continue;
        if (!first) output << ',';
        output << support[index];
        first = false;
    }
    output << "]}\n";
    return true;
}

bool expand(const std::vector<int>& support, const std::string& path, int seed, const std::vector<int>* explicit_candidates = nullptr) {
    std::array<bool, 384> occupied{};
    for (int position : support) for (int check : checks[position]) occupied[check] = true;
    std::vector<int> candidates = support;
    if (explicit_candidates) candidates = *explicit_candidates;
    else for (int position = 0; position < size; ++position) {
        if (selected[position]) continue;
        int overlap = 0;
        for (int check : checks[position]) overlap += occupied[check];
        if (overlap >= 3) candidates.push_back(position);
    }
    std::shuffle(candidates.begin() + support.size(), candidates.end(), generator);
    if (candidates.size() > 768) candidates.resize(768);
    struct Row {
        std::array<uint64_t, 6> syndrome{};
        std::array<uint64_t, 12> coefficients{};
    };
    std::array<int, 384> pivots;
    pivots.fill(-1);
    std::array<Row, 384> basis;
    int rank = 0;
    for (size_t index = 0; index < candidates.size(); ++index) {
        Row row;
        for (int check : checks[candidates[index]]) row.syndrome[check / 64] ^= uint64_t(1) << (check % 64);
        row.coefficients[index / 64] = uint64_t(1) << (index % 64);
        bool inserted = false;
        for (int pass = 5; pass >= 0; --pass) {
            while (row.syndrome[pass]) {
                int pivot = 64 * pass + 63 - __builtin_clzll(row.syndrome[pass]);
                if (pivots[pivot] == -1) {
                    pivots[pivot] = rank;
                    basis[rank++] = row;
                    inserted = true;
                    break;
                }
                const Row& other = basis[pivots[pivot]];
                for (int word = 0; word < 6; ++word) row.syndrome[word] ^= other.syndrome[word];
                for (int word = 0; word < 12; ++word) row.coefficients[word] ^= other.coefficients[word];
            }
            if (inserted) break;
        }
        if (inserted) continue;
        int weight = 0;
        for (uint64_t word : row.coefficients) weight += __builtin_popcountll(word);
        if (weight < 8 || weight > 18) continue;
        std::cout << "EXPANSION FOUND " << weight << " pool " << candidates.size() << std::endl;
        std::ofstream output(path + "/expanded_core_" + std::to_string(seed) + ".json");
        output << "{\"errors\":[";
        bool first = true;
        for (size_t position_index = 0; position_index < candidates.size(); ++position_index) {
            if (!(row.coefficients[position_index / 64] >> (position_index % 64) & 1)) continue;
            if (!first) output << ',';
            output << candidates[position_index];
            first = false;
        }
        output << "]}\n";
        return true;
    }
    return false;
}

void flip(int position) {
    selected[position] = !selected[position];
    for (int check : checks[position]) {
        occupation[check] += selected[position] ? 1 : -1;
        energy += parity[check] ? -1 : 1;
        parity[check] ^= 1;
    }
}

int gain(int position) {
    int value = 0;
    for (int check : checks[position]) value += weights[check] * (2 * parity[check] - 1);
    return value;
}

void save(const std::string& path, int seed, int best) {
    std::ofstream output(path + "/anneal_" + std::to_string(seed) + ".json");
    output << "{\"energy\":" << best << ",\"errors\":[";
    bool first = true;
    for (int position = 0; position < size; ++position) {
        if (!selected[position]) continue;
        if (!first) output << ',';
        first = false;
        output << position;
    }
    output << "]}\n";
}

int main(int argc, char** argv) {
    std::string path = argv[1];
    int seed = argc > 2 ? std::stoi(argv[2]) : 1;
    int duration = argc > 3 ? std::stoi(argv[3]) : 600;
    generator.seed(seed);
    std::ifstream input(path + "/signatures.txt");
    std::array<int, 384> counts{};
    for (int position = 0; position < size; ++position) {
        for (int pass = 0; pass < 6; ++pass) {
            int block;
            input >> block;
            int check = pass * 64 + block;
            checks[position][pass] = check;
            neighbors[check][counts[check]++] = position;
        }
    }
    auto started = std::chrono::steady_clock::now();
    int best = 384;
    long long total = 0;
    for (int restart = 0;; ++restart) {
        double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
        if (elapsed > duration) break;
        int weight = seed >= 60 ? 18 - 2 * ((restart / 8) % 6) : seed >= 20 ? 18 : 18 - 2 * ((restart / 8) % 4);
        std::vector<int> support;
        parity.fill(0);
        occupation.fill(0);
        selected.fill(false);
        weights.fill(1);
        energy = 0;
        while ((int)support.size() < weight) {
            int position = generator() % size;
            bool allowed = true;
            if (seed >= 20) for (int check : checks[position]) if (occupation[check] >= 2) allowed = false;
            if (!allowed) continue;
            if (!selected[position]) {
                support.push_back(position);
                flip(position);
            }
        }
        int stagnant = 0;
        int local_best = energy;
        for (int iteration = 0; iteration < 30000; ++iteration) {
            ++total;
            if (energy <= 30 && peel_core(support, path, seed)) return 0;
            if (iteration % 500 == 0 && energy <= 24 && expand(support, path, seed)) return 0;
            if (energy < best) {
                best = energy;
                std::cout << "best " << best << " weight " << weight << " restart " << restart << " iteration " << iteration << " total " << total << " seconds " << elapsed << std::endl;
                save(path, seed, best);
                if (best == 0) return 0;
            }
            if (energy < local_best) {
                local_best = energy;
                stagnant = 0;
            } else ++stagnant;
            if (stagnant > 200 && (seed % 3 == 0)) {
                for (int check = 0; check < 384; ++check) {
                    if (parity[check]) ++weights[check];
                    if (iteration % 5000 == 0) weights[check] = (weights[check] + 1) / 2;
                }
                stagnant = 0;
            }
            int old_index = generator() % weight;
            if (generator() % 100 < 85) {
                int old_gain = -100000;
                for (int index = 0; index < weight; ++index) {
                    int value = gain(support[index]) * 100 + int(generator() % (seed % 2 ? 750 : 350));
                    if (value > old_gain) {
                        old_gain = value;
                        old_index = index;
                    }
                }
            }
            int old = support[old_index];
            flip(old);
            int check = generator() % 384;
            while (!parity[check]) check = generator() % 384;
            int replacement = seed >= 60 ? old : -1;
            int best_gain = seed >= 60 ? gain(old) * 100 + int(generator() % 350) : -100000;
            int noise = 100 + (iteration % 5000 < 1000 ? 850 : 250);
            if (seed % 3 == 2) noise = 600;
            for (int position : neighbors[check]) {
                if (selected[position] || position == old) continue;
                bool allowed = true;
                if (seed >= 20) for (int candidate_check : checks[position]) if (occupation[candidate_check] >= 2) allowed = false;
                if (!allowed) continue;
                int value = gain(position) * 100 + int(generator() % noise);
                if (value > best_gain) {
                    best_gain = value;
                    replacement = position;
                }
            }
            if (replacement < 0) replacement = old;
            support[old_index] = replacement;
            flip(replacement);
        }
        if (restart % 20 == 0) std::cout << "progress restart " << restart << " best " << best << " seconds " << elapsed << std::endl;
    }
}
