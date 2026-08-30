#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

using Pattern = std::array<int, 24>;
using Vector = std::array<uint64_t, 7>;

struct Sample {
    int family;
    std::vector<int> support;
};

struct Case {
    int words;
    std::vector<int> cells;
    std::vector<std::array<Vector, 3>> columns;
    std::vector<Sample> samples;
};

uint32_t read_integer(std::ifstream &stream) {
    uint32_t value;
    stream.read(reinterpret_cast<char *>(&value), sizeof(value));
    return value;
}

std::vector<Case> read_cases(const std::string &path) {
    std::ifstream stream(path, std::ios::binary);
    if (!stream) throw std::runtime_error("Cannot read " + path);
    std::vector<Case> cases(read_integer(stream));
    for (auto &item : cases) {
        int slots = read_integer(stream);
        item.words = read_integer(stream);
        item.cells.resize(slots);
        item.columns.resize(slots);
        for (int slot = 0; slot < slots; ++slot) {
            item.cells[slot] = read_integer(stream);
            for (auto &column : item.columns[slot]) {
                column.fill(0);
                stream.read(reinterpret_cast<char *>(column.data()), item.words * 8);
            }
        }
        item.samples.resize(read_integer(stream));
        for (auto &sample : item.samples) {
            sample.family = read_integer(stream);
            sample.support.resize(read_integer(stream));
            for (auto &slot : sample.support) slot = read_integer(stream);
        }
    }
    if (!stream) throw std::runtime_error("Truncated dataset");
    return cases;
}

bool correctable(const std::vector<Vector> &columns, const Sample &sample, int words) {
    std::array<Vector, 448> pivots;
    std::array<bool, 448> occupied{};
    for (int slot : sample.support) {
        Vector column = columns[slot];
        int word = words - 1;
        while (true) {
            while (word >= 0 && column[word] == 0) --word;
            if (word < 0) break;
            int pivot = word * 64 + 63 - __builtin_clzll(column[word]);
            if (pivot < 4) return false;
            if (!occupied[pivot]) {
                occupied[pivot] = true;
                pivots[pivot] = column;
                break;
            }
            const auto &previous = pivots[pivot];
            for (int index = 0; index <= word; ++index) column[index] ^= previous[index];
        }
    }
    return true;
}

struct Score {
    std::array<double, 9> fractions;
    double mean;
    double worst;
    double objective;
};

Score evaluate(const std::vector<Case> &cases, const Pattern &pattern) {
    Score result{};
    int group_offset = 0;
    for (const auto &item : cases) {
        std::vector<Vector> columns(item.columns.size());
        for (size_t slot = 0; slot < columns.size(); ++slot) columns[slot] = item.columns[slot][pattern[item.cells[slot]]];
        std::array<int, 3> totals{};
        std::array<int, 3> successes{};
        for (const auto &sample : item.samples) {
            ++totals[sample.family];
            successes[sample.family] += correctable(columns, sample, item.words);
        }
        for (int family = 0; family < 3; ++family) result.fractions[group_offset + family] = double(successes[family]) / totals[family];
        group_offset += 3;
    }
    result.worst = 1;
    result.objective = 0;
    for (double fraction : result.fractions) {
        result.mean += fraction / 9;
        result.worst = std::min(result.worst, fraction);
        result.objective += std::log(std::max(0.05, fraction)) / 9;
        result.objective -= std::max(0.0, 0.70 - fraction) * 0.15;
    }
    return result;
}

std::string pattern_text(const Pattern &pattern) {
    std::string result;
    for (int axis : pattern) result += char('0' + axis);
    return result;
}

Pattern parse_pattern(const std::string &text) {
    if (text.size() != 24) throw std::runtime_error("Pattern must have 24 digits");
    Pattern pattern;
    for (int cell = 0; cell < 24; ++cell) {
        pattern[cell] = text[cell] - '0';
        if (pattern[cell] < 0 || pattern[cell] > 2) throw std::runtime_error("Invalid pattern");
    }
    return pattern;
}

void print_score(const Pattern &pattern, const Score &score, const std::string &label) {
    std::cout << label << " " << pattern_text(pattern) << std::fixed << std::setprecision(6)
              << " " << score.objective << " " << score.mean << " " << score.worst;
    for (double fraction : score.fractions) std::cout << " " << fraction;
    std::cout << std::endl;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        std::cerr << "Usage: optimize dataset score pattern... | search seconds seed [pattern]\n";
        return 1;
    }
    auto cases = read_cases(argv[1]);
    if (std::string(argv[2]) == "scan") {
        std::ifstream patterns(argv[3]);
        std::string text;
        while (patterns >> text) {
            Pattern pattern = parse_pattern(text);
            print_score(pattern, evaluate(cases, pattern), "SCORE");
        }
        return 0;
    }
    if (std::string(argv[2]) == "score") {
        for (int argument = 3; argument < argc; ++argument) {
            Pattern pattern = parse_pattern(argv[argument]);
            print_score(pattern, evaluate(cases, pattern), "SCORE");
        }
        return 0;
    }
    double seconds = std::stod(argv[3]);
    std::mt19937_64 generator(std::stoull(argv[4]));
    std::uniform_real_distribution<double> uniform(0, 1);
    Pattern best_pattern{};
    Score best_score{};
    best_score.objective = -1e9;
    auto start = std::chrono::steady_clock::now();
    int evaluations = 0;
    int restart = 0;
    while (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds) {
        Pattern current;
        if (restart == 0 && argc >= 6) current = parse_pattern(argv[5]);
        else if (restart > 0 && restart % 3 != 0) {
            current = best_pattern;
            int mutations = 3 + generator() % 8;
            for (int mutation = 0; mutation < mutations; ++mutation) current[generator() % 24] = generator() % 3;
        } else for (int &axis : current) axis = generator() % 3;
        Score current_score = evaluate(cases, current);
        ++evaluations;
        if (current_score.objective > best_score.objective) {
            best_pattern = current;
            best_score = current_score;
            print_score(best_pattern, best_score, "BEST " + std::to_string(evaluations));
        }
        for (int iteration = 0; iteration < 600; ++iteration) {
            double temperature = 0.018 * std::pow(0.04, double(iteration) / 600);
            Pattern candidate = current;
            int changes = uniform(generator) < 0.15 ? 2 + generator() % 3 : 1;
            for (int change = 0; change < changes; ++change) {
                int cell = generator() % 24;
                candidate[cell] = (candidate[cell] + 1 + generator() % 2) % 3;
            }
            Score candidate_score = evaluate(cases, candidate);
            ++evaluations;
            if (candidate_score.objective > current_score.objective || uniform(generator) < std::exp((candidate_score.objective - current_score.objective) / temperature)) {
                current = candidate;
                current_score = candidate_score;
            }
            if (candidate_score.objective > best_score.objective) {
                best_pattern = candidate;
                best_score = candidate_score;
                print_score(best_pattern, best_score, "BEST " + std::to_string(evaluations));
            }
            if (iteration % 16 == 0 && std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() >= seconds) break;
        }
        ++restart;
    }
    print_score(best_pattern, best_score, "FINAL " + std::to_string(evaluations));
}
