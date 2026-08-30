#include <algorithm>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <random>
#include <vector>

extern "C" void sample_posterior(int observations, int edges, int pairs, int family,
    const double* design, const double* spam_design, int spam_count,
    const double* depths, const double* shots, const double* successes,
    const double* prior, const int64_t* pair_edges, int sweeps, int burn, int thin, uint64_t seed,
    double* state, double* output) {
    int rate_count = 1 + edges + pairs;
    int total_count = rate_count + spam_count;
    std::mt19937_64 generator(seed);
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    std::normal_distribution<double> normal(0.0, 1.0);
    std::vector<std::vector<int>> active(rate_count);
    std::vector<std::vector<int>> incident(edges);
    for (int pair = 0; pair < pairs; ++pair) {
        incident[pair_edges[2 * pair]].push_back(pair);
        incident[pair_edges[2 * pair + 1]].push_back(pair);
    }
    for (int parameter = 0; parameter < rate_count; ++parameter) {
        for (int row = 0; row < observations; ++row) {
            if (design[row * rate_count + parameter] != 0.0 && depths[row] > 0)
                active[parameter].push_back(row);
        }
    }
    std::vector<double> rates(observations, 0.0), latent(observations, 0.0);
    std::vector<double> log_contrast(observations), probability(observations);
    for (int row = 0; row < observations; ++row) {
        for (int parameter = 0; parameter < rate_count; ++parameter)
            rates[row] += design[row * rate_count + parameter] * state[parameter];
        for (int parameter = 0; parameter < spam_count; ++parameter)
            latent[row] += spam_design[row * spam_count + parameter] * state[rate_count + parameter];
        log_contrast[row] = std::log(0.58 + 0.37 / (1.0 + std::exp(-latent[row])));
        probability[row] = std::exp(log_contrast[row] - depths[row] * rates[row]);
    }
    std::vector<int> order(rate_count);
    std::iota(order.begin(), order.end(), 0);
    std::vector<double> values(25), log_weights(25), adjusted(observations);
    std::vector<double> exponential(3 * 129 * 25);
    for (int kind = 0; kind < 3; ++kind) {
        int count = kind == 2 ? 19 : 23;
        double lower = kind == 0 ? 0.001 : (family >= 2 ? 0.0015 : 0.002);
        double upper = kind == 0 ? 0.004 : (family >= 2 ? 0.010 : 0.007);
        if (kind == 2) {
            lower = 0.010;
            upper = 0.035;
        }
        for (int depth = 0; depth < 129; ++depth) {
            for (int point = 0; point < count; ++point) {
                double value = lower + (upper - lower) * (point + 0.5) / count;
                if (kind == 2)
                    value = point == 0 ? 0.0 : lower + (upper - lower) * (point - 0.5) / (count - 1);
                exponential[(kind * 129 + depth) * 25 + point] = std::exp(-2.0 * depth * value);
            }
        }
    }
    int kept = 0;
    for (int iteration = 0; iteration < sweeps; ++iteration) {
        std::shuffle(order.begin(), order.end(), generator);
        for (int parameter : order) {
            bool cross = parameter > edges;
            double old_value = state[parameter];
            int count = cross ? 19 : 23;
            double lower = parameter == 0 ? 0.001 : (family >= 2 ? 0.0015 : 0.002);
            double upper = parameter == 0 ? 0.004 : (family >= 2 ? 0.010 : 0.007);
            if (cross) {
                lower = 0.010;
                upper = 0.035;
            }
            double linear = 0.0;
            for (int row : active[parameter]) {
                adjusted[row] = std::exp(log_contrast[row] - depths[row] * (rates[row] - old_value));
                linear += depths[row] * successes[row];
            }
            double inclusion = cross ? std::max(1e-7, std::min(0.8, prior[parameter - edges - 1])) : 1.0;
            for (int point = 0; point < count; ++point) {
                double value;
                double log_prior = 0.0;
                if (cross) {
                    value = point == 0 ? 0.0 : lower + (upper - lower) * (point - 0.5) / (count - 1);
                    log_prior = point == 0 ? std::log1p(-inclusion) : std::log(inclusion / (count - 1));
                    if (family == 2 && point > 0) {
                        int pair = parameter - edges - 1;
                        double base_sum = state[pair_edges[2 * pair] + 1] + state[pair_edges[2 * pair + 1] + 1];
                        double half_width = 0.025 / 36.0;
                        double overlap = std::min(value + half_width, 0.035 - 0.5 * base_sum) -
                                         std::max(value - half_width, 0.020 - 0.5 * base_sum);
                        log_prior = overlap > 0 ? std::log(inclusion * overlap / 0.015) : -1e100;
                    }
                } else {
                    value = lower + (upper - lower) * (point + 0.5) / count;
                    if (family >= 2 && parameter > 0) log_prior = -std::log(value);
                    if (family == 2 && parameter > 0) {
                        for (int pair : incident[parameter - 1]) {
                            double cross_value = state[edges + 1 + pair];
                            if (cross_value == 0) continue;
                            int other = pair_edges[2 * pair] == parameter - 1 ? pair_edges[2 * pair + 1] : pair_edges[2 * pair];
                            double base_sum = value + state[other + 1];
                            double half_width = 0.025 / 36.0;
                            double overlap = std::min(cross_value + half_width, 0.035 - 0.5 * base_sum) -
                                             std::max(cross_value - half_width, 0.020 - 0.5 * base_sum);
                            log_prior += overlap > 0 ? std::log(overlap / 0.015) : -1e100;
                        }
                    }
                }
                values[point] = value;
                double likelihood = log_prior - value * linear;
                for (int row : active[parameter]) {
                    int kind = cross ? 2 : (parameter == 0 ? 0 : 1);
                    double prob = std::min(0.999999999, adjusted[row] * exponential[(kind * 129 + int(depths[row] / 2)) * 25 + point]);
                    likelihood += (shots[row] - successes[row]) * std::log1p(-prob);
                }
                log_weights[point] = likelihood;
            }
            double maximum = *std::max_element(log_weights.begin(), log_weights.begin() + count);
            double total = 0.0;
            for (int point = 0; point < count; ++point) {
                log_weights[point] = std::exp(log_weights[point] - maximum);
                total += log_weights[point];
            }
            double draw = uniform(generator) * total;
            int chosen = 0;
            while (chosen + 1 < count && (draw -= log_weights[chosen]) > 0) ++chosen;
            double new_value = values[chosen];
            state[parameter] = new_value;
            for (int row : active[parameter]) {
                rates[row] += new_value - old_value;
                probability[row] = adjusted[row] * std::exp(-depths[row] * new_value);
            }
        }
        for (int parameter = 0; parameter < spam_count; ++parameter) {
            double old_value = state[rate_count + parameter];
            double sigma = parameter == 0 ? 0.231 : 0.520;
            if (parameter == edges + 1) sigma = 0.577;
            if (parameter > edges + 1) sigma = 0.65;
            double new_value = old_value + 0.28 * normal(generator);
            double difference = new_value - old_value;
            double log_ratio = -0.5 * (new_value * new_value - old_value * old_value) / (sigma * sigma);
            for (int row = 0; row < observations; ++row) {
                double shift = spam_design[row * spam_count + parameter] * difference;
                if (shift == 0.0) continue;
                double log_amplitude = std::log(0.58 + 0.37 / (1.0 + std::exp(-latent[row] - shift)));
                double new_probability = std::exp(log_amplitude - depths[row] * rates[row]);
                log_ratio += successes[row] * (log_amplitude - log_contrast[row]);
                log_ratio += (shots[row] - successes[row]) * (std::log1p(-new_probability) - std::log1p(-probability[row]));
            }
            if (std::log(uniform(generator)) < log_ratio) {
                state[rate_count + parameter] = new_value;
                for (int row = 0; row < observations; ++row) {
                    latent[row] += spam_design[row * spam_count + parameter] * difference;
                    log_contrast[row] = std::log(0.58 + 0.37 / (1.0 + std::exp(-latent[row])));
                    probability[row] = std::exp(log_contrast[row] - depths[row] * rates[row]);
                }
            }
        }
        if (iteration >= burn && (iteration - burn) % thin == 0) {
            std::copy(state, state + total_count, output + kept * total_count);
            ++kept;
        }
    }
}
