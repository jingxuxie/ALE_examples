#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <limits>
#include <numeric>
#include <vector>

using Byte = uint8_t;
using Word = uint64_t;
using State = std::vector<Byte>;

static double logadd(double first, double second) {
    return std::max(first, second) + std::log1p(std::exp(-std::abs(first - second)));
}

struct Edge {
    int variable;
    int sector;
};

struct Belief {
    State hard;
    std::vector<std::array<double, 4>> cost;
    bool converged = false;
    int unsatisfied = 0;
    int iterations = 0;
};

struct Decoder {
    int size, rows, words;
    std::vector<Edge> edges;
    std::vector<int> starts;
    std::vector<std::vector<int>> variable_edges;
    std::vector<std::array<double, 4>> channel;
    std::vector<std::array<int, 2>> axes;
    std::vector<std::vector<int>> columns;

    Decoder(int length, int rx, int rz, const Byte* hx, const Byte* hz,
            const double* probabilities): size(length), rows(rx + rz),
            words((2 * length + 63) / 64), variable_edges(length),
            channel(length), axes(length), columns(2 * length) {
        for (int variable = 0; variable < size; ++variable) {
            for (int state = 0; state < 4; ++state)
                channel[variable][state] = std::log(probabilities[4 * variable] /
                                                   probabilities[4 * variable + state]);
            std::array<int, 3> order{1, 2, 3};
            std::stable_sort(order.begin(), order.end(), [&](int first, int second) {
                return channel[variable][first] < channel[variable][second];
            });
            axes[variable] = {order[0], order[1]};
        }
        for (int row = 0; row < rows; ++row) {
            starts.push_back(edges.size());
            int sector = row < rx ? 1 : 0;
            const Byte* matrix_row = row < rx ? hx + row * size : hz + (row - rx) * size;
            for (int variable = 0; variable < size; ++variable) {
                if (!matrix_row[variable]) continue;
                variable_edges[variable].push_back(edges.size());
                edges.push_back({variable, sector});
                for (int component = 0; component < 2; ++component)
                    if ((axes[variable][component] >> sector) & 1)
                        columns[2 * variable + component].push_back(row);
            }
        }
        starts.push_back(edges.size());
    }

    double score(const State& state) const {
        double total = 0;
        for (int variable = 0; variable < size; ++variable)
            total += channel[variable][state[variable]];
        return total;
    }

    void stabilize(State& state) const {
        for (int iteration = 0; iteration < 4; ++iteration) {
            bool improved = false;
            for (int row = 0; row < rows; ++row) {
                if (starts[row] == starts[row + 1]) continue;
                int axis = 1 << (1 - edges[starts[row]].sector);
                double delta = 0;
                for (int edge = starts[row]; edge < starts[row + 1]; ++edge) {
                    int variable = edges[edge].variable;
                    delta += channel[variable][state[variable] ^ axis] - channel[variable][state[variable]];
                }
                if (delta >= -1e-9) continue;
                for (int edge = starts[row]; edge < starts[row + 1]; ++edge)
                    state[edges[edge].variable] ^= axis;
                improved = true;
            }
            if (!improved) break;
        }
    }

    int mismatch(const State& state, const Byte* syndrome) const {
        int count = 0;
        for (int row = 0; row < rows; ++row) {
            int parity = syndrome[row];
            for (int edge = starts[row]; edge < starts[row + 1]; ++edge)
                parity ^= (state[edges[edge].variable] >> edges[edge].sector) & 1;
            count += parity;
        }
        return count;
    }

