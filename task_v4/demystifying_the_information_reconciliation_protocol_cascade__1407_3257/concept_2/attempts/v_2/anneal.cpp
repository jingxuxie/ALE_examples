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
constexpr int checks = 384;
std::array<std::array<int, 6>, size> signatures;
std::array<std::vector<int>, checks> neighbors;
std::array<std::vector<int>, 7> buckets;
std::array<int, size> degree, location;
std::array<bool, size> selected;
std::array<bool, checks> odd;
int energy = 0;
std::mt19937 generator;

void erase_bucket(int bit) {
    auto& bucket = buckets[degree[bit]];
    int last = bucket.back();
    bucket[location[bit]] = last;
    location[last] = location[bit];
    bucket.pop_back();
}

void insert_bucket(int bit) {
    auto& bucket = buckets[degree[bit]];
    location[bit] = bucket.size();
    bucket.push_back(bit);
}

void toggle(int bit) {
    for (int check : signatures[bit]) {
        int delta = odd[check] ? -1 : 1;
        odd[check] = !odd[check];
        energy += delta;
        for (int neighbor : neighbors[check]) {
            if (!selected[neighbor]) erase_bucket(neighbor);
            degree[neighbor] += delta;
            if (!selected[neighbor]) insert_bucket(neighbor);
        }
    }
}

int sample(const std::array<double, 7>& probabilities) {
    double total = 0;
    for (int score = 0; score <= 6; ++score) total += probabilities[score] * buckets[score].size();
    double draw = std::generate_canonical<double, 53>(generator) * total;
    for (int score = 6; score >= 0; --score) {
        draw -= probabilities[score] * buckets[score].size();
        if (draw < 0 && !buckets[score].empty()) return buckets[score][generator() % buckets[score].size()];
    }
    std::abort();
}

void save(const std::vector<int>& support, const std::string& path) {
    std::ofstream stream(path);
    stream << '[';
    for (size_t index = 0; index < support.size(); ++index) stream << (index ? "," : "") << support[index];
    stream << "]\n";
}

int main(int argc, char** argv) {
    int seed = argc > 1 ? std::stoi(argv[1]) : 1;
    int weight = argc > 2 ? std::stoi(argv[2]) : 18;
    int seconds = argc > 3 ? std::stoi(argv[3]) : 2400;
    generator.seed(seed);
    std::ifstream stream("signatures.txt");
    int count;
    stream >> count;
    for (int bit = 0; bit < size; ++bit) {
        for (int dimension = 0; dimension < 6; ++dimension) {
            int block;
            stream >> block;
            int check = 64 * dimension + block;
            signatures[bit][dimension] = check;
            neighbors[check].push_back(bit);
        }
    }
    for (int bit = 0; bit < size; ++bit) insert_bucket(bit);
    std::vector<int> support;
    for (int index = 0; index < weight; ++index) {
        int bit;
        do bit = generator() % size; while (selected[bit]);
        erase_bucket(bit);
        selected[bit] = true;
        toggle(bit);
        support.push_back(bit);
    }
    int best = energy;
    std::vector<int> best_support = support;
    auto start = std::chrono::steady_clock::now();
    uint64_t iteration = 0;
    std::array<double, 7> probabilities;
    while (true) {
        int phase = iteration % 200000;
        if (phase % 100 == 0) {
            double temperature = 1.1 - 0.8 * phase / 200000.0;
            for (int score = 0; score <= 6; ++score) probabilities[score] = std::exp(2 * (score - 6) / temperature);
        }
        int index = generator() % weight;
        int removed = support[index];
        toggle(removed);
        selected[removed] = false;
        insert_bucket(removed);
        int added = sample(probabilities);
        erase_bucket(added);
        selected[added] = true;
        toggle(added);
        support[index] = added;
        ++iteration;
        if (energy < best) {
            best = energy;
            best_support = support;
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            std::cout << "best " << best << " iterations " << iteration << " time " << elapsed << " support";
            for (int bit : support) std::cout << ' ' << bit;
            std::cout << std::endl;
            save(support, "anneal_best_" + std::to_string(seed) + ".json");
            if (!energy) return 0;
        }
        if (iteration % 10000 == 0) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            if (elapsed > seconds) break;
        }
    }
}
