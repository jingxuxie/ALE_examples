#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>

constexpr int length = 2048;
constexpr int checks = 384;
using Syndrome = std::array<uint64_t, 6>;
std::array<std::array<int, 6>, length> incidence;
std::array<std::array<int, 32>, checks> members;
std::array<std::array<int, 6>, length> edges;
std::array<Syndrome, length> columns;
std::mt19937 generator(345778);
int best_weight = 1000;

bool bit(const Syndrome& value, int position) {
    return (value[position / 64] >> (position % 64)) & 1;
}

void add(Syndrome& destination, const Syndrome& source) {
    for (int word = 0; word < 6; ++word) destination[word] ^= source[word];
}

bool save(const std::vector<int>& support) {
    if (support.size() >= size_t(best_weight)) return false;
    Syndrome syndrome{};
    for (int position : support) add(syndrome, columns[position]);
    for (auto word : syndrome) if (word) return false;
    best_weight = support.size();
    std::cout << "BEST " << best_weight << ':';
    for (int position : support) std::cout << ' ' << position;
    std::cout << std::endl;
    std::ofstream output("bp_core.json");
    output << "{\"errors\": [";
    for (size_t index = 0; index < support.size(); ++index) output << (index ? ", " : "") << support[index];
    output << "]}\n";
    return best_weight >= 8 && best_weight <= 18;
}

bool osd(const std::array<float, length>& reliability, const std::vector<int>& forced, int order_depth) {
    std::array<int, length> order;
    std::iota(order.begin(), order.end(), 0);
    std::array<bool, length> excluded{};
    Syndrome target{};
    for (int position : forced) {
        excluded[position] = true;
        add(target, columns[position]);
    }
    std::sort(order.begin(), order.end(), [&](int left, int right) {return reliability[left] < reliability[right];});
    std::array<Syndrome, checks> basis{};
    std::array<Syndrome, checks> representations{};
    std::array<int, checks> pivots;
    pivots.fill(-1);
    std::vector<int> selected;
    std::vector<std::pair<int, Syndrome>> nonpivots;
    for (int position : order) {
        if (excluded[position]) continue;
        Syndrome value = columns[position];
        Syndrome representation{};
        bool independent = false;
        for (int row = 0; row < checks; ++row) {
            if (!bit(value, row)) continue;
            if (pivots[row] >= 0) {
                add(value, basis[row]);
                add(representation, representations[row]);
            } else {
                int pivot_index = selected.size();
                representation[pivot_index / 64] ^= 1ULL << (pivot_index % 64);
                basis[row] = value;
                representations[row] = representation;
                pivots[row] = pivot_index;
                selected.push_back(position);
                independent = true;
                break;
            }
        }
        if (!independent && int(nonpivots.size()) < order_depth) nonpivots.push_back({position, representation});
        if (selected.size() >= 379 && int(nonpivots.size()) >= order_depth) break;
    }
    Syndrome representation{};
    for (int row = 0; row < checks; ++row) if (bit(target, row)) {
        if (pivots[row] < 0) return false;
        add(target, basis[row]);
        add(representation, representations[row]);
    }
    auto candidate = [&](const Syndrome& encoded, int extra_one, int extra_two) {
        int weight = forced.size() + (extra_one >= 0) + (extra_two >= 0);
        for (auto word : encoded) weight += __builtin_popcountll(word);
        if (weight >= best_weight) return false;
        std::vector<int> support = forced;
        if (extra_one >= 0) support.push_back(extra_one);
        if (extra_two >= 0) support.push_back(extra_two);
        for (size_t index = 0; index < selected.size(); ++index) if (bit(encoded, index)) support.push_back(selected[index]);
        std::sort(support.begin(), support.end());
        return save(support);
    };
    if (candidate(representation, -1, -1)) return true;
    for (size_t first = 0; first < nonpivots.size(); ++first) {
        Syndrome trial = representation;
        add(trial, nonpivots[first].second);
        if (candidate(trial, nonpivots[first].first, -1)) return true;
        for (size_t second = 0; second < first; ++second) {
            Syndrome pair_trial = trial;
            add(pair_trial, nonpivots[second].second);
            if (candidate(pair_trial, nonpivots[first].first, nonpivots[second].first)) return true;
        }
    }
    return false;
}

