#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <vector>

using Mask = std::array<uint64_t, 6>;
struct Vector {
    Mask value{};
    Mask support{};
    uint64_t hash = 0;
};

int popcount(const Mask& value) {
    int count = 0;
    for (uint64_t word : value) count += __builtin_popcountll(word);
    return count;
}

void combine(Vector& target, const Vector& source) {
    for (int coordinate = 0; coordinate < 6; ++coordinate) {
        target.value[coordinate] ^= source.value[coordinate];
        target.support[coordinate] ^= source.support[coordinate];
    }
    target.hash ^= source.hash;
}

int main(int argc, char** argv) {
    std::string path = argc > 1 ? argv[1] : "tempering_best_51.json";
    int base_count = argc > 2 ? std::stoi(argv[2]) : 256;
    int maximum = argc > 3 ? std::stoi(argv[3]) : 8192;
    int seed = argc > 4 ? std::stoi(argv[4]) : 1;
    std::ifstream input("signatures.txt");
    int size;
    input >> size;
    std::vector<std::array<int, 6>> signatures(size);
    std::vector<Mask> columns(size);
    std::vector<uint64_t> hashes(size);
    std::mt19937_64 generator(seed);
    std::array<uint64_t, 384> random_checks;
    for (auto& random : random_checks) random = generator();
    for (int bit = 0; bit < size; ++bit) {
        for (int dimension = 0; dimension < 6; ++dimension) {
            int block;
            input >> block;
            signatures[bit][dimension] = block;
            columns[bit][dimension] = 1ull << block;
            hashes[bit] ^= random_checks[64 * dimension + block];
        }
    }
    std::ifstream support_file(path);
    std::string contents((std::istreambuf_iterator<char>(support_file)), {});
    for (char& character : contents) if (character < '0' || character > '9') character = ' ';
    std::istringstream support_input(contents);
    std::vector<int> initial;
    int bit;
    while (support_input >> bit) initial.push_back(bit);
    std::array<int, 384> counts{};
    std::vector<bool> included(size);
    for (int selected : initial) {
        included[selected] = true;
        for (int dimension = 0; dimension < 6; ++dimension) ++counts[64 * dimension + signatures[selected][dimension]];
    }
    std::vector<std::pair<double, int>> scores;
    for (int position = 0; position < size; ++position) {
        if (included[position]) continue;
        double score = std::generate_canonical<double, 53>(generator);
        for (int dimension = 0; dimension < 6; ++dimension) score += counts[64 * dimension + signatures[position][dimension]] > 0;
        scores.push_back({score, position});
    }
    std::sort(scores.rbegin(), scores.rend());
    std::vector<int> base = initial;
    for (auto entry : scores) {
        if (base.size() >= static_cast<size_t>(base_count)) break;
        base.push_back(entry.second);
        included[entry.second] = true;
    }
    std::array<Vector, 384> basis;
    std::array<bool, 384> occupied{};
    auto verify = [&](const Mask& support, std::vector<int> outside) {
        if (popcount(support) + outside.size() < 8 || popcount(support) + outside.size() > 18) return false;
        for (size_t index = 0; index < base.size(); ++index) if (support[index / 64] >> (index % 64) & 1) outside.push_back(base[index]);
        std::sort(outside.begin(), outside.end());
        if (std::unique(outside.begin(), outside.end()) != outside.end()) return false;
        Mask syndrome{};
        for (int selected : outside) for (int dimension = 0; dimension < 6; ++dimension) syndrome[dimension] ^= columns[selected][dimension];
        if (popcount(syndrome)) return false;
        std::cout << "FOUND";
        std::ofstream output("projection_core_" + std::to_string(seed) + ".json");
        output << '[';
        for (size_t index = 0; index < outside.size(); ++index) {
            std::cout << ' ' << outside[index];
            output << (index ? "," : "") << outside[index];
        }
        output << "]\n";
        std::cout << std::endl;
        return true;
    };
    for (size_t index = 0; index < base.size(); ++index) {
        Vector current;
        current.value = columns[base[index]];
        current.hash = hashes[base[index]];
        current.support[index / 64] = 1ull << (index % 64);
        bool inserted = false;
        for (int dimension = 5; dimension >= 0 && !inserted; --dimension) {
            while (current.value[dimension]) {
                int pivot = 64 * dimension + 63 - __builtin_clzll(current.value[dimension]);
                if (!occupied[pivot]) {
                    occupied[pivot] = true;
                    basis[pivot] = current;
                    inserted = true;
                    break;
                }
                combine(current, basis[pivot]);
            }
        }
        if (!inserted && verify(current.support, {})) return 0;
    }
    std::vector<int> outside;
    std::vector<Vector> projected(size);
    for (auto entry : scores) {
        int position = entry.second;
        if (included[position]) continue;
        Vector current;
        current.value = columns[position];
        current.hash = hashes[position];
        for (int dimension = 5; dimension >= 0; --dimension) {
            for (int offset = 63; offset >= 0; --offset) {
                int pivot = dimension * 64 + offset;
                if (occupied[pivot] && (current.value[dimension] >> offset & 1)) combine(current, basis[pivot]);
            }
        }
        if (!current.hash && verify(current.support, {position})) return 0;
        projected[position] = current;
        outside.push_back(position);
    }
    maximum = std::min(maximum, static_cast<int>(outside.size()));
    std::cout << "projected " << path << " base " << base.size() << " outside " << maximum << std::endl;
    for (int requested : {512, 1024, 2048, 4096, 8192}) {
        int limit = std::min(requested, maximum);
        uint64_t pair_count = uint64_t(limit) * (limit - 1) / 2;
        uint64_t capacity = 1;
        while (capacity < pair_count * 1.4) capacity *= 2;
        std::vector<uint64_t> keys(capacity);
        std::vector<uint32_t> values(capacity);
        for (int left_index = 0; left_index < limit; ++left_index) {
            int left = outside[left_index];
            for (int right_index = left_index + 1; right_index < limit; ++right_index) {
                int right = outside[right_index];
                uint64_t hash = projected[left].hash ^ projected[right].hash;
                Mask support{};
                if (!hash) {
                    for (int coordinate = 0; coordinate < 6; ++coordinate) support[coordinate] = projected[left].support[coordinate] ^ projected[right].support[coordinate];
                    if (verify(support, {left, right})) return 0;
                    continue;
                }
                uint64_t location = hash & (capacity - 1);
                while (keys[location] && keys[location] != hash) location = (location + 1) & (capacity - 1);
                if (keys[location]) {
                    int other_left = values[location] & 8191;
                    int other_right = values[location] >> 13;
                    if (other_left == left || other_right == left || other_left == right || other_right == right) continue;
                    for (int coordinate = 0; coordinate < 6; ++coordinate) support[coordinate] = projected[left].support[coordinate] ^ projected[right].support[coordinate] ^ projected[other_left].support[coordinate] ^ projected[other_right].support[coordinate];
                    if (verify(support, {left, right, other_left, other_right})) return 0;
                } else {
                    keys[location] = hash;
                    values[location] = left | (right << 13);
                }
            }
        }
        std::cout << "checked " << limit << " pairs " << pair_count << std::endl;
        if (limit == maximum) break;
    }
}
