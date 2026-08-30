#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

struct Record {
    uint64_t fingerprint;
    uint64_t support;
    bool operator<(const Record& other) const {
        return fingerprint < other.fingerprint || (fingerprint == other.fingerprint && support < other.support);
    }
};

int main(int argc, char** argv) {
    std::string path = argv[1];
    std::array<std::array<int, 6>, 8192> signatures;
    std::array<uint64_t, 8192> fingerprints{};
    std::array<uint64_t, 384> hashes;
    std::mt19937_64 generator(77324051);
    for (auto& hash : hashes) hash = generator();
    std::ifstream input(path + "/signatures.txt");
    for (int position = 0; position < 8192; ++position) {
        for (int pass = 0; pass < 6; ++pass) {
            input >> signatures[position][pass];
            fingerprints[position] ^= hashes[64 * pass + signatures[position][pass]];
        }
    }
    std::vector<Record> records;
    records.reserve(110000000);
    auto started = std::chrono::steady_clock::now();
    std::vector<std::vector<int>> small_cores;
    for (int first_pass = 0; first_pass < 6; ++first_pass) {
        for (int second_pass = first_pass + 1; second_pass < 6; ++second_pass) {
            records.clear();
            std::array<std::vector<int>, 64> groups;
            std::array<std::vector<std::array<int, 2>>, 4096> pairs;
            for (int position = 0; position < 8192; ++position) groups[signatures[position][first_pass]].push_back(position);
            for (const auto& group : groups) {
                for (size_t first_index = 0; first_index < group.size(); ++first_index) {
                    for (size_t second_index = first_index + 1; second_index < group.size(); ++second_index) {
                        int first = group[first_index];
                        int second = group[second_index];
                        int left = signatures[first][second_pass];
                        int right = signatures[second][second_pass];
                        int key = left == right ? 0 : 64 * std::min(left, right) + std::max(left, right);
                        pairs[key].push_back({first, second});
                    }
                }
            }
            for (const auto& group : pairs) {
                for (size_t first_index = 0; first_index < group.size(); ++first_index) {
                    auto first_pair = group[first_index];
                    for (size_t second_index = first_index + 1; second_index < group.size(); ++second_index) {
                        auto second_pair = group[second_index];
                        std::array<int, 4> positions{first_pair[0], first_pair[1], second_pair[0], second_pair[1]};
                        if (positions[0] > positions[2]) {
                            std::swap(positions[0], positions[2]);
                            std::swap(positions[1], positions[3]);
                        }
                        if (positions[1] > positions[3]) std::swap(positions[1], positions[3]);
                        if (positions[1] > positions[2]) std::swap(positions[1], positions[2]);
                        if (positions[0] == positions[1] || positions[1] == positions[2] || positions[2] == positions[3]) continue;
                        uint64_t fingerprint = 0;
                        uint64_t support = 0;
                        for (int index = 0; index < 4; ++index) {
                            fingerprint ^= fingerprints[positions[index]];
                            support |= uint64_t(positions[index]) << (13 * index);
                        }
                        records.push_back({fingerprint, support});
                    }
                }
            }
            std::cout << "generated " << first_pass << ' ' << second_pass << " count " << records.size() << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
            std::sort(records.begin(), records.end());
            for (size_t index = 1; index < records.size(); ++index) {
                if (records[index].fingerprint != records[index - 1].fingerprint || records[index].support == records[index - 1].support) continue;
                std::vector<int> positions;
                for (auto support : {records[index].support, records[index - 1].support}) {
                    for (int offset = 0; offset < 4; ++offset) {
                        int position = (support >> (13 * offset)) & 8191;
                        auto existing = std::find(positions.begin(), positions.end(), position);
                        if (existing != positions.end()) positions.erase(existing);
                        else positions.push_back(position);
                    }
                }
                std::array<uint64_t, 6> syndrome{};
                for (int position : positions) for (int pass = 0; pass < 6; ++pass) syndrome[pass] ^= uint64_t(1) << signatures[position][pass];
                bool zero = true;
                for (uint64_t word : syndrome) if (word) zero = false;
                if (!zero || positions.empty()) continue;
                std::sort(positions.begin(), positions.end());
                std::cout << "CORE " << positions.size();
                for (int position : positions) std::cout << ' ' << position;
                std::cout << std::endl;
                if (positions.size() < 8) {
                    for (const auto& old : small_cores) {
                        std::vector<int> combined;
                        std::set_symmetric_difference(old.begin(), old.end(), positions.begin(), positions.end(), std::back_inserter(combined));
                        if (combined.size() >= 8 && combined.size() <= 18) {
                            positions = combined;
                            break;
                        }
                    }
                }
                if (positions.size() < 8) {
                    small_cores.push_back(positions);
                    continue;
                }
                std::ofstream output(path + "/pair_quad_core.json");
                output << "{\"errors\":[";
                for (size_t offset = 0; offset < positions.size(); ++offset) {
                    if (offset) output << ',';
                    output << positions[offset];
                }
                output << "]}\n";
                return 0;
            }
            std::cout << "finished " << first_pass << ' ' << second_pass << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
        }
    }
}