    Belief bp(const Byte* syndrome, int iterations, double scale, double damping,
              bool sum_product, double memory = 1.0,
              const std::vector<std::array<double, 4>>* alternate = nullptr,
              bool max_log = false) const {
        auto combine = [max_log](double first, double second) {
            return max_log ? std::max(first, second) : logadd(first, second);
        };
        const auto& prior = alternate ? *alternate : channel;
        std::vector<double> outgoing(edges.size()), incoming(edges.size(), 0.0);
        Belief belief;
        belief.hard.resize(size);
        belief.cost = prior;
        std::vector<std::array<double, 4>> average = prior;
        for (size_t edge = 0; edge < edges.size(); ++edge) {
            const auto& costs = prior[edges[edge].variable];
            int axis = 1 << edges[edge].sector;
            int other = 3 ^ axis;
            outgoing[edge] = combine(-costs[0], -costs[other]) -
                             combine(-costs[axis], -costs[3]);
        }
        std::vector<double> temporary(64), prefix(65);
        for (int iteration = 0; iteration < iterations; ++iteration) {
            for (int row = 0; row < rows; ++row) {
                int begin = starts[row], end = starts[row + 1];
                if (sum_product) {
                    if (int(temporary.size()) < end - begin) {
                        temporary.resize(end - begin);
                        prefix.resize(end - begin + 1);
                    }
                    prefix[0] = syndrome[row] ? -1.0 : 1.0;
                    for (int edge = begin; edge < end; ++edge) {
                        temporary[edge - begin] = std::tanh(outgoing[edge] * 0.5);
                        prefix[edge - begin + 1] = prefix[edge - begin] * temporary[edge - begin];
                    }
                    double suffix = 1.0;
                    for (int edge = end - 1; edge >= begin; --edge) {
                        double product = std::clamp(prefix[edge - begin] * suffix, -0.999999999999, 0.999999999999);
                        double message = scale * (std::log1p(product) - std::log1p(-product));
                        incoming[edge] = damping * incoming[edge] + (1.0 - damping) * message;
                        suffix *= temporary[edge - begin];
                    }
                } else {
                    double minimum = 40.0, second = 40.0;
                    int sign = syndrome[row];
                    for (int edge = begin; edge < end; ++edge) {
                        double magnitude = std::abs(outgoing[edge]);
                        if (magnitude < minimum) {
                            second = minimum;
                            minimum = magnitude;
                        } else if (magnitude < second) second = magnitude;
                        sign ^= outgoing[edge] < 0;
                    }
                    for (int edge = begin; edge < end; ++edge) {
                        double message = scale * (std::abs(outgoing[edge]) == minimum ? second : minimum);
                        if (sign ^ (outgoing[edge] < 0)) message = -message;
                        incoming[edge] = damping * incoming[edge] + (1.0 - damping) * message;
                    }
                }
            }
            for (int variable = 0; variable < size; ++variable) {
                std::array<double, 2> sums{0, 0};
                for (int edge : variable_edges[variable]) sums[edges[edge].sector] += incoming[edge];
                auto& costs = belief.cost[variable];
                costs[0] = 0;
                costs[1] = prior[variable][1] + memory * sums[0];
                costs[2] = prior[variable][2] + memory * sums[1];
                costs[3] = prior[variable][3] + memory * (sums[0] + sums[1]);
                belief.hard[variable] = std::min_element(costs.begin(), costs.end()) - costs.begin();
                double llr_x = combine(-costs[0], -costs[2]) - combine(-costs[1], -costs[3]);
                double llr_z = combine(-costs[0], -costs[1]) - combine(-costs[2], -costs[3]);
                for (int edge : variable_edges[variable]) {
                    double marginal = edges[edge].sector ? llr_z : llr_x;
                    outgoing[edge] = std::clamp(marginal - incoming[edge], -40.0, 40.0);
                }
                for (int state = 1; state < 4; ++state)
                    average[variable][state] = 0.8 * average[variable][state] + 0.2 * costs[state];
            }
            belief.iterations = iteration + 1;
            belief.unsatisfied = mismatch(belief.hard, syndrome);
            if (belief.unsatisfied == 0) {
                belief.converged = true;
                return belief;
            }
        }
        belief.cost = average;
        for (int variable = 0; variable < size; ++variable)
            belief.hard[variable] = std::min_element(average[variable].begin(), average[variable].end()) - average[variable].begin();
        return belief;
    }

