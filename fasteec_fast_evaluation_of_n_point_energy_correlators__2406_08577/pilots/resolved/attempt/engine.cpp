#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>

#ifdef ENGINE_VECTOR
#include <immintrin.h>
extern "C" __m256d _ZGVdN4v_log(__m256d);
extern "C" __m256d _ZGVdN4v_exp(__m256d);
#endif

constexpr double PI = 3.141592653589793238462643383279502884;
constexpr double TWO_PI = 2.0 * PI;

#ifndef DENSE_FACTOR
#define DENSE_FACTOR 12
#endif

struct Particle {
    double pt, rapidity, phi;
};

struct Query {
    int order, bins, ratio_bins, phi_bins;
    double log_min, nu1, nu2, nu3, radial_scale, radial_min;
    int first_exponent, second_exponent, tail_exponent, projected_second;
    std::vector<double> histogram;
    std::vector<double> contact_first, contact_repeat, contact_special;
};

struct Group {
    int ratio_bins, phi_bins;
    std::vector<int> queries;
    std::vector<double> exponents;
    std::vector<double> tail_exponents;
};

double wrap(double angle) {
    if (angle > PI || angle <= -PI) {
        if (angle > 3.0 * PI || angle <= -3.0 * PI) {
            angle = std::fmod(angle, TWO_PI);
        }
        if (angle > PI) angle -= TWO_PI;
        if (angle <= -PI) angle += TWO_PI;
    }
    return angle;
}

__attribute__((optimize("fp-contract=off")))
double precise_angle(double outer_y, double outer_phi, double inner_y, double inner_phi) {
    double determinant = outer_y * inner_phi - outer_phi * inner_y;
    double dot = outer_y * inner_y + outer_phi * inner_phi;
    if (!std::isfinite(determinant) || !std::isfinite(dot) || (determinant == 0.0 && dot == 0.0)) {
        long double extended_determinant = static_cast<long double>(outer_y) * inner_phi
                                        - static_cast<long double>(outer_phi) * inner_y;
        long double extended_dot = static_cast<long double>(outer_y) * inner_y
                                + static_cast<long double>(outer_phi) * inner_phi;
        return wrap(static_cast<double>(std::atan2(extended_determinant, extended_dot)));
    }
    return wrap(std::atan2(determinant, dot));
}

int exponent_index(std::vector<double>& exponents, double exponent) {
    if (exponent == 1.0) return -1;
    for (int index = 0; index < static_cast<int>(exponents.size()); ++index) {
        if (exponents[index] == exponent) return index;
    }
    exponents.push_back(exponent);
    return static_cast<int>(exponents.size()) - 1;
}

double difference(double prefix, double weight, double exponent,
                  double old_power, double new_power) {
    if (weight == 0.0) return 0.0;
    if (exponent == 1.0) return weight;
    if (exponent == 2.0) return weight * (2.0 * prefix + weight);
    if (prefix == 0.0) return new_power;
    double result = new_power - old_power;
    if (weight > 1.0e-5 * prefix && result > 1.0e-6 * new_power) return result;
    double logarithmic_ratio = weight <= prefix
        ? std::log1p(weight / prefix)
        : std::log(weight) - std::log(prefix) + std::log1p(prefix / weight);
    return new_power * (-std::expm1(-exponent * logarithmic_ratio));
}

double power_from_log(double base, double logarithm, double exponent) {
    if (exponent == 2.0) return base * base;
    if (exponent == 0.5) return std::sqrt(base);
    if (exponent == 3.0) return base * base * base;
    return std::exp(exponent * logarithm);
}

int radial_bin(double radius, const Query& query) {
    if (radius < query.radial_min) return 0;
    if (radius >= 1.0) return query.bins - 1;
    int result = 1 + static_cast<int>((std::log10(radius) - query.log_min) * query.radial_scale);
    return std::max(1, std::min(query.bins - 2, result));
}

class Engine {
#ifdef ENGINE_PROFILE
    double timings[5] = {};
#endif
    std::vector<Query> queries;
    std::vector<Group> groups;
    bool need_pair_geometry = false;
    std::vector<double> first_exponents;
    std::vector<double> weights, weight_logs, radii, ranked_suffix;
    bool extended_mode = false;
    std::vector<long double> extended_weights, ranked_extended_weights, extended_suffix;
    std::vector<double> distance_matrix, phi_matrix, bearing_matrix;
    std::vector<double> ranked_weights, ranked_y, ranked_phi, ranked_bearings;
    std::vector<double> ratios, angles;
    std::vector<int> ranks, cells, phi_cells, radial_cells;
    std::vector<std::vector<double>> first_differences, pair_differences, tail_differences;
    std::vector<double> prefixes, prefix_powers, unit_tails;
    std::vector<int> tail_indices, tail_offsets;
#ifdef ENGINE_VECTOR
    std::vector<double> delta_prefixes, delta_next, delta_weights, delta_logs, delta_powers;
    std::vector<int> delta_previous, delta_destinations, prefix_previous;
    std::vector<int> correction_indices;
    std::vector<double> correction_values;

