#include <algorithm>
#include <cstring>
#include <cmath>
#include <random>

extern "C" void forward(const double* weights, const int* permutations, double* vectors, double* signal) {
    std::fill(vectors, vectors + 255, 1.0);
    signal[0] = 1.0;
    for (int depth = 1; depth <= 128; ++depth) {
        double* current = vectors + depth * 255;
        const double* previous = current - 255;
        std::fill(current, current + 255, 0.0);
        for (int layer = 0; layer < 32; ++layer) {
            for (int pauli = 0; pauli < 255; ++pauli) {
                int index = layer * 255 + pauli;
                current[pauli] += weights[index] * previous[permutations[index]];
            }
        }
        double total = 0.0;
        for (int pauli = 0; pauli < 255; ++pauli) total += current[pauli];
        signal[depth] = total / 255.0;
    }
}

extern "C" void backward(const double* weights, const int* permutations, const double* vectors,
                         const double* signal_gradient, double* weight_gradient) {
    double adjoint[255] = {};
    double previous[255];
    std::fill(weight_gradient, weight_gradient + 32 * 255, 0.0);
    for (int depth = 128; depth >= 1; --depth) {
        for (int pauli = 0; pauli < 255; ++pauli) adjoint[pauli] += signal_gradient[depth] / 255.0;
        std::fill(previous, previous + 255, 0.0);
        for (int layer = 0; layer < 32; ++layer) {
            for (int pauli = 0; pauli < 255; ++pauli) {
                int index = layer * 255 + pauli;
                int transformed = permutations[index];
                weight_gradient[index] += adjoint[pauli] * vectors[(depth - 1) * 255 + transformed];
                previous[transformed] += adjoint[pauli] * weights[index];
            }
        }
        std::memcpy(adjoint, previous, sizeof(adjoint));
    }
}

extern "C" int repair(int* counts, const double* target, const int* lower, const int* upper,
                      const int* partner, const int* cycles, int cycle_count, int cycle_width, int iterations,
                      int seed, double distance_weight, int* statistics) {
    std::mt19937 random(seed);
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    int overlaps[2] = {};
    for (int index = 0; index < 192; ++index) overlaps[index >= 72] += counts[index] * counts[partner[index]];
    int best[192];
    double best_distance = 1e100;
    int solutions = 0;
    for (int iteration = 0; iteration < iterations; ++iteration) {
        const int* cycle = cycles + cycle_width * (random() % cycle_count);
        int length = cycle[0];
        int indices[192];
        bool single_only = true;
        for (int entry = 0; entry < length; ++entry) {
            indices[entry] = std::abs(cycle[entry + 1]) - 1;
            if (indices[entry] >= 72) single_only = false;
        }
        int direction = (random() & 1) ? 1 : -1;
        int changes[192];
        bool allowed = true;
        for (int entry = 0; entry < length; ++entry) {
            int index = indices[entry];
            int sign = cycle[entry + 1] > 0 ? 1 : -1;
            changes[entry] = direction * sign * (index < 72 && !single_only ? 2 : 1);
            int value = counts[index] + changes[entry];
            if (value < lower[index] || value > upper[index]) allowed = false;
        }
        if (!allowed) continue;
        int delta[2] = {};
        double delta_distance = 0.0;
        for (int entry = 0; entry < length; ++entry) {
            int index = indices[entry];
            int family = index >= 72;
            delta[family] += 2 * changes[entry] * counts[partner[index]];
            for (int other = 0; other < length; ++other) {
                if (indices[other] == partner[index]) delta[family] += changes[entry] * changes[other];
            }
            delta_distance += (2 * (counts[index] - target[index]) + changes[entry]) * changes[entry]
                              / (index < 72 ? 4.0 : 1.0);
        }
        double phase = static_cast<double>(iteration % 200000) / 200000.0;
        double temperature = 0.05 + 15.0 * std::pow(1.0 - phase, 3);
        double penalty_change = (2.0 * overlaps[0] + delta[0]) * delta[0] / 64.0
                              + (2.0 * overlaps[1] + delta[1]) * delta[1] / 4.0;
        double energy_change = penalty_change + distance_weight * delta_distance;
        if (energy_change <= 0.0 || uniform(random) < std::exp(-energy_change / temperature)) {
            for (int entry = 0; entry < length; ++entry) counts[indices[entry]] += changes[entry];
            overlaps[0] += delta[0];
            overlaps[1] += delta[1];
            if (overlaps[0] == 0 && overlaps[1] == 0) {
                ++solutions;
                double distance = 0.0;
                for (int index = 0; index < 192; ++index) {
                    double difference = counts[index] - target[index];
                    distance += difference * difference / (index < 72 ? 4.0 : 1.0);
                }
                if (distance < best_distance) {
                    best_distance = distance;
                    std::memcpy(best, counts, sizeof(best));
                }
            }
        }
    }
    statistics[0] = overlaps[0];
    statistics[1] = overlaps[1];
    statistics[2] = solutions;
    if (solutions) std::memcpy(counts, best, sizeof(best));
    return solutions;
}
