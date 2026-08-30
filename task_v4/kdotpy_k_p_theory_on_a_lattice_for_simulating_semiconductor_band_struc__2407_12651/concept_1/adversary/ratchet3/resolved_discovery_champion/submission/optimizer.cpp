#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>

using Clock = std::chrono::steady_clock;

struct Factor {
    int offset, arity;
    int vertices[4];
};

struct Incident {
    int factor, multiplier;
};

struct Move {
    int count = 0;
    int factor[320], index[320];
    double delta[4] = {}, flux[4] = {};
    int cost = 0;
    bool valid = true;
};

class Optimizer {
public:
    int vertices, budget, nx, ny;
    const int *fixed, *costs;
    const double *losses, *fluxes, *weights, *targets;
    const unsigned char *valid;
    std::vector<Factor> factors;
    std::vector<std::vector<Incident>> adjacent;
    std::vector<int> choices, indices, available, best, baseline, seed;
    std::vector<int> marks, locations;
    std::vector<std::array<int, 4>> labels_by_cost;
    int stamp = 0, cost = 0;
    double totals[4] = {}, current_flux[4] = {};
    double best_value = 1e100;
    std::mt19937_64 random;
    Clock::time_point deadline;
    long long proposals = 0;
    long long nodes = 0;
    const double *reduced = nullptr;
    double lower_bound = 0;

    double uniform() { return (random() >> 11) * 0x1.0p-53; }
    int integer(int upper) { return random() % upper; }
    bool expired() { return Clock::now() >= deadline; }

    double objective(const double *values) {
        double maximum = values[0], mean = 0;
        for (int scenario = 0; scenario < 4; ++scenario) {
            maximum = std::max(maximum, values[scenario]);
            mean += weights[scenario] * values[scenario];
        }
        return maximum + mean;
    }

    void initialize(const std::vector<int> &start) {
        choices = start;
        cost = 0;
        std::fill(totals, totals + 4, 0.0);
        std::fill(current_flux, current_flux + 4, 0.0);
        for (int vertex = 0; vertex < vertices; ++vertex)
            cost += costs[4 * vertex + choices[vertex]];
        for (int factor = 0; factor < (int)factors.size(); ++factor) {
            const Factor &description = factors[factor];
            int index = 0;
            for (int position = 0; position < description.arity; ++position)
                index = 4 * index + choices[description.vertices[position]];
            index += description.offset;
            indices[factor] = index;
            for (int scenario = 0; scenario < 4; ++scenario) {
                totals[scenario] += losses[4 * index + scenario];
                current_flux[scenario] += fluxes[4 * index + scenario];
            }
        }
        record();
    }

    void record() {
        double value = objective(totals);
        if (cost <= budget && value < best_value - 1e-12) {
            bool feasible = true;
            for (int scenario = 0; scenario < 4; ++scenario)
                feasible &= std::abs(current_flux[scenario] / (2 * M_PI) - targets[scenario]) < 1e-7;
            for (int index : indices) feasible &= valid[index];
            if (feasible) { best_value = value; best = choices; }
        }
    }

    Move evaluate_many(const int *changed_vertices, const int *changed_choices, int changed_count) {
        Move move;
        ++stamp;
        for (int changed = 0; changed < changed_count; ++changed) {
            int vertex = changed_vertices[changed];
            if (vertex < 0) break;
            int label = changed_choices[changed];
            move.cost += costs[4 * vertex + label] - costs[4 * vertex + choices[vertex]];
            int difference = label - choices[vertex];
            for (const Incident &incident : adjacent[vertex]) {
                int factor = incident.factor;
                int position;
                if (marks[factor] != stamp) {
                    marks[factor] = stamp;
                    position = move.count++;
                    locations[factor] = position;
                    move.factor[position] = factor;
                    move.index[position] = indices[factor];
                } else position = locations[factor];
                move.index[position] += difference * incident.multiplier;
            }
        }
        for (int position = 0; position < move.count; ++position) {
            int next = move.index[position];
            int previous = indices[move.factor[position]];
            if (!valid[next]) { move.valid = false; return move; }
            for (int scenario = 0; scenario < 4; ++scenario) {
                move.delta[scenario] += losses[4 * next + scenario] - losses[4 * previous + scenario];
                move.flux[scenario] += fluxes[4 * next + scenario] - fluxes[4 * previous + scenario];
            }
        }
        return move;
    }

