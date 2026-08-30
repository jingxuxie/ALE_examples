#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>
#include <numeric>
#include <random>

static const std::vector<double> phi_table = [] {
    std::vector<double> result(16385);
    result[0] = 30;
    for (int index = 1; index <= 16384; ++index)
        result[index] = -std::log(std::tanh(index / 1024.0));
    return result;
}();

static double phi(double value) {
    value = std::abs(value);
    if (value < 1.0 / 512.0) return -std::log(std::max(value * 0.5, 1e-15));
    if (value >= 32) return 0;
    double position = value * 512;
    int index = int(position);
    return phi_table[index] + (phi_table[index + 1] - phi_table[index]) * (position - index);
}

extern "C" __attribute__((target_clones("avx2", "default")))
void bp_fast(int shots, int checks, int variables, int links,
    const int* starts, const int* neighbors, const double* prior,
    const uint8_t* syndromes, int iterations, double damping, double scale,
    double* posterior, uint8_t* converged, int* used_iterations, int mode) {
    std::vector<double> messages(links), incoming(links), values(variables), accumulated(variables);
    std::vector<uint8_t> hard(variables), signs(links);
    std::vector<int> schedule(checks);
    std::iota(schedule.begin(), schedule.end(), 0);
    if (mode >= 16) {
        std::mt19937 generator(mode >> 4);
        std::shuffle(schedule.begin(), schedule.end(), generator);
    }
    for (int shot = 0; shot < shots; ++shot) {
        std::fill(messages.begin(), messages.end(), 0.0);
        std::fill(accumulated.begin(), accumulated.end(), 0.0);
        std::copy(prior, prior + variables, values.begin());
        const uint8_t* syndrome = syndromes + shot * checks;
        converged[shot] = 0;
        for (int iteration = 0; iteration < iterations; ++iteration) {
            if (!(mode & 2)) {
                for (int link = 0; link < links; ++link) {
                    double value = (values[neighbors[link]] - messages[link]) * scale;
                    signs[link] = value < 0;
                    incoming[link] = (mode & 8) ? std::abs(value) : phi(value);
                }
                std::copy(prior, prior + variables, values.begin());
            }
            for (int check : schedule) {
                double total = 0;
                double least = 1e100, next_least = 1e100;
                int least_index = -1;
                uint8_t sign = syndrome[check];
                for (int link = starts[check]; link < starts[check + 1]; ++link) {
                    if (mode & 2) {
                        double value = (values[neighbors[link]] - messages[link]) * scale;
                        signs[link] = value < 0;
                        incoming[link] = (mode & 8) ? std::abs(value) : phi(value);
                        values[neighbors[link]] -= messages[link];
                    }
                    total += incoming[link];
                    sign ^= signs[link];
                    if (mode & 8) {
                        if (incoming[link] < least) {
                            next_least = least;
                            least = incoming[link];
                            least_index = link;
                        } else if (incoming[link] < next_least) next_least = incoming[link];
                    }
                }
                for (int link = starts[check]; link < starts[check + 1]; ++link) {
                    double value = (mode & 8) ? std::min(30.0, link == least_index ? next_least : least) : phi(total - incoming[link]);
                    if (sign ^ signs[link]) value = -value;
                    messages[link] = damping * messages[link] + (1 - damping) * value;
                    values[neighbors[link]] += messages[link];
                }
            }
            for (int variable = 0; variable < variables; ++variable) {
                hard[variable] = values[variable] < 0;
                accumulated[variable] = 0.8 * accumulated[variable] + 0.2 * values[variable];
            }
            bool valid = true;
            for (int check = 0; check < checks; ++check) {
                uint8_t parity = syndrome[check];
                for (int link = starts[check]; link < starts[check + 1]; ++link) parity ^= hard[neighbors[link]];
                if (parity) { valid = false; break; }
            }
            used_iterations[shot] = iteration + 1;
            if (valid) { converged[shot] = 1; break; }
        }
        if ((mode & 4) && !converged[shot])
            std::copy(accumulated.begin(), accumulated.end(), posterior + shot * variables);
        else
            std::copy(values.begin(), values.end(), posterior + shot * variables);
    }
}

