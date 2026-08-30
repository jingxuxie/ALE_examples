#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

struct Quad {
    std::array<uint64_t, 6> syndrome;
    std::array<int, 4> positions;
};
struct Index {
    uint64_t key;
    uint32_t quad;
    bool operator<(const Index& other) const { return key < other.key; }
};
struct Result {
    uint64_t fingerprint;
    std::array<uint16_t, 8> positions;
    bool operator<(const Result& other) const {
        return fingerprint < other.fingerprint || (fingerprint == other.fingerprint && positions < other.positions);
    }
};

int main(int argc, char** argv) {
    std::string path = argv[1];
    std::array<std::array<int, 6>, 8192> signatures;
    std::array<uint64_t, 8192> hashes{};
    std::array<uint64_t, 384> check_hashes;
    std::mt19937_64 generator(178710321);
    for (auto& value : check_hashes) value = generator();
    std::ifstream input(path + "/signatures.txt");
    for (int position = 0; position < 8192; ++position) {
        for (int pass = 0; pass < 6; ++pass) {
            input >> signatures[position][pass];
            hashes[position] ^= check_hashes[64 * pass + signatures[position][pass]];
        }
    }
    std::ifstream counts(path + "/quad_counts.txt");
    std::ifstream data(path + "/quads.bin", std::ios::binary);
    auto started = std::chrono::steady_clock::now();
    size_t count;
    int group = 0;
    while (counts >> count) {
        std::vector<Quad> quads(count);
        data.read(reinterpret_cast<char*>(quads.data()), count * sizeof(Quad));
        std::vector<Index> index;
        index.reserve(count * 495);
        for (size_t quad_index = 0; quad_index < count; ++quad_index) {
            std::vector<int> support;
            for (int pass = 0; pass < 6; ++pass) {
                uint64_t word = quads[quad_index].syndrome[pass];
                while (word) {
                    support.push_back(64 * pass + __builtin_ctzll(word));
                    word &= word - 1;
                }
            }
            for (size_t first = 0; first < support.size(); ++first)
                for (size_t second = first + 1; second < support.size(); ++second)
                    for (size_t third = second + 1; third < support.size(); ++third)
                        for (size_t fourth = third + 1; fourth < support.size(); ++fourth) {
                            uint64_t key = support[first] | (uint64_t(support[second]) << 9) | (uint64_t(support[third]) << 18) | (uint64_t(support[fourth]) << 27);
                            index.push_back({key, uint32_t(quad_index)});
                        }
        }
        std::cout << "GROUP " << group << " indexed " << index.size() << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
        std::sort(index.begin(), index.end());
        std::vector<Result> results;
        results.reserve(20000000);
        for (const auto& quad : quads) {
            Result result{};
            result.positions.fill(65535);
            for (int offset = 0; offset < 4; ++offset) {
                result.positions[offset] = quad.positions[offset];
                result.fingerprint ^= hashes[quad.positions[offset]];
            }
            results.push_back(result);
        }
        for (size_t start = 0; start < index.size();) {
            size_t stop = start + 1;
            while (stop < index.size() && index[stop].key == index[start].key) ++stop;
            for (size_t first = start; first < stop; ++first) {
                const auto& left = quads[index[first].quad];
                for (size_t second = first + 1; second < stop; ++second) {
                    const auto& right = quads[index[second].quad];
                    std::array<int, 4> common;
                    int common_count = 0;
                    for (int pass = 0; pass < 6 && common_count < 4; ++pass) {
                        uint64_t word = left.syndrome[pass] & right.syndrome[pass];
                        while (word && common_count < 4) {
                            common[common_count++] = 64 * pass + __builtin_ctzll(word);
                            word &= word - 1;
                        }
                    }
                    uint64_t key = common[0] | (uint64_t(common[1]) << 9) | (uint64_t(common[2]) << 18) | (uint64_t(common[3]) << 27);
                    if (key != index[start].key) continue;
                    Result result{};
                    result.positions.fill(65535);
                    auto end = std::set_symmetric_difference(left.positions.begin(), left.positions.end(), right.positions.begin(), right.positions.end(), result.positions.begin());
                    if (end == result.positions.begin()) continue;
                    for (auto pointer = result.positions.begin(); pointer != end; ++pointer) result.fingerprint ^= hashes[*pointer];
                    results.push_back(result);
                }
            }
            start = stop;
        }
        index.clear();
        index.shrink_to_fit();
        std::cout << "GROUP " << group << " results " << results.size() << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
        std::sort(results.begin(), results.end());
        for (size_t index_result = 1; index_result < results.size(); ++index_result) {
            const auto& left = results[index_result - 1];
            const auto& right = results[index_result];
            if (left.fingerprint != right.fingerprint || left.positions == right.positions) continue;
            std::vector<int> support;
            std::set_symmetric_difference(left.positions.begin(), left.positions.end(), right.positions.begin(), right.positions.end(), std::back_inserter(support));
            support.erase(std::remove(support.begin(), support.end(), 65535), support.end());
            if (support.size() < 8 || support.size() > 18) continue;
            std::array<uint64_t, 6> syndrome{};
            for (int position : support) for (int pass = 0; pass < 6; ++pass) syndrome[pass] ^= uint64_t(1) << signatures[position][pass];
            bool zero = true;
            for (uint64_t word : syndrome) if (word) zero = false;
            if (!zero) continue;
            std::ofstream output(path + "/combined_quad_core.json");
            output << "{\"errors\":[";
            for (size_t offset = 0; offset < support.size(); ++offset) {
                if (offset) output << ',';
                output << support[offset];
            }
            output << "]}\n";
            std::cout << "FOUND " << support.size() << std::endl;
            return 0;
        }
        std::cout << "FINISHED " << group++ << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
    }
}