    Move evaluate(int first, int first_choice, int second = -1, int second_choice = -1,
                  int third = -1, int third_choice = -1) {
        int changed_vertices[3] = {first, second, third};
        int changed_choices[3] = {first_choice, second_choice, third_choice};
        return evaluate_many(changed_vertices, changed_choices, 3);
    }

    bool preserves_topology(const Move &move) {
        for (int scenario = 0; scenario < 4; ++scenario)
            if (std::abs(move.flux[scenario]) > 1e-6) return false;
        return true;
    }

    double topology_error(const Move *move = nullptr) {
        double error = 0;
        for (int scenario = 0; scenario < 4; ++scenario) {
            double next = current_flux[scenario] + (move ? move->flux[scenario] : 0.0);
            error += std::abs(std::round(next / (2 * M_PI)) - targets[scenario]);
        }
        return error;
    }

    double value_after(const Move &move) {
        double values[4];
        for (int scenario = 0; scenario < 4; ++scenario) values[scenario] = totals[scenario] + move.delta[scenario];
        return objective(values);
    }

    void apply(const Move &move, int first, int first_choice, int second = -1, int second_choice = -1,
               int third = -1, int third_choice = -1) {
        cost += move.cost;
        choices[first] = first_choice;
        if (second >= 0) choices[second] = second_choice;
        if (third >= 0) choices[third] = third_choice;
        for (int scenario = 0; scenario < 4; ++scenario) {
            totals[scenario] += move.delta[scenario];
            current_flux[scenario] += move.flux[scenario];
        }
        for (int position = 0; position < move.count; ++position)
            indices[move.factor[position]] = move.index[position];
        record();
    }

    void descent(bool pairs) {
        for (int iteration = 0; iteration < 300 && !expired(); ++iteration) {
            double best_next = objective(totals) - 1e-12;
            int first_best = -1, second_best = -1, first_label = -1, second_label = -1;
            Move best_move;
            for (int first : available) {
                for (int first_choice = 0; first_choice < 4; ++first_choice) {
                    if (first_choice == choices[first]) continue;
                    int difference = costs[4 * first + first_choice] - costs[4 * first + choices[first]];
                    if (cost + difference > budget) continue;
                    Move move = evaluate(first, first_choice);
                    if (!move.valid || !preserves_topology(move)) continue;
                    double value = value_after(move);
                    if (value < best_next) {
                        best_next = value; best_move = move;
                        first_best = first; first_label = first_choice; second_best = -1;
                    }
                }
            }
            if (first_best >= 0) {
                apply(best_move, first_best, first_label);
                continue;
            }
            if (!pairs) break;
            for (int first : available) {
                for (int second : available) {
                    if (second <= first) continue;
                    for (int first_choice = 0; first_choice < 4; ++first_choice) {
                        if (first_choice == choices[first]) continue;
                        int difference = costs[4 * first + first_choice] - costs[4 * first + choices[first]];
                        for (int second_choice = 0; second_choice < 4; ++second_choice) {
                            if (second_choice == choices[second]) continue;
                            int other_difference = costs[4 * second + second_choice] - costs[4 * second + choices[second]];
                            if (cost + difference + other_difference > budget) continue;
                            Move move = evaluate(first, first_choice, second, second_choice);
                            if (!move.valid || !preserves_topology(move)) continue;
                            double value = value_after(move);
                            if (value < best_next) {
                                best_next = value; best_move = move;
                                first_best = first; first_label = first_choice;
                                second_best = second; second_label = second_choice;
                            }
                        }
                    }
                }
            }
            if (first_best < 0) break;
            apply(best_move, first_best, first_label, second_best, second_label);
        }
    }

