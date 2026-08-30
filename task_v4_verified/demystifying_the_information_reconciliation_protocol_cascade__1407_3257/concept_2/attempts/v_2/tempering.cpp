#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <mutex>
#include <random>
#include <sstream>
#include <string>
#include <vector>
#include <omp.h>

constexpr int size = 8192;
constexpr int checks = 384;
using Mask = std::array<uint64_t, 6>;
std::array<std::array<int, 6>, size> signatures;
std::array<std::vector<int>, checks> neighbors;
std::array<Mask, size> columns;
std::atomic<bool> found{false};
std::atomic<int> global_best{1000};
std::mutex output_mutex;
std::chrono::steady_clock::time_point start;
int tag;
int active_begin = 0;
int active_count = size;
bool enforce_capacity = false;
std::vector<int> initial_support;

void save(const std::vector<int>& support, const std::string& path) {
    std::ofstream stream(path);
    stream << '[';
    for (size_t index = 0; index < support.size(); ++index) stream << (index ? "," : "") << support[index];
    stream << "]\n";
}

struct State {
    std::array<std::vector<int>, 7> buckets;
    std::array<int, size> degree{}, location{};
    std::array<int, size> blocked{};
    std::array<int, checks> check_counts{};
    std::array<bool, size> selected{};
    std::array<bool, checks> odd{};
    std::vector<int> support;
    std::mt19937 generator;
    int energy = 0;

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

    void toggle(int bit, int direction) {
        for (int check : signatures[bit]) {
            int delta = odd[check] ? -1 : 1;
            int previous_count = check_counts[check];
            check_counts[check] += direction;
            int capacity_delta = enforce_capacity ? (check_counts[check] == 2) - (previous_count == 2) : 0;
            odd[check] = !odd[check];
            energy += delta;
            for (int neighbor : neighbors[check]) {
                if (!selected[neighbor] && !blocked[neighbor]) erase_bucket(neighbor);
                degree[neighbor] += delta;
                blocked[neighbor] += capacity_delta;
                if (!selected[neighbor] && !blocked[neighbor]) insert_bucket(neighbor);
            }
        }
    }

    State(int seed, int weight) : generator(seed) {
        for (int bit = 0; bit < size; ++bit) {
            if (bit >= active_begin && bit < active_begin + active_count) insert_bucket(bit);
            else selected[bit] = true;
        }
        for (int index = 0; index < weight; ++index) {
            int bit;
            if (initial_support.size() == static_cast<size_t>(weight)) bit = initial_support[index];
            else do bit = active_begin + generator() % active_count; while (selected[bit] || blocked[bit]);
            erase_bucket(bit);
            selected[bit] = true;
            toggle(bit, 1);
            support.push_back(bit);
        }
    }

    void check_core() {
        std::array<Mask, checks> basis{};
        std::array<uint32_t, checks> supports{};
        for (size_t index = 0; index < support.size(); ++index) {
            Mask value = columns[support[index]];
            uint32_t subset = 1u << index;
            bool inserted = false;
            for (int dimension = 5; dimension >= 0 && !inserted; --dimension) {
                while (value[dimension]) {
                    int pivot = 64 * dimension + 63 - __builtin_clzll(value[dimension]);
                    if (!supports[pivot]) {
                        basis[pivot] = value;
                        supports[pivot] = subset;
                        inserted = true;
                        break;
                    }
                    for (int coordinate = 0; coordinate <= dimension; ++coordinate) value[coordinate] ^= basis[pivot][coordinate];
                    subset ^= supports[pivot];
                }
            }
            if (!inserted && __builtin_popcount(subset) >= 8 && __builtin_popcount(subset) <= 18) {
                std::vector<int> core;
                for (size_t position = 0; position < support.size(); ++position) if (subset >> position & 1) core.push_back(support[position]);
                std::lock_guard<std::mutex> lock(output_mutex);
                save(core, "tempering_core_" + std::to_string(tag) + ".json");
                std::cout << "CORE";
                for (int bit : core) std::cout << ' ' << bit;
                std::cout << std::endl;
                found = true;
                return;
            }
        }
    }