    void correct_large_exponent_logs(const Group& group, int special, bool sparse) {
        correction_indices.clear();
        correction_values.clear();
        const auto& exponents = sparse ? group.tail_exponents : group.exponents;
        if (std::none_of(exponents.begin(), exponents.end(), [](double value) { return value > 1024.0; })) return;
        int remaining = static_cast<int>(ranks.size());
        std::vector<double> totals(group.phi_bins);
        for (int outer = 1; outer < remaining; ++outer) {
            std::fill(totals.begin(), totals.end(), 0.0);
            totals[group.phi_bins / 2] = weights[special];
            int begin = sparse ? tail_offsets[outer] : outer * (outer - 1) / 2;
            int end = sparse ? tail_offsets[outer + 1] : begin + outer;
            for (int position = begin; position < end; ++position) {
                int phi = sparse ? tail_indices[position] % group.phi_bins : phi_cells[position];
                totals[phi] += delta_weights[position];
            }
            int dominant = -1;
            for (int phi = 0; phi < group.phi_bins; ++phi) {
                if (totals[phi] > 0.5) dominant = phi;
            }
            if (dominant < 0) continue;
            double excluded = ranked_suffix[outer];
            if (dominant != group.phi_bins / 2) excluded += weights[special];
            for (int position = begin; position < end; ++position) {
                int phi = sparse ? tail_indices[position] % group.phi_bins : phi_cells[position];
                if (phi != dominant) excluded += delta_weights[position];
            }
            for (int position = end - 1; position >= begin; --position) {
                int phi = sparse ? tail_indices[position] % group.phi_bins : phi_cells[position];
                if (phi != dominant) continue;
                if (delta_next[position] > 0.5) {
                    correction_indices.push_back(position);
                    correction_values.push_back(std::log1p(-std::min(1.0, excluded)));
                }
                excluded += delta_weights[position];
            }
        }
    }

    template<bool Sparse>
    void evaluate_prefixes(const std::vector<double>& exponents, int special,
                           std::vector<std::vector<double>>& output) {
        size_t count = delta_next.size();
        delta_logs.resize(count);
        delta_powers.resize(count);
        size_t position = 0;
        for (; position + 4 <= count; position += 4) {
            _mm256_storeu_pd(delta_logs.data() + position,
                _ZGVdN4v_log(_mm256_loadu_pd(delta_next.data() + position)));
        }
        for (; position < count; ++position) delta_logs[position] = std::log(delta_next[position]);
        for (size_t index = 0; index < correction_indices.size(); ++index) {
            delta_logs[correction_indices[index]] = correction_values[index];
        }
        for (size_t exponent_index = 0; exponent_index < exponents.size(); ++exponent_index) {
            double exponent = exponents[exponent_index];
            if (exponent == 2.0) {
                for (size_t index = 0; index < count; ++index) delta_powers[index] = delta_next[index] * delta_next[index];
            } else if (exponent == 3.0) {
                for (size_t index = 0; index < count; ++index) delta_powers[index] = delta_next[index] * delta_next[index] * delta_next[index];
            } else {
                position = 0;
                __m256d exponent_vector = _mm256_set1_pd(exponent);
                for (; position + 4 <= count; position += 4) {
                    _mm256_storeu_pd(delta_powers.data() + position,
                        _ZGVdN4v_exp(_mm256_mul_pd(exponent_vector,
                            _mm256_loadu_pd(delta_logs.data() + position))));
                }
                for (; position < count; ++position) delta_powers[position] = std::exp(exponent * delta_logs[position]);
            }
            double initial_power = weight_power(special, exponent);
            auto& differences = output[exponent_index];
            for (size_t index = 0; index < count; ++index) {
                double old_power = delta_previous[index] >= 0 ? delta_powers[delta_previous[index]]
                    : (delta_prefixes[index] > 0.0 ? initial_power : 0.0);
                size_t destination = Sparse ? delta_destinations[index] : index;
                differences[destination] = difference(delta_prefixes[index], delta_weights[index],
                    exponent, old_power, delta_powers[index]);
            }
        }
    }

