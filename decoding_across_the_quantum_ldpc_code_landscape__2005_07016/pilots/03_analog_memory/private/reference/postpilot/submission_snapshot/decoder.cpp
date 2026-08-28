#include <algorithm>
#include <cmath>
#include <cstdint>
#include <ctime>
#include <limits>
#include <numeric>
#include <random>
#include <vector>

using Bits = std::vector<uint8_t>;

struct Decoder {
    int rows, columns, base_rows, edges, move_count;
    const int *row_ptr, *edge_columns, *move_ptr, *move_columns;
    std::mt19937 random;

    Decoder(int row_count, int column_count, int independent_rows, const int *pointers,
            const int *indices, int moves, const int *move_pointers, const int *move_indices)
        : rows(row_count), columns(column_count), base_rows(independent_rows),
          edges(pointers[row_count]), move_count(moves), row_ptr(pointers),
          edge_columns(indices), move_ptr(move_pointers), move_columns(move_indices), random(18371) {}

    bool valid(const Bits &candidate, const uint8_t *syndrome) const {
        for (int row = 0; row < base_rows; ++row) {
            int parity = syndrome[row];
            for (int edge = row_ptr[row]; edge < row_ptr[row + 1]; ++edge) parity ^= candidate[edge_columns[edge]];
            if (parity) return false;
        }
        return true;
    }

    double cost(const Bits &candidate, const double *prior) const {
        double total = 0;
        for (int variable = 0; variable < columns; ++variable) if (candidate[variable]) total += prior[variable];
        return total;
    }

    void local_search(Bits &candidate, const double *prior, int sweeps = 8) const {
        for (int sweep = 0; sweep < sweeps; ++sweep) {
            bool changed = false;
            for (int index = 0; index < move_count; ++index) {
                int move = (sweep & 1) ? move_count - 1 - index : index;
                double delta = 0;
                for (int offset = move_ptr[move]; offset < move_ptr[move + 1]; ++offset) {
                    int variable = move_columns[offset];
                    delta += candidate[variable] ? -prior[variable] : prior[variable];
                }
                if (delta < -1e-9) {
                    changed = true;
                    for (int offset = move_ptr[move]; offset < move_ptr[move + 1]; ++offset)
                        candidate[move_columns[offset]] ^= 1;
                }
            }
            if (!changed) break;
        }
    }