    void advance(int steps, double temperature) {
        std::array<double, 7> probabilities;
        for (int score = 0; score <= 6; ++score) probabilities[score] = std::exp(2 * (score - 6) / temperature);
        for (int iteration = 0; iteration < steps && !found; ++iteration) {
            int index = generator() % support.size();
            int removed = support[index];
            toggle(removed, -1);
            selected[removed] = false;
            insert_bucket(removed);
            double total = 0;
            for (int score = 0; score <= 6; ++score) total += probabilities[score] * buckets[score].size();
            double draw = std::generate_canonical<double, 53>(generator) * total;
            int added = -1;
            for (int score = 6; score >= 0; --score) {
                draw -= probabilities[score] * buckets[score].size();
                if (draw < 0 && !buckets[score].empty()) {
                    added = buckets[score][generator() % buckets[score].size()];
                    break;
                }
            }
            if (added < 0) std::abort();
            erase_bucket(added);
            selected[added] = true;
            toggle(added, 1);
            support[index] = added;
            if (energy < global_best) {
                std::lock_guard<std::mutex> lock(output_mutex);
                if (energy < global_best) {
                    global_best = energy;
                    double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
                    std::cout << "best " << energy << " time " << elapsed << " temperature " << temperature << " support";
                    for (int bit : support) std::cout << ' ' << bit;
                    std::cout << std::endl;
                    save(support, "tempering_best_" + std::to_string(tag) + ".json");
                }
            }
            if (iteration % 500 == 0 || !energy) check_core();
        }
    }
};

int main(int argc, char** argv) {
    tag = argc > 1 ? std::stoi(argv[1]) : 1;
    int weight = argc > 2 ? std::stoi(argv[2]) : 18;
    int seconds = argc > 3 ? std::stoi(argv[3]) : 1800;
    int replicas = argc > 4 ? std::stoi(argv[4]) : 16;
    active_begin = argc > 5 ? std::stoi(argv[5]) : 0;
    active_count = argc > 6 ? std::stoi(argv[6]) : size;
    enforce_capacity = argc > 7 ? std::stoi(argv[7]) : false;
    if (argc > 8) {
        std::ifstream initial_file(argv[8]);
        std::string contents((std::istreambuf_iterator<char>(initial_file)), {});
        for (char& character : contents) if (character < '0' || character > '9') character = ' ';
        std::istringstream initial_input(contents);
        int bit;
        while (initial_input >> bit) initial_support.push_back(bit);
    }
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
            columns[bit][dimension] = 1ull << block;
        }
    }
    start = std::chrono::steady_clock::now();
    std::vector<std::unique_ptr<State>> states;
    std::vector<double> temperatures;
    for (int replica = 0; replica < replicas; ++replica) {
        states.push_back(std::make_unique<State>(tag * 1000 + replica, weight));
        temperatures.push_back(0.3 * std::pow(1.2 / 0.3, double(replica) / (replicas - 1)));
    }
    omp_set_num_threads(replicas);
    std::mt19937 generator(tag);
    int round = 0;
    while (!found) {
        #pragma omp parallel for schedule(static)
        for (int replica = 0; replica < replicas; ++replica) states[replica]->advance(1000, temperatures[replica]);
        for (int replica = round % 2; replica + 1 < replicas; replica += 2) {
            double exponent = (1 / temperatures[replica] - 1 / temperatures[replica + 1]) * (states[replica]->energy - states[replica + 1]->energy);
            if (std::generate_canonical<double, 53>(generator) < std::exp(exponent)) std::swap(states[replica], states[replica + 1]);
        }
        ++round;
        if (round % 10 == 0) {
            for (int replica = 0; replica < std::min(replicas, 4); ++replica) {
                if (states[replica]->energy <= 8) save(states[replica]->support, "tempering_low_" + std::to_string(tag) + "_" + std::to_string(replica) + ".json");
            }
        }
        double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        if (round % 100 == 0) {
            std::lock_guard<std::mutex> lock(output_mutex);
            std::cout << "round " << round << " time " << elapsed << " energies";
            for (const auto& state : states) std::cout << ' ' << state->energy;
            std::cout << std::endl;
        }
        if (elapsed > seconds) break;
    }
}