    void prepare_vector_differences(const Group& group, int special) {
        int remaining = static_cast<int>(ranks.size());
        int cell_count = group.ratio_bins * group.phi_bins;
        pair_differences.resize(group.exponents.size());
        for (auto& differences : pair_differences) differences.resize(ratios.size());
        prefixes.resize(group.phi_bins);
        prefix_previous.resize(group.phi_bins);
        if (!group.exponents.empty()) {
            delta_prefixes.resize(ratios.size());
            delta_next.resize(ratios.size());
            delta_weights.resize(ratios.size());
            delta_previous.resize(ratios.size());
            for (int outer = 1; outer < remaining; ++outer) {
                std::fill(prefixes.begin(), prefixes.end(), 0.0);
                std::fill(prefix_previous.begin(), prefix_previous.end(), -1);
                prefixes[group.phi_bins / 2] = weights[special];
                size_t offset = static_cast<size_t>(outer) * (outer - 1) / 2;
                for (int inner = 0; inner < outer; ++inner) {
                    size_t pair = offset + inner;
                    int phi_cell = phi_cells[pair];
                    double weight = ranked_weights[inner];
                    delta_prefixes[pair] = prefixes[phi_cell];
                    delta_weights[pair] = weight;
                    delta_previous[pair] = prefix_previous[phi_cell];
                    double next = std::min(1.0, prefixes[phi_cell] + weight);
                    delta_next[pair] = next;
                    prefixes[phi_cell] = next;
                    prefix_previous[phi_cell] = static_cast<int>(pair);
                }
            }
            correct_large_exponent_logs(group, special, false);
            evaluate_prefixes<false>(group.exponents, special, pair_differences);
        }
        tail_differences.resize(group.tail_exponents.size());
        for (auto& differences : tail_differences) differences.assign(unit_tails.size(), 0.0);
        if (!group.tail_exponents.empty()) {
            delta_prefixes.resize(tail_indices.size());
            delta_next.resize(tail_indices.size());
            delta_weights.resize(tail_indices.size());
            delta_previous.resize(tail_indices.size());
            delta_destinations.resize(tail_indices.size());
            for (int outer = 1; outer < remaining; ++outer) {
                std::fill(prefixes.begin(), prefixes.end(), 0.0);
                std::fill(prefix_previous.begin(), prefix_previous.end(), -1);
                prefixes[group.phi_bins / 2] = weights[special];
                size_t offset = static_cast<size_t>(outer) * cell_count;
                for (int position = tail_offsets[outer]; position < tail_offsets[outer + 1]; ++position) {
                    int cell = tail_indices[position];
                    int phi_cell = cell % group.phi_bins;
                    double weight = unit_tails[offset + cell];
                    delta_prefixes[position] = prefixes[phi_cell];
                    delta_weights[position] = weight;
                    delta_previous[position] = prefix_previous[phi_cell];
                    delta_destinations[position] = static_cast<int>(offset) + cell;
                    double next = std::min(1.0, prefixes[phi_cell] + weight);
                    delta_next[position] = next;
                    prefixes[phi_cell] = next;
                    prefix_previous[phi_cell] = position;
                }
            }
            correct_large_exponent_logs(group, special, true);
            evaluate_prefixes<true>(group.tail_exponents, special, tail_differences);
        }
    }
#endif
    double weight_power(int index, double exponent) const {
        if (exponent > 1024.0 || weights[index] == 0.0) return std::exp(exponent * weight_logs[index]);
        return std::pow(weights[index], exponent);
    }

    int boundary_phi(int outer, int inner, int phi_bins) const {
        double angle = 0.0;
        if (radii[outer] != 0.0 && radii[inner] != 0.0) {
            angle = precise_angle(ranked_y[outer], ranked_phi[outer], ranked_y[inner], ranked_phi[inner]);
        }
        double scaled = (angle + PI) / TWO_PI * phi_bins;
        return std::max(0, std::min(phi_bins - 1, static_cast<int>(scaled)));
    }

    void prepare_extended_differences(const Group& group, int special) {
        int remaining = static_cast<int>(ranks.size());
        int cell_count = group.ratio_bins * group.phi_bins;
        std::vector<long double> starts(ratios.size()), upper_logs(ratios.size()), phi_prefix(group.phi_bins);
        for (int outer = 1; outer < remaining; ++outer) {
            std::fill(phi_prefix.begin(), phi_prefix.end(), 0.0L);
            phi_prefix[group.phi_bins / 2] = extended_weights[special];
            size_t offset = static_cast<size_t>(outer) * (outer - 1) / 2;
            for (int inner = 0; inner < outer; ++inner) {
                size_t pair = offset + inner;
                int phi = phi_cells[pair];
                starts[pair] = phi_prefix[phi];
                phi_prefix[phi] += ranked_extended_weights[inner];
                upper_logs[pair] = std::log(phi_prefix[phi]);
            }
            int dominant = -1;
            for (int phi = 0; phi < group.phi_bins; ++phi) {
                if (phi_prefix[phi] > 0.5L) dominant = phi;
            }
            if (dominant < 0) continue;
            long double excluded = extended_suffix[outer];
            if (dominant != group.phi_bins / 2) excluded += extended_weights[special];
            for (int inner = 0; inner < outer; ++inner) {
                if (phi_cells[offset + inner] != dominant) excluded += ranked_extended_weights[inner];
            }
            for (int inner = outer - 1; inner >= 0; --inner) {
                size_t pair = offset + inner;
                if (phi_cells[pair] != dominant) continue;
                if (starts[pair] + ranked_extended_weights[inner] > 0.5L) {
                    upper_logs[pair] = std::log1p(-std::min(1.0L, excluded));
                }
                excluded += ranked_extended_weights[inner];
            }
        }
        auto extended_difference = [&](size_t pair, int inner, double exponent) {
            long double weight = ranked_extended_weights[inner];
            if (weight == 0.0L || exponent == 1.0) return static_cast<double>(weight);
            long double power = std::exp(static_cast<long double>(exponent) * upper_logs[pair]);
            if (starts[pair] == 0.0L) return static_cast<double>(power);
            long double factor = -std::expm1(-static_cast<long double>(exponent) * std::log1p(weight / starts[pair]));
            return static_cast<double>(power * factor);
        };
        pair_differences.resize(group.exponents.size());
        for (auto& differences : pair_differences) differences.resize(ratios.size());
        tail_differences.resize(group.tail_exponents.size());
        for (auto& differences : tail_differences) differences.assign(unit_tails.size(), 0.0);
        std::fill(unit_tails.begin(), unit_tails.end(), 0.0);
        tail_indices.clear();
        std::vector<unsigned char> seen(cell_count);
        for (int outer = 1; outer < remaining; ++outer) {
            std::fill(seen.begin(), seen.end(), 0);
            size_t offset = static_cast<size_t>(outer) * (outer - 1) / 2;
            size_t tail_base = static_cast<size_t>(outer) * cell_count;
            tail_offsets[outer] = static_cast<int>(tail_indices.size());
            for (int inner = 0; inner < outer; ++inner) {
                size_t pair = offset + inner;
                int cell = cells[pair];
                if (ranked_extended_weights[inner] > 0.0L && !seen[cell]) {
                    seen[cell] = 1;
                    tail_indices.push_back(cell);
                }
                unit_tails[tail_base + cell] += static_cast<double>(ranked_extended_weights[inner]);
                for (size_t exponent = 0; exponent < group.exponents.size(); ++exponent) {
                    pair_differences[exponent][pair] = extended_difference(pair, inner, group.exponents[exponent]);
                }
                for (size_t exponent = 0; exponent < group.tail_exponents.size(); ++exponent) {
                    tail_differences[exponent][tail_base + cell]
                        += extended_difference(pair, inner, group.tail_exponents[exponent]);
                }
            }
            tail_offsets[outer + 1] = static_cast<int>(tail_indices.size());
        }
    }