    bool belief_propagation(const double *prior, const uint8_t *syndrome, int run,
                            int iterations, std::vector<double> &reliability, Bits &hard) {
        std::vector<double> channel(prior, prior + columns), messages(edges, 0.0);
        std::vector<double> posterior(columns), average(columns), outgoing(edges, 0.0);
        std::normal_distribution<double> normal(0.0, 1.0);
        double noise = run < 2 ? 0.0 : (0.10 + 0.05 * ((run - 2) % 4));
        for (int variable = 0; variable < columns; ++variable) {
            channel[variable] *= std::exp(noise * normal(random) - 0.5 * noise * noise);
            posterior[variable] = average[variable] = channel[variable];
        }
        bool layered = (run % 3 != 1);
        bool sum_product = (run % 4 == 1);
        double alpha = run == 0 ? 0.80 : (run % 3 == 1 ? 0.70 : 0.90);
        double damping = layered ? 0.15 : 0.30;
        std::vector<int> schedule(rows);
        std::iota(schedule.begin(), schedule.end(), 0);
        int maximum_degree = 1;
        for (int row = 0; row < rows; ++row) maximum_degree = std::max(maximum_degree, row_ptr[row + 1] - row_ptr[row]);
        std::vector<double> incoming(maximum_degree);
        std::vector<double> prefix(maximum_degree + 1), suffix(maximum_degree + 1);
        for (int iteration = 0; iteration < iterations; ++iteration) {
            if (run > 1 && iteration % 5 == 0) std::shuffle(schedule.begin(), schedule.end(), random);
            for (int offset = 0; offset < rows; ++offset) {
                int scheduled = (iteration & 1) ? rows - 1 - offset : offset;
                int row = schedule[scheduled];
                int start = row_ptr[row], stop = row_ptr[row + 1];
                double minimum = 100.0, second = 100.0;
                int minimum_index = -1, sign = syndrome[row] ? -1 : 1;
                for (int edge = start; edge < stop; ++edge) {
                    double value = std::clamp(posterior[edge_columns[edge]] - messages[edge], -50.0, 50.0);
                    incoming[edge - start] = value;
                    if (value < 0) sign = -sign;
                    double magnitude = std::abs(value);
                    if (magnitude < minimum) {
                        second = minimum;
                        minimum = magnitude;
                        minimum_index = edge;
                    } else if (magnitude < second) second = magnitude;
                }
                if (sum_product) {
                    prefix[0] = 1;
                    for (int edge = start; edge < stop; ++edge) {
                        int position = edge - start;
                        incoming[position] = std::tanh(incoming[position] * 0.5);
                        prefix[position + 1] = prefix[position] * incoming[position];
                    }
                    suffix[stop - start] = 1;
                    for (int position = stop - start - 1; position >= 0; --position)
                        suffix[position] = suffix[position + 1] * incoming[position];
                }
                double factor = alpha * (row >= base_rows ? 0.85 : 1.0);
                for (int edge = start; edge < stop; ++edge) {
                    double value = factor * (edge == minimum_index ? second : minimum);
                    if ((incoming[edge - start] < 0 ? -sign : sign) < 0) value = -value;
                    if (sum_product) {
                        int position = edge - start;
                        double product = prefix[position] * suffix[position + 1] * (syndrome[row] ? -1 : 1);
                        product = std::clamp(product, -0.999999999999, 0.999999999999);
                        value = std::log1p(product) - std::log1p(-product);
                        if (row >= base_rows) value *= 0.85;
                    }
                    value = damping * messages[edge] + (1.0 - damping) * value;
                    if (layered) {
                        posterior[edge_columns[edge]] += value - messages[edge];
                        messages[edge] = value;
                    } else outgoing[edge] = value;
                }
            }
            if (!layered) {
                posterior = channel;
                messages.swap(outgoing);
                for (int edge = 0; edge < edges; ++edge) posterior[edge_columns[edge]] += messages[edge];
            }
            for (int variable = 0; variable < columns; ++variable) {
                average[variable] = 0.80 * average[variable] + 0.20 * posterior[variable];
                hard[variable] = posterior[variable] < 0;
            }
            if (valid(hard, syndrome)) {
                reliability = posterior;
                return true;
            }
        }
        reliability = average;
        for (int variable = 0; variable < columns; ++variable) hard[variable] = average[variable] < 0;
        return false;
    }

