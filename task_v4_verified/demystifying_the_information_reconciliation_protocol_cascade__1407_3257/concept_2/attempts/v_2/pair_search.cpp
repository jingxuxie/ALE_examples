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
using Mask = std::array<uint64_t, 4>;
std::array<std::array<int, 6>, size> signatures;
std::array<Mask, size> columns;
std::vector<int> cells[64][64];
std::array<bool, size> selected;
std::mt19937 generator;

void toggle(Mask& syndrome, int bit) {
    for (int dimension = 0; dimension < 4; ++dimension) syndrome[dimension] ^= columns[bit][dimension];
}

int count(const Mask& syndrome) {
    int result = 0;
    for (uint64_t value : syndrome) result += __builtin_popcountll(value);
    return result;
}

void save(const std::vector<int>& support, const std::string& path) {
    std::ofstream stream(path);
    stream << '[';
    for (size_t index = 0; index < support.size(); ++index) stream << (index ? "," : "") << support[index];
    stream << "]\n";
}

struct Candidate {
    int left;
    int right;
    int energy;
};

int main(int argc, char** argv) {
    int seed = argc > 1 ? std::stoi(argv[1]) : 1;
    int weight = argc > 2 ? std::stoi(argv[2]) : 18;
    int seconds = argc > 3 ? std::stoi(argv[3]) : 2400;
    int first = argc > 4 ? std::stoi(argv[4]) : 0;
    int second = argc > 5 ? std::stoi(argv[5]) : 1;
    generator.seed(seed);
    std::ifstream stream("signatures.txt");
    int size_read;
    stream >> size_read;
    std::array<int, 6> dimensions{first, second};
    int target = 2;
    for (int dimension = 0; dimension < 6; ++dimension) if (dimension != first && dimension != second) dimensions[target++] = dimension;
    for (int bit = 0; bit < size; ++bit) {
        std::array<int, 6> original;
        for (int& block : original) stream >> block;
        for (int dimension = 0; dimension < 6; ++dimension) signatures[bit][dimension] = original[dimensions[dimension]];
        for (int dimension = 0; dimension < 4; ++dimension) columns[bit][dimension] = 1ull << signatures[bit][dimension + 2];
        cells[signatures[bit][0]][signatures[bit][1]].push_back(bit);
    }
    std::vector<int> support;
    Mask syndrome{};
    while (support.size() < static_cast<size_t>(weight)) {
        auto& group = cells[generator() % 64][generator() % 64];
        if (group.size() < 2) continue;
        int left = group[generator() % group.size()];
        int right = group[generator() % group.size()];
        if (left == right || selected[left] || selected[right]) continue;
        selected[left] = selected[right] = true;
        support.push_back(left);
        support.push_back(right);
        toggle(syndrome, left);
        toggle(syndrome, right);
    }
    int best = count(syndrome);
    auto start = std::chrono::steady_clock::now();
    uint64_t iteration = 0;
    std::array<double, 17> probabilities;
    std::vector<Candidate> candidates;
    candidates.reserve(4096);
    while (true) {
        int phase = iteration % 200000;
        if (phase % 50 == 0) {
            double temperature = 1.5 - 1.2 * phase / 200000.0;
            for (int change = 0; change <= 16; ++change) probabilities[change] = std::exp(-change / temperature);
        }
        int left_index = generator() % weight;
        int left = support[left_index];
        int right_index = -1;
        int dimension = generator() % 2;
        if (generator() % 5 == 0) {
            do right_index = generator() % weight; while (right_index == left_index);
        } else {
            int matches = 0;
            for (int index = 0; index < weight; ++index) {
                if (index != left_index && signatures[support[index]][dimension] == signatures[left][dimension]) {
                    ++matches;
                    if (generator() % matches == 0) right_index = index;
                }
            }
        }
        if (right_index < 0) continue;
        int right = support[right_index];
        Mask reduced = syndrome;
        toggle(reduced, left);
        toggle(reduced, right);
        selected[left] = selected[right] = false;
        candidates.clear();
        int minimum = 1000;
        auto add = [&](int new_left, int new_right) {
            if (new_left == new_right || selected[new_left] || selected[new_right]) return;
            int energy = 0;
            for (int coordinate = 0; coordinate < 4; ++coordinate) energy += __builtin_popcountll(reduced[coordinate] ^ columns[new_left][coordinate] ^ columns[new_right][coordinate]);
            candidates.push_back({new_left, new_right, energy});
            minimum = std::min(minimum, energy);
        };
        if (signatures[left][dimension] == signatures[right][dimension]) {
            for (int block = 0; block < 64; ++block) {
                const auto& left_cell = dimension ? cells[signatures[left][0]][block] : cells[block][signatures[left][1]];
                const auto& right_cell = dimension ? cells[signatures[right][0]][block] : cells[block][signatures[right][1]];
                for (int new_left : left_cell) for (int new_right : right_cell) add(new_left, new_right);
            }
        } else {
            add(left, right);
            for (int new_left : cells[signatures[left][0]][signatures[right][1]])
                for (int new_right : cells[signatures[right][0]][signatures[left][1]]) add(new_left, new_right);
        }
        if (candidates.empty()) {
            selected[left] = selected[right] = true;
            continue;
        }
        double total = 0;
        for (const auto& candidate : candidates) total += probabilities[candidate.energy - minimum];
        double draw = std::generate_canonical<double, 53>(generator) * total;
        Candidate chosen = candidates.back();
        for (const auto& candidate : candidates) {
            draw -= probabilities[candidate.energy - minimum];
            if (draw < 0) { chosen = candidate; break; }
        }
        support[left_index] = chosen.left;
        support[right_index] = chosen.right;
        selected[chosen.left] = selected[chosen.right] = true;
        syndrome = reduced;
        toggle(syndrome, chosen.left);
        toggle(syndrome, chosen.right);
        ++iteration;
        if (chosen.energy < best) {
            best = chosen.energy;
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            std::cout << "best " << best << " iterations " << iteration << " time " << elapsed << " support";
            for (int bit : support) std::cout << ' ' << bit;
            std::cout << std::endl;
            save(support, "pair_best_" + std::to_string(seed) + ".json");
            if (!best) return 0;
        }
        if (iteration % 10000 == 0) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            if (elapsed > seconds) break;
        }
    }
}