    void prepare_geometry(const std::vector<Particle>& event) {
        int count = static_cast<int>(event.size());
        weights.resize(count);
        weight_logs.resize(count);
        extended_weights.resize(count);
        extended_mode = false;
        long double total = 0.0L;
        for (const auto& particle : event) total += particle.pt;
        if (!(total > 0.0L)) throw std::runtime_error("A jet has zero total pt");
        for (int index = 0; index < count; ++index) {
            extended_weights[index] = event[index].pt / total;
            weights[index] = static_cast<double>(extended_weights[index]);
            if (event[index].pt > 0.0 && extended_weights[index] < 1.0e-280L) extended_mode = true;
            if (event[index].pt == 0.0) {
                weight_logs[index] = -std::numeric_limits<double>::infinity();
            } else if (weights[index] > 0.5) {
                long double remainder = 0.0L;
                for (int other = 0; other < count; ++other) {
                    if (other != index) remainder += event[other].pt;
                }
                weight_logs[index] = static_cast<double>(-std::log1p(remainder / event[index].pt));
            } else {
                weight_logs[index] = static_cast<double>(std::log(event[index].pt / total));
            }
        }
        distance_matrix.resize(static_cast<size_t>(count) * count);
        phi_matrix.resize(static_cast<size_t>(count) * count);
        bearing_matrix.resize(static_cast<size_t>(count) * count);
        for (int special = 0; special < count; ++special) {
            for (int other = 0; other < count; ++other) {
                size_t offset = static_cast<size_t>(special) * count + other;
                double delta_y = event[other].rapidity - event[special].rapidity;
                double delta_phi = event[other].phi - event[special].phi;
                if (!std::isfinite(delta_phi)) {
                    delta_phi = std::fmod(event[other].phi, TWO_PI)
                              - std::fmod(event[special].phi, TWO_PI);
                }
                delta_phi = wrap(delta_phi);
                double radius = std::hypot(delta_y, delta_phi);
                distance_matrix[offset] = radius;
                phi_matrix[offset] = delta_phi;
                bearing_matrix[offset] = radius == 0.0 ? 0.0 : std::atan2(delta_phi, delta_y);
            }
        }
        for (auto& query : queries) {
            if (query.order != 3) continue;
            query.contact_first.resize(count);
            query.contact_repeat.resize(count);
            query.contact_special.resize(count);
            for (int index = 0; index < count; ++index) {
                double weight = weights[index];
                query.contact_first[index] = query.nu1 == 1.0 ? weight : weight_power(index, query.nu1);
                query.contact_repeat[index] = weight_power(index, query.nu1 + query.nu2);
                query.contact_special[index] = weight_power(index, 1.0 + query.nu2);
                query.histogram[query.phi_bins / 2] += weight_power(index, 1.0 + query.nu1 + query.nu2);
            }
        }
    }