    Belief layered(const Byte* syndrome, int iterations, double scale, bool sum_product,
                   double memory = 1.0, bool reverse = false) const {
        std::vector<double> incoming(edges.size(), 0.0);
        std::vector<std::array<double, 2>> sums(size, {0.0, 0.0});
        Belief belief;
        belief.hard.resize(size);
        belief.cost = channel;
        std::vector<std::array<double, 4>> average = channel;
        std::vector<double> outgoing(64), temporary(64), prefix(65);
        for (int iteration = 0; iteration < iterations; ++iteration) {
            for (int row_index = 0; row_index < rows; ++row_index) {
                int row = reverse ? rows - 1 - row_index : row_index;
                int begin = starts[row], end = starts[row + 1];
                int degree = end - begin;
                if (int(outgoing.size()) < degree) {
                    outgoing.resize(degree);
                    temporary.resize(degree);
                    prefix.resize(degree + 1);
                }
                double minimum = 40.0, second = 40.0;
                int sign = syndrome[row];
                prefix[0] = sign ? -1.0 : 1.0;
                for (int edge = begin; edge < end; ++edge) {
                    int variable = edges[edge].variable, sector = edges[edge].sector;
                    int axis = 1 << sector, other = 3 ^ axis;
                    const auto& costs = channel[variable];
                    double other_sum = memory * sums[variable][1 - sector];
                    double message = memory * sums[variable][sector] - incoming[edge] +
                                     logadd(0, -costs[other] - other_sum) -
                                     logadd(-costs[axis], -costs[3] - other_sum);
                    message = std::clamp(message, -40.0, 40.0);
                    outgoing[edge - begin] = message;
                    if (sum_product) {
                        temporary[edge - begin] = std::tanh(message * 0.5);
                        prefix[edge - begin + 1] = prefix[edge - begin] * temporary[edge - begin];
                    } else {
                        double magnitude = std::abs(message);
                        if (magnitude < minimum) {
                            second = minimum;
                            minimum = magnitude;
                        } else if (magnitude < second) second = magnitude;
                        sign ^= message < 0;
                    }
                }
                double suffix = 1.0;
                for (int edge = end - 1; edge >= begin; --edge) {
                    double message;
                    if (sum_product) {
                        double product = std::clamp(prefix[edge - begin] * suffix, -0.999999999999, 0.999999999999);
                        message = scale * (std::log1p(product) - std::log1p(-product));
                        suffix *= temporary[edge - begin];
                    } else {
                        message = scale * (std::abs(outgoing[edge - begin]) == minimum ? second : minimum);
                        if (sign ^ (outgoing[edge - begin] < 0)) message = -message;
                    }
                    int variable = edges[edge].variable, sector = edges[edge].sector;
                    sums[variable][sector] += message - incoming[edge];
                    incoming[edge] = message;
                }
            }
            for (int variable = 0; variable < size; ++variable) {
                auto& costs = belief.cost[variable];
                costs[1] = channel[variable][1] + memory * sums[variable][0];
                costs[2] = channel[variable][2] + memory * sums[variable][1];
                costs[3] = channel[variable][3] + memory * (sums[variable][0] + sums[variable][1]);
                belief.hard[variable] = std::min_element(costs.begin(), costs.end()) - costs.begin();
                for (int state = 1; state < 4; ++state)
                    average[variable][state] = 0.8 * average[variable][state] + 0.2 * costs[state];
            }
            belief.iterations = iteration + 1;
            belief.unsatisfied = mismatch(belief.hard, syndrome);
            if (belief.unsatisfied == 0) {
                belief.converged = true;
                return belief;
            }
        }
        belief.cost = average;
        for (int variable = 0; variable < size; ++variable)
            belief.hard[variable] = std::min_element(average[variable].begin(), average[variable].end()) - average[variable].begin();
        return belief;
    }

