#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>

constexpr int rows = 4;
constexpr int columns = 5;
constexpr int edge_count = 39;
using Rates = std::array<double, edge_count>;
struct Metrics {
    double gap;
    double opposite;
    double mass;
    int physical;
};

Metrics evaluate(const Rates& rates, unsigned syndrome, double scale) {
    double horizontal_mass[6][16], horizontal_cost[6][16];
    double vertical_mass[5][8], vertical_cost[5][8];
    for (int cut = 0; cut <= columns; ++cut) {
        for (int mask = 0; mask < 16; ++mask) {
            double mass = 1.0, cost = 0.0;
            for (int row = 0; row < rows; ++row) {
                double probability = scale * rates[cut * rows + row];
                bool active = (mask >> row) & 1;
                mass *= active ? probability : 1.0 - probability;
                if (active) cost += std::log((1.0 - probability) / probability);
            }
            horizontal_mass[cut][mask] = mass;
            horizontal_cost[cut][mask] = cost;
        }
    }
    for (int column = 0; column < columns; ++column) {
        for (int mask = 0; mask < 8; ++mask) {
            double mass = 1.0, cost = 0.0;
            for (int row = 0; row < rows - 1; ++row) {
                double probability = scale * rates[24 + column * 3 + row];
                bool active = (mask >> row) & 1;
                mass *= active ? probability : 1.0 - probability;
                if (active) cost += std::log((1.0 - probability) / probability);
            }
            vertical_mass[column][mask] = mass;
            vertical_cost[column][mask] = cost;
        }
    }
    double mass[2][16] = {}, cost[2][16];
    std::fill(&cost[0][0], &cost[0][0] + 32, 1e100);
    for (int mask = 0; mask < 16; ++mask) {
        int logical = __builtin_parity(static_cast<unsigned>(mask));
        mass[logical][mask] = horizontal_mass[0][mask];
        cost[logical][mask] = horizontal_cost[0][mask];
    }
    for (int column = 0; column < columns; ++column) {
        double next_mass[2][16] = {}, next_cost[2][16];
        std::fill(&next_cost[0][0], &next_cost[0][0] + 32, 1e100);
        int target = (syndrome >> (column * rows)) & 15;
        for (int logical = 0; logical < 2; ++logical) {
            for (int incoming = 0; incoming < 16; ++incoming) {
                for (int vertical = 0; vertical < 8; ++vertical) {
                    int outgoing = incoming ^ target ^ vertical ^ (vertical << 1);
                    next_mass[logical][outgoing] += mass[logical][incoming] *
                        vertical_mass[column][vertical] * horizontal_mass[column + 1][outgoing];
                    next_cost[logical][outgoing] = std::min(next_cost[logical][outgoing],
                        cost[logical][incoming] + vertical_cost[column][vertical] +
                        horizontal_cost[column + 1][outgoing]);
                }
            }
        }
        std::copy(&next_mass[0][0], &next_mass[0][0] + 32, &mass[0][0]);
        std::copy(&next_cost[0][0], &next_cost[0][0] + 32, &cost[0][0]);
    }
    double totals[2] = {}, minima[2] = {1e100, 1e100};
    for (int logical = 0; logical < 2; ++logical) {
        for (int mask = 0; mask < 16; ++mask) {
            totals[logical] += mass[logical][mask];
            minima[logical] = std::min(minima[logical], cost[logical][mask]);
        }
    }
    int physical = minima[1] < minima[0];
    return {std::abs(minima[1] - minima[0]),
        totals[1 - physical] / (totals[0] + totals[1]), totals[0] + totals[1], physical};
}

bool valid_syndrome(unsigned syndrome) {
    int count = __builtin_popcount(syndrome);
    if (count < 3 || count > 6) return false;
    unsigned occupied_rows = 0, occupied_columns = 0;
    for (int detector = 0; detector < 20; ++detector) {
        if ((syndrome >> detector) & 1) {
            occupied_rows |= 1U << (detector % 4);
            occupied_columns |= 1U << (detector / 4);
        }
    }
    return __builtin_popcount(occupied_rows) >= 3 && __builtin_popcount(occupied_columns) >= 3;
}