bool decode(const std::vector<int>& forced, int iteration_limit, float normalization, float noise) {
    std::array<float, length * 6> variable_messages;
    std::array<float, length * 6> check_messages{};
    std::array<float, length> prior;
    std::array<float, length> posterior;
    std::array<float, length> accumulated{};
    std::uniform_real_distribution<float> random(-noise, noise);
    for (int position = 0; position < length; ++position) prior[position] = 1.0f + random(generator);
    for (int position : forced) prior[position] = -100.0f;
    for (int position = 0; position < length; ++position) for (int edge : edges[position]) variable_messages[edge] = prior[position];
    for (int iteration = 0; iteration < iteration_limit; ++iteration) {
        for (int check = 0; check < checks; ++check) {
            float minimum = 1e8f, second_minimum = 1e8f;
            int minimum_index = -1, sign = 1;
            for (int index = 0; index < 32; ++index) {
                float value = variable_messages[check * 32 + index];
                sign *= value < 0 ? -1 : 1;
                float magnitude = std::abs(value);
                if (magnitude < minimum) {
                    second_minimum = minimum;
                    minimum = magnitude;
                    minimum_index = index;
                } else if (magnitude < second_minimum) second_minimum = magnitude;
            }
            for (int index = 0; index < 32; ++index) {
                int edge = check * 32 + index;
                float value = (index == minimum_index ? second_minimum : minimum) * normalization;
                check_messages[edge] = value * sign * (variable_messages[edge] < 0 ? -1 : 1);
            }
        }
        std::vector<int> support;
        for (int position = 0; position < length; ++position) {
            float value = prior[position];
            for (int edge : edges[position]) value += check_messages[edge];
            posterior[position] = value;
            accumulated[position] = 0.95f * accumulated[position] + value;
            if (value < 0) support.push_back(position);
            for (int edge : edges[position]) variable_messages[edge] = std::clamp(value - check_messages[edge], -100.0f, 100.0f);
        }
        if (support.size() >= 8 && support.size() < size_t(best_weight) && save(support)) return true;
        if (iteration == 19 || iteration == 49 || iteration + 1 == iteration_limit) {
            if (osd(accumulated, forced, 50)) return true;
            if (osd(posterior, forced, 50)) return true;
        }
    }
    return false;
}

int main(int argc, char** argv) {
    int seconds = argc > 1 ? std::stoi(argv[1]) : 1800;
    std::ifstream input("blocks.txt");
    std::array<int, checks> counts{};
    for (int position = 0; position < length; ++position) for (int pass = 0; pass < 6; ++pass) {
        int group;
        input >> group;
        int check = pass * 64 + group;
        incidence[position][pass] = check;
        members[check][counts[check]] = position;
        edges[position][pass] = check * 32 + counts[check]++;
        columns[position][check / 64] |= 1ULL << (check % 64);
    }
    std::vector<std::pair<int, std::vector<int>>> impulses;
    for (int first = 0; first < length; ++first) {
        impulses.push_back({0, {first}});
        for (int second = 0; second < first; ++second) {
            int common = 0;
            for (int pass = 0; pass < 6; ++pass) common += incidence[first][pass] == incidence[second][pass];
            if (common >= 2) impulses.push_back({common, {second, first}});
        }
    }
    std::sort(impulses.begin(), impulses.end(), [](const auto& left, const auto& right) {return left.first > right.first;});
    auto start = std::chrono::steady_clock::now();
    int trial = 0;
    for (int round = 0; ; ++round) {
        for (const auto& impulse : impulses) {
            float normalization = round % 3 == 0 ? 0.8f : (round % 3 == 1 ? 1.0f : 0.6f);
            if (decode(impulse.second, 100, normalization, round == 0 ? 0.1f : 0.8f)) return 0;
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
            if (++trial % 100 == 0) std::cout << "PROGRESS " << trial << ' ' << elapsed << ' ' << impulse.first << std::endl;
            if (elapsed > seconds) return 0;
        }
        std::shuffle(impulses.begin(), impulses.end(), generator);
    }
}
