#define main previous_main
#include "structured.cpp"
#undef main

using Vector = std::array<uint64_t, 12>;
std::array<std::array<Vector, 4>, 6> coefficients{};
std::vector<std::array<int, 6>> permutations;

int main(int argc, char **argv) {
    int limit = argc > 1 ? std::stoi(argv[1]) : 1000;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 480;
    int architecture = argc > 3 ? std::stoi(argv[3]) : 0;
    std::array<std::array<int, 4>, 6> matrices{{{1,0,0,1}, {0,1,1,0}, {1,0,1,1}, {0,1,1,1}, {1,1,1,0}, {1,1,0,1}}};
    std::array<int, 6> permutation{0,1,2,3,4,5};
    do {
        int index = permutations.size();
        permutations.push_back(permutation);
        for (int choice = 0; choice < 6; choice++) {
            for (int coefficient = 0; coefficient < 4; coefficient++) {
                coefficients[choice][coefficient][index / 64] |= uint64_t(matrices[permutation[choice]][coefficient]) << (index % 64);
            }
        }
    } while (std::next_permutation(permutation.begin(), permutation.end()));
    std::vector<uint32_t> seeds{42, 12345, 1234, 1337, 2024, 2025, 2026, 123456, 1234567, 12345678, 123456789, 314159, 271828, 8675309, 0xC1FF0D, 0xC1FF0D36, 0xC1FF, 0xC11FF0D, 0x5EED, 0xC0FFEE, 0xBADC0DE, 20250308, 20250301, 20240517, 20250101, 20250403, 20250321, 20250911, 20251001, 20260101, 20260301, 20260828, 20260217, 20250217, 20250617, 424242, 31415926, 27182818, 0, 1, 2, 3, 4, 5, 7, 11, 17, 19, 36, 64, 72, 99, 100, 101, 123, 999, 1000, 20250314, 20250317, 20250318, 20250417, 20260417, 20260401, 31415, 27182};
    for (int year = 2019; year <= 2026; year++) for (int month = 1; month <= 12; month++) for (int day = 1; day <= 31; day++) seeds.push_back(year * 10000 + month * 100 + day);
    for (int seed = 1000; seed < limit; seed++) seeds.push_back(seed);
    for (int row = 0; row < 6; row++) for (int column = 0; column < 5; column++) matchings[column % 2].push_back({6 * row + column, 6 * row + column + 1});
    for (int row = 0; row < 5; row++) for (int column = 0; column < 6; column++) matchings[2 + row % 2].push_back({6 * row + column, 6 * row + column + 6});
    std::vector<std::array<int, 2>> all_edges;
    for (int qubit = 0; qubit < 36; qubit++) {
        if (qubit % 6 < 5) all_edges.push_back({qubit, qubit + 1});
        if (qubit / 6 < 5) all_edges.push_back({qubit, qubit + 6});
    }
    std::ifstream input("target_rows.txt");
    uint64_t target_x, target_z;
    input >> target_x >> target_z;
    auto start = std::chrono::steady_clock::now();
    uint64_t tested = 0;
    for (uint32_t seed : seeds) {
        for (int rounds : {20}) {
            for (int direction = 0; direction < 4; direction++) {
                for (int layout = 0; layout < 3; layout++) {
                    std::array<int, 4> order{0, 1, 2, 3};
                    do {
                        PythonRandom randomizer;
                        randomizer.seed(seed);
                        std::array<Vector, 36> xrows{}, zrows{};
                        xrows[0].fill(~0ULL);
                        xrows[0][11] = 0xffff;
                        std::vector<Gate> operations;
                        auto singles = [&]() {
                            for (int qubit = 0; qubit < 36; qubit++) {
                                int choice = randomizer.below(6);
                                operations.push_back({choice, qubit, -1});
                                for (int word = 0; word < 12; word++) {
                                    uint64_t xbits = xrows[qubit][word], zbits = zrows[qubit][word];
                                    xrows[qubit][word] = (xbits & coefficients[choice][0][word]) ^ (zbits & coefficients[choice][1][word]);
                                    zrows[qubit][word] = (xbits & coefficients[choice][2][word]) ^ (zbits & coefficients[choice][3][word]);
                                }
                            }
                        };
                        auto choose_matching = [&](int layer) {
                            if (architecture == 0) return matchings[order[layer % 4]];
                            if (architecture == 1) return matchings[order[randomizer.below(4)]];
                            auto shuffled = all_edges;
                            for (int index = int(shuffled.size()) - 1; index > 0; index--) std::swap(shuffled[index], shuffled[randomizer.below(index + 1)]);
                            std::array<bool, 36> used{};
                            std::vector<std::array<int, 2>> selected;
                            for (auto edge : shuffled) {
                                if (used[edge[0]] || used[edge[1]]) continue;
                                selected.push_back(edge);
                                used[edge[0]] = used[edge[1]] = true;
                            }
                            return selected;
                        };
                        for (int layer = 0; layer < rounds; layer++) {
                            std::vector<std::array<int, 2>> chosen;
                            if (architecture == 3) chosen = choose_matching(layer);
                            if (layout != 2) singles();
                            if (architecture != 3) chosen = choose_matching(layer);
                            for (auto edge : chosen) {
                                bool reverse = direction < 2 ? randomizer.coin(direction) : direction < 4 ? (randomizer.coin(2) ^ (direction == 2)) : direction == 4 ? false : direction == 5 ? true : direction == 6 ? layer % 2 : ((edge[0] / 6 + edge[0] % 6 + layer) % 2);
                                int first = edge[reverse], second = edge[!reverse];
                                operations.push_back({6, first, second});
                                for (int word = 0; word < 12; word++) {
                                    xrows[second][word] ^= xrows[first][word];
                                    zrows[first][word] ^= zrows[second][word];
                                }
                            }
                            if (layout == 2) singles();
                        }
                        if (layout == 1) singles();
                        tested += 720;
                        Vector matches;
                        matches.fill(~0ULL);
                        matches[11] = 0xffff;
                        for (int qubit = 0; qubit < 36; qubit++) {
                            for (int word = 0; word < 12; word++) {
                                matches[word] &= ((target_x >> qubit) & 1) ? xrows[qubit][word] : ~xrows[qubit][word];
                                matches[word] &= ((target_z >> qubit) & 1) ? zrows[qubit][word] : ~zrows[qubit][word];
                            }
                        }
                        for (int word = 0; word < 12; word++) {
                            if (!matches[word]) continue;
                            int found = word * 64 + __builtin_ctzll(matches[word]);
                            std::cout << "MATCH " << seed << ' ' << rounds << ' ' << direction << ' ' << layout << " order ";
                            for (auto value : order) std::cout << value;
                            std::cout << " permutation ";
                            for (auto value : permutations[found]) std::cout << value;
                            std::cout << std::endl;
                            std::ofstream output("structured_match.json");
                            output << '[';
                            bool separator = false;
                            for (auto gate : operations) {
                                if (gate.name == 6) {
                                    if (separator) output << ',';
                                    separator = true;
                                    output << "[\"CX\",[" << gate.first << ',' << gate.second << "]]";
                                } else {
                                    for (char name : word_sets[0][permutations[found][gate.name]]) {
                                        if (separator) output << ',';
                                        separator = true;
                                        output << "[\"" << name << "\",[" << gate.first << "]]";
                                    }
                                }
                            }
                            output << ']';
                            return 0;
                        }
                    } while (architecture < 2 && std::next_permutation(order.begin(), order.end()));
                }
            }
        }
        std::cout << "seed " << seed << " tested " << tested << std::endl;
        if (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() > seconds) break;
    }
}
