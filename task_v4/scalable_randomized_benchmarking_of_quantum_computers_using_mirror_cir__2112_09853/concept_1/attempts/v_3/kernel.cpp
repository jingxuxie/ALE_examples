#include <cmath>
#include <algorithm>
#include <cstring>

static int permutations[32][255];
static int inverse_rows[32];
static int offsets[33];
static double characters[192][255];

extern "C" void initialize(const int *permutation_data, const int *inverse_data,
                           const int *offset_data, const double *character_data) {
    std::memcpy(permutations, permutation_data, sizeof(permutations));
    std::memcpy(inverse_rows, inverse_data, sizeof(inverse_rows));
    std::memcpy(offsets, offset_data, sizeof(offsets));
    std::memcpy(characters, character_data, sizeof(characters));
}

extern "C" void compute(const double *counts, double *signal, double *gradient,
                        double *metrics, int need_gradient) {
    double eigenvalues[32][255];
    double weights[32][255];
    double vectors[129][255];
    for (int layer = 0; layer < 32; ++layer) {
        for (int label = 0; label < 255; ++label) {
            double value = 0.98;
            for (int entry = offsets[layer]; entry < offsets[layer + 1]; ++entry)
                value += counts[entry] * characters[entry][label];
            eigenvalues[layer][label] = value;
        }
    }
    for (int layer = 0; layer < 32; ++layer)
        for (int label = 0; label < 255; ++label)
            weights[layer][label] = (layer < 24 ? 0.025 : 0.05)
                * eigenvalues[inverse_rows[layer]][label]
                * eigenvalues[layer][permutations[layer][label]];
    std::fill(vectors[0], vectors[0] + 255, 1.0);
    signal[0] = 1.0;
    for (int depth = 1; depth < 129; ++depth) {
        std::fill(vectors[depth], vectors[depth] + 255, 0.0);
        for (int layer = 0; layer < 32; ++layer)
            for (int label = 0; label < 255; ++label)
                vectors[depth][label] += weights[layer][label]
                    * vectors[depth - 1][permutations[layer][label]];
        double total = 0.0;
        for (int label = 0; label < 255; ++label) total += vectors[depth][label];
        signal[depth] = total / 255.0;
    }
    double decay = 0.020;
    double amplitude, denominator, shape[129], moment_zero, moment_one;
    for (int iteration = 0; iteration < 15; ++iteration) {
        moment_zero = 0.0;
        moment_one = 0.0;
        double moment_two = 0.0, data_zero = 0.0, data_one = 0.0, data_two = 0.0;
        for (int depth = 0; depth < 129; ++depth) {
            double distance = 2.0 * depth;
            shape[depth] = std::exp(-decay * distance);
            double squared = shape[depth] * shape[depth];
            moment_zero += squared;
            moment_one -= distance * squared;
            moment_two += distance * distance * squared;
            data_zero += shape[depth] * signal[depth];
            data_one -= distance * shape[depth] * signal[depth];
            data_two += distance * distance * shape[depth] * signal[depth];
        }
        amplitude = data_zero / moment_zero;
        denominator = 2 * amplitude * moment_two - data_two
            - amplitude * moment_one * moment_one / moment_zero;
        double step = (amplitude * moment_one - data_one) / denominator;
        if (std::abs(step) < 1e-15) break;
        decay -= std::clamp(step, -0.002, 0.002);
    }
    double residual = 0.0;
    for (int depth = 0; depth < 129; ++depth)
        residual = std::max(residual, std::abs(amplitude * shape[depth] - signal[depth]));
    metrics[0] = 1 + (255.0 / 256.0 / 0.02) * std::expm1(-decay);
    metrics[1] = residual;
    metrics[2] = amplitude;
    metrics[3] = decay;
    if (!need_gradient) return;
    double signal_gradient[129];
    for (int depth = 0; depth < 129; ++depth)
        signal_gradient[depth] = -(255.0 / 256.0 / 0.02) * std::exp(-decay)
            * shape[depth] * (-2.0 * depth - moment_one / moment_zero) / denominator;
    double weight_gradient[32][255] = {};
    double adjoint[255] = {};
    for (int depth = 128; depth > 0; --depth) {
        for (int label = 0; label < 255; ++label)
            adjoint[label] += signal_gradient[depth] / 255.0;
        double next_adjoint[255] = {};
        for (int layer = 0; layer < 32; ++layer)
            for (int label = 0; label < 255; ++label) {
                int transformed = permutations[layer][label];
                weight_gradient[layer][label] += adjoint[label] * vectors[depth - 1][transformed];
                next_adjoint[transformed] += adjoint[label] * weights[layer][label];
            }
        std::copy(next_adjoint, next_adjoint + 255, adjoint);
    }
    double eigen_gradient[32][255] = {};
    for (int layer = 0; layer < 32; ++layer)
        for (int label = 0; label < 255; ++label) {
            int transformed = permutations[layer][label];
            double value = weight_gradient[layer][label] * (layer < 24 ? 0.025 : 0.05);
            eigen_gradient[inverse_rows[layer]][label] += value * eigenvalues[layer][transformed];
            eigen_gradient[layer][transformed] += value * eigenvalues[inverse_rows[layer]][label];
        }
    std::fill(gradient, gradient + 192, 0.0);
    for (int layer = 0; layer < 32; ++layer)
        for (int entry = offsets[layer]; entry < offsets[layer + 1]; ++entry)
            for (int label = 0; label < 255; ++label)
                gradient[entry] += eigen_gradient[layer][label] * characters[entry][label];
}