    Bits ordered_statistics(const double *prior, const uint8_t *syndrome,
                            const std::vector<double> &reliability, int order) const {
        std::vector<int> permutation(columns), inverse(columns);
        std::iota(permutation.begin(), permutation.end(), 0);
        std::stable_sort(permutation.begin(), permutation.end(), [&](int first, int second) {
            return std::abs(reliability[first]) < std::abs(reliability[second]);
        });
        for (int position = 0; position < columns; ++position) inverse[permutation[position]] = position;
        int words = (columns + 1 + 63) / 64;
        std::vector<uint64_t> storage(static_cast<size_t>(base_rows) * words, 0);
        std::vector<uint64_t *> matrix(base_rows);
        for (int row = 0; row < base_rows; ++row) {
            matrix[row] = storage.data() + static_cast<size_t>(row) * words;
            for (int edge = row_ptr[row]; edge < row_ptr[row + 1]; ++edge) {
                int position = inverse[edge_columns[edge]];
                matrix[row][position / 64] ^= uint64_t(1) << (position % 64);
            }
            if (syndrome[row]) matrix[row][columns / 64] ^= uint64_t(1) << (columns % 64);
        }
        std::vector<int> pivots;
        std::vector<int> free_columns;
        int rank = 0;
        for (int position = 0; position < columns; ++position) {
            int word = position / 64;
            uint64_t mask = uint64_t(1) << (position % 64);
            int pivot = rank;
            while (pivot < base_rows && !(matrix[pivot][word] & mask)) ++pivot;
            if (pivot == base_rows) {
                free_columns.push_back(position);
                continue;
            }
            std::swap(matrix[rank], matrix[pivot]);
            for (int row = rank + 1; row < base_rows; ++row) {
                if (matrix[row][word] & mask) {
                    for (int block = word; block < words; ++block) matrix[row][block] ^= matrix[rank][block];
                }
            }
            pivots.push_back(position);
            ++rank;
        }
        for (int pivot = rank - 1; pivot >= 0; --pivot) {
            int word = pivots[pivot] / 64;
            uint64_t mask = uint64_t(1) << (pivots[pivot] % 64);
            for (int row = 0; row < pivot; ++row) {
                if (matrix[row][word] & mask) {
                    for (int block = word; block < words; ++block) matrix[row][block] ^= matrix[pivot][block];
                }
            }
        }
        Bits initial(columns, 0);
        for (int pivot = 0; pivot < rank; ++pivot)
            initial[permutation[pivots[pivot]]] = (matrix[pivot][columns / 64] >> (columns % 64)) & 1;
        std::vector<std::vector<int>> moves(free_columns.size());
        for (size_t index = 0; index < free_columns.size(); ++index) {
            int position = free_columns[index];
            int word = position / 64;
            uint64_t mask = uint64_t(1) << (position % 64);
            auto &move = moves[index];
            for (int pivot = 0; pivot < rank; ++pivot)
                if (matrix[pivot][word] & mask) move.push_back(permutation[pivots[pivot]]);
            move.push_back(permutation[position]);
            std::sort(move.begin(), move.end());
        }
        Bits posterior_candidate = initial;
        for (size_t index = 0; index < moves.size(); ++index)
            if (reliability[permutation[free_columns[index]]] < 0)
                for (int variable : moves[index]) posterior_candidate[variable] ^= 1;
        Bits best = cost(posterior_candidate, prior) < cost(initial, prior) ? posterior_candidate : initial;
        for (int sweep = 0; sweep < 5; ++sweep) {
            std::vector<double> signed_cost(columns), deltas(moves.size());
            for (int variable = 0; variable < columns; ++variable)
                signed_cost[variable] = best[variable] ? -prior[variable] : prior[variable];
            double improvement = -1e-9;
            int best_first = -1, best_second = -1;
            for (size_t index = 0; index < moves.size(); ++index) {
                double delta = 0;
                for (int variable : moves[index]) delta += signed_cost[variable];
                deltas[index] = delta;
                if (delta < improvement) {
                    improvement = delta;
                    best_first = static_cast<int>(index);
                    best_second = -1;
                }
            }
            int width = std::min(order, static_cast<int>(moves.size()));
            for (int first = 0; first < width; ++first) {
                for (int second = first + 1; second < width; ++second) {
                    double delta = deltas[first] + deltas[second];
                    const auto &first_move = moves[first];
                    const auto &second_move = moves[second];
                    size_t first_index = 0, second_index = 0;
                    while (first_index < first_move.size() && second_index < second_move.size()) {
                        if (first_move[first_index] < second_move[second_index]) ++first_index;
                        else if (second_move[second_index] < first_move[first_index]) ++second_index;
                        else {
                            delta -= 2 * signed_cost[first_move[first_index]];
                            ++first_index;
                            ++second_index;
                        }
                    }
                    if (delta < improvement) {
                        improvement = delta;
                        best_first = first;
                        best_second = second;
                    }
                }
            }
            if (best_first < 0) break;
            for (int variable : moves[best_first]) best[variable] ^= 1;
            if (best_second >= 0) for (int variable : moves[best_second]) best[variable] ^= 1;
        }
        return best;
    }
};

extern "C" int decode(int rows, int columns, int base_rows, int shots,
                      const int *row_ptr, const int *edge_columns,
                      const double *priors, const uint8_t *syndromes,
                      int move_count, const int *move_ptr, const int *move_columns,
                      int runs, int iterations, int order, double budget,
                      uint8_t *answers, double *statistics) {
    try {
        Decoder decoder(rows, columns, base_rows, row_ptr, edge_columns, move_count, move_ptr, move_columns);
        double start = static_cast<double>(std::clock()) / CLOCKS_PER_SEC;
        for (int shot = 0; shot < shots; ++shot) {
            const double *prior = priors + static_cast<size_t>(shot) * columns;
            const uint8_t *syndrome = syndromes + static_cast<size_t>(shot) * rows;
            Bits best(columns, 0), hard(columns, 0);
            std::vector<double> reliability(columns);
            double best_cost = std::numeric_limits<double>::infinity();
            int completed = 0, convergences = 0;
            double shot_start = static_cast<double>(std::clock()) / CLOCKS_PER_SEC;
            double allowance = std::max(0.03, (budget - (shot_start - start)) / (shots - shot));
            for (int run = 0; run < runs; ++run) {
                double now = static_cast<double>(std::clock()) / CLOCKS_PER_SEC;
                if (run && now - shot_start > allowance * 0.85) break;
                bool converged = decoder.belief_propagation(prior, syndrome, run, iterations, reliability, hard);
                Bits candidate;
                if (converged) {
                    ++convergences;
                    candidate = hard;
                } else candidate = decoder.ordered_statistics(prior, syndrome, reliability, order);
                decoder.local_search(candidate, prior);
                double candidate_cost = decoder.cost(candidate, prior);
                if (candidate_cost < best_cost) {
                    best_cost = candidate_cost;
                    best = candidate;
                }
                ++completed;
            }
            if (!decoder.valid(best, syndrome)) return 2;
            std::copy(best.begin(), best.end(), answers + static_cast<size_t>(shot) * columns);
            statistics[shot * 4] = best_cost;
            statistics[shot * 4 + 1] = completed;
            statistics[shot * 4 + 2] = convergences;
            statistics[shot * 4 + 3] = static_cast<double>(std::clock()) / CLOCKS_PER_SEC - shot_start;
        }
        return 0;
    } catch (...) {
        return 1;
    }
}