    void prepare_special(const std::vector<Particle>& event, int special) {
        int count = static_cast<int>(event.size());
        int remaining = count - 1;
        ranks.clear();
        for (int other = 0; other < count; ++other) {
            if (other != special) ranks.push_back(other);
        }
        const double* distances = distance_matrix.data() + static_cast<size_t>(special) * count;
        std::sort(ranks.begin(), ranks.end(), [&](int left, int right) {
            return distances[left] < distances[right]
                || (distances[left] == distances[right] && left < right);
        });
        radii.resize(remaining);
        ranked_weights.resize(remaining);
        ranked_y.resize(remaining);
        ranked_phi.resize(remaining);
        ranked_bearings.resize(remaining);
        for (int rank = 0; rank < remaining; ++rank) {
            int original = ranks[rank];
            size_t offset = static_cast<size_t>(special) * count + original;
            radii[rank] = distances[original];
            ranked_weights[rank] = weights[original];
            ranked_y[rank] = event[original].rapidity - event[special].rapidity;
            ranked_phi[rank] = phi_matrix[offset];
            ranked_bearings[rank] = bearing_matrix[offset];
        }
        ranked_suffix.resize(remaining + 1);
        ranked_suffix[remaining] = 0.0;
        for (int rank = remaining - 1; rank >= 0; --rank) ranked_suffix[rank] = ranked_suffix[rank + 1] + ranked_weights[rank];
        if (extended_mode) {
            ranked_extended_weights.resize(remaining);
            extended_suffix.resize(remaining + 1);
            extended_suffix[remaining] = 0.0L;
            for (int rank = remaining - 1; rank >= 0; --rank) {
                ranked_extended_weights[rank] = extended_weights[ranks[rank]];
                extended_suffix[rank] = extended_suffix[rank + 1] + ranked_extended_weights[rank];
            }
        }
        size_t pair_count = need_pair_geometry ? static_cast<size_t>(remaining) * (remaining - 1) / 2 : 0;
        ratios.resize(pair_count);
        angles.resize(pair_count);
        for (int outer = 1; need_pair_geometry && outer < remaining; ++outer) {
            size_t offset = static_cast<size_t>(outer) * (outer - 1) / 2;
            for (int inner = 0; inner < outer; ++inner) {
                ratios[offset + inner] = radii[outer] > 0.0 ? radii[inner] / radii[outer] : 0.0;
                double angle = radii[inner] == 0.0 || radii[outer] == 0.0
                    ? 0.0 : wrap(ranked_bearings[inner] - ranked_bearings[outer]);
                angles[offset + inner] = angle;
            }
        }
        first_differences.resize(first_exponents.size());
        for (size_t exponent_index = 0; exponent_index < first_exponents.size(); ++exponent_index) {
            double exponent = first_exponents[exponent_index];
            auto& differences = first_differences[exponent_index];
            differences.resize(remaining);
            double prefix = weights[special];
            double power = weight_power(special, exponent);
            for (int rank = 0; rank < remaining; ++rank) {
                double weight = ranked_weights[rank];
                double next = ranked_suffix[rank + 1] == 0.0 ? 1.0 : std::min(1.0, prefix + weight);
                double next_power = exponent > 1024.0 && next > 0.5
                    ? std::exp(exponent * std::log1p(-std::min(1.0, ranked_suffix[rank + 1])))
                    : std::pow(next, exponent);
                differences[rank] = difference(prefix, weight, exponent, power, next_power);
                prefix = next;
                power = next_power;
            }
        }
    }

