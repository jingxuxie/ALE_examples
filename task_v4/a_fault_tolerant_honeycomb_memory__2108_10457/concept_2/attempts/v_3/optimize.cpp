#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <sstream>
#include <string>
#include <vector>

using Pattern = std::array<int, 24>;
using Vector = std::array<uint64_t, 7>;
using Support = std::vector<int>;
using Supports = std::vector<Support>;
std::mt19937_64 generator;
double uniform() { return (generator() >> 11) * 0x1.0p-53; }
Pattern baseline = {1,0,0,2,2,1,2,2,1,1,0,0,1,0,0,2,2,1,2,2,1,1,0,0};

Pattern parse(const std::string &text) {
    Pattern result{};
    int index = 0;
    for (char value : text) if (value >= '0' && value <= '2' && index < 24) result[index++] = value - '0';
    if (index != 24) throw std::runtime_error("pattern must have 24 digits");
    return result;
}
std::string encode(const Pattern &pattern) {
    std::string result;
    for (int axis : pattern) result += char('0' + axis);
    return result;
}
struct Case {
    int slots;
    int words;
    std::vector<int> cells;
    std::vector<std::array<Vector,3>> columns;
    Case(int scale) : words(scale == 1 ? 1 : scale == 2 ? 4 : 7) {
        std::ifstream input("case" + std::to_string(scale) + ".txt");
        input >> slots;
        cells.resize(slots);
        columns.resize(slots);
        for (int slot = 0; slot < slots; ++slot) {
            input >> cells[slot];
            for (int axis = 0; axis < 3; ++axis) {
                std::string hex;
                input >> hex;
                int word = 0;
                while (!hex.empty()) {
                    int start = std::max(0, int(hex.size()) - 16);
                    columns[slot][axis][word++] = std::stoull(hex.substr(start), nullptr, 16);
                    hex.resize(start);
                }
            }
        }
    }
    Supports generate(int count, double density, uint64_t seed) const {
        std::mt19937_64 random(seed);
        uint64_t threshold = density * double(UINT64_MAX);
        Supports supports(count);
        for (auto &support : supports) {
            support.reserve(slots / 2);
            for (int slot = 0; slot < slots; ++slot) if (random() < threshold) support.push_back(slot);
        }
        return supports;
    }
    Supports read_supports(int scale) const {
        std::ifstream input("check" + std::to_string(scale) + ".txt");
        int count;
        input >> count;
        Supports result(count);
        for (auto &support : result) {
            int size;
            input >> size;
            support.resize(size);
            for (auto &slot : support) input >> slot;
        }
        return result;
    }
    Supports mixture(int count, uint64_t seed) const {
        Supports result;
        for (int family = 0; family < 3; ++family) {
            auto group = generate((count + 2 - family) / 3, .28 + .02 * family, seed + family * 83723);
            result.insert(result.end(), group.begin(), group.end());
        }
        std::mt19937_64 random(seed + 28891);
        std::shuffle(result.begin(), result.end(), random);
        return result;
    }
    template<int Words> double score(const Pattern &pattern, const Supports &supports, bool full = false) const {
        std::vector<Vector> selected(slots);
        for (int slot = 0; slot < slots; ++slot) selected[slot] = columns[slot][pattern[cells[slot]]];
        int failures = 0;
        for (const auto &support : supports) {
            std::array<std::array<uint64_t,Words>,Words*64> basis{};
            int ambiguity = 0;
            for (int slot : support) {
                std::array<uint64_t,Words> value;
                for (int word = 0; word < Words; ++word) value[word] = selected[slot][word];
                for (int word = Words - 1; word >= 0; --word) {
                    while (value[word]) {
                        int pivot = word * 64 + 63 - __builtin_clzll(value[word]);
                        if (pivot < 4) {
                            if (!full) { ambiguity = 1; goto finished; }
                        }
                        if (!basis[pivot][word]) {
                            for (int part = 0; part <= word; ++part) basis[pivot][part] = value[part];
                            ambiguity += pivot < 4;
                            goto next_slot;
                        }
                        for (int part = 0; part <= word; ++part) value[part] ^= basis[pivot][part];
                    }
                }
                next_slot:;
            }
            finished: failures += ambiguity;
        }
        return 1.0 - double(failures) / supports.size();
    }
    double score(const Pattern &pattern, const Supports &supports, bool full = false) const {
        if (words == 1) return score<1>(pattern, supports, full);
        if (words == 4) return score<4>(pattern, supports, full);
        return score<7>(pattern, supports, full);
    }
    std::pair<int,int> ranks(const Pattern &pattern) const {
        std::array<uint64_t,64> basis{};
        int rank = 0, logical = 0;
        for (int slot = 0; slot < slots; ++slot) {
            uint64_t value = columns[slot][pattern[cells[slot]]][0];
            while (value) {
                int pivot = 63 - __builtin_clzll(value);
                if (!basis[pivot]) {
                    basis[pivot] = value;
                    ++rank;
                    logical += pivot < 4;
                    break;
                }
                value ^= basis[pivot];
            }
        }
        return {rank,logical};
    }
};