extern "C" int refine_history(int columns, int shots, int data_count,
                              const double *priors, const double *thresholds,
                              int move_count, const int *move_ptr, const int *move_columns,
                              int sweeps, double budget, uint8_t *answers) {
    try {
        std::mt19937 random(918273);
        std::uniform_real_distribution<double> uniform(0.0, 1.0);
        double start = static_cast<double>(std::clock()) / CLOCKS_PER_SEC;
        for (int shot = 0; shot < shots; ++shot) {
            const double *prior = priors + static_cast<size_t>(shot) * columns;
            const double *threshold = thresholds + static_cast<size_t>(shot) * (columns - data_count);
            uint8_t *answer = answers + static_cast<size_t>(shot) * columns;
            Bits sample(answer, answer + columns);
            std::vector<double> average(columns, 0.0), counts(columns, 0.0), metric(columns, 0.0);
            int samples = 0;
            double shot_start = static_cast<double>(std::clock()) / CLOCKS_PER_SEC;
            if (shot_start - start >= budget) break;
            double allowance = std::max(0.005, (budget - (shot_start - start)) / (shots - shot));
            int burn = std::min(50, sweeps / 4);
            for (int sweep = 0; sweep < sweeps; ++sweep) {
                for (int index = 0; index < move_count; ++index) {
                    int move = (sweep & 1) ? move_count - 1 - index : index;
                    double delta = 0;
                    for (int offset = move_ptr[move]; offset < move_ptr[move + 1]; ++offset) {
                        int variable = move_columns[offset];
                        delta += sample[variable] ? -prior[variable] : prior[variable];
                    }
                    double probability = delta > 35 ? 0 : (delta < -35 ? 1 : 1 / (1 + std::exp(delta)));
                    if (sweep >= burn) {
                        for (int offset = move_ptr[move]; offset < move_ptr[move + 1]; ++offset) {
                            int variable = move_columns[offset];
                            if (variable >= data_count) {
                                average[variable] += sample[variable] ? 1 - probability : probability;
                                counts[variable] += 1;
                            }
                        }
                    }
                    if (uniform(random) < probability)
                        for (int offset = move_ptr[move]; offset < move_ptr[move + 1]; ++offset)
                            sample[move_columns[offset]] ^= 1;
                }
                if (sweep >= burn) {
                    ++samples;
                    for (int variable = data_count; variable < columns; ++variable) {
                        average[variable] += sample[variable];
                        counts[variable] += 1;
                    }
                }
                if (samples >= 24 && (sweep % 8 == 7) &&
                    static_cast<double>(std::clock()) / CLOCKS_PER_SEC - shot_start > allowance) break;
            }
            if (!samples) continue;
            for (int variable = data_count; variable < columns; ++variable)
                metric[variable] = threshold[variable - data_count] - average[variable] / counts[variable];
            for (int sweep = 0; sweep < 12; ++sweep) {
                bool changed = false;
                for (int index = 0; index < move_count; ++index) {
                    int move = (sweep & 1) ? move_count - 1 - index : index;
                    double delta = 0;
                    for (int offset = move_ptr[move]; offset < move_ptr[move + 1]; ++offset) {
                        int variable = move_columns[offset];
                        delta += answer[variable] ? -metric[variable] : metric[variable];
                    }
                    if (delta < -1e-9) {
                        changed = true;
                        for (int offset = move_ptr[move]; offset < move_ptr[move + 1]; ++offset)
                            answer[move_columns[offset]] ^= 1;
                    }
                }
                if (!changed) break;
            }
        }
        return 0;
    } catch (...) {
        return 1;
    }
}
