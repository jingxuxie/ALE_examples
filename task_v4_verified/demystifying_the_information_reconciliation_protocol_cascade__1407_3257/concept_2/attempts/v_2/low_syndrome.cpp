#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <unordered_map>
#include <vector>

struct Hash {
    uint64_t left, right;
    bool operator==(const Hash& other) const { return left == other.left && right == other.right; }
};
Hash operator^(const Hash& left, const Hash& right) { return {left.left ^ right.left, left.right ^ right.right}; }
struct Hasher {
    size_t operator()(const Hash& value) const { return value.left; }
};
struct Pair {
    int left, right;
    std::array<int, 8> syndrome;
    int count;
    Hash hash;
};
struct Entry {
    uint64_t key;
    int pair;
    bool operator<(const Entry& other) const { return key < other.key; }
};

int main() {
    std::ifstream input("signatures.txt");
    int size;
    input >> size;
    std::vector<std::array<int, 6>> signatures(size);
    for (auto& signature : signatures) for (int& block : signature) input >> block;
    std::mt19937_64 generator(334191);
    std::array<Hash, 384> check_hash;
    for (auto& hash : check_hash) hash = {generator(), generator()};
    std::vector<Hash> hashes(size);
    for (int bit = 0; bit < size; ++bit) {
        for (int dimension = 0; dimension < 6; ++dimension) hashes[bit] = hashes[bit] ^ check_hash[dimension * 64 + signatures[bit][dimension]];
    }
    std::vector<Pair> pairs;
    std::vector<Entry> entries;
    for (int left = 0; left < size; ++left) for (int right = left + 1; right < size; ++right) {
        int common = 0;
        for (int dimension = 0; dimension < 6; ++dimension) common += signatures[left][dimension] == signatures[right][dimension];
        if (common < 2) continue;
        Pair pair{left, right, {}, 0, hashes[left] ^ hashes[right]};
        for (int dimension = 0; dimension < 6; ++dimension) {
            if (signatures[left][dimension] == signatures[right][dimension]) continue;
            pair.syndrome[pair.count++] = dimension * 64 + signatures[left][dimension];
            pair.syndrome[pair.count++] = dimension * 64 + signatures[right][dimension];
        }
        std::sort(pair.syndrome.begin(), pair.syndrome.begin() + pair.count);
        int index = pairs.size();
        pairs.push_back(pair);
        for (int first = 0; first < pair.count; ++first)
            for (int second = first + 1; second < pair.count; ++second)
                for (int third = second + 1; third < pair.count; ++third)
                    for (int fourth = third + 1; fourth < pair.count; ++fourth) {
                        uint64_t key = pair.syndrome[first] | (uint64_t(pair.syndrome[second]) << 9) | (uint64_t(pair.syndrome[third]) << 18) | (uint64_t(pair.syndrome[fourth]) << 27);
                        entries.push_back({key, index});
                    }
    }
    std::cout << "pairs " << pairs.size() << " entries " << entries.size() << std::endl;
    std::sort(entries.begin(), entries.end());
    std::unordered_map<Hash, std::array<int, 4>, Hasher> seen;
    seen.reserve(2000000);
    uint64_t tried = 0;
    for (size_t begin = 0; begin < entries.size();) {
        size_t end = begin + 1;
        while (end < entries.size() && entries[end].key == entries[begin].key) ++end;
        for (size_t left_index = begin; left_index < end; ++left_index) for (size_t right_index = left_index + 1; right_index < end; ++right_index) {
            const Pair& left = pairs[entries[left_index].pair];
            const Pair& right = pairs[entries[right_index].pair];
            if (left.left == right.left || left.left == right.right || left.right == right.left || left.right == right.right) continue;
            std::array<int, 4> support{left.left, left.right, right.left, right.right};
            std::sort(support.begin(), support.end());
            Hash hash = left.hash ^ right.hash;
            auto result = seen.emplace(hash, support);
            ++tried;
            if (!result.second && result.first->second != support) {
                std::vector<int> errors;
                auto other = result.first->second;
                std::set_symmetric_difference(support.begin(), support.end(), other.begin(), other.end(), std::back_inserter(errors));
                std::cout << "FOUND " << errors.size();
                for (int bit : errors) std::cout << ' ' << bit;
                std::cout << std::endl;
                std::ofstream output("low_core.json");
                output << '[';
                for (size_t index = 0; index < errors.size(); ++index) output << (index ? "," : "") << errors[index];
                output << "]\n";
                if (errors.size() >= 8) return 0;
            }
        }
        begin = end;
    }
    std::cout << "done " << tried << " unique " << seen.size() << std::endl;
}
