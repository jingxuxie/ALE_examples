#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <vector>

constexpr int size = 8192;
constexpr int dimensions = 6;
constexpr int checks = 384;

void save(const std::vector<int>& support, const std::string& path) {
    std::ofstream stream(path);
    stream << '[';
    for (size_t index = 0; index < support.size(); ++index) stream << (index ? "," : "") << support[index];
    stream << "]\n";
}

int main(int argc, char** argv) {
    int seed = argc > 1 ? std::stoi(argv[1]) : 1;
    int weight = argc > 2 ? std::stoi(argv[2]) : 18;
    double beta = argc > 3 ? std::stod(argv[3]) : 0.5;
    bool affine = beta < 0;
    beta = std::abs(beta);
    int seconds = argc > 4 ? std::stoi(argv[4]) : 1200;
    bool capacity = argc > 5 ? std::stoi(argv[5]) : false;
    std::ifstream input("signatures.txt");
    int count;
    input >> count;
    std::array<std::array<int, dimensions>, size> signatures;
    std::array<std::vector<int>, checks> members;
    for (int bit = 0; bit < size; ++bit) {
        for (int dimension = 0; dimension < dimensions; ++dimension) {
            int block;
            input >> block;
            int check = 64 * dimension + block;
            signatures[bit][dimension] = check;
            members[check].push_back(bit * dimensions + dimension);
        }
    }
    std::mt19937 generator(seed);
    std::normal_distribution<double> normal(0, 0.15);
    std::vector<double> state(size * dimensions), score(size), consensus(size);
    for (double& value : state) value = normal(generator);
    if (argc > 6) {
        std::ifstream source(argv[6]);
        std::string text((std::istreambuf_iterator<char>(source)), {});
        for (char& character : text) if (character < '0' || character > '9') character = ' ';
        std::istringstream values(text);
        int bit;
        while (values >> bit) for (int dimension = 0; dimension < dimensions; ++dimension) state[bit * dimensions + dimension] += 1;
    }
    std::vector<int> order(size);
    std::iota(order.begin(), order.end(), 0);
    std::vector<unsigned char> selected(size), local(size * dimensions);
    std::vector<int> support;
    int best = 1000;
    auto start = std::chrono::steady_clock::now();
    uint64_t iteration = 0;
    while (true) {
        for (int bit = 0; bit < size; ++bit) {
            score[bit] = 0;
            for (int dimension = 0; dimension < dimensions; ++dimension) score[bit] += state[bit * dimensions + dimension];
        }
        std::nth_element(order.begin(), order.begin() + weight, order.end(), [&](int left, int right) { return score[left] > score[right]; });
        std::fill(selected.begin(), selected.end(), 0);
        support.assign(order.begin(), order.begin() + weight);
        std::array<int, checks> parity{};
        for (int bit : support) {
            selected[bit] = 1;
            for (int check : signatures[bit]) parity[check] ^= 1;
        }
        double shift = double(weight) / size - std::accumulate(score.begin(), score.end(), 0.0) / (size * dimensions);
        for (int bit = 0; bit < size; ++bit) consensus[bit] = affine ? score[bit] / dimensions + shift : selected[bit];
        int energy = std::accumulate(parity.begin(), parity.end(), 0);
        if (energy < best) {
            best = energy;
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            std::cout << "best " << best << " iteration " << iteration << " time " << elapsed << " support";
            for (int bit : support) std::cout << ' ' << bit;
            std::cout << std::endl;
            save(support, "rrr_best_" + std::to_string(seed) + ".json");
            if (!best) return 0;
        }
        if (iteration % 1000 == 0 && energy <= 8) save(support, "rrr_low_" + std::to_string(seed) + ".json");
        for (const auto& group : members) {
            if (capacity) {
                int first = -1, second = -1;
                double first_value = -1e100, second_value = -1e100;
                for (int edge : group) {
                    double reflected = 2 * consensus[edge / dimensions] - state[edge];
                    local[edge] = 0;
                    if (reflected > first_value) {
                        second = first;
                        second_value = first_value;
                        first = edge;
                        first_value = reflected;
                    } else if (reflected > second_value) {
                        second = edge;
                        second_value = reflected;
                    }
                }
                if (first_value + second_value > 1) local[first] = local[second] = 1;
            } else {
                int parity = 0;
                int closest = -1;
                double distance = 1e100;
                for (int edge : group) {
                    double reflected = 2 * consensus[edge / dimensions] - state[edge];
                    local[edge] = reflected > 0.5;
                    parity ^= local[edge];
                    if (std::abs(reflected - 0.5) < distance) {
                        distance = std::abs(reflected - 0.5);
                        closest = edge;
                    }
                }
                if (parity) local[closest] ^= 1;
            }
        }
        for (int bit = 0; bit < size; ++bit) {
            for (int dimension = 0; dimension < dimensions; ++dimension) {
                int edge = bit * dimensions + dimension;
                state[edge] += beta * (double(local[edge]) - consensus[bit]);
            }
        }
        ++iteration;
        if (iteration % 10000 == 0) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            if (elapsed > seconds) break;
        }
    }
}
