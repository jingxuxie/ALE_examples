#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <random>
#include <utility>
#include <vector>

using Clock = std::chrono::steady_clock;

struct Row {
    std::vector<std::pair<int, int>> entries;
    std::vector<double> values;
    int bound;
};

struct Problem {
    int length;
    int count;
    int width;
    double step;
    std::vector<int> caps;
    std::vector<int> positive;
    std::vector<Row> rows;
    std::vector<std::vector<std::pair<int, int>>> adjacency;
    std::mt19937 generator;
    Clock::time_point deadline;
    std::vector<int> best;
    double best_score = -1;
    double best_min = 0;

    double random() { return std::generate_canonical<double, 32>(generator); }
    bool expired() { return Clock::now() >= deadline; }
    int dot(const Row &row, const std::vector<int> &ticks) {
        int total = 0;
        for (auto entry : row.entries) total += ticks[entry.first] * entry.second;
        return total;
    }
    void consider(const std::vector<int> &ticks) {
        double minimum = 1e9, total = 0;
        for (const auto &row : rows) {
            double value = row.values[dot(row, ticks) + row.bound];
            minimum = std::min(minimum, value);
            total += value;
        }
        double score = 0.75 * minimum + 0.25 * total / count;
        if (score > best_score + 1e-12) {
            best = ticks;
            best_score = score;
            best_min = minimum;
        }
    }
    double utility(double value, double threshold) {
        return 0.25 * value / count - 0.75 * std::max(0.0, threshold - value);
    }
    void coordinates(std::vector<int> &ticks, double threshold, int sweeps) {
        std::vector<int> dots(count), order(length);
        std::iota(order.begin(), order.end(), 0);
        for (int row_index = 0; row_index < count; ++row_index) dots[row_index] = dot(rows[row_index], ticks);
        for (int sweep = 0; sweep < sweeps && !expired(); ++sweep) {
            std::shuffle(order.begin(), order.end(), generator);
            bool changed = false;
            for (int site : order) {
                if (expired()) return;
                int old = ticks[site], selected = old;
                double highest = -1e100;
                for (int candidate = positive[site] ? 0 : -caps[site]; candidate <= caps[site]; ++candidate) {
                    double score = 0;
                    for (auto entry : adjacency[site]) {
                        const Row &row = rows[entry.first];
                        score += utility(row.values[dots[entry.first] + (candidate - old) * entry.second + row.bound], threshold);
                    }
                    if (score > highest + 1e-13 || (std::abs(score - highest) < 1e-13 && candidate == old)) {
                        highest = score;
                        selected = candidate;
                    }
                }
                if (selected != old) {
                    changed = true;
                    for (auto entry : adjacency[site]) dots[entry.first] += (selected - old) * entry.second;
                    ticks[site] = selected;
                }
            }
            consider(ticks);
            if (!changed) break;
        }
    }

