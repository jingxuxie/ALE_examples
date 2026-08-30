#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <vector>

struct Path {
    std::vector<float> likelihoods;
    std::vector<unsigned char> bits;
    float metric = 0;
};

struct Choice {
    float metric;
    int parent;
    uint64_t flips;
    int last;
    bool operator<(const Choice& other) const { return metric > other.metric; }
};

struct Decoder {
    int limit;
    std::vector<Path> paths;

    void select(const std::vector<Choice>& choices, int offset, int length, bool repetition) {
        std::vector<Path> selected;
        selected.reserve(choices.size());
        for (const auto& choice : choices) {
            selected.push_back(paths[choice.parent]);
            auto& path = selected.back();
            path.metric = choice.metric;
            if (repetition) std::fill(path.bits.begin() + offset, path.bits.begin() + offset + length, choice.flips != 0);
            else {
                uint64_t flips = choice.flips;
                while (flips) {
                    int bit = __builtin_ctzll(flips);
                    path.bits[offset + bit] ^= 1;
                    flips &= flips - 1;
                }
            }
        }
        paths = std::move(selected);
    }

    void decode(int dimension, int degree, int offset) {
        int length = 1 << dimension;
        if (degree < 0) {
            for (auto& path : paths) {
                for (int index = 0; index < length; ++index) {
                    path.metric += std::max(0.0f, -path.likelihoods[offset + index]);
                    path.bits[offset + index] = 0;
                }
            }
            return;
        }
        if (degree == 0) {
            std::vector<Choice> choices;
            for (int parent = 0; parent < static_cast<int>(paths.size()); ++parent) {
                float zero = paths[parent].metric, one = zero;
                for (int index = 0; index < length; ++index) {
                    float value = paths[parent].likelihoods[offset + index];
                    zero += std::max(0.0f, -value);
                    one += std::max(0.0f, value);
                }
                choices.push_back({zero, parent, 0, 0});
                choices.push_back({one, parent, 1, 0});
            }
            std::sort(choices.begin(), choices.end(), [](const Choice& first, const Choice& second) { return first.metric < second.metric; });
            if (choices.size() > static_cast<size_t>(limit)) choices.resize(limit);
            select(choices, offset, length, true);
            return;
        }
        if (degree >= dimension && length <= 64) {
            std::vector<std::vector<int>> orderings;
            std::priority_queue<Choice> heap;
            for (int parent = 0; parent < static_cast<int>(paths.size()); ++parent) {
                std::vector<int> ordering(length);
                std::iota(ordering.begin(), ordering.end(), 0);
                auto& path = paths[parent];
                std::sort(ordering.begin(), ordering.end(), [&](int first, int second) { return std::abs(path.likelihoods[offset + first]) < std::abs(path.likelihoods[offset + second]); });
                orderings.push_back(ordering);
                for (int index = 0; index < length; ++index) path.bits[offset + index] = path.likelihoods[offset + index] < 0;
                heap.push({path.metric, parent, 0, -1});
            }
            std::vector<Choice> choices;
            while (!heap.empty() && choices.size() < static_cast<size_t>(limit)) {
                auto choice = heap.top();
                heap.pop();
                choices.push_back(choice);
                int next = choice.last + 1;
                if (next >= length) continue;
                int next_bit = orderings[choice.parent][next];
                float weight = std::abs(paths[choice.parent].likelihoods[offset + next_bit]);
                heap.push({choice.metric + weight, choice.parent, choice.flips ^ (uint64_t(1) << next_bit), next});
                if (choice.last >= 0) {
                    int previous_bit = orderings[choice.parent][choice.last];
                    float previous_weight = std::abs(paths[choice.parent].likelihoods[offset + previous_bit]);
                    heap.push({choice.metric + weight - previous_weight, choice.parent, choice.flips ^ (uint64_t(1) << next_bit) ^ (uint64_t(1) << previous_bit), next});
                }
            }
            select(choices, offset, length, false);
            return;
        }
        int half = length / 2, child = offset + length;
        for (auto& path : paths) {
            for (int index = 0; index < half; ++index) {
                float first = path.likelihoods[offset + index], second = path.likelihoods[offset + half + index];
                path.likelihoods[child + index] = std::copysign(std::min(std::abs(first), std::abs(second)), first * second);
            }
        }
        decode(dimension - 1, degree - 1, child);
        for (auto& path : paths) {
            for (int index = 0; index < half; ++index) {
                int left = path.bits[child + index];
                path.bits[offset + index] = left;
                path.likelihoods[child + index] = path.likelihoods[offset + half + index] + (left ? -1.0f : 1.0f) * path.likelihoods[offset + index];
            }
        }
        decode(dimension - 1, degree, child);
        for (auto& path : paths) {
            for (int index = 0; index < half; ++index) {
                path.bits[offset + index] ^= path.bits[child + index];
                path.bits[offset + half + index] = path.bits[child + index];
            }
        }
    }
};

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    int width;
    input >> width;
    int rows = 1 << width, degree = std::atoi(argv[2]), limit = std::atoi(argv[3]), trials = std::atoi(argv[4]);
    std::vector<int> likelihoods(rows);
    for (auto& value : likelihoods) input >> value;
    int best = 0;
    for (int value : likelihoods) best += std::max(0, -value);
    std::mt19937 generator(5287);
    std::uniform_real_distribution<float> noise(-0.01f, 0.01f);
    for (int trial = 0; trial < trials; ++trial) {
        std::vector<int> columns(width), permutation(rows);
        for (int bit = 0; bit < width; ++bit) columns[bit] = 1 << bit;
        for (int repeat = 0; repeat < width * 12; ++repeat) {
            int source = generator() % width, target = generator() % width;
            if (source != target) columns[target] ^= columns[source];
        }
        permutation[0] = generator() % rows;
        for (int address = 1; address < rows; ++address) {
            int bit = __builtin_ctz(address);
            permutation[address] = permutation[address ^ (1 << bit)] ^ columns[bit];
        }
        Decoder decoder{limit, {Path{std::vector<float>(rows * 2), std::vector<unsigned char>(rows * 2), 0}}};
        for (int address = 0; address < rows; ++address) decoder.paths[0].likelihoods[address] = likelihoods[permutation[address]] + noise(generator);
        decoder.decode(width, degree, 0);
        for (const auto& path : decoder.paths) {
            int cost = 0, weight = 0;
            for (int address = 0; address < rows; ++address) {
                int bit = path.bits[address];
                cost += std::max(0, bit ? likelihoods[permutation[address]] : -likelihoods[permutation[address]]);
                weight += bit;
            }
            if (cost < best) {
                best = cost;
                std::cout << "trial " << trial << " best " << best << " weight " << weight << std::endl;
                std::vector<int> result(rows);
                for (int address = 0; address < rows; ++address) result[permutation[address]] = path.bits[address];
                std::ofstream output(argv[5]);
                for (int value : result) output << value << ' ';
                output << std::endl;
            }
        }
        std::cout << "done trial " << trial << " best " << best << std::endl;
    }
}