    Belief run(const Byte* syndrome, int mode) const {
        if (mode == 14 || mode == 16 || mode == 18) {
            auto perturbed = channel;
            uint64_t random = 0x7d3927eb96f34a21ULL + mode;
            for (int row = 0; row < rows; ++row) random = (random ^ syndrome[row]) * 0x100000001b3ULL;
            double strength = mode == 18 ? 0.9 : 0.45;
            for (int variable = 0; variable < size; ++variable) {
                random ^= random << 13;
                random ^= random >> 7;
                random ^= random << 17;
                double factor = std::exp(strength * (double(random >> 11) * 0x1.0p-53 - 0.5));
                for (int state = 1; state < 4; ++state) perturbed[variable][state] *= factor;
            }
            return bp(syndrome, 100, mode == 16 ? 1.0 : 0.8, 0.3, mode == 16, 1.0, &perturbed);
        }
        if (mode == 15) return bp(syndrome, 100, 0.8, 0.5, false, 1.0, nullptr, true);
        if (mode == 17) return layered(syndrome, 80, 1.0, true, 1.0, true);
        if (mode == 19) return bp(syndrome, 100, 0.6, 0.3, false, 1.0, nullptr, true);
        if (mode == 4) return bp(syndrome, 100, 1.0, 0.0, false, 0.8);
        if (mode == 5) return bp(syndrome, 100, 1.0, 0.0, true, 0.8);
        if (mode == 6) return bp(syndrome, 100, 0.7, 0.3, false);
        if (mode == 7) return bp(syndrome, 100, 1.0, 0.5, false);
        if (mode == 8) return layered(syndrome, 80, 0.8, false);
        if (mode == 9) return layered(syndrome, 80, 1.0, true);
        if (mode == 10) return layered(syndrome, 80, 1.0, false, 0.8);
        if (mode == 11) return layered(syndrome, 80, 1.0, true, 0.8);
        if (mode == 12) return bp(syndrome, 200, 0.8, 0.3, false);
        if (mode == 13) return bp(syndrome, 0, 1.0, 0.0, false);
        bool sum_product = mode == 1 || mode == 3;
        double scale = sum_product ? 1.0 : 0.8;
        double damping = mode == 2 || mode == 3 ? 0.3 : 0.0;
        return bp(syndrome, 80, scale, damping, sum_product);
    }

    std::vector<std::array<int, 2>> guesses(const Belief& belief) const {
        std::vector<std::array<int, 4>> hypotheses(size);
        std::vector<int> variables(size);
        std::iota(variables.begin(), variables.end(), 0);
        for (int variable = 0; variable < size; ++variable) {
            hypotheses[variable] = {0, 1, 2, 3};
            std::stable_sort(hypotheses[variable].begin(), hypotheses[variable].end(), [&](int first, int second) {
                return belief.cost[variable][first] < belief.cost[variable][second];
            });
        }
        std::stable_sort(variables.begin(), variables.end(), [&](int first, int second) {
            return belief.cost[first][hypotheses[first][1]] - belief.cost[first][hypotheses[first][0]] <
                   belief.cost[second][hypotheses[second][1]] - belief.cost[second][hypotheses[second][0]];
        });
        std::vector<std::array<int, 2>> selected;
        for (int index = 0; index < std::min(6, size); ++index) {
            int variable = variables[index];
            selected.push_back({variable, hypotheses[variable][0]});
            selected.push_back({variable, hypotheses[variable][1]});
        }
        return selected;
    }

    Belief guided(const Byte* syndrome, int variable, int hypothesis) const {
        auto prior = channel;
        for (int state = 0; state < 4; ++state)
            prior[variable][state] += state == hypothesis ? 0.0 : 12.0;
        double offset = prior[variable][0];
        for (int state = 0; state < 4; ++state) prior[variable][state] -= offset;
        return bp(syndrome, 80, 0.8, 0.3, false, 1.0, &prior);
    }