    bool dynamic(std::vector<int> &ticks, double threshold, int alphabet) {
        if (width < 1 || width > 6 || expired()) return false;
        int rotation = generator() % length;
        std::vector<std::vector<int>> domains(length + width, std::vector<int>(alphabet));
        for (int position = 0; position < length; ++position) {
            int site = (position + rotation) % length;
            std::vector<int> choices;
            for (int value = positive[site] ? 0 : -caps[site]; value <= caps[site]; ++value) choices.push_back(value);
            if ((int)choices.size() > alphabet) {
                std::shuffle(choices.begin(), choices.end(), generator);
                choices.erase(std::remove(choices.begin(), choices.end(), ticks[site]), choices.end());
                choices.insert(choices.begin(), ticks[site]);
                choices.resize(alphabet);
                std::sort(choices.begin(), choices.end());
            }
            for (int index = 0; index < alphabet; ++index) domains[position][index] = choices[index % choices.size()];
        }
        for (int position = 0; position < width; ++position) domains[length + position] = domains[position];
        struct Factor { int row; std::vector<std::pair<int, int>> entries; };
        std::vector<std::vector<Factor>> factors(length + width);
        for (int row_index = 0; row_index < count; ++row_index) {
            std::vector<std::pair<int, int>> entries;
            for (auto entry : rows[row_index].entries) entries.emplace_back((entry.first - rotation + length) % length, entry.second);
            if (entries.empty()) continue;
            std::sort(entries.begin(), entries.end());
            int largest = -1, first = 0;
            for (int index = 0; index < (int)entries.size(); ++index) {
                int next = (index + 1) % entries.size();
                int distance = entries[next].first - entries[index].first;
                if (distance <= 0) distance += length;
                if (distance > largest) { largest = distance; first = entries[next].first; }
            }
            int last = first;
            for (auto &entry : entries) {
                if (entry.first < first) entry.first += length;
                last = std::max(last, entry.first);
            }
            if (last < width) continue;
            Factor factor;
            factor.row = row_index;
            for (auto entry : entries) factor.entries.emplace_back(last - entry.first, entry.second);
            factors[last].push_back(std::move(factor));
        }
        int states = 1;
        for (int index = 0; index < width; ++index) states *= alphabet;
        int suffix = states / alphabet;
        int initial = 0;
        std::vector<int> fixed(width);
        for (int position = 0; position < width; ++position) {
            int value = ticks[(rotation + position) % length];
            fixed[position] = std::find(domains[position].begin(), domains[position].end(), value) - domains[position].begin();
            initial = initial * alphabet + fixed[position];
        }
        std::vector<double> current(states, -1e100), next(states);
        std::vector<uint16_t> predecessor((size_t)length * states);
        current[initial] = 0;
        std::vector<std::vector<double>> utilities(count);
        for (int row_index = 0; row_index < count; ++row_index) {
            for (double value : rows[row_index].values) utilities[row_index].push_back(utility(value, threshold));
        }
        std::vector<int> partial;
        for (int position = width; position < length + width; ++position) {
            if (expired()) return false;
            std::fill(next.begin(), next.end(), -1e100);
            int first_choice = position >= length ? fixed[position - length] : 0;
            int last_choice = position >= length ? first_choice + 1 : alphabet;
            const auto &local = factors[position];
            partial.resize(local.size());
            for (int state = 0; state < states; ++state) {
                if ((state & 255) == 0 && expired()) return false;
                if (current[state] < -1e90) continue;
                int previous[7] = {0, 0, 0, 0, 0, 0, 0};
                int encoded = state;
                for (int offset = 1; offset <= width; ++offset) {
                    previous[offset] = domains[position - offset][encoded % alphabet];
                    encoded /= alphabet;
                }
                for (int factor_index = 0; factor_index < (int)local.size(); ++factor_index) {
                    int total = rows[local[factor_index].row].bound;
                    for (auto entry : local[factor_index].entries) if (entry.first) total += previous[entry.first] * entry.second;
                    partial[factor_index] = total;
                }
                int base = (state % suffix) * alphabet;
                for (int choice = first_choice; choice < last_choice; ++choice) {
                    double score = current[state];
                    int value = domains[position][choice];
                    for (int factor_index = 0; factor_index < (int)local.size(); ++factor_index) {
                        const auto &factor = local[factor_index];
                        int total = partial[factor_index];
                        for (auto entry : factor.entries) if (!entry.first) total += value * entry.second;
                        score += utilities[factor.row][total];
                    }
                    int next_state = base + choice;
                    if (score > next[next_state]) {
                        next[next_state] = score;
                        predecessor[(size_t)(position - width) * states + next_state] = state / suffix;
                    }
                }
            }
            current.swap(next);
        }
        int state = std::max_element(current.begin(), current.end()) - current.begin();
        for (int position = length + width - 1; position >= width; --position) {
            if (position < length) ticks[(position + rotation) % length] = domains[position][state % alphabet];
            int dropped = predecessor[(size_t)(position - width) * states + state];
            state = dropped * suffix + state / alphabet;
        }
        consider(ticks);
        return true;
    }