extern "C" __attribute__((target_clones("avx2", "default")))
void osd(int shots, int checks, int variables, const int* starts,
    const int* neighbors, const double* prior, const uint8_t* logical,
    const uint8_t* syndromes, const double* posterior, int order_count,
    double* minima, double* evidence) {
    int words = (checks + 63) / 64;
    std::vector<uint64_t> columns(variables * words, 0);
    for (int check = 0; check < checks; ++check)
        for (int link = starts[check]; link < starts[check + 1]; ++link)
            columns[neighbors[link] * words + check / 64] ^= uint64_t(1) << (check % 64);
    for (int shot = 0; shot < shots; ++shot) {
        const double* belief = posterior + shot * variables;
        std::vector<int> order(variables), pivots, nonpivots;
        std::iota(order.begin(), order.end(), 0);
        std::stable_sort(order.begin(), order.end(), [&](int left, int right) {
            return std::abs(belief[left]) < std::abs(belief[right]);
        });
        std::vector<int> occupied(checks, -1);
        std::vector<uint64_t> basis(checks * words, 0), transforms(checks * words, 0);
        std::vector<uint64_t> nonpivot_transforms, value(words), combination(words), residual(words, 0);
        std::vector<uint8_t> hard(variables);
        for (int check = 0; check < checks; ++check)
            if (syndromes[shot * checks + check]) residual[check / 64] ^= uint64_t(1) << (check % 64);
        for (int variable = 0; variable < variables; ++variable) {
            hard[variable] = belief[variable] < 0;
            if (hard[variable])
                for (int word = 0; word < words; ++word) residual[word] ^= columns[variable * words + word];
        }
        for (int variable : order) {
            std::copy(columns.begin() + variable * words, columns.begin() + (variable + 1) * words, value.begin());
            std::fill(combination.begin(), combination.end(), 0);
            bool independent = false;
            for (int word = 0; word < words; ++word) {
                while (value[word]) {
                    int check = word * 64 + __builtin_ctzll(value[word]);
                    if (occupied[check] < 0) {
                        int pivot = pivots.size();
                        occupied[check] = pivot;
                        pivots.push_back(variable);
                        combination[pivot / 64] ^= uint64_t(1) << (pivot % 64);
                        std::copy(value.begin(), value.end(), basis.begin() + check * words);
                        std::copy(combination.begin(), combination.end(), transforms.begin() + check * words);
                        independent = true;
                        break;
                    }
                    for (int other = word; other < words; ++other) value[other] ^= basis[check * words + other];
                    for (int other = 0; other < words; ++other) combination[other] ^= transforms[check * words + other];
                }
                if (independent) break;
            }
            if (!independent) {
                nonpivots.push_back(variable);
                nonpivot_transforms.insert(nonpivot_transforms.end(), combination.begin(), combination.end());
            }
        }
        std::fill(combination.begin(), combination.end(), 0);
        for (int word = 0; word < words; ++word) {
            while (residual[word]) {
                int check = word * 64 + __builtin_ctzll(residual[word]);
                if (occupied[check] < 0) break;
                for (int other = word; other < words; ++other) residual[other] ^= basis[check * words + other];
                for (int other = 0; other < words; ++other) combination[other] ^= transforms[check * words + other];
            }
        }
        for (int pivot = 0; pivot < int(pivots.size()); ++pivot)
            hard[pivots[pivot]] ^= (combination[pivot / 64] >> (pivot % 64)) & 1;
        double base_weight = 0;
        int base_logical = 0;
        std::vector<double> delta(pivots.size());
        for (int variable = 0; variable < variables; ++variable) {
            if (hard[variable]) {
                base_weight += prior[variable];
                base_logical ^= logical[variable];
            }
        }
        for (int pivot = 0; pivot < int(pivots.size()); ++pivot)
            delta[pivot] = hard[pivots[pivot]] ? -prior[pivots[pivot]] : prior[pivots[pivot]];
        double best[2] = {1e100, 1e100};
        double sums[2] = {0, 0};
        auto add = [&](double weight, int parity) {
            if (weight < best[parity]) {
                sums[parity] = sums[parity] * std::exp(weight - best[parity]) + 1;
                best[parity] = weight;
            } else {
                if (weight < best[parity] + 25) sums[parity] += std::exp(best[parity] - weight);
            }
        };
        add(base_weight, base_logical);
        auto candidate = [&](int first, int second, int third) {
            double weight = base_weight;
            int parity = base_logical;
            for (int index : {first, second, third}) {
                if (index >= 0) {
                    int variable = nonpivots[index];
                    weight += hard[variable] ? -prior[variable] : prior[variable];
                    parity ^= logical[variable];
                }
            }
            for (int word = 0; word < words; ++word) {
                uint64_t flipped = nonpivot_transforms[first * words + word];
                if (second >= 0) flipped ^= nonpivot_transforms[second * words + word];
                if (third >= 0) flipped ^= nonpivot_transforms[third * words + word];
                while (flipped) {
                    int pivot = word * 64 + __builtin_ctzll(flipped);
                    weight += delta[pivot];
                    parity ^= logical[pivots[pivot]];
                    flipped &= flipped - 1;
                }
            }
            add(weight, parity);
        };
        std::vector<double> single_weight(nonpivots.size());
        std::vector<int> single_logical(nonpivots.size());
        for (int index = 0; index < int(nonpivots.size()); ++index) {
            int variable = nonpivots[index];
            double difference = hard[variable] ? -prior[variable] : prior[variable];
            int parity = logical[variable];
            for (int word = 0; word < words; ++word) {
                uint64_t flipped = nonpivot_transforms[index * words + word];
                while (flipped) {
                    int pivot = word * 64 + __builtin_ctzll(flipped);
                    difference += delta[pivot];
                    parity ^= logical[pivots[pivot]];
                    flipped &= flipped - 1;
                }
            }
            single_weight[index] = difference;
            single_logical[index] = parity;
            add(base_weight + difference, base_logical ^ parity);
        }
        int count = std::min(order_count, int(nonpivots.size()));
        for (int first = 0; first < count; ++first)
            for (int second = first + 1; second < count; ++second) {
                double weight = base_weight + single_weight[first] + single_weight[second];
                for (int word = 0; word < words; ++word) {
                    uint64_t overlap = nonpivot_transforms[first * words + word] & nonpivot_transforms[second * words + word];
                    while (overlap) {
                        int pivot = word * 64 + __builtin_ctzll(overlap);
                        weight -= 2 * delta[pivot];
                        overlap &= overlap - 1;
                    }
                }
                add(weight, base_logical ^ single_logical[first] ^ single_logical[second]);
            }
        int triple_count = std::min(count, 20);
        for (int first = 0; first < triple_count; ++first)
            for (int second = first + 1; second < triple_count; ++second)
                for (int third = second + 1; third < triple_count; ++third)
                    candidate(first, second, third);
        for (int parity = 0; parity < 2; ++parity) {
            minima[shot * 2 + parity] = best[parity];
            evidence[shot * 2 + parity] = best[parity] - std::log(sums[parity]);
        }
    }
}
