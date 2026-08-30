#include <cmath>
#include <vector>
#include <algorithm>

static std::vector<double> probabilities(32768), rewards(32768), log_probabilities(32768);
static std::vector<double> residuals(32768 * 16);
static double cached_mean_reward;

extern "C" void evaluate_fast(const double *weights, const double *potential,
                              const double *sector, double *metrics,
                              double *derivatives) {
    const int count = 32768;
    double mean_reward = 0, mean_potential = 0, entropy = 0, sector_mass = 0;
    for (int state = 0; state < count; ++state) {
        double spins[16];
        spins[0] = 1;
        for (int row = 1; row < 16; ++row) spins[row] = 2 * ((state >> (row - 1)) & 1) - 1;
        double log_probability = -std::log(2.0);
        int coordinate = 0;
        for (int row = 1; row < 16; ++row) {
            double logit = 0;
            for (int column = 0; column < row; ++column) logit += weights[coordinate++] * spins[column];
            double aligned = logit * spins[row];
            log_probability -= std::max(0.0, -aligned) + std::log1p(std::exp(-std::abs(aligned)));
            residuals[state * 16 + row] = (spins[row] + 1) * .5 - 1 / (1 + std::exp(-logit));
        }
        double probability = 2 * std::exp(log_probability);
        double reward = potential[state] + log_probability;
        probabilities[state] = probability;
        rewards[state] = reward;
        log_probabilities[state] = log_probability;
        mean_reward += probability * reward;
        mean_potential += probability * potential[state];
        entropy -= probability * log_probability;
        sector_mass += probability * sector[state];
    }
    double variance = 0;
    std::fill(derivatives, derivatives + 5 * 120, 0);
    for (int state = 0; state < count; ++state) {
        double centered = rewards[state] - mean_reward;
        double probability = probabilities[state];
        variance += probability * centered * centered;
        double factors[5] = {probability * centered,
                             probability * (centered * centered + 2 * centered),
                             probability * (potential[state] - mean_potential),
                             -probability * (log_probabilities[state] + entropy),
                             probability * (sector[state] - sector_mass)};
        double spins[16];
        spins[0] = 1;
        for (int row = 1; row < 16; ++row) spins[row] = 2 * ((state >> (row - 1)) & 1) - 1;
        int coordinate = 0;
        for (int row = 1; row < 16; ++row) {
            double terms[5];
            for (int metric = 0; metric < 5; ++metric) terms[metric] = factors[metric] * residuals[state * 16 + row];
            for (int column = 0; column < row; ++column) {
                for (int metric = 0; metric < 5; ++metric) derivatives[metric * 120 + coordinate] += terms[metric] * spins[column];
                ++coordinate;
            }
        }
    }
    metrics[0] = mean_reward;
    metrics[1] = variance;
    metrics[2] = mean_potential;
    metrics[3] = entropy;
    metrics[4] = sector_mass;
    cached_mean_reward = mean_reward;
}

extern "C" void hessian_fast(const double *direction, double *result) {
    std::fill(result, result + 120, 0);
    for (int state = 0; state < 32768; ++state) {
        double spins[16];
        spins[0] = 1;
        for (int row = 1; row < 16; ++row) spins[row] = 2 * ((state >> (row - 1)) & 1) - 1;
        double row_directions[16];
        double score_direction = 0;
        int coordinate = 0;
        for (int row = 1; row < 16; ++row) {
            double row_direction = 0;
            for (int column = 0; column < row; ++column) row_direction += direction[coordinate++] * spins[column];
            row_directions[row] = row_direction;
            score_direction += residuals[state * 16 + row] * row_direction;
        }
        double centered = rewards[state] - cached_mean_reward;
        double factor = probabilities[state] * (centered + 1) * score_direction;
        coordinate = 0;
        for (int row = 1; row < 16; ++row) {
            double residual = residuals[state * 16 + row];
            double curvature = std::abs(residual) * (1 - std::abs(residual));
            double row_factor = factor * residual - probabilities[state] * centered * curvature * row_directions[row];
            for (int column = 0; column < row; ++column) result[coordinate++] += row_factor * spins[column];
        }
    }
}