    void run(const int *initial) {
        std::vector<int> ticks(length);
        for (int site = 0; site < length; ++site) ticks[site] = initial[site];
        consider(ticks);
        int iteration = 0;
        int maximum_domain = 0;
        for (int site = 0; site < length; ++site) maximum_domain = std::max(maximum_domain, caps[site] * (positive[site] ? 1 : 2) + 1);
        while (!expired()) {
            if (iteration % 5 == 0 && iteration > 0) {
                int period = 2 + generator() % 7;
                std::vector<double> pattern(period);
                for (double &value : pattern) value = random();
                for (int site = 0; site < length; ++site) {
                    double value = pattern[site % period];
                    ticks[site] = positive[site] ? std::lround(value * caps[site]) : std::lround((2 * value - 1) * caps[site]);
                }
            } else if (iteration % 3 == 0) {
                ticks = best;
                for (int changed = 0; changed < std::max(1, length / 12); ++changed) {
                    int site = generator() % length;
                    int lower = positive[site] ? 0 : -caps[site];
                    ticks[site] = lower + generator() % (caps[site] - lower + 1);
                }
            }
            double threshold;
            if (iteration % 7 == 6) threshold = std::max(0.0, best_min - step * (0.1 + random()));
            else threshold = best_min + step * (0.1 + 1.6 * random());
            if (iteration < 4) threshold = std::max(threshold, 0.12 * (iteration + 1));
            bool polishing = iteration % 13 == 12;
            if (polishing) {
                ticks = best;
                threshold = best_min;
            }
            coordinates(ticks, threshold, 5);
            if (width <= 6 && width > 0) {
                int limit = width <= 2 ? 35 : (iteration % 4 == 0 ? 15 : 10);
                if (width >= 4) limit = width == 4 ? 8 : (width == 5 ? 5 : 4);
                if (polishing && width == 3) limit = 35;
                int alphabet = std::min(maximum_domain, limit);
                dynamic(ticks, threshold, alphabet);
                if (iteration % 2 == 0 && !polishing) dynamic(ticks, threshold, alphabet);
                coordinates(ticks, threshold, 3);
            } else {
                for (int move = 0; move < length / 2; ++move) {
                    int site = generator() % length;
                    int lower = positive[site] ? 0 : -caps[site];
                    ticks[site] = lower + generator() % (caps[site] - lower + 1);
                }
            }
            ++iteration;
        }
    }
};

extern "C" double optimize_schedule(int length, int count, const int *matrix, const int *caps,
                                    const int *positive, const double *uncertainty,
                                    int denominator, int bandwidth, int phase, int phase_denominator,
                                    double seconds, unsigned seed, int *ticks) {
    Problem problem;
    problem.length = length;
    problem.count = count;
    problem.caps.assign(caps, caps + length);
    problem.positive.assign(positive, positive + length);
    problem.adjacency.resize(length);
    problem.generator.seed(seed);
    problem.deadline = Clock::now() + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
    problem.width = 0;
    int coefficient_gcd = 0;
    for (int row_index = 0; row_index < count; ++row_index) {
        Row row;
        row.bound = 0;
        double error = 0;
        for (int site = 0; site < length; ++site) {
            int coefficient = matrix[row_index * length + site];
            if (!coefficient) continue;
            row.entries.emplace_back(site, coefficient);
            row.bound += std::abs(coefficient) * caps[site];
            error += std::abs(coefficient) * uncertainty[site];
            coefficient_gcd = std::gcd(coefficient_gcd, std::abs(coefficient));
            problem.adjacency[site].emplace_back(row_index, coefficient);
        }
        int largest = length;
        if (row.entries.size() > 1) {
            largest = 0;
            for (int index = 0; index < (int)row.entries.size(); ++index) {
                int next = (index + 1) % row.entries.size();
                int distance = (row.entries[next].first - row.entries[index].first + length) % length;
                largest = std::max(largest, distance);
            }
        }
        problem.width = std::max(problem.width, length - largest);
        for (int gap = -row.bound; gap <= row.bound; ++gap) {
            double value;
            if (phase == 0) value = (std::abs((double)gap / denominator) - error) / bandwidth;
            else {
                double angle = (double)phase * gap / (phase_denominator * denominator);
                value = std::abs(angle - 2 * std::round(angle / 2)) - (double)std::abs(phase) / phase_denominator * error;
            }
            row.values.push_back(std::max(0.0, value));
        }
        problem.rows.push_back(std::move(row));
    }
    if (!phase) problem.step = (double)std::max(1, coefficient_gcd) / (denominator * bandwidth);
    else problem.step = std::max(0.018, (double)std::gcd(phase * coefficient_gcd, 2 * phase_denominator * denominator) / (phase_denominator * denominator));
    problem.run(ticks);
    std::copy(problem.best.begin(), problem.best.end(), ticks);
    return problem.best_score;
}