int main(int argc, char **argv) {
    std::cout << std::setprecision(7) << std::unitbuf;
    std::string mode = argc > 1 ? argv[1] : "eval";
    uint64_t seed = argc > 2 ? std::stoull(argv[2]) : 1;
    generator.seed(seed);
    if (mode == "eval" || mode == "check") {
        Pattern pattern = argc > 3 ? parse(argv[3]) : baseline;
        int count = argc > 4 ? std::stoi(argv[4]) : 4096;
        double sum = 0, worst = 1;
        std::cout << encode(pattern) << '\n';
        for (int scale = 1; scale <= 3; ++scale) {
            Case data(scale);
            for (int family = 0; family < 3; ++family) {
                Supports supports;
                if (mode == "check") {
                    auto all = data.read_supports(scale);
                    supports = Supports(all.begin() + 512 * family, all.begin() + 512 * (family + 1));
                } else supports = data.generate(count, .28 + .02 * family, seed + 37 * scale + family * 1383);
                double score = data.score(pattern, supports);
                double ambiguity = 1 - data.score(pattern, supports, true);
                sum += score;
                worst = std::min(worst, score);
                std::cout << scale << ' ' << family << ' ' << score << ' ' << ambiguity << '\n';
            }
        }
        std::cout << "CORE " << sum / 9 << " WORST " << worst << '\n';
        return 0;
    }
    if (mode == "ranksearch") {
        Case data(1);
        auto supports = data.generate(1024, .32, seed + 832);
        int iterations = argc > 3 ? std::stoi(argv[3]) : 1000000;
        std::array<long long,5> histogram{};
        std::array<long long,65> rankhist{};
        double best = 0;
        for (int iteration = 0; iteration < iterations; ++iteration) {
            Pattern pattern;
            for (int &axis : pattern) axis = generator() % 3;
            auto [rank,logical] = data.ranks(pattern);
            ++histogram[logical];
            ++rankhist[rank];
            if (logical <= 2) {
                double score = data.score(pattern, supports);
                if (score > best) {
                    best = score;
                    std::cout << "BEST " << score << ' ' << encode(pattern) << " rank " << rank << ' ' << logical << '\n';
                }
            }
        }
        for (int logical = 0; logical < 5; ++logical) std::cout << "LOGICAL " << logical << ' ' << histogram[logical] << '\n';
        for (int rank = 0; rank < 65; ++rank) if (rankhist[rank]) std::cout << "RANK " << rank << ' ' << rankhist[rank] << '\n';
        return 0;
    }
    if (mode == "rankbranch") {
        Case data(1);
        auto supports = data.generate(4096, .32, seed);
        std::array<uint64_t,64> basis{};
        std::vector<int> changes;
        Pattern pattern{};
        std::array<uint64_t,25> nodes{};
        std::ofstream patterns("rank2_patterns_" + std::to_string(seed) + ".txt");
        std::function<void(int,int)> visit = [&](int depth, int logical) {
            ++nodes[depth];
            if (depth == 24) {
                patterns << encode(pattern) << '\n';
                double score = data.score(pattern, supports);
                std::cout << "POOL " << score << ' ' << encode(pattern) << " logical " << logical << '\n';
                return;
            }
            for (int axis = 0; axis < 3; ++axis) {
                pattern[depth] = axis;
                size_t saved = changes.size();
                int added = 0;
                for (int slot = depth; slot < data.slots; slot += 24) {
                    uint64_t value = data.columns[slot][axis][0];
                    while (value) {
                        int pivot = 63 - __builtin_clzll(value);
                        if (!basis[pivot]) {
                            basis[pivot] = value;
                            changes.push_back(pivot);
                            added += pivot < 4;
                            break;
                        }
                        value ^= basis[pivot];
                    }
                }
                if (logical + added <= 2) visit(depth+1, logical+added);
                while (changes.size() > saved) {
                    basis[changes.back()] = 0;
                    changes.pop_back();
                }
            }
        };
        visit(0,0);
        for (int depth = 0; depth <= 24; ++depth) std::cout << "DEPTH " << depth << ' ' << nodes[depth] << '\n';
        return 0;
    }
    if (mode == "branch") {
        Case data(1);
        int count = argc > 3 ? std::stoi(argv[3]) : 32;
        int minimum = argc > 4 ? std::stoi(argv[4]) : 16;
        int order = argc > 5 ? std::stoi(argv[5]) : 0;
        std::string prefix = argc > 6 ? argv[6] : "";
        bool mixture = argc > 7 && std::string(argv[7]) == "mix";
        bool lookahead = argc > 8 && std::string(argv[8]) == "look";
        bool canonical = argc > 9 && std::string(argv[9]) == "sym";
        auto screening = mixture ? data.mixture(count, seed) : data.generate(count, .32, seed);
        if (argc > 10) {
            std::ifstream input(argv[10]);
            int records = 0;
            input >> records;
            if (records != count) throw std::runtime_error("screening record count mismatch");
            screening.assign(count, {});
            for (auto &support : screening) {
                int size = 0;
                input >> size;
                support.resize(size);
                for (int &slot : support) input >> slot;
            }
        }
        auto training = mixture ? data.mixture(2048, seed + 32167) : data.generate(2048, .32, seed + 32167);
        auto validation = mixture ? data.mixture(32768, seed + 821746) : data.generate(32768, .32, seed + 821746);
        std::vector<std::array<Support,24>> selected(count);
        for (int sample = 0; sample < count; ++sample) {
            for (int slot : screening[sample]) selected[sample][data.cells[slot]].push_back(slot);
        }
        std::vector<std::array<uint64_t,64>> basis(count);
        std::vector<bool> active(count, true);
        std::vector<std::pair<int,int>> changes;
        std::vector<int> failed;
        std::array<uint64_t,25> nodes{};
        std::array<int,24> cellorder;
        std::iota(cellorder.begin(), cellorder.end(), 0);
        if (order == 1) for (int index = 0; index < 24; ++index) cellorder[index] = (index % 4) * 6 + index / 4;
        if (order == 2) std::shuffle(cellorder.begin(), cellorder.end(), generator);
        if (order == 3) cellorder = {0,6,12,18,3,9,15,21,1,7,13,19,4,10,16,22,2,8,14,20,5,11,17,23};
        std::array<int,24> position;
        for (int depth = 0; depth < 24; ++depth) position[cellorder[depth]] = depth;
        std::vector<std::array<int,24>> symmetries;
        for (int reflected = 0; reflected < 2; ++reflected) {
            for (int shift = 0; shift < 4; ++shift) {
                std::array<int,24> permutation;
                for (int cell = 0; cell < 24; ++cell) {
                    int column = reflected ? 3 - cell / 6 : cell / 6;
                    permutation[cell] = ((column + shift) % 4) * 6 + (cell % 6 + 3 * shift) % 6;
                }
                symmetries.push_back(permutation);
            }
        }
        Pattern pattern{};
        double best = .4;
        uint64_t total = 0, leaves = 0;
        uint64_t covered = 0;
        std::array<uint64_t,25> powers;
        powers[0] = 1;
        for (int power = 1; power <= 24; ++power) powers[power] = powers[power-1] * 3;
        auto start = std::chrono::steady_clock::now();
        std::function<void(int)> visit = [&](int depth) {
            ++nodes[depth];
            ++total;
            if (canonical) {
                for (const auto &permutation : symmetries) {
                    for (int cell = 0; cell < 24; ++cell) {
                        int mapped = permutation[cell];
                        if (position[cell] >= depth || position[mapped] >= depth) break;
                        if (pattern[cell] < pattern[mapped]) break;
                        if (pattern[cell] > pattern[mapped]) {
                            covered += powers[24-depth];
                            return;
                        }
                    }
                }
            }
            if (total % 10000000 == 0) {
                auto seconds = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
                std::cout << "NODES " << total << " leaves " << leaves << " seconds " << seconds << " prefix " << encode(pattern).substr(0,depth) << '\n';
            }
            if (depth == 24) {
                ++leaves;
                ++covered;
                double direct = data.score(pattern, screening);
                if (std::abs(direct * count - (count - int(failed.size()))) > 1e-6) throw std::runtime_error("incremental rank mismatch");
                if (minimum == 0) return;
                double score = data.score(pattern, training);
                if (score > .36) {
                    double checked = data.score(pattern, validation);
                    std::cout << "POOL " << checked << ' ' << encode(pattern) << '\n';
                    if (checked > best) {
                        best = checked;
                        std::cout << "BEST " << best << ' ' << encode(pattern) << '\n';
                    }
                }
                return;
            }
            if (lookahead && (depth == 14 || depth == 16 || depth == 18)) {
                for (int sample = 0; sample < count; ++sample) {
                    if (!active[sample]) continue;
                    for (int future = depth; future < 24; ++future) {
                        int futurecell = cellorder[future];
                        if (selected[sample][futurecell].empty()) continue;
                        bool unavoidable = true;
                        for (int axis = 0; axis < 3; ++axis) {
                            std::array<int,6> inserted;
                            int insertedcount = 0;
                            bool failure = false;
                            for (int slot : selected[sample][futurecell]) {
                                uint64_t value = data.columns[slot][axis][0];
                                while (value) {
                                    int pivot = 63 - __builtin_clzll(value);
                                    if (pivot < 4) {
                                        failure = true;
                                        break;
                                    }
                                    if (!basis[sample][pivot]) {
                                        basis[sample][pivot] = value;
                                        inserted[insertedcount++] = pivot;
                                        break;
                                    }
                                    value ^= basis[sample][pivot];
                                }
                                if (failure) break;
                            }
                            for (int index = 0; index < insertedcount; ++index) basis[sample][inserted[index]] = 0;
                            if (!failure) {
                                unavoidable = false;
                                break;
                            }
                        }
                        if (unavoidable) {
                            active[sample] = false;
                            failed.push_back(sample);
                            break;
                        }
                    }
                    if (count - int(failed.size()) < minimum) {
                        covered += powers[24-depth];
                        return;
                    }
                }
            }
            int cell = cellorder[depth];
            for (int axis = 0; axis < 3; ++axis) {
                if (depth < int(prefix.size()) && axis != prefix[depth] - '0') continue;
                pattern[cell] = axis;
                size_t savedchanges = changes.size(), savedfailed = failed.size();
                for (int sample = 0; sample < count; ++sample) {
                    if (!active[sample]) continue;
                    for (int slot : selected[sample][cell]) {
                        uint64_t value = data.columns[slot][axis][0];
                        while (value) {
                            int pivot = 63 - __builtin_clzll(value);
                            if (pivot < 4) {
                                active[sample] = false;
                                failed.push_back(sample);
                                goto next_sample;
                            }
                            if (!basis[sample][pivot]) {
                                basis[sample][pivot] = value;
                                changes.push_back({sample,pivot});
                                break;
                            }
                            value ^= basis[sample][pivot];
                        }
                    }
                    next_sample:;
                    if (count - int(failed.size()) < minimum) break;
                }
                if (count - int(failed.size()) >= minimum) visit(depth+1);
                else covered += powers[24 - depth - 1];
                while (changes.size() > savedchanges) {
                    auto [sample,pivot] = changes.back();
                    basis[sample][pivot] = 0;
                    changes.pop_back();
                }
                while (failed.size() > savedfailed) {
                    active[failed.back()] = true;
                    failed.pop_back();
                }
            }
        };
        visit(0);
        std::cout << "COVERED " << covered << '\n';
        for (int depth = 0; depth <= 24; ++depth) std::cout << "DEPTH " << depth << ' ' << nodes[depth] << '\n';
        return 0;
    }
    if (mode == "enumerate") {
        Case data(1);
        int mapping = argc > 3 ? std::stoi(argv[3]) : 0;
        auto screening = data.generate(128, .32, seed);
        auto training = data.generate(2048, .32, seed + 47293);
        auto validation = data.generate(32768, .32, seed + 7932923);
        double best = .4;
        std::array<int,3> permutation = {0,1,2};
        for (int perm = 0; perm < 6; ++perm) {
            for (int code = 0; code < 531441; ++code) {
                int remaining = code;
                std::array<int,12> small;
                for (int &axis : small) { axis = remaining % 3; remaining /= 3; }
                Pattern pattern;
                for (int cell = 0; cell < 24; ++cell) {
                    int index = mapping == 0 ? cell % 12 : (cell / 6) * 3 + cell % 3;
                    bool transform = mapping == 0 ? cell >= 12 : cell % 6 >= 3;
                    pattern[cell] = transform ? permutation[small[index]] : small[index];
                }
                double quick = data.score(pattern, screening);
                if (quick < .28) continue;
                double score = data.score(pattern, training);
                if (score < .36) continue;
                double checked = data.score(pattern, validation);
                std::cout << "POOL " << checked << ' ' << encode(pattern) << " perm " << perm << '\n';
                if (checked > best) {
                    best = checked;
                    std::cout << "BEST " << best << ' ' << encode(pattern) << '\n';
                }
            }
            std::cout << "PERM_DONE " << perm << '\n';
            std::next_permutation(permutation.begin(), permutation.end());
        }
        return 0;
    }
    if (mode == "screen") {
        int count = argc > 4 ? std::stoi(argv[4]) : 2048;
        int scale = argc > 5 ? std::stoi(argv[5]) : 1;
        Case data(scale);
        auto supports = data.generate(count, .32, seed);
        std::ifstream input(argv[3]);
        std::string text;
        std::vector<std::pair<double,std::string>> ranked;
        while (input >> text) {
            auto pattern = parse(text);
            ranked.push_back({data.score(pattern, supports), text});
        }
        std::sort(ranked.rbegin(), ranked.rend());
        for (auto &[score, text] : ranked) std::cout << score << ' ' << text << '\n';
        return 0;
    }
    if (mode == "search") {
        Case data(1);
        int iterations = argc > 3 ? std::stoi(argv[3]) : 10000;
        int count = argc > 4 ? std::stoi(argv[4]) : 512;
        auto validation = data.generate(16384, .32, 8293634);
        auto training = data.generate(count, .32, generator());
        Pattern current = baseline;
        double score = data.score(current, training);
        double best = data.score(current, validation);
        std::cout << "BEST " << best << ' ' << encode(current) << '\n';
        for (int iteration = 0; iteration < iterations; ++iteration) {
            int cycle = iteration % 1000;
            if (cycle == 0) {
                training = data.generate(count, .32, generator());
                if (iteration % 5000 == 0 && iteration) for (int &axis : current) axis = generator() % 3;
                score = data.score(current, training);
            }
            double temperature = .025 * std::pow(.02, cycle / 999.0);
            Pattern candidate = current;
            int changes = 1 + (uniform() < .2) + (uniform() < .08) * 2;
            for (int change = 0; change < changes; ++change) {
                int cell = generator() % 24;
                candidate[cell] = (candidate[cell] + 1 + generator() % 2) % 3;
            }
            double next = data.score(candidate, training);
            if (next >= score || uniform() < std::exp((next - score) / temperature)) {
                current = candidate;
                score = next;
            }
            if (cycle % 100 == 99 || next > best + .04) {
                double checked = data.score(current, validation);
                if (checked > best) {
                    best = checked;
                    std::cout << "BEST " << best << ' ' << encode(current) << " iter " << iteration << '\n';
                }
                if (cycle % 100 == 99) std::cout << "POOL " << checked << ' ' << encode(current) << " iter " << iteration << '\n';
            }
        }
    }
    if (mode == "anneal") {
        Case data(1);
        int iterations = argc > 3 ? std::stoi(argv[3]) : 1000000;
        int count = argc > 4 ? std::stoi(argv[4]) : 256;
        auto validation = data.generate(16384, .32, 8293634);
        auto training = data.generate(count, .20, generator());
        Pattern current = baseline;
        double score = data.score(current, training);
        double best = .48;
        for (int iteration = 0; iteration < iterations; ++iteration) {
            int cycle = iteration % 4000;
            if (cycle % 1000 == 0) {
                training = data.generate(count, .20 + .04 * (cycle / 1000), generator());
                if (cycle == 0) for (int &axis : current) axis = generator() % 3;
                score = data.score(current, training);
            }
            double temperature = .015 * std::pow(.2, (cycle % 1000) / 999.0);
            Pattern candidate = current;
            int changes = 1 + (uniform() < .2) + (uniform() < .08) * 2;
            for (int change = 0; change < changes; ++change) {
                int cell = generator() % 24;
                candidate[cell] = (candidate[cell] + 1 + generator() % 2) % 3;
            }
            double next = data.score(candidate, training);
            if (next >= score || uniform() < std::exp((next - score) / temperature)) {
                current = candidate;
                score = next;
            }
            if (cycle % 500 == 499) {
                double checked = data.score(current, validation);
                if (checked > best) {
                    best = checked;
                    std::cout << "BEST " << best << ' ' << encode(current) << " iter " << iteration << '\n';
                }
                std::cout << "POOL " << checked << ' ' << encode(current) << " iter " << iteration << '\n';
            }
        }
    }
}