    void prepare_group(const Group& group, int special) {
        int remaining = static_cast<int>(ranks.size());
        size_t pair_count = ratios.size();
        cells.resize(pair_count);
        phi_cells.resize(pair_count);
        int cell_count = group.ratio_bins * group.phi_bins;
        unit_tails.assign(static_cast<size_t>(remaining) * cell_count, 0.0);
        tail_indices.clear();
        tail_offsets.resize(remaining + 1);
        tail_offsets[0] = 0;
        if (remaining > 0) tail_offsets[1] = 0;
        double phi_scale = group.phi_bins / TWO_PI;
        for (int outer = 1; outer < remaining; ++outer) {
            size_t offset = static_cast<size_t>(outer) * (outer - 1) / 2;
            double* tail = unit_tails.data() + static_cast<size_t>(outer) * cell_count;
            int inner = 0;
#if defined(ENGINE_VECTOR) && !defined(ENGINE_SCALAR_GEOMETRY)
            for (; inner + 4 <= outer; inner += 4) {
                size_t pair = offset + inner;
                __m256d scaled = _mm256_mul_pd(_mm256_add_pd(_mm256_loadu_pd(angles.data() + pair),
                    _mm256_set1_pd(PI)), _mm256_set1_pd(phi_scale));
                __m256d nearest = _mm256_round_pd(scaled, _MM_FROUND_TO_NEAREST_INT | _MM_FROUND_NO_EXC);
                __m256d distance = _mm256_andnot_pd(_mm256_set1_pd(-0.0), _mm256_sub_pd(scaled, nearest));
                int boundary_mask = _mm256_movemask_pd(_mm256_cmp_pd(distance,
                    _mm256_set1_pd(2.0e-14 * group.phi_bins), _CMP_LT_OQ));
                __m128i phi = _mm_max_epi32(_mm_setzero_si128(), _mm_min_epi32(
                    _mm_set1_epi32(group.phi_bins - 1), _mm256_cvttpd_epi32(scaled)));
                __m256d scaled_ratios = _mm256_mul_pd(_mm256_loadu_pd(ratios.data() + pair),
                    _mm256_set1_pd(group.ratio_bins));
                __m128i ratio = _mm_max_epi32(_mm_setzero_si128(), _mm_min_epi32(
                    _mm_set1_epi32(group.ratio_bins - 1), _mm256_cvttpd_epi32(scaled_ratios)));
                __m128i cell = _mm_add_epi32(_mm_mullo_epi32(ratio, _mm_set1_epi32(group.phi_bins)), phi);
                _mm_storeu_si128(reinterpret_cast<__m128i*>(phi_cells.data() + pair), phi);
                _mm_storeu_si128(reinterpret_cast<__m128i*>(cells.data() + pair), cell);
                while (boundary_mask) {
                    int lane = __builtin_ctz(static_cast<unsigned>(boundary_mask));
                    int corrected = boundary_phi(outer, inner + lane, group.phi_bins);
                    cells[pair + lane] += corrected - phi_cells[pair + lane];
                    phi_cells[pair + lane] = corrected;
                    boundary_mask &= boundary_mask - 1;
                }
            }
#endif
            for (; inner < outer; ++inner) {
                size_t pair = offset + inner;
                double scaled_phi = (angles[pair] + PI) * phi_scale;
                double nearest = std::nearbyint(scaled_phi);
                int phi_cell;
                if (std::abs(scaled_phi - nearest) < 2.0e-14 * group.phi_bins) {
                    phi_cell = boundary_phi(outer, inner, group.phi_bins);
                } else {
                    phi_cell = std::max(0, std::min(group.phi_bins - 1, static_cast<int>(scaled_phi)));
                }
                int ratio_cell = std::max(0, std::min(group.ratio_bins - 1,
                    static_cast<int>(ratios[pair] * group.ratio_bins)));
                phi_cells[pair] = phi_cell;
                cells[pair] = ratio_cell * group.phi_bins + phi_cell;
            }
            for (inner = 0; inner < outer; ++inner) {
                int cell = cells[offset + inner];
                if (ranked_weights[inner] > 0.0) {
                    if (tail[cell] == 0.0) tail_indices.push_back(cell);
                    tail[cell] += ranked_weights[inner];
                }
            }
            tail_offsets[outer + 1] = static_cast<int>(tail_indices.size());
        }
        if (extended_mode) {
            prepare_extended_differences(group, special);
            return;
        }
#ifdef ENGINE_VECTOR
        prepare_vector_differences(group, special);
        return;
#endif
        pair_differences.resize(group.exponents.size());
        for (auto& differences : pair_differences) differences.resize(pair_count);
        prefixes.resize(group.phi_bins);
        prefix_powers.resize(static_cast<size_t>(group.phi_bins) * group.exponents.size());
        for (int outer = 1; outer < remaining && !group.exponents.empty(); ++outer) {
            std::fill(prefixes.begin(), prefixes.end(), 0.0);
            std::fill(prefix_powers.begin(), prefix_powers.end(), 0.0);
            prefixes[group.phi_bins / 2] = weights[special];
            for (size_t exponent = 0; exponent < group.exponents.size(); ++exponent) {
                prefix_powers[exponent * group.phi_bins + group.phi_bins / 2]
                    = std::pow(weights[special], group.exponents[exponent]);
            }
            size_t offset = static_cast<size_t>(outer) * (outer - 1) / 2;
            for (int inner = 0; inner < outer; ++inner) {
                size_t pair = offset + inner;
                int phi_cell = phi_cells[pair];
                double weight = ranked_weights[inner];
                double prefix = prefixes[phi_cell];
                double next = std::min(1.0, prefix + weight);
                double logarithm = group.exponents.size() > 1 ? std::log(next) : 0.0;
                for (size_t exponent = 0; exponent < group.exponents.size(); ++exponent) {
                    size_t power_index = exponent * group.phi_bins + phi_cell;
                    double next_power = group.exponents.size() > 1
                        ? power_from_log(next, logarithm, group.exponents[exponent])
                        : std::pow(next, group.exponents[exponent]);
                    pair_differences[exponent][pair] = difference(prefix, weight,
                        group.exponents[exponent], prefix_powers[power_index], next_power);
                    prefix_powers[power_index] = next_power;
                }
                prefixes[phi_cell] = next;
            }
        }
        tail_differences.resize(group.tail_exponents.size());
        for (auto& differences : tail_differences) differences.assign(unit_tails.size(), 0.0);
        prefix_powers.resize(static_cast<size_t>(group.phi_bins) * group.tail_exponents.size());
        for (int outer = 1; outer < remaining && !group.tail_exponents.empty(); ++outer) {
            std::fill(prefixes.begin(), prefixes.end(), 0.0);
            std::fill(prefix_powers.begin(), prefix_powers.end(), 0.0);
            prefixes[group.phi_bins / 2] = weights[special];
            for (size_t exponent = 0; exponent < group.tail_exponents.size(); ++exponent) {
                prefix_powers[exponent * group.phi_bins + group.phi_bins / 2]
                    = std::pow(weights[special], group.tail_exponents[exponent]);
            }
            size_t offset = static_cast<size_t>(outer) * cell_count;
            for (int position = tail_offsets[outer]; position < tail_offsets[outer + 1]; ++position) {
                int cell = tail_indices[position];
                int phi_cell = cell % group.phi_bins;
                double weight = unit_tails[offset + cell];
                double prefix = prefixes[phi_cell];
                double next = std::min(1.0, prefix + weight);
                double logarithm = group.tail_exponents.size() > 1 ? std::log(next) : 0.0;
                for (size_t exponent = 0; exponent < group.tail_exponents.size(); ++exponent) {
                    size_t power_index = exponent * group.phi_bins + phi_cell;
                    double next_power = group.tail_exponents.size() > 1
                        ? power_from_log(next, logarithm, group.tail_exponents[exponent])
                        : std::pow(next, group.tail_exponents[exponent]);
                    tail_differences[exponent][offset + cell] = difference(prefix, weight,
                        group.tail_exponents[exponent], prefix_powers[power_index], next_power);
                    prefix_powers[power_index] = next_power;
                }
                prefixes[phi_cell] = next;
            }
        }
    }

