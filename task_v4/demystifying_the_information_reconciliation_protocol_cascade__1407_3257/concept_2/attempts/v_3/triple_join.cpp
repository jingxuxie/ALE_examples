#define main unused_sixes_main
#include "sixes.cpp"
#undef main

struct Triple {
    uint64_t key_support;
    uint64_t fingerprint;
    bool operator<(const Triple& other) const { return key_support < other.key_support; }
};

int main(int argc, char** argv) {
    std::string path = argv[1];
    int begin = std::stoi(argv[2]), end = std::stoi(argv[3]);
    std::ifstream input(path + "/signatures.txt");
    std::mt19937_64 generator(81712709);
    std::array<uint64_t, 384> check_hashes;
    for (auto& hash : check_hashes) hash = generator();
    for (int position = 0; position < 8192; ++position) for (int pass = 0; pass < 6; ++pass) {
        input >> signatures[position][pass];
        hashes[position] ^= check_hashes[64 * pass + signatures[position][pass]];
    }
    auto started = std::chrono::steady_clock::now();
    int group_index = 0;
    for (int first_pass = 0; first_pass < 6; ++first_pass) for (int second_pass = first_pass + 1; second_pass < 6; ++second_pass) for (int third_pass = second_pass + 1; third_pass < 6; ++third_pass, ++group_index) {
        if (group_index < begin || group_index >= end) continue;
        dimensions = {first_pass, second_pass, third_pass};
        for (int mask = 0; mask < 8; ++mask) groups[mask].assign(1 << (6 * __builtin_popcount(unsigned(mask))), {});
        for (int position = 0; position < 8192; ++position) for (int mask = 0; mask < 8; ++mask) {
            int key = 0, shift = 0;
            for (int color = 0; color < 3; ++color) if (mask >> color & 1) { key |= signatures[position][dimensions[color]] << shift; shift += 6; }
            groups[mask][key].push_back(position);
        }
        std::vector<Triple> triples;
        triples.reserve(12000000);
        auto add = [&](int first, int second, int third) {
            if (first == second || first == third || second == third) return;
            uint64_t key = 0;
            for (int color = 0; color < 3; ++color) {
                int left = signatures[first][dimensions[color]], middle = signatures[second][dimensions[color]], right = signatures[third][dimensions[color]];
                if ((left == middle) + (left == right) + (middle == right) != 1) return;
                key |= uint64_t(left ^ middle ^ right) << (6 * color);
            }
            std::array<int, 3> positions{first, second, third};
            std::sort(positions.begin(), positions.end());
            uint64_t support = positions[0] | (uint64_t(positions[1]) << 13) | (uint64_t(positions[2]) << 26);
            triples.push_back({(key << 39) | support, hashes[first] ^ hashes[second] ^ hashes[third]});
        };
        for (int omitted = 0; omitted < 3; ++omitted) {
            int pair_mask = 7 ^ (1 << omitted);
            for (const auto& bucket : groups[pair_mask]) for (size_t left = 0; left < bucket.size(); ++left) for (size_t right = left + 1; right < bucket.size(); ++right) {
                int first = bucket[left], second = bucket[right];
                int first_label = signatures[first][dimensions[omitted]], second_label = signatures[second][dimensions[omitted]];
                if (first_label == second_label) {
                    for (int third = 0; third < 8192; ++third) add(first, second, third);
                } else {
                    for (int third : groups[1 << omitted][first_label]) add(first, second, third);
                    for (int third : groups[1 << omitted][second_label]) add(first, second, third);
                }
            }
        }
        for (int first = 0; first < 8192; ++first) for (int second : groups[1][signatures[first][dimensions[0]]]) {
            if (second <= first) continue;
            int key = signatures[first][dimensions[1]] | (signatures[second][dimensions[2]] << 6);
            for (int third : groups[6][key]) if (third > first) add(first, second, third);
        }
        std::sort(triples.begin(), triples.end());
        triples.erase(std::unique(triples.begin(), triples.end(), [](const Triple& left, const Triple& right) { return left.key_support == right.key_support; }), triples.end());
        std::cout << "TRIPLES " << group_index << ' ' << triples.size() << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
        records.clear();
        records.reserve(150000000);
        for (size_t start = 0; start < triples.size();) {
            size_t stop = start + 1;
            while (stop < triples.size() && (triples[stop].key_support >> 39) == (triples[start].key_support >> 39)) ++stop;
            for (size_t left = start; left < stop; ++left) for (size_t right = left + 1; right < stop; ++right) {
                Record result{};
                for (int offset = 0; offset < 3; ++offset) {
                    result.positions[offset] = (triples[left].key_support >> (13 * offset)) & 8191;
                    result.positions[offset + 3] = (triples[right].key_support >> (13 * offset)) & 8191;
                }
                std::sort(result.positions.begin(), result.positions.end());
                if (std::adjacent_find(result.positions.begin(), result.positions.end()) != result.positions.end()) continue;
                result.fingerprint = triples[left].fingerprint ^ triples[right].fingerprint;
                records.push_back(result);
            }
            start = stop;
        }
        std::cout << "SIXES " << group_index << ' ' << records.size() << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
        std::sort(records.begin(), records.end());
        for (size_t index = 1; index < records.size(); ++index) {
            const auto& left = records[index - 1]; const auto& right = records[index];
            if (left.fingerprint != right.fingerprint || left.positions == right.positions) continue;
            std::vector<int> support;
            std::set_symmetric_difference(left.positions.begin(), left.positions.end(), right.positions.begin(), right.positions.end(), std::back_inserter(support));
            if (support.size() < 8) continue;
            std::array<uint64_t, 6> syndrome{};
            for (int position : support) for (int pass = 0; pass < 6; ++pass) syndrome[pass] ^= uint64_t(1) << signatures[position][pass];
            bool zero = true;
            for (uint64_t word : syndrome) if (word) zero = false;
            if (!zero) continue;
            std::ofstream output(path + "/triple_join_core.json");
            output << "{\"errors\":[";
            for (size_t offset = 0; offset < support.size(); ++offset) { if (offset) output << ','; output << support[offset]; }
            output << "]}\n";
            std::cout << "FOUND " << support.size() << std::endl;
            return 0;
        }
        std::cout << "FINISHED " << group_index << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
    }
}
