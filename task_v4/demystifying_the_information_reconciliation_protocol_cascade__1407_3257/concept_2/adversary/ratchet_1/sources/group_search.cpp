#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <vector>

#include "geometry.hpp"
constexpr int words = (length + 63) / 64;
constexpr int hash_bits = 20;
using Row = std::array<uint64_t, words>;
using Column = std::array<uint64_t, syndrome_words>;
struct PairEntry {
    uint16_t first;
    uint16_t second;
    int next;
};
std::array<Row, checks> original{};
std::array<Row, checks> matrix;
std::array<Column, length> columns;
std::vector<std::vector<int>> groups;
std::array<int, length> group_id;
std::array<int, checks> pivots;
std::array<bool, length> is_pivot;
std::array<uint32_t, length> keys;
std::array<int, 1 << hash_bits> heads;
std::vector<PairEntry> entries;
#ifndef INITIAL_BEST
#define INITIAL_BEST 20
#endif
int best = INITIAL_BEST;

bool candidate(int first, int second, int third, int fourth, int rank) {
    Column encoded{};
    int extra = 1 + (second >= 0) + (third >= 0 ? 2 : 0);
    int weight = extra;
    for (int word = 0; word < syndrome_words; ++word) {
        encoded[word] = columns[first][word];
        if (second >= 0) encoded[word] ^= columns[second][word];
        if (third >= 0) encoded[word] ^= columns[third][word] ^ columns[fourth][word];
        weight += __builtin_popcountll(encoded[word]);
        if (weight >= best) return false;
    }
    if (weight < 8) return false;
    std::vector<int> support{first};
    if (second >= 0) support.push_back(second);
    if (third >= 0) {
        support.push_back(third);
        support.push_back(fourth);
    }
    for (int index = 0; index < rank; ++index) if ((encoded[index / 64] >> (index % 64)) & 1) support.push_back(pivots[index]);
    std::sort(support.begin(), support.end());
    if (std::adjacent_find(support.begin(), support.end()) != support.end()) return false;
    for (const auto& row : original) {
        int parity = 0;
        for (int position : support) parity ^= (row[position / 64] >> (position % 64)) & 1;
        if (parity) return false;
    }
    best = weight;
    std::cout << "BEST " << best << ':';
    for (int position : support) std::cout << ' ' << position;
    std::cout << std::endl;
    std::ofstream output("sparse_core.json");
    output << "{\"errors\": [";
    for (size_t index = 0; index < support.size(); ++index) output << (index ? ", " : "") << support[index];
    output << "]}\n";
    return weight >= 8 && weight <= 18;
}

int main(int argc, char** argv) {
    int seconds = argc > 1 ? std::stoi(argv[1]) : 1800;
    unsigned seed = argc > 2 ? std::stoul(argv[2]) : 478931;
    int grouping_pass = argc > 3 ? std::stoi(argv[3]) : 0;
    int chosen_groups = argc > 4 ? std::stoi(argv[4]) : 10;
    std::mt19937 generator(seed);
    std::ifstream input("blocks.txt");
    groups.resize(group_counts[grouping_pass]);
    for (int position = 0; position < length; ++position) for (int pass = 0; pass < 6; ++pass) {
        int group;
        input >> group;
        original[check_offsets[pass] + group][position / 64] |= 1ULL << (position % 64);
        if (pass == grouping_pass) {
            group_id[position] = group;
            groups[group].push_back(position);
        }
    }
    std::vector<int> group_order(groups.size());
    std::iota(group_order.begin(), group_order.end(), 0);
    std::array<int, length> order;
    entries.reserve(32768);
    if (chosen_groups < 0 || chosen_groups > int(groups.size())) return 2;
    std::cout << "CONFIG n " << length << " checks " << checks << " rank " << matrix_rank << " pass " << grouping_pass << " groups " << chosen_groups << " initial_best " << best << std::endl;
    auto start = std::chrono::steady_clock::now();
    for (int trial = 0; ; ++trial) {
        matrix = original;
        is_pivot.fill(false);
        std::shuffle(group_order.begin(), group_order.end(), generator);
        int offset = 0;
        for (int group : group_order) {
            auto members = groups[group];
            std::shuffle(members.begin(), members.end(), generator);
            for (int position : members) order[offset++] = position;
        }
        int retained_positions = 0;
        for (int group_index = 0; group_index < chosen_groups; ++group_index) retained_positions += groups[group_order[group_index]].size();
        std::shuffle(order.begin() + retained_positions, order.end(), generator);
        int rank = 0;
        for (int position : order) {
            int selected = rank;
            uint64_t mask = 1ULL << (position % 64);
            int word_index = position / 64;
            while (selected < checks && !(matrix[selected][word_index] & mask)) ++selected;
            if (selected == checks) continue;
            std::swap(matrix[rank], matrix[selected]);
            for (int row = 0; row < checks; ++row) {
                if (row == rank || !(matrix[row][word_index] & mask)) continue;
                for (int word = 0; word < words; ++word) matrix[row][word] ^= matrix[rank][word];
            }
            pivots[rank++] = position;
            is_pivot[position] = true;
            if (rank == matrix_rank) break;
        }
        for (auto& column : columns) column.fill(0);
        keys.fill(0);
        for (int row = 0; row < rank; ++row) {
            uint64_t mask = 1ULL << (row % 64);
            for (int word = 0; word < words; ++word) {
                uint64_t remaining = matrix[row][word];
                while (remaining) {
                    int position = word * 64 + __builtin_ctzll(remaining);
                    columns[position][row / 64] |= mask;
                    if (row < hash_bits) keys[position] |= 1U << row;
                    remaining &= remaining - 1;
                }
            }
        }
        heads.fill(-1);
        entries.clear();
        for (int position = 0; position < length; ++position) {
            if (!is_pivot[position] && candidate(position, -1, -1, -1, rank)) return 0;
        }
        for (int group = 0; group < int(groups.size()); ++group) {
            for (int first_index = 0; first_index < int(groups[group].size()); ++first_index) {
                int first = groups[group][first_index];
                if (is_pivot[first]) continue;
                for (int second_index = 0; second_index < first_index; ++second_index) {
                    int second = groups[group][second_index];
                    if (is_pivot[second]) continue;
                    if (candidate(first, second, -1, -1, rank)) return 0;
                    uint32_t key = keys[first] ^ keys[second];
                    for (int entry_index = heads[key]; entry_index >= 0; entry_index = entries[entry_index].next) {
                        const auto& entry = entries[entry_index];
                        if (entry.first == first || entry.second == first || entry.first == second || entry.second == second) continue;
                        if (candidate(first, second, entry.first, entry.second, rank)) return 0;
                    }
                    entries.push_back({uint16_t(first), uint16_t(second), heads[key]});
                    heads[key] = entries.size() - 1;
                }
            }
        }
        double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        if (trial % 10 == 0) std::cout << "PROGRESS " << trial << ' ' << elapsed << " rank " << rank << std::endl;
        if (elapsed > seconds) {
            std::cout << "END trials " << trial + 1 << " elapsed " << elapsed << std::endl;
            return 0;
        }
    }
}