    State osd(const Byte* syndrome, const Belief& belief, int order, bool enhanced = false) const {
        int bits = 2 * size;
        std::vector<double> reliability(bits);
        std::vector<Byte> hard(bits);
        std::vector<int> sorted(bits);
        std::iota(sorted.begin(), sorted.end(), 0);
        for (int variable = 0; variable < size; ++variable) {
            int first = axes[variable][0], second = axes[variable][1];
            const auto& costs = belief.cost[variable];
            reliability[2 * variable] = std::abs(logadd(-costs[0], -costs[second]) -
                                                logadd(-costs[first], -costs[first ^ second]));
            reliability[2 * variable + 1] = std::abs(logadd(-costs[0], -costs[first]) -
                                                    logadd(-costs[second], -costs[first ^ second]));
            hard[2 * variable] = belief.hard[variable] == first || belief.hard[variable] == (first ^ second);
            hard[2 * variable + 1] = belief.hard[variable] == second || belief.hard[variable] == (first ^ second);
        }
        std::stable_sort(sorted.begin(), sorted.end(), [&](int first, int second) {
            return reliability[first] < reliability[second];
        });
        std::vector<Word> matrix(rows * words, 0);
        std::vector<Byte> target(syndrome, syndrome + rows);
        for (int column = 0; column < bits; ++column) {
            int original = sorted[column];
            for (int row : columns[original]) {
                matrix[row * words + column / 64] |= Word(1) << (column % 64);
                target[row] ^= hard[original];
            }
        }
        int rank = 0;
        std::vector<int> pivots, free_columns;
        for (int column = 0; column < bits; ++column) {
            int selected = rank;
            Word mask = Word(1) << (column % 64);
            while (selected < rows && !(matrix[selected * words + column / 64] & mask)) ++selected;
            if (selected == rows) {
                free_columns.push_back(column);
                continue;
            }
            if (selected != rank) {
                for (int word = column / 64; word < words; ++word)
                    std::swap(matrix[selected * words + word], matrix[rank * words + word]);
                std::swap(target[selected], target[rank]);
            }
            for (int row = 0; row < rows; ++row) {
                if (row == rank || !(matrix[row * words + column / 64] & mask)) continue;
                for (int word = column / 64; word < words; ++word)
                    matrix[row * words + word] ^= matrix[rank * words + word];
                target[row] ^= target[rank];
            }
            pivots.push_back(column);
            ++rank;
        }
        State base = belief.hard;
        for (int row = 0; row < rank; ++row) {
            int original = sorted[pivots[row]];
            if (target[row]) base[original / 2] ^= axes[original / 2][original % 2];
        }
        if (order == 0) return base;
        struct Change {
            int variable;
            Byte axis;
        };
        std::vector<std::vector<Change>> changes(free_columns.size());
        std::vector<double> deltas(free_columns.size());
        double base_score = score(base), best_score = base_score;
        int best_first = -1, best_second = -1;
        for (size_t free_index = 0; free_index < free_columns.size(); ++free_index) {
            int column = free_columns[free_index];
            int original = sorted[column];
            State difference(size, 0);
            difference[original / 2] ^= axes[original / 2][original % 2];
            for (int row = 0; row < rank; ++row) {
                if ((matrix[row * words + column / 64] >> (column % 64)) & 1) {
                    int pivot = sorted[pivots[row]];
                    difference[pivot / 2] ^= axes[pivot / 2][pivot % 2];
                }
            }
            double delta = 0;
            for (int variable = 0; variable < size; ++variable) {
                if (!difference[variable]) continue;
                changes[free_index].push_back({variable, difference[variable]});
                delta += channel[variable][base[variable] ^ difference[variable]] - channel[variable][base[variable]];
            }
            deltas[free_index] = delta;
            if (base_score + delta < best_score) {
                best_score = base_score + delta;
                best_first = free_index;
            }
        }
        if (enhanced) {
            int exhaustive = std::min(12, int(free_columns.size()));
            State modified = base, optimum = base;
            double modified_score = base_score;
            for (int pattern = 1; pattern < (1 << exhaustive); ++pattern) {
                int changed = __builtin_ctz(unsigned(pattern));
                for (const auto& change : changes[changed]) {
                    int variable = change.variable;
                    modified_score += channel[variable][modified[variable] ^ change.axis] -
                                      channel[variable][modified[variable]];
                    modified[variable] ^= change.axis;
                }
                if (modified_score < best_score - 1e-9) {
                    best_score = modified_score;
                    optimum = modified;
                }
            }
            if (best_first >= 0 && score(optimum) > base_score + deltas[best_first]) {
                optimum = base;
                for (const auto& change : changes[best_first]) optimum[change.variable] ^= change.axis;
            }
            for (int round = 0; round < 3; ++round) {
                base_score = score(base);
                best_first = -1;
                best_second = -1;
                for (size_t free_index = 0; free_index < changes.size(); ++free_index) {
                    double delta = 0;
                    for (const auto& change : changes[free_index]) {
                        int variable = change.variable;
                        delta += channel[variable][base[variable] ^ change.axis] - channel[variable][base[variable]];
                    }
                    deltas[free_index] = delta;
                    if (base_score + delta < best_score - 1e-9) {
                        best_score = base_score + delta;
                        best_first = free_index;
                    }
                }
                std::vector<int> selected;
                int cutoff = std::min(order / 2, int(changes.size()));
                for (int free_index = 0; free_index < cutoff; ++free_index) selected.push_back(free_index);
                std::vector<int> by_cost(changes.size());
                std::iota(by_cost.begin(), by_cost.end(), 0);
                std::stable_sort(by_cost.begin(), by_cost.end(), [&](int first, int second) {
                    return deltas[first] < deltas[second];
                });
                for (int free_index : by_cost) {
                    if (free_index < cutoff) continue;
                    selected.push_back(free_index);
                    if (int(selected.size()) >= order) break;
                }
                for (size_t first_index = 0; first_index < selected.size(); ++first_index) {
                    int first = selected[first_index];
                    modified = base;
                    for (const auto& change : changes[first]) modified[change.variable] ^= change.axis;
                    for (size_t second_index = first_index + 1; second_index < selected.size(); ++second_index) {
                        int second = selected[second_index];
                        double candidate_score = base_score + deltas[first];
                        for (const auto& change : changes[second]) {
                            int variable = change.variable;
                            candidate_score += channel[variable][modified[variable] ^ change.axis] - channel[variable][modified[variable]];
                        }
                        if (candidate_score < best_score - 1e-9) {
                            best_score = candidate_score;
                            best_first = first;
                            best_second = second;
                        }
                    }
                }
                if (best_first >= 0) {
                    for (const auto& change : changes[best_first]) base[change.variable] ^= change.axis;
                    if (best_second >= 0)
                        for (const auto& change : changes[best_second]) base[change.variable] ^= change.axis;
                    optimum = base;
                } else if (round == 0 && score(optimum) < base_score - 1e-9) {
                    base = optimum;
                } else break;
            }
            return optimum;
        }
        int searched = std::min(order, int(free_columns.size()));
        for (int first = 0; first < searched; ++first) {
            State modified = base;
            for (const auto& change : changes[first]) modified[change.variable] ^= change.axis;
            for (int second = first + 1; second < searched; ++second) {
                double candidate_score = base_score + deltas[first];
                for (const auto& change : changes[second]) {
                    int variable = change.variable;
                    candidate_score += channel[variable][modified[variable] ^ change.axis] -
                                       channel[variable][modified[variable]];
                }
                if (candidate_score < best_score) {
                    best_score = candidate_score;
                    best_first = first;
                    best_second = second;
                }
            }
        }
        if (best_first >= 0)
            for (const auto& change : changes[best_first]) base[change.variable] ^= change.axis;
        if (best_second >= 0)
            for (const auto& change : changes[best_second]) base[change.variable] ^= change.axis;
        return base;
    }
};