    void accumulate_projected(Query& query, int special) {
        int remaining = static_cast<int>(ranks.size());
        if (query.order == 4 && remaining < 3) return;
        const double* first = query.first_exponent < 0 ? ranked_weights.data()
            : first_differences[query.first_exponent].data();
        const double* second = query.projected_second < 0 ? ranked_weights.data()
            : first_differences[query.projected_second].data();
        double special_weight = weights[special];
        double tail_exponent = query.order == 3 ? query.nu2 : query.nu3;
        double initial_power = weight_power(special, tail_exponent);
        double prefix = 0.0;
        double cumulative_middle = 0.0;
        for (int outer = 0; outer < remaining; ++outer) {
            int radial = radial_bin(radii[outer], query);
            double tail = prefix;
            if (tail_exponent != 1.0 && prefix > 0.0) {
                double upper = std::min(1.0, special_weight + prefix);
                double upper_power = tail_exponent > 1024.0 && upper > 0.5
                    ? std::exp(tail_exponent * std::log1p(-std::min(1.0, ranked_suffix[outer])))
                    : std::pow(upper, tail_exponent);
                tail = difference(special_weight, prefix, tail_exponent, initial_power, upper_power);
            }
            if (query.order == 3) {
                int original = ranks[outer];
                query.histogram[radial] += 2.0 * query.contact_special[special] * query.contact_first[original]
                    + special_weight * query.contact_repeat[original]
                    + 2.0 * special_weight * first[outer] * tail;
            } else {
                query.histogram[radial] += 6.0 * special_weight * first[outer] * cumulative_middle;
                cumulative_middle += second[outer] * tail;
            }
            prefix += ranked_weights[outer];
        }
    }

    void accumulate(Query& query, int special) {
        int remaining = static_cast<int>(ranks.size());
        int cell_count = query.ratio_bins * query.phi_bins;
        const double* first = query.first_exponent < 0 ? ranked_weights.data()
            : first_differences[query.first_exponent].data();
        const double* second = query.second_exponent < 0 ? nullptr
            : pair_differences[query.second_exponent].data();
        const double* tails = query.tail_exponent < 0 ? unit_tails.data()
            : tail_differences[query.tail_exponent].data();
        radial_cells.resize(remaining);
        for (int rank = 0; rank < remaining; ++rank) radial_cells[rank] = radial_bin(radii[rank], query);
        double special_weight = weights[special];
        if (query.order == 3) {
            int zero_phi = query.phi_bins / 2;
            for (int outer = 0; outer < remaining; ++outer) {
                size_t row = static_cast<size_t>(radial_cells[outer]) * cell_count;
                int original = ranks[outer];
                query.histogram[row + zero_phi] += 2.0 * query.contact_special[special]
                    * query.contact_first[original];
                query.histogram[row + (query.ratio_bins - 1) * query.phi_bins + zero_phi]
                    += special_weight * query.contact_repeat[original];
                double factor = 2.0 * special_weight * first[outer];
                size_t offset = static_cast<size_t>(outer) * cell_count;
                for (int position = tail_offsets[outer]; position < tail_offsets[outer + 1]; ++position) {
                    int cell = tail_indices[position];
                    query.histogram[row + cell] += factor * tails[offset + cell];
                }
            }
            return;
        }
        if (remaining < 3) return;
        for (int outer = 2; outer < remaining; ++outer) {
            double factor = 6.0 * special_weight * first[outer];
            size_t offset = static_cast<size_t>(outer) * (outer - 1) / 2;
            size_t base = static_cast<size_t>(radial_cells[outer]) * cell_count * cell_count;
            for (int middle = 1; middle < outer; ++middle) {
                int tail_begin = tail_offsets[middle];
                int tail_end = tail_offsets[middle + 1];
                double value = factor * (second ? second[offset + middle] : ranked_weights[middle]);
                const double* __restrict tail = tails + static_cast<size_t>(middle) * cell_count;
                double* __restrict destination = query.histogram.data() + base
                    + static_cast<size_t>(cells[offset + middle]) * cell_count;
                if (cell_count <= 64 || (tail_end - tail_begin) * DENSE_FACTOR >= cell_count) {
                    for (int cell = 0; cell < cell_count; ++cell) destination[cell] += value * tail[cell];
                } else {
                    for (int position = tail_begin; position < tail_end; ++position) {
                        int cell = tail_indices[position];
                        destination[cell] += value * tail[cell];
                    }
                }
            }
        }
    }

public:
    long long requested_events;

#ifdef ENGINE_PROFILE
    ~Engine() {
        std::cerr << "geometry " << timings[0] << " special " << timings[1]
                  << " group " << timings[2] << " third " << timings[3]
                  << " fourth " << timings[4] << '\n';
    }
#endif