    void anneal(int iterations, double start_temperature, double end_temperature, double penalty,
                bool allow_topology = false, bool blocks = false) {
        double temperature = start_temperature;
        double cooling = std::pow(end_temperature / start_temperature, 1.0 / iterations);
        double topology_penalty = best_value * 0.04;
        double value = objective(totals) + penalty * std::max(0, cost - budget) + topology_penalty * topology_error();
        for (int iteration = 0; iteration < iterations; ++iteration) {
            if ((iteration & 2047) == 0 && expired()) return;
            temperature *= cooling;
            int first = available[integer(available.size())];
            int first_choice = (choices[first] + 1 + integer(3)) % 4;
            int second = -1, second_choice = -1, third = -1, third_choice = -1;
            int kind = integer(100);
            if (blocks && kind >= 95) {
                int changed_vertices[32], changed_choices[32], count = 0;
                int width = 2 + integer(3), height = 2 + integer(3);
                int cost_choice = integer(4) == 0 ? 1 + integer(3) : 0;
                for (int row = 0; row < height; ++row) {
                    for (int column = 0; column < width; ++column) {
                        int vertex = ((first / nx + row) % ny) * nx + (first % nx + column) % nx;
                        if (fixed[vertex]) continue;
                        int label = labels_by_cost[vertex][cost_choice];
                        if (label == choices[vertex]) continue;
                        changed_vertices[count] = vertex;
                        changed_choices[count++] = label;
                    }
                }
                if (!count) continue;
                Move move = evaluate_many(changed_vertices, changed_choices, count);
                ++proposals;
                if (!move.valid || (!allow_topology && !preserves_topology(move))) continue;
                double next = value_after(move) + penalty * std::max(0, cost + move.cost - budget) + topology_penalty * topology_error(&move);
                if (next < value || uniform() < std::exp((value - next) / temperature)) {
                    for (int changed = 0; changed < count; ++changed) choices[changed_vertices[changed]] = changed_choices[changed];
                    apply(move, changed_vertices[0], changed_choices[0]);
                    value = next;
                }
                continue;
            }
            if (kind < 55) {
                second = available[integer(available.size())];
                if (first == second) continue;
                second_choice = (choices[second] + 1 + integer(3)) % 4;
            }
            if (kind < 8) {
                third = available[integer(available.size())];
                if (third == first || third == second) continue;
                third_choice = (choices[third] + 1 + integer(3)) % 4;
            }
            Move move = evaluate(first, first_choice, second, second_choice, third, third_choice);
            ++proposals;
            if (!move.valid || (!allow_topology && !preserves_topology(move))) continue;
            double next = value_after(move) + penalty * std::max(0, cost + move.cost - budget) + topology_penalty * topology_error(&move);
            double difference = next - value;
            if (difference <= 0 || uniform() < std::exp(-difference / temperature)) {
                apply(move, first, first_choice, second, second_choice, third, third_choice);
                value = next;
            }
        }
    }