double objective(const Rates& rates, unsigned syndrome, Metrics* summary = nullptr) {
    double mean = 0.0;
    for (double rate : rates) mean += rate / edge_count;
    Metrics center = evaluate(rates, syndrome, 1.0);
    Metrics result = center;
    for (double scale : {0.95, 1.05}) {
        Metrics current = evaluate(rates, syndrome, scale);
        if (current.physical != center.physical) current.gap = -current.gap;
        result.gap = std::min(result.gap, current.gap);
        result.opposite = std::min(result.opposite, current.opposite);
        result.mass = std::min(result.mass, current.mass);
    }
    if (summary) *summary = result;
    double log_odds = std::log(result.opposite / (1.0 - result.opposite));
    return log_odds + 0.35 * std::min(result.gap, 1.2)
        - 5.0 * std::max(0.0, 1.2 - result.gap)
        - 1.5 * std::max(0.0, std::log(0.00002 / result.mass))
        - 100.0 * std::max(0.0, mean - 0.085);
}

void save(const std::string& path, const Rates& rates, unsigned syndrome) {
    std::ofstream output(path);
    output << std::setprecision(17) << "{\"version\":1,\"probabilities\":[";
    for (int edge = 0; edge < edge_count; ++edge) output << (edge ? "," : "") << rates[edge];
    output << "],\"syndrome\":[";
    bool first = true;
    for (int detector = 0; detector < 20; ++detector) {
        if ((syndrome >> detector) & 1) {
            output << (first ? "" : ",") << detector;
            first = false;
        }
    }
    output << "]}\n";
}

int main(int argc, char** argv) {
    int seconds = argc > 1 ? std::stoi(argv[1]) : 240;
    unsigned seed = argc > 2 ? std::stoul(argv[2]) : 230315933;
    std::string prefix = argc > 3 ? argv[3] : "search";
    std::mt19937 random(seed);
    std::uniform_real_distribution<double> uniform(0.0, 1.0);
    std::normal_distribution<double> normal(0.0, 1.0);
    auto started = std::chrono::steady_clock::now();
    double best_score = -1e100;
    Rates best_rates{};
    unsigned best_syndrome = 0;
    long long evaluations = 0;
    int restarts = 0;
    bool weak_saved = false;
    while (std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() < seconds) {
        Rates rates;
        unsigned syndrome = 0;
        do { syndrome = random() & ((1U << 20) - 1); } while (!valid_syndrome(syndrome));
        for (double& rate : rates) rate = 0.02 + 0.10 * uniform(random);
        if (restarts % 4 && best_score > -1e50) {
            rates = best_rates;
            syndrome = best_syndrome;
            for (double& rate : rates) rate = std::clamp(rate + 0.025 * normal(random), 0.02, 0.14);
        }
        double score = objective(rates, syndrome);
        for (int iteration = 0; iteration < 2500; ++iteration) {
            Rates proposed = rates;
            unsigned next_syndrome = syndrome;
            if (uniform(random) < 0.05) {
                next_syndrome ^= 1U << (random() % 20);
                if (uniform(random) < 0.7) next_syndrome ^= 1U << (random() % 20);
                if (!valid_syndrome(next_syndrome)) continue;
            } else {
                int mutations = uniform(random) < 0.15 ? 4 : 1;
                for (int mutation = 0; mutation < mutations; ++mutation) {
                    int edge = random() % edge_count;
                    proposed[edge] = std::clamp(proposed[edge] + (iteration < 1200 ? 0.02 : 0.005) * normal(random), 0.02, 0.14);
                }
            }
            Metrics metrics;
            double proposed_score = objective(proposed, next_syndrome, &metrics);
            ++evaluations;
            double temperature = 0.05 * std::pow(0.015, iteration / 2500.0);
            if (proposed_score > score || uniform(random) < std::exp((proposed_score - score) / temperature)) {
                rates = proposed;
                syndrome = next_syndrome;
                score = proposed_score;
            }
            if (!weak_saved && metrics.gap > 0.15 && metrics.opposite > 0.51 && metrics.mass > 0.00002) {
                save(prefix + "_weak.json", proposed, next_syndrome);
                weak_saved = true;
            }
            if (proposed_score > best_score) {
                best_score = proposed_score;
                best_rates = proposed;
                best_syndrome = next_syndrome;
                save(prefix + "_best.json", best_rates, best_syndrome);
                std::cout << std::setprecision(10) << evaluations << " score=" << best_score
                    << " gap=" << metrics.gap << " opposite=" << metrics.opposite
                    << " mass=" << metrics.mass << " syndrome=" << syndrome << std::endl;
            }
        }
        ++restarts;
    }
    std::cout << "DONE seed=" << seed << " evaluations=" << evaluations << " restarts=" << restarts << std::endl;
}
