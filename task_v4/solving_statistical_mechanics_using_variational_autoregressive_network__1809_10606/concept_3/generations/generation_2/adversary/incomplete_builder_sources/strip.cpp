#include <algorithm>
#include <cmath>
#include <cstring>

extern "C" double strip_partition(const double* values, const double* signs, double beta, double* gradient, double* output_marginals) {
    double couplings[172];
    for (int edge = 0; edge < 172; ++edge) couplings[edge] = values[edge] * signs[edge];
    double unary[12][256];
    double forward[12][256];
    double stages[11][9][256];
    double marginals[12][256];
    double same[11][8];
    double different[11][8];
    double shifts[12];
    for (int column = 0; column < 12; ++column) {
        shifts[column] = -1e100;
        for (int state = 0; state < 256; ++state) {
            double energy = 0;
            for (int row = 0; row < 8; ++row) {
                const int spin = 2 * ((state >> row) & 1) - 1;
                energy += values[172 + column * 8 + row] * spin;
                if (row < 7) energy += couplings[column * 7 + row] * spin * (2 * ((state >> (row + 1)) & 1) - 1);
            }
            unary[column][state] = beta * energy;
            shifts[column] = std::max(shifts[column], beta * energy);
        }
        for (int state = 0; state < 256; ++state) unary[column][state] = std::exp(unary[column][state] - shifts[column]);
        if (column < 11) {
            for (int row = 0; row < 8; ++row) {
                same[column][row] = std::exp(beta * couplings[84 + column * 8 + row]);
                different[column][row] = 1 / same[column][row];
            }
        }
    }
    double normalization = 0;
    for (int state = 0; state < 256; ++state) normalization += unary[0][state];
    for (int state = 0; state < 256; ++state) forward[0][state] = unary[0][state] / normalization;
    double log_partition = std::log(normalization) + shifts[0];
    for (int column = 1; column < 12; ++column) {
        std::memcpy(stages[column - 1][0], forward[column - 1], 256 * sizeof(double));
        for (int row = 0; row < 8; ++row) {
            const int stride = 1 << row;
            for (int base = 0; base < 256; base += 2 * stride) {
                for (int offset = 0; offset < stride; ++offset) {
                    const int negative = base + offset;
                    const int positive = negative + stride;
                    stages[column - 1][row + 1][negative] = same[column - 1][row] * stages[column - 1][row][negative] + different[column - 1][row] * stages[column - 1][row][positive];
                    stages[column - 1][row + 1][positive] = different[column - 1][row] * stages[column - 1][row][negative] + same[column - 1][row] * stages[column - 1][row][positive];
                }
            }
        }
        normalization = 0;
        for (int state = 0; state < 256; ++state) {
            forward[column][state] = unary[column][state] * stages[column - 1][8][state];
            normalization += forward[column][state];
        }
        for (int state = 0; state < 256; ++state) forward[column][state] /= normalization;
        log_partition += std::log(normalization) + shifts[column];
    }
    if (!gradient && !output_marginals) return log_partition;
    std::memcpy(marginals[11], forward[11], 256 * sizeof(double));
    double backward[256];
    std::fill(backward, backward + 256, 1.0);
    double horizontal_moments[11][8];
    for (int column = 10; column >= 0; --column) {
        double sensitivity[256];
        normalization = 0;
        for (int state = 0; state < 256; ++state) {
            sensitivity[state] = unary[column + 1][state] * backward[state];
            normalization += stages[column][8][state] * sensitivity[state];
        }
        for (int state = 0; state < 256; ++state) sensitivity[state] /= normalization;
        for (int row = 7; row >= 0; --row) {
            const int stride = 1 << row;
            double moment = 0;
            for (int base = 0; base < 256; base += 2 * stride) {
                for (int offset = 0; offset < stride; ++offset) {
                    const int negative = base + offset;
                    const int positive = negative + stride;
                    const double negative_sensitivity = sensitivity[negative];
                    const double positive_sensitivity = sensitivity[positive];
                    moment += same[column][row] * (negative_sensitivity * stages[column][row][negative] + positive_sensitivity * stages[column][row][positive]) - different[column][row] * (negative_sensitivity * stages[column][row][positive] + positive_sensitivity * stages[column][row][negative]);
                    sensitivity[negative] = same[column][row] * negative_sensitivity + different[column][row] * positive_sensitivity;
                    sensitivity[positive] = different[column][row] * negative_sensitivity + same[column][row] * positive_sensitivity;
                }
            }
            horizontal_moments[column][row] = moment;
        }
        const double largest = *std::max_element(sensitivity, sensitivity + 256);
        normalization = 0;
        for (int state = 0; state < 256; ++state) {
            backward[state] = sensitivity[state] / largest;
            marginals[column][state] = forward[column][state] * backward[state];
            normalization += marginals[column][state];
        }
        for (int state = 0; state < 256; ++state) marginals[column][state] /= normalization;
    }
    if (output_marginals) std::memcpy(output_marginals, marginals, 12 * 256 * sizeof(double));
    if (gradient) {
        std::fill(gradient, gradient + 268, 0.0);
        for (int column = 0; column < 12; ++column) {
            for (int state = 0; state < 256; ++state) {
                for (int row = 0; row < 8; ++row) {
                    const int spin = 2 * ((state >> row) & 1) - 1;
                    gradient[172 + column * 8 + row] += beta * marginals[column][state] * spin;
                    if (row < 7) gradient[column * 7 + row] += beta * marginals[column][state] * spin * (2 * ((state >> (row + 1)) & 1) - 1);
                }
            }
        }
        for (int column = 0; column < 11; ++column) {
            for (int row = 0; row < 8; ++row) gradient[84 + column * 8 + row] = beta * horizontal_moments[column][row];
        }
        for (int edge = 0; edge < 172; ++edge) gradient[edge] *= signs[edge];
    }
    return log_partition;
}