    bool refine_search(std::vector<unsigned char> domains) {
        ++nodes;
        if ((nodes & 31) == 1 && expired()) return false;
        std::vector<std::array<double, 4>> conditional(vertices);
        double minimum_total = 0;
        while (true) {
            for (auto &values : conditional) values.fill(0.0);
            minimum_total = 0;
            int minimum_cost = 0;
            std::vector<int> minimum_vertex_cost(vertices, 1000000);
            for (int vertex = 0; vertex < vertices; ++vertex) {
                for (int label = 0; label < 4; ++label) {
                    if (domains[vertex] & (1 << label))
                        minimum_vertex_cost[vertex] = std::min(minimum_vertex_cost[vertex], costs[4 * vertex + label]);
                }
                minimum_cost += minimum_vertex_cost[vertex];
            }
            if (minimum_cost > budget) return true;
            for (const Factor &factor : factors) {
                double minimum = 1e100;
                double local[16];
                std::fill(local, local + 16, 1e100);
                int count = 1 << (2 * factor.arity);
                for (int code = 0; code < count; ++code) {
                    int index = factor.offset + code;
                    if (!valid[index]) continue;
                    int labels[4];
                    bool allowed = true;
                    for (int position = 0; position < factor.arity; ++position) {
                        labels[position] = (code >> (2 * (factor.arity - position - 1))) & 3;
                        if (!(domains[factor.vertices[position]] & (1 << labels[position]))) {
                            allowed = false;
                            break;
                        }
                    }
                    if (!allowed) continue;
                    double value = reduced[index];
                    minimum = std::min(minimum, value);
                    for (int position = 0; position < factor.arity; ++position) {
                        int selected = 4 * position + labels[position];
                        local[selected] = std::min(local[selected], value);
                    }
                }
                if (minimum > 1e90) return true;
                minimum_total += minimum;
                for (int position = 0; position < factor.arity; ++position) {
                    for (int label = 0; label < 4; ++label)
                        conditional[factor.vertices[position]][label] += local[4 * position + label] - minimum;
                }
            }
            double allowance = best_value - lower_bound - minimum_total + 2e-7;
            if (allowance < 0) return true;
            bool changed = false;
            for (int vertex = 0; vertex < vertices; ++vertex) {
                for (int label = 0; label < 4; ++label) {
                    if (!(domains[vertex] & (1 << label))) continue;
                    if (conditional[vertex][label] > allowance ||
                        minimum_cost + costs[4 * vertex + label] - minimum_vertex_cost[vertex] > budget) {
                        domains[vertex] &= ~(1 << label);
                        changed = true;
                    }
                }
                if (!domains[vertex]) return true;
            }
            if (!changed) break;
        }
        int selected_vertex = -1;
        double priority = -1;
        for (int vertex : available) {
            if (__builtin_popcount(domains[vertex]) < 2) continue;
            double smallest = 1e100, second = 1e100;
            for (int label = 0; label < 4; ++label) {
                if (!(domains[vertex] & (1 << label))) continue;
                double value = conditional[vertex][label];
                if (value < smallest) { second = smallest; smallest = value; }
                else second = std::min(second, value);
            }
            double value = second - smallest + 1e-10 * __builtin_popcount(domains[vertex]);
            if (value > priority) { priority = value; selected_vertex = vertex; }
        }
        if (selected_vertex < 0) {
            std::vector<int> assignment(vertices);
            for (int vertex = 0; vertex < vertices; ++vertex) assignment[vertex] = __builtin_ctz(domains[vertex]);
            initialize(assignment);
            return true;
        }
        std::vector<int> labels;
        for (int label = 0; label < 4; ++label)
            if (domains[selected_vertex] & (1 << label)) labels.push_back(label);
        std::sort(labels.begin(), labels.end(), [&](int first, int second) {
            return conditional[selected_vertex][first] < conditional[selected_vertex][second];
        });
        for (int label : labels) {
            domains[selected_vertex] = 1 << label;
            if (!refine_search(domains)) return false;
        }
        return true;
    }
};

Optimizer make_optimizer(int vertices, int budget, const int *fixed, const int *costs,
                          const int *factor_vertices, const int *arities, const int *offsets,
                          const double *losses, const double *fluxes, const unsigned char *valid,
                          const int *seeds, const double *weights, const double *targets,
                          double seconds, uint64_t random_seed) {
    Optimizer optimizer;
    optimizer.vertices = vertices; optimizer.budget = budget;
    optimizer.nx = factor_vertices[4 * (vertices + 1) + 1];
    optimizer.ny = vertices / optimizer.nx;
    optimizer.fixed = fixed; optimizer.costs = costs; optimizer.losses = losses;
    optimizer.fluxes = fluxes; optimizer.valid = valid; optimizer.weights = weights;
    optimizer.targets = targets; optimizer.random.seed(random_seed);
    optimizer.deadline = Clock::now() + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
    optimizer.adjacent.resize(vertices);
    optimizer.factors.resize(4 * vertices);
    optimizer.indices.resize(4 * vertices);
    optimizer.marks.assign(4 * vertices, -1);
    optimizer.locations.resize(4 * vertices);
    optimizer.baseline.assign(seeds, seeds + vertices);
    optimizer.seed.assign(seeds + vertices, seeds + 2 * vertices);
    optimizer.labels_by_cost.resize(vertices);
    for (int vertex = 0; vertex < vertices; ++vertex) {
        for (int label = 0; label < 4; ++label) optimizer.labels_by_cost[vertex][label] = label;
        std::sort(optimizer.labels_by_cost[vertex].begin(), optimizer.labels_by_cost[vertex].end(),
                  [&](int first, int second) { return costs[4 * vertex + first] < costs[4 * vertex + second]; });
    }
    for (int vertex = 0; vertex < vertices; ++vertex)
        if (!fixed[vertex]) optimizer.available.push_back(vertex);
    for (int factor = 0; factor < 4 * vertices; ++factor) {
        Factor &description = optimizer.factors[factor];
        description.offset = offsets[factor]; description.arity = arities[factor];
        int multiplier = 1;
        for (int position = arities[factor] - 1; position >= 0; --position) {
            int vertex = factor_vertices[4 * factor + position];
            description.vertices[position] = vertex;
            optimizer.adjacent[vertex].push_back({factor, multiplier});
            multiplier *= 4;
        }
    }
    return optimizer;
}

