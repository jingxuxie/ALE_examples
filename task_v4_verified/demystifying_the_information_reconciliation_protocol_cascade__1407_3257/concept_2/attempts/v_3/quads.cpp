#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

using Syndrome = std::array<uint64_t, 6>;
struct Hash {
    size_t operator()(const Syndrome& value) const {
        uint64_t result = 0x9e3779b97f4a7c15ULL;
        for (uint64_t part : value) {
            part ^= part >> 30;
            part *= 0xbf58476d1ce4e5b9ULL;
            part ^= part >> 27;
            part *= 0x94d049bb133111ebULL;
            part ^= part >> 31;
            result ^= part + 0x9e3779b97f4a7c15ULL + (result << 6) + (result >> 2);
        }
        return result;
    }
};
std::array<std::array<int, 6>, 8192> signatures;
std::array<Syndrome, 8192> syndromes;
std::unordered_map<Syndrome, std::array<int, 4>, Hash> known;
std::ofstream records;
std::string path;
long long total = 0;
long long unique = 0;
bool found = false;

void candidate(int first, int second, int third, int fourth) {
    std::array<int, 4> positions{first, second, third, fourth};
    std::sort(positions.begin(), positions.end());
    if (std::adjacent_find(positions.begin(), positions.end()) != positions.end()) return;
    Syndrome syndrome{};
    for (int position : positions) {
        for (int pass = 0; pass < 6; ++pass) syndrome[pass] ^= syndromes[position][pass];
    }
    ++total;
    auto insertion = known.emplace(syndrome, positions);
    if (insertion.second) {
        ++unique;
        records.write(reinterpret_cast<const char*>(syndrome.data()), sizeof(syndrome));
        records.write(reinterpret_cast<const char*>(positions.data()), sizeof(positions));
        return;
    }
    if (insertion.first->second == positions) return;
    std::vector<int> result;
    for (int position : positions) {
        if (!std::binary_search(insertion.first->second.begin(), insertion.first->second.end(), position)) result.push_back(position);
    }
    for (int position : insertion.first->second) {
        if (!std::binary_search(positions.begin(), positions.end(), position)) result.push_back(position);
    }
    if (result.size() < 8) return;
    std::sort(result.begin(), result.end());
    std::cout << "FOUND " << result.size();
    std::ofstream output(path + "/quad_core.json");
    output << "{\"errors\":[";
    for (size_t index = 0; index < result.size(); ++index) {
        if (index) output << ',';
        output << result[index];
        std::cout << ' ' << result[index];
    }
    output << "]}\n";
    std::cout << std::endl;
    found = true;
}

int main(int argc, char** argv) {
    path = argv[1];
    std::ifstream input(path + "/signatures.txt");
    for (int position = 0; position < 8192; ++position) {
        for (int pass = 0; pass < 6; ++pass) {
            input >> signatures[position][pass];
            syndromes[position][pass] = uint64_t(1) << signatures[position][pass];
        }
    }
    records.open(path + "/quads.bin", std::ios::binary);
    for (int first_pass = 0; first_pass < 6; ++first_pass) {
        for (int second_pass = first_pass + 1; second_pass < 6; ++second_pass) {
            for (int third_pass = second_pass + 1; third_pass < 6; ++third_pass) {
                known.clear();
                std::array<int, 3> dimensions{first_pass, second_pass, third_pass};
                for (int choice = 0; choice < 3; ++choice) {
                    int left = dimensions[choice];
                    int right = dimensions[(choice + 1) % 3];
                    int other = dimensions[(choice + 2) % 3];
                    std::vector<std::vector<int>> groups(4096);
                    std::vector<std::vector<std::array<int, 2>>> pairs(4096);
                    for (int position = 0; position < 8192; ++position) groups[64 * signatures[position][left] + signatures[position][right]].push_back(position);
                    for (const auto& group : groups) {
                        for (size_t first_index = 0; first_index < group.size(); ++first_index) {
                            for (size_t second_index = first_index + 1; second_index < group.size(); ++second_index) {
                                int first = group[first_index];
                                int second = group[second_index];
                                int label_first = signatures[first][other];
                                int label_second = signatures[second][other];
                                int key = label_first == label_second ? 0 : 64 * std::min(label_first, label_second) + std::max(label_first, label_second);
                                pairs[key].push_back({first, second});
                            }
                        }
                    }
                    for (const auto& group : pairs) {
                        for (size_t first_index = 0; first_index < group.size(); ++first_index) {
                            for (size_t second_index = first_index + 1; second_index < group.size(); ++second_index) {
                                candidate(group[first_index][0], group[first_index][1], group[second_index][0], group[second_index][1]);
                            }
                        }
                    }
                }
                std::vector<std::vector<int>> first_groups(64), pair_groups(4096), triple_groups(262144);
                for (int position = 0; position < 8192; ++position) {
                    auto signature = signatures[position];
                    first_groups[signature[first_pass]].push_back(position);
                    pair_groups[64 * signature[second_pass] + signature[third_pass]].push_back(position);
                    triple_groups[4096 * signature[first_pass] + 64 * signature[second_pass] + signature[third_pass]].push_back(position);
                }
                for (int first = 0; first < 8192; ++first) {
                    auto signature = signatures[first];
                    for (int second : first_groups[signature[first_pass]]) {
                        if (second <= first) continue;
                        for (int third : pair_groups[64 * signature[second_pass] + signatures[second][third_pass]]) {
                            if (third <= first || third == second) continue;
                            int key = 4096 * signatures[third][first_pass] + 64 * signatures[second][second_pass] + signature[third_pass];
                            for (int fourth : triple_groups[key]) {
                                if (fourth > first) candidate(first, second, third, fourth);
                            }
                        }
                    }
                }
                std::cout << "passes " << first_pass << ' ' << second_pass << ' ' << third_pass << " quads " << known.size() << " total " << total << " unique " << unique << std::endl;
                if (found) return 0;
            }
        }
    }
}
