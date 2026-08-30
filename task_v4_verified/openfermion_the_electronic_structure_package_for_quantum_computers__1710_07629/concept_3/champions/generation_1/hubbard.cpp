#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>

struct SpinBasis {
    int size;
    std::vector<int> states, lookup, offsets, columns;
    std::vector<float> values, potential;
    SpinBasis(int sites, int particles, const double* hopping, const double* onsite) {
        lookup.resize(1 << sites, -1);
        for (int mask = 0; mask < (1 << sites); ++mask) {
            if (__builtin_popcount((unsigned)mask) == particles) {
                lookup[mask] = states.size();
                states.push_back(mask);
            }
        }
        size = states.size();
        offsets.push_back(0);
        for (int mask : states) {
            float diagonal = 0;
            for (int site = 0; site < sites; ++site) {
                if ((mask >> site) & 1) diagonal += onsite[site];
                for (int other = 0; other < site; ++other) {
                    if (hopping[site * sites + other] == 0) continue;
                    if (((mask >> site) ^ (mask >> other)) & 1) {
                        int between = mask & (((1 << site) - 1) ^ ((1 << (other + 1)) - 1));
                        float sign = (__builtin_popcount((unsigned)between) & 1) ? 1.0f : -1.0f;
                        columns.push_back(lookup[mask ^ (1 << site) ^ (1 << other)]);
                        values.push_back(sign * hopping[site * sites + other]);
                    }
                }
            }
            potential.push_back(diagonal);
            offsets.push_back(columns.size());
        }
    }
};

static void transpose(const float* source, float* target, int rows, int cols) {
    for (int first = 0; first < rows; first += 16) {
        for (int second = 0; second < cols; second += 16) {
            for (int row = first; row < std::min(first + 16, rows); ++row) {
                for (int col = second; col < std::min(second + 16, cols); ++col) {
                    target[col * rows + row] = source[row * cols + col];
                }
            }
        }
    }
}

static void sparse_product(const SpinBasis& basis, const float* source, float* target, int width) {
    for (int row = 0; row < basis.size; ++row) {
        float* destination = target + row * width;
        for (int index = basis.offsets[row]; index < basis.offsets[row + 1]; ++index) {
            const float* input = source + basis.columns[index] * width;
            float value = basis.values[index];
            for (int col = 0; col < width; ++col) destination[col] += value * input[col];
        }
    }
}

static double smallest(const std::vector<double>& diagonal, const std::vector<double>& offdiag) {
    double lower = diagonal[0], upper = diagonal[0];
    int count = diagonal.size();
    for (int index = 0; index < count; ++index) {
        double radius = (index ? offdiag[index - 1] : 0) + (index + 1 < count ? offdiag[index] : 0);
        lower = std::min(lower, diagonal[index] - radius);
        upper = std::max(upper, diagonal[index] + radius);
    }
    for (int iteration = 0; iteration < 45; ++iteration) {
        double middle = (lower + upper) * 0.5;
        double pivot = diagonal[0] - middle;
        int negative = (pivot < 0);
        for (int index = 1; index < count; ++index) {
            if (std::abs(pivot) < 1e-20) pivot = -1e-20;
            pivot = diagonal[index] - middle - offdiag[index - 1] * offdiag[index - 1] / pivot;
            negative += (pivot < 0);
        }
        if (negative) upper = middle; else lower = middle;
    }
    return (lower + upper) * 0.5;
}

static double energy(int sites, int up, int down, const double* hopping, const double* interaction,
                     const double* potential, const double* trial_up, const double* trial_down,
                     int steps, double tolerance, double* history) {
    SpinBasis first(sites, up, hopping, potential), second(sites, down, hopping, potential);
    bool symmetric = up == down && trial_up && trial_up == trial_down;
    int dimension = first.size * second.size;
    std::vector<float> diagonal(dimension), current(dimension), previous(dimension, 0), result(dimension);
    std::vector<float> transposed(dimension), product(dimension);
    std::vector<double> interaction_sum(1 << sites, 0);
    for (int mask = 1; mask < (1 << sites); ++mask) {
        int site = __builtin_ctz((unsigned)mask);
        interaction_sum[mask] = interaction_sum[mask ^ (1 << site)] + interaction[site];
    }
    double norm = 0;
    uint64_t random_state = 317;
    for (int row = 0; row < first.size; ++row) {
        for (int col = 0; col < second.size; ++col) {
            int index = row * second.size + col;
            int doubles = first.states[row] & second.states[col];
            diagonal[index] = first.potential[row] + second.potential[col] + interaction_sum[doubles];
            if (trial_up && trial_down) {
                current[index] = trial_up[row] * trial_down[col] * std::exp(-0.15 * interaction_sum[doubles]);
            } else {
                random_state ^= random_state << 13;
                random_state ^= random_state >> 7;
                random_state ^= random_state << 17;
                current[index] = float(int(random_state & 65535) - 32768) / 32768;
            }
            norm += double(current[index]) * current[index];
        }
    }
    float scale = 1 / std::sqrt(norm);
    for (int index = 0; index < dimension; ++index) current[index] *= scale;
    std::vector<double> alphas, betas;
    double last = 1e100, estimate = last;
    float beta = 0;
    for (int iteration = 0; iteration < steps; ++iteration) {
        for (int index = 0; index < dimension; ++index) {
            result[index] = diagonal[index] * current[index] - beta * previous[index];
        }
        if (symmetric) {
            std::fill(product.begin(), product.end(), 0);
            sparse_product(first, current.data(), product.data(), second.size);
            transpose(product.data(), transposed.data(), first.size, second.size);
            for (int index = 0; index < dimension; ++index) transposed[index] += product[index];
        } else {
            sparse_product(first, current.data(), result.data(), second.size);
            transpose(current.data(), transposed.data(), first.size, second.size);
            std::fill(product.begin(), product.end(), 0);
            sparse_product(second, transposed.data(), product.data(), first.size);
            transpose(product.data(), transposed.data(), second.size, first.size);
        }
        double alpha_sum = 0;
        for (int index = 0; index < dimension; ++index) {
            result[index] += transposed[index];
            alpha_sum += double(current[index]) * result[index];
        }
        float alpha = alpha_sum;
        norm = 0;
        for (int index = 0; index < dimension; ++index) {
            result[index] -= alpha * current[index];
            norm += double(result[index]) * result[index];
        }
        alphas.push_back(alpha_sum);
        beta = std::sqrt(norm);
        if (beta < 1e-7f) {
            estimate = smallest(alphas, betas);
            if (history) history[iteration] = estimate;
            break;
        }
        if (iteration >= 9 && (iteration % 5 == 4 || iteration + 1 == steps)) {
            estimate = smallest(alphas, betas);
            if (history) history[iteration] = estimate;
            if (last - estimate < tolerance) break;
            last = estimate;
        }
        betas.push_back(beta);
        scale = 1 / beta;
        for (int index = 0; index < dimension; ++index) {
            previous[index] = current[index];
            current[index] = result[index] * scale;
        }
    }
    return estimate;
}

extern "C" double ground_energy(int sites, int up, int down, const double* hopping,
                                const double* interaction, const double* potential,
                                const double* trial_up, const double* trial_down,
                                int steps, double tolerance, double* history) {
    return energy(sites, up, down, hopping, interaction, potential, trial_up, trial_down,
                  steps, tolerance, history);
}
