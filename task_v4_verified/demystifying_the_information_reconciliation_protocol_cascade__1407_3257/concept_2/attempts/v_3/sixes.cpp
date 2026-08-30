#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

struct Template {
    std::array<std::array<int, 3>, 6> partners;
    std::vector<std::array<int, 6>> automorphisms;
};
struct Record {
    uint64_t fingerprint;
    std::array<uint16_t, 6> positions;
    bool operator<(const Record& other) const {
        return fingerprint < other.fingerprint || (fingerprint == other.fingerprint && positions < other.positions);
    }
};
std::array<std::array<int, 6>, 8192> signatures;
std::array<uint64_t, 8192> hashes;
std::array<int, 3> dimensions;
std::array<int, 6> assignment;
std::array<std::vector<std::vector<int>>, 8> groups;
std::vector<Record> records;

void enumerate(const Template& pattern, int depth) {
    if (depth == 6) {
        Record result{};
        for (int offset = 0; offset < 6; ++offset) {
            result.positions[offset] = assignment[offset];
            result.fingerprint ^= hashes[assignment[offset]];
        }
        std::sort(result.positions.begin(), result.positions.end());
        records.push_back(result);
        return;
    }
    int mask = 0, key = 0, shift = 0;
    for (int color = 0; color < 3; ++color) {
        int partner = pattern.partners[depth][color];
        if (partner >= depth) continue;
        mask |= 1 << color;
        key |= signatures[assignment[partner]][dimensions[color]] << shift;
        shift += 6;
    }
    for (int position : groups[mask][key]) {
        bool allowed = true;
        for (int previous = 0; previous < depth && allowed; ++previous) {
            if (position == assignment[previous]) { allowed = false; break; }
            for (int color = 0; color < 3; ++color) {
                if (pattern.partners[depth][color] != previous && signatures[position][dimensions[color]] == signatures[assignment[previous]][dimensions[color]]) { allowed = false; break; }
            }
        }
        if (!allowed) continue;
        assignment[depth] = position;
        for (const auto& permutation : pattern.automorphisms) {
            for (int offset = 0; offset <= depth; ++offset) {
                int other = permutation[offset];
                if (other > depth) break;
                if (assignment[offset] < assignment[other]) break;
                if (assignment[offset] > assignment[other]) { allowed = false; break; }
            }
            if (!allowed) break;
        }
        if (allowed) enumerate(pattern, depth + 1);
    }
}

int main(int argc, char** argv) {
    std::string path = argv[1];
    int begin_group = argc > 2 ? std::stoi(argv[2]) : 0;
    int end_group = argc > 3 ? std::stoi(argv[3]) : 20;
    std::ifstream input(path + "/signatures.txt");
    std::mt19937_64 generator(81712709);
    std::array<uint64_t, 384> check_hashes;
    for (auto& hash : check_hashes) hash = generator();
    for (int position = 0; position < 8192; ++position) {
        for (int pass = 0; pass < 6; ++pass) {
            input >> signatures[position][pass];
            hashes[position] ^= check_hashes[64 * pass + signatures[position][pass]];
        }
    }
    std::ifstream template_input(path + "/six_templates.txt");
    int count;
    template_input >> count;
    std::vector<Template> templates(count);
    for (auto& pattern : templates) {
        for (auto& row : pattern.partners) for (int& value : row) template_input >> value;
        template_input >> count;
        pattern.automorphisms.resize(count);
        for (auto& permutation : pattern.automorphisms) for (int& value : permutation) template_input >> value;
    }
    int group = 0;
    auto started = std::chrono::steady_clock::now();
    for (int first = 0; first < 6; ++first) for (int second = first + 1; second < 6; ++second) for (int third = second + 1; third < 6; ++third, ++group) {
        if (group < begin_group || group >= end_group) continue;
        dimensions = {first, second, third};
        for (int mask = 0; mask < 8; ++mask) groups[mask].assign(1 << (6 * __builtin_popcount(unsigned(mask))), {});
        for (int position = 0; position < 8192; ++position) {
            for (int mask = 0; mask < 8; ++mask) {
                int key = 0, shift = 0;
                for (int color = 0; color < 3; ++color) if (mask >> color & 1) { key |= signatures[position][dimensions[color]] << shift; shift += 6; }
                groups[mask][key].push_back(position);
            }
        }
        records.clear();
        records.reserve(100000000);
        for (size_t pattern_index = 0; pattern_index < templates.size(); ++pattern_index) {
            enumerate(templates[pattern_index], 0);
            std::cout << "GROUP " << group << " template " << pattern_index << " records " << records.size() << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
        }
        std::sort(records.begin(), records.end());
        for (size_t index = 1; index < records.size(); ++index) {
            const auto& left = records[index - 1];
            const auto& right = records[index];
            if (left.fingerprint != right.fingerprint || left.positions == right.positions) continue;
            std::vector<int> support;
            std::set_symmetric_difference(left.positions.begin(), left.positions.end(), right.positions.begin(), right.positions.end(), std::back_inserter(support));
            if (support.size() < 8) continue;
            std::array<uint64_t, 6> syndrome{};
            for (int position : support) for (int pass = 0; pass < 6; ++pass) syndrome[pass] ^= uint64_t(1) << signatures[position][pass];
            bool zero = true;
            for (uint64_t word : syndrome) if (word) zero = false;
            if (!zero) continue;
            std::ofstream output(path + "/six_core.json");
            output << "{\"errors\":[";
            for (size_t offset = 0; offset < support.size(); ++offset) { if (offset) output << ','; output << support[offset]; }
            output << "]}\n";
            std::cout << "FOUND " << support.size() << std::endl;
            return 0;
        }
        std::cout << "FINISHED " << group << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
    }
}