extern "C" int decode_batch(int size, int rx, int rz, int shots,
                             const Byte* hx, const Byte* hz, const double* probabilities,
                             const Byte* syndromes, Byte* output, double* statistics, int mode) {
    try {
        std::clock_t start = std::clock();
        Decoder decoder(size, rx, rz, hx, hz, probabilities);
        for (int shot = 0; shot < shots; ++shot) {
            const Byte* syndrome = syndromes + shot * (rx + rz);
            if (mode >= 100) {
                std::clock_t shot_start = std::clock();
                double remaining = 48.0 - double(shot_start - start) / CLOCKS_PER_SEC;
                double allowance = std::max(0.0, remaining / (shots - shot));
                std::array<int, 12> methods{2, 3, 9, 14, 15, 17, 6, 18, 16, 8, 12, 19};
                State best;
                double best_score = std::numeric_limits<double>::infinity();
                std::vector<State> converged;
                bool zero_syndrome = std::all_of(syndrome, syndrome + rx + rz, [](Byte value) { return value == 0; });
                if (zero_syndrome) {
                    std::fill(output + shot * size, output + (shot + 1) * size, Byte(0));
                    continue;
                }
                int pass = 0;
                std::vector<std::array<int, 2>> guesses;
                for (size_t pass_index = 0; pass_index < methods.size() + guesses.size(); ++pass_index) {
                    if (pass && double(std::clock() - shot_start) / CLOCKS_PER_SEC >= allowance) break;
                    Belief belief;
                    if (pass_index < methods.size()) {
                        belief = decoder.run(syndrome, methods[pass_index]);
                    } else {
                        const auto& guess = guesses[pass_index - methods.size()];
                        belief = decoder.guided(syndrome, guess[0], guess[1]);
                    }
                    if (pass_index == 0 && !belief.converged && mode != 103)
                        guesses = decoder.guesses(belief);
                    State candidate = belief.converged ? belief.hard : decoder.osd(syndrome, belief, 120, true);
                    if (mode != 102) decoder.stabilize(candidate);
                    double candidate_score = decoder.score(candidate);
                    if (candidate_score < best_score - 1e-9) {
                        best_score = candidate_score;
                        best = candidate;
                    }
                    statistics[0] += belief.converged;
                    statistics[1] += belief.iterations;
                    statistics[3] += 1;
                    ++pass;
                    if (pass_index < methods.size() && mode != 101 && belief.converged && candidate_score <= best_score + 1e-9) {
                        if (std::find(converged.begin(), converged.end(), candidate) != converged.end()) break;
                        converged.push_back(candidate);
                    }
                }
                statistics[2] += best_score;
                if (decoder.mismatch(best, syndrome)) return 2;
                std::copy(best.begin(), best.end(), output + shot * size);
                continue;
            }
            auto belief = decoder.run(syndrome, mode >= 20 ? mode - 20 : mode);
            State answer = belief.converged ? belief.hard : decoder.osd(syndrome, belief, mode >= 20 ? 120 : 50, mode >= 20);
            statistics[0] += belief.converged;
            statistics[1] += belief.iterations;
            statistics[2] += decoder.score(answer);
            if (decoder.mismatch(answer, syndrome)) return 2;
            std::copy(answer.begin(), answer.end(), output + shot * size);
        }
        statistics[7] = double(std::clock() - start) / CLOCKS_PER_SEC;
        return 0;
    } catch (...) {
        return 1;
    }
}
