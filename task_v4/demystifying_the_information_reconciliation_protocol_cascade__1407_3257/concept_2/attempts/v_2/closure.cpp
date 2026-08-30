#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <unordered_map>
#include <vector>

using Mask = std::array<uint64_t, 6>;
struct Hash {
    uint64_t left, right;
    bool operator==(const Hash& other) const { return left == other.left && right == other.right; }
};
Hash operator^(const Hash& left, const Hash& right) { return {left.left ^ right.left, left.right ^ right.right}; }
struct Hasher { size_t operator()(const Hash& value) const { return value.left; } };
struct Candidate {
    Mask value{};
    Hash hash{};
    std::vector<int> support;
};
struct Entry {
    uint64_t key;
    int candidate;
    bool operator<(const Entry& other) const { return key < other.key; }
};

int count(const Mask& mask) {
    int result = 0;
    for (uint64_t word : mask) result += __builtin_popcountll(word);
    return result;
}

bool save(const std::vector<int>& support) {
    if (support.size() < 8 || support.size() > 18) return false;
    std::cout << "FOUND";
    std::ofstream output("closure_core.json");
    output << '[';
    for (size_t index = 0; index < support.size(); ++index) {
        std::cout << ' ' << support[index];
        output << (index ? "," : "") << support[index];
    }
    output << "]\n";
    std::cout << std::endl;
    return true;
}

int main() {
    std::ifstream input("signatures.txt");
    int size;
    input >> size;
    std::vector<Mask> columns(size);
    std::vector<Hash> hashes(size);
    std::mt19937_64 generator(910334);
    std::array<Hash, 384> check_hash;
    for (auto& hash : check_hash) hash = {generator(), generator()};
    for (int bit = 0; bit < size; ++bit) {
        for (int dimension = 0; dimension < 6; ++dimension) {
            int block;
            input >> block;
            columns[bit][dimension] = 1ull << block;
            hashes[bit] = hashes[bit] ^ check_hash[64 * dimension + block];
        }
    }
    std::vector<Candidate> pool;
    std::unordered_map<Hash, int, Hasher> seen;
    pool.reserve(1000000);
    seen.reserve(1000000);
    for (int bit = 0; bit < size; ++bit) {
        Candidate candidate;
        candidate.value = columns[bit];
        candidate.hash = hashes[bit];
        candidate.support = {bit};
        seen.emplace(candidate.hash, pool.size());
        pool.push_back(std::move(candidate));
    }
    for (int left = 0; left < size; ++left) for (int right = left + 1; right < size; ++right) {
        Candidate candidate;
        for (int dimension = 0; dimension < 6; ++dimension) candidate.value[dimension] = columns[left][dimension] ^ columns[right][dimension];
        if (count(candidate.value) > 8) continue;
        candidate.hash = hashes[left] ^ hashes[right];
        candidate.support = {left, right};
        seen.emplace(candidate.hash, pool.size());
        pool.push_back(std::move(candidate));
    }
    size_t previous = 0;
    for (int round = 0; round < 20; ++round) {
        size_t current = pool.size();
        std::vector<Entry> entries;
        entries.reserve(current * 70);
        for (size_t index = 0; index < current; ++index) {
            std::vector<int> syndrome;
            for (int dimension = 0; dimension < 6; ++dimension) {
                uint64_t word = pool[index].value[dimension];
                while (word) {
                    syndrome.push_back(64 * dimension + __builtin_ctzll(word));
                    word &= word - 1;
                }
            }
            for (size_t first = 0; first < syndrome.size(); ++first)
                for (size_t second = first + 1; second < syndrome.size(); ++second)
                    for (size_t third = second + 1; third < syndrome.size(); ++third) {
                            uint64_t key = syndrome[first] | (uint64_t(syndrome[second]) << 9) | (uint64_t(syndrome[third]) << 18);
                            entries.push_back({key, int(index)});
                        }
        }
        std::cout << "round " << round << " pool " << current << " entries " << entries.size() << std::endl;
        std::sort(entries.begin(), entries.end());
        for (size_t begin = 0; begin < entries.size();) {
            size_t end = begin + 1;
            while (end < entries.size() && entries[end].key == entries[begin].key) ++end;
            for (size_t left_index = begin; left_index < end; ++left_index) for (size_t right_index = left_index + 1; right_index < end; ++right_index) {
                int left_id = entries[left_index].candidate;
                int right_id = entries[right_index].candidate;
                if (static_cast<size_t>(left_id) < previous && static_cast<size_t>(right_id) < previous) continue;
                const auto& left = pool[left_id];
                const auto& right = pool[right_id];
                Candidate candidate;
                for (int dimension = 0; dimension < 6; ++dimension) candidate.value[dimension] = left.value[dimension] ^ right.value[dimension];
                int syndrome_weight = count(candidate.value);
                if (syndrome_weight > 8) continue;
                std::set_symmetric_difference(left.support.begin(), left.support.end(), right.support.begin(), right.support.end(), std::back_inserter(candidate.support));
                if (!syndrome_weight) {
                    if (save(candidate.support)) return 0;
                    continue;
                }
                candidate.hash = left.hash ^ right.hash;
                auto existing = seen.find(candidate.hash);
                if (existing != seen.end()) {
                    const auto& other = pool[existing->second];
                    if (candidate.support != other.support && candidate.value == other.value) {
                        std::vector<int> core;
                        std::set_symmetric_difference(candidate.support.begin(), candidate.support.end(), other.support.begin(), other.support.end(), std::back_inserter(core));
                        if (save(core)) return 0;
                    }
                } else if (candidate.support.size() <= 10 && pool.size() < 1000000) {
                    seen.emplace(candidate.hash, pool.size());
                    pool.push_back(std::move(candidate));
                }
            }
            begin = end;
        }
        if (pool.size() == current) break;
        previous = current;
    }
}
