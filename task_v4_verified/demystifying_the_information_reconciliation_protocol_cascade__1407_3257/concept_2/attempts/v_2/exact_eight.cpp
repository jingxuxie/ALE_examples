#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <memory>
#include <mutex>
#include <random>
#include <vector>
#include <omp.h>
#include <parallel/algorithm>

using Mask = std::array<uint64_t, 6>;
struct Pair {
    uint16_t left, right;
    std::array<uint16_t, 10> syndrome;
    int count;
    uint64_t hash;
};

int main(int argc, char** argv) {
    int first_target = argc > 1 ? std::stoi(argv[1]) : 0;
    int search_seconds = argc > 2 ? std::stoi(argv[2]) : 650;
    omp_set_num_threads(16);
    std::ifstream input("signatures.txt");
    int size;
    input >> size;
    std::vector<Mask> columns(size);
    std::vector<uint64_t> hashes(size);
    std::mt19937_64 generator(178229);
    std::array<uint64_t, 384> check_hash;
    for (auto& hash : check_hash) hash = generator();
    for (int bit = 0; bit < size; ++bit) {
        for (int dimension = 0; dimension < 6; ++dimension) {
            int block;
            input >> block;
            columns[bit][dimension] = 1ull << block;
            hashes[bit] ^= check_hash[64 * dimension + block];
        }
    }
    std::vector<Pair> pairs;
    std::vector<uint64_t> offsets{0};
    for (int left = 0; left < size; ++left) for (int right = left + 1; right < size; ++right) {
        int common = 0;
        for (int dimension = 0; dimension < 6; ++dimension) common += columns[left][dimension] == columns[right][dimension];
        if (!common) continue;
        Pair pair{uint16_t(left), uint16_t(right), {}, 0, hashes[left] ^ hashes[right]};
        for (int dimension = 0; dimension < 6; ++dimension) {
            uint64_t word = columns[left][dimension] ^ columns[right][dimension];
            while (word) {
                pair.syndrome[pair.count++] = 64 * dimension + __builtin_ctzll(word);
                word &= word - 1;
            }
        }
        pairs.push_back(pair);
        int count = pair.count;
        offsets.push_back(offsets.back() + uint64_t(count) * (count - 1) * (count - 2) * (count - 3) / 24);
    }
    std::cout << "pairs " << pairs.size() << " entries " << offsets.back() << std::endl;
    std::vector<uint64_t> entries(offsets.back());
    #pragma omp parallel for schedule(static)
    for (size_t index = 0; index < pairs.size(); ++index) {
        const auto& pair = pairs[index];
        uint64_t offset = offsets[index];
        for (int first = 0; first < pair.count; ++first)
            for (int second = first + 1; second < pair.count; ++second)
                for (int third = second + 1; third < pair.count; ++third)
                    for (int fourth = third + 1; fourth < pair.count; ++fourth) {
                        uint64_t key = pair.syndrome[first] | (uint64_t(pair.syndrome[second]) << 9) | (uint64_t(pair.syndrome[third]) << 18) | (uint64_t(pair.syndrome[fourth]) << 27);
                        entries[offset++] = (key << 22) | index;
                    }
    }
    std::cout << "sorting" << std::endl;
    __gnu_parallel::sort(entries.begin(), entries.end());
    std::cout << "searching" << std::endl;
    constexpr uint64_t capacity = 1ull << 28;
    auto keys = std::make_unique<std::atomic<uint64_t>[]>(capacity);
    auto values = std::make_unique<std::atomic<uint64_t>[]>(capacity);
    #pragma omp parallel for schedule(static)
    for (uint64_t index = 0; index < capacity; ++index) { keys[index] = 0; values[index] = 0; }
    std::atomic<bool> found{false}, full{false};
    std::atomic<uint64_t> inserted{0};
    std::mutex output_mutex;
    std::vector<std::vector<int>> short_cores;
    auto consider = [&](std::vector<int> core) {
        if (core.empty()) return;
        Mask syndrome{};
        for (int bit : core) for (int dimension = 0; dimension < 6; ++dimension) syndrome[dimension] ^= columns[bit][dimension];
        for (auto word : syndrome) if (word) return;
        std::lock_guard<std::mutex> lock(output_mutex);
        if (core.size() < 8) {
            for (const auto& previous : short_cores) {
                std::vector<int> combined;
                std::set_symmetric_difference(core.begin(), core.end(), previous.begin(), previous.end(), std::back_inserter(combined));
                if (combined.size() >= 8 && combined.size() <= 18) { core = combined; break; }
            }
            if (core.size() < 8) { short_cores.push_back(core); return; }
        }
        std::cout << "FOUND";
        std::ofstream output("exact_core.json");
        output << '[';
        for (size_t index = 0; index < core.size(); ++index) {
            std::cout << ' ' << core[index];
            output << (index ? "," : "") << core[index];
        }
        output << "]\n";
        std::cout << std::endl;
        found = true;
    };
    #pragma omp parallel for schedule(dynamic, 4096)
    for (uint64_t begin = 0; begin < entries.size(); ++begin) {
        if (found || full || (begin && (entries[begin] >> 22) == (entries[begin - 1] >> 22))) continue;
        uint64_t end = begin + 1;
        while (end < entries.size() && (entries[end] >> 22) == (entries[begin] >> 22)) ++end;
        for (uint64_t left_index = begin; left_index < end; ++left_index) for (uint64_t right_index = left_index + 1; right_index < end; ++right_index) {
            const auto& left = pairs[entries[left_index] & ((1u << 22) - 1)];
            const auto& right = pairs[entries[right_index] & ((1u << 22) - 1)];
            if (left.left == right.left || left.left == right.right || left.right == right.left || left.right == right.right) continue;
            std::array<int, 4> support{left.left, left.right, right.left, right.right};
            std::sort(support.begin(), support.end());
            uint64_t packed = support[0] | (uint64_t(support[1]) << 13) | (uint64_t(support[2]) << 26) | (uint64_t(support[3]) << 39);
            uint64_t hash = left.hash ^ right.hash;
            if (!hash) { consider(std::vector<int>(support.begin(), support.end())); continue; }
            uint64_t location = hash & (capacity - 1);
            while (true) {
                uint64_t key = keys[location].load(std::memory_order_relaxed);
                if (!key && keys[location].compare_exchange_strong(key, hash)) {
                    values[location].store(packed, std::memory_order_release);
                    if (++inserted > capacity * 0.8) full = true;
                    break;
                }
                if (key == hash) {
                    uint64_t previous;
                    do previous = values[location].load(std::memory_order_acquire); while (!previous);
                    if (previous != packed) {
                        std::array<int, 4> other;
                        for (int index = 0; index < 4; ++index) other[index] = (previous >> (13 * index)) & 8191;
                        std::vector<int> core;
                        std::set_symmetric_difference(support.begin(), support.end(), other.begin(), other.end(), std::back_inserter(core));
                        consider(core);
                    }
                    break;
                }
                location = (location + 1) & (capacity - 1);
            }
        }
    }
    std::cout << "done unique " << inserted << " full " << full << std::endl;
    if (found || full) return 0;
    std::vector<Pair> targets;
    for (const auto& pair : pairs) if (pair.count <= 6) targets.push_back(pair);
    std::sort(targets.begin(), targets.end(), [](const Pair& left, const Pair& right) { return left.count < right.count; });
    auto search_start = std::chrono::steady_clock::now();
    omp_set_num_threads(128);
    for (size_t target_index = first_target; target_index < targets.size() && !found; ++target_index) {
        const auto& target = targets[target_index];
        #pragma omp parallel for schedule(static)
        for (uint64_t index = 0; index < capacity; ++index) {
            uint64_t hash = keys[index].load(std::memory_order_relaxed);
            if (!hash || found) continue;
            uint64_t desired = hash ^ target.hash;
            uint64_t location = desired & (capacity - 1);
            uint64_t current;
            while ((current = keys[location].load(std::memory_order_relaxed)) && current != desired) location = (location + 1) & (capacity - 1);
            if (!current) continue;
            uint64_t left = values[index].load(std::memory_order_relaxed);
            uint64_t right = values[location].load(std::memory_order_relaxed);
            std::array<int, 10> combined;
            for (int position = 0; position < 4; ++position) {
                combined[position] = (left >> (13 * position)) & 8191;
                combined[position + 4] = (right >> (13 * position)) & 8191;
            }
            combined[8] = target.left;
            combined[9] = target.right;
            std::sort(combined.begin(), combined.end());
            std::vector<int> core;
            for (size_t position = 0; position < combined.size();) {
                size_t end = position + 1;
                while (end < combined.size() && combined[end] == combined[position]) ++end;
                if ((end - position) % 2) core.push_back(combined[position]);
                position = end;
            }
            consider(core);
        }
        double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - search_start).count();
        if (target_index % 10 == 0) std::cout << "target " << target_index << " time " << elapsed << std::endl;
        if (elapsed > search_seconds) break;
    }
}