extern "C" void optimize(int vertices, int budget, const int *fixed, const int *costs,
                          const int *factor_vertices, const int *arities, const int *offsets,
                          const double *losses, const double *fluxes, const unsigned char *valid,
                          const int *seeds, const double *weights, const double *targets,
                          double seconds, uint64_t random_seed, int *output) {
    Optimizer optimizer = make_optimizer(vertices, budget, fixed, costs, factor_vertices, arities,
                                         offsets, losses, fluxes, valid, seeds, weights, targets, seconds, random_seed);
    optimizer.initialize(optimizer.baseline);
    if (optimizer.available.empty()) {
        std::copy(optimizer.best.begin(), optimizer.best.end(), output);
        return;
    }
    optimizer.descent(true);
    int runs = 0;
    while (!optimizer.expired()) {
        optimizer.initialize(runs % 7 == 6 ? optimizer.seed : optimizer.best);
        double scale = optimizer.best_value;
        double temperatures[6] = {0.025, 0.010, 0.004, 0.0015, 0.06, 0.15};
        double start_temperature = scale * temperatures[runs % 6];
        optimizer.anneal(150000, start_temperature, scale * 0.000025, scale * 0.015, runs % 3 == 2, true);
        optimizer.initialize(optimizer.best);
        optimizer.descent(true);
        ++runs;
    }
    std::copy(optimizer.best.begin(), optimizer.best.end(), output);
}

extern "C" int refine(int vertices, int budget, const int *fixed, const int *costs,
                       const int *factor_vertices, const int *arities, const int *offsets,
                       const double *losses, const double *fluxes, const unsigned char *valid,
                       const int *seeds, const double *weights, const double *targets,
                       const double *reduced, double lower_bound, double seconds, int *output) {
    Optimizer optimizer = make_optimizer(vertices, budget, fixed, costs, factor_vertices, arities,
                                         offsets, losses, fluxes, valid, seeds, weights, targets, seconds, 2718281828);
    optimizer.initialize(optimizer.baseline);
    if (optimizer.available.empty()) {
        std::copy(optimizer.best.begin(), optimizer.best.end(), output);
        return 1;
    }
    optimizer.descent(true);
    for (int run = 0; run < 12 && !optimizer.expired(); ++run) {
        optimizer.initialize(optimizer.best);
        optimizer.anneal(150000, optimizer.best_value * 0.01, optimizer.best_value * 0.000025, optimizer.best_value * 0.015);
        optimizer.initialize(optimizer.best);
        optimizer.descent(true);
    }
    optimizer.reduced = reduced;
    optimizer.lower_bound = lower_bound;
    std::vector<unsigned char> domains(vertices, 15);
    for (int vertex = 0; vertex < vertices; ++vertex)
        if (fixed[vertex]) domains[vertex] = 1 << optimizer.baseline[vertex];
    bool complete = optimizer.refine_search(domains);
    std::copy(optimizer.best.begin(), optimizer.best.end(), output);
    return complete;
}