    Engine() {
        int query_count;
        if (!(std::cin >> requested_events >> query_count) || requested_events <= 0 || query_count < 0) {
            throw std::runtime_error("Invalid configuration");
        }
        queries.resize(query_count);
        for (int query_index = 0; query_index < query_count; ++query_index) {
            Query& query = queries[query_index];
            if (!(std::cin >> query.order >> query.log_min >> query.bins >> query.ratio_bins
                  >> query.phi_bins >> query.nu1 >> query.nu2 >> query.nu3)) {
                throw std::runtime_error("Invalid query configuration");
            }
            query.radial_min = std::pow(10.0, query.log_min);
            query.radial_scale = (query.bins - 2) / -query.log_min;
            size_t cell_count = static_cast<size_t>(query.ratio_bins) * query.phi_bins;
            size_t size = static_cast<size_t>(query.bins) * cell_count;
            if (query.order == 4) size *= cell_count;
            query.histogram.assign(size, 0.0);
            query.first_exponent = exponent_index(first_exponents, query.nu1);
            query.projected_second = -1;
            if (query.ratio_bins == 1 && query.phi_bins == 1) {
                if (query.order == 4) query.projected_second = exponent_index(first_exponents, query.nu2);
            } else {
                need_pair_geometry = true;
            }
            int group_index = 0;
            for (; group_index < static_cast<int>(groups.size()); ++group_index) {
                if (groups[group_index].ratio_bins == query.ratio_bins
                    && groups[group_index].phi_bins == query.phi_bins) break;
            }
            if (group_index == static_cast<int>(groups.size())) {
                groups.push_back(Group{query.ratio_bins, query.phi_bins, {}, {}, {}});
            }
            Group& group = groups[group_index];
            group.queries.push_back(query_index);
            query.second_exponent = query.order == 4 ? exponent_index(group.exponents, query.nu2) : -1;
            query.tail_exponent = exponent_index(group.tail_exponents, query.order == 4 ? query.nu3 : query.nu2);
        }
    }

    void process(const std::vector<Particle>& event) {
        if (event.empty()) throw std::runtime_error("Empty jet");
#ifdef ENGINE_PROFILE
        auto start = std::chrono::steady_clock::now();
#endif
        prepare_geometry(event);
#ifdef ENGINE_PROFILE
        timings[0] += std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
#endif
        for (int special = 0; special < static_cast<int>(event.size()); ++special) {
            if (weights[special] == 0.0) continue;
#ifdef ENGINE_PROFILE
            start = std::chrono::steady_clock::now();
#endif
            prepare_special(event, special);
#ifdef ENGINE_PROFILE
            timings[1] += std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
#endif
            for (const auto& group : groups) {
#ifdef ENGINE_PROFILE
                start = std::chrono::steady_clock::now();
#endif
                bool projected = group.ratio_bins == 1 && group.phi_bins == 1;
                if (!projected) prepare_group(group, special);
#ifdef ENGINE_PROFILE
                timings[2] += std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
#endif
                for (int query : group.queries) {
#ifdef ENGINE_PROFILE
                    start = std::chrono::steady_clock::now();
#endif
                    if (projected) accumulate_projected(queries[query], special);
                    else accumulate(queries[query], special);
#ifdef ENGINE_PROFILE
                    timings[queries[query].order] += std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
#endif
                }
            }
        }
    }

    void write(const char* filename) {
        std::ofstream output(filename, std::ios::binary);
        if (!output) throw std::runtime_error("Cannot open output");
        for (auto& query : queries) {
            for (double& value : query.histogram) {
                value /= requested_events;
                if (!std::isfinite(value)) throw std::runtime_error("Nonfinite histogram entry");
            }
            output.write(reinterpret_cast<const char*>(query.histogram.data()),
                         query.histogram.size() * sizeof(double));
        }
        if (!output) throw std::runtime_error("Failed writing output");
    }
};

int main(int argc, char** argv) {
    try {
        if (argc != 3) throw std::runtime_error("Usage: engine events_file binary_output");
        Engine engine;
        FILE* input = std::fopen(argv[1], "r");
        if (!input) throw std::runtime_error("Cannot open events file");
        std::vector<Particle> event;
        char* line = nullptr;
        size_t capacity = 0;
        long long current_id = -1;
        long long processed = 0;
        while (getline(&line, &capacity, input) >= 0) {
            char* cursor = line;
            while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r' || *cursor == '\n') ++cursor;
            if (*cursor == '\0') continue;
            char* end;
            long long event_id = std::strtoll(cursor, &end, 10);
            if (end == cursor || event_id < 0) throw std::runtime_error("Invalid event ID");
            cursor = end;
            if (event_id != current_id && current_id >= 0) {
                if (event_id <= current_id) throw std::runtime_error("Event IDs must increase");
                engine.process(event);
                event.clear();
                ++processed;
                if (processed == engine.requested_events) break;
            }
            current_id = event_id;
            Particle particle;
            particle.pt = std::strtod(cursor, &end);
            if (end == cursor) throw std::runtime_error("Missing pt");
            cursor = end;
            particle.rapidity = std::strtod(cursor, &end);
            if (end == cursor) throw std::runtime_error("Missing rapidity");
            cursor = end;
            particle.phi = std::strtod(cursor, &end);
            if (end == cursor) throw std::runtime_error("Missing phi");
            if (!std::isfinite(particle.pt) || particle.pt < 0.0
                || !std::isfinite(particle.rapidity) || !std::isfinite(particle.phi)) {
                throw std::runtime_error("Invalid particle data");
            }
            event.push_back(particle);
        }
        if (processed < engine.requested_events && !event.empty()) {
            engine.process(event);
            ++processed;
        }
        std::free(line);
        std::fclose(input);
        if (processed != engine.requested_events) throw std::runtime_error("Fewer jets than requested");
        engine.write(argv[2]);
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
