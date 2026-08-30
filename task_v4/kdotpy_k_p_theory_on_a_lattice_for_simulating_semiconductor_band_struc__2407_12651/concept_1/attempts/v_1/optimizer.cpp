#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <vector>

using Clock = std::chrono::steady_clock;
constexpr int MAX_VERTICES = 80;

struct Entry {
    double loss[4];
    double flux[4];
    double invalid;
};

struct Delta {
    double loss[4] = {};
    double flux[4] = {};
    double invalid = 0;
    int cost = 0;
    void add(const Entry& newer, const Entry& older) {
        for (int scenario = 0; scenario < 4; ++scenario) {
            loss[scenario] += newer.loss[scenario] - older.loss[scenario];
            flux[scenario] += newer.flux[scenario] - older.flux[scenario];
        }
        invalid += newer.invalid - older.invalid;
    }
};

struct Factor {
    int width;
    int members[4];
    int strides[4];
    const Entry* table;
};

struct Incidence {
    int factor;
    int stride;
};

struct Shared {
    int factor;
    int first_stride;
    int second_stride;
};

struct State {
    std::array<int, MAX_VERTICES> choices{};
    std::vector<int> indices;
    double loss[4] = {};
    double flux[4] = {};
    double invalid = 0;
    int cost = 0;
    double objective = 0;
};

class Optimizer {
public:
    int vertices;
    int budget;
    const int* costs;
    const int* anchors;
    const double* weights;
    std::vector<Factor> factors;
    std::vector<Incidence> incident[MAX_VERTICES];
    std::vector<Shared> shared[MAX_VERTICES][MAX_VERTICES];
    std::vector<int> free_vertices;
    std::mt19937_64 random;
    Clock::time_point deadline;
    State best;
    double target_flux[4] = {};
    int ranked[MAX_VERTICES][4];
    int nx;
    int ny;
    long long descents = 0;
    long long evaluations = 0;

    Optimizer(int vertex_count, int factor_count, const int* widths, const int* members,
              const double* tables, const int* acquisition, const int* fixed,
              const double* mean_weights, int limit, double seconds, uint64_t seed)
        : vertices(vertex_count), budget(limit), costs(acquisition), anchors(fixed),
          weights(mean_weights), random(seed) {
        deadline = Clock::now() + std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(seconds));
        const Entry* cursor = reinterpret_cast<const Entry*>(tables);
        for (int factor_index = 0; factor_index < factor_count; ++factor_index) {
            Factor factor;
            factor.width = widths[factor_index];
            factor.table = cursor;
            int states = 1;
            for (int position = factor.width - 1; position >= 0; --position) {
                factor.members[position] = members[4 * factor_index + position];
                factor.strides[position] = states;
                states *= 4;
                incident[factor.members[position]].push_back({factor_index, factor.strides[position]});
            }
            for (int first = 0; first < factor.width; ++first) {
                for (int second = first + 1; second < factor.width; ++second) {
                    int left = factor.members[first];
                    int right = factor.members[second];
                    shared[left][right].push_back({factor_index, factor.strides[first], factor.strides[second]});
                    shared[right][left].push_back({factor_index, factor.strides[second], factor.strides[first]});
                }
            }
            factors.push_back(factor);
            cursor += states;
        }
        for (int vertex = 0; vertex < vertices; ++vertex) {
            if (anchors[vertex] < 0) free_vertices.push_back(vertex);
            for (int choice = 0; choice < 4; ++choice) ranked[vertex][choice] = choice;
            std::sort(ranked[vertex], ranked[vertex] + 4, [&](int left, int right) {
                return costs[4 * vertex + left] < costs[4 * vertex + right];
            });
        }
        nx = factors[vertices + 1].members[1];
        ny = vertices / nx;
    }

    bool expired() const { return Clock::now() >= deadline; }

    double objective(const double* loss) const {
        double maximum = loss[0];
        double mean = 0;
        for (int scenario = 0; scenario < 4; ++scenario) {
            maximum = std::max(maximum, loss[scenario]);
            mean += weights[scenario] * loss[scenario];
        }
        return maximum + mean;
    }

    State initialize(const int* choices) const {
        State state;
        state.indices.resize(factors.size());
        for (int vertex = 0; vertex < vertices; ++vertex) {
            state.choices[vertex] = choices[vertex];
            state.cost += costs[4 * vertex + choices[vertex]];
        }
        for (size_t factor_index = 0; factor_index < factors.size(); ++factor_index) {
            const Factor& factor = factors[factor_index];
            int index = 0;
            for (int position = 0; position < factor.width; ++position)
                index += factor.strides[position] * choices[factor.members[position]];
            state.indices[factor_index] = index;
            for (int scenario = 0; scenario < 4; ++scenario) {
                state.loss[scenario] += factor.table[index].loss[scenario];
                state.flux[scenario] += factor.table[index].flux[scenario];
            }
            state.invalid += factor.table[index].invalid;
        }
        state.objective = objective(state.loss);
        return state;
    }

    Delta single(const State& state, int vertex, int choice) const {
        Delta delta;
        int change = choice - state.choices[vertex];
        delta.cost = costs[4 * vertex + choice] - costs[4 * vertex + state.choices[vertex]];
        for (const Incidence& item : incident[vertex]) {
            const Factor& factor = factors[item.factor];
            int index = state.indices[item.factor];
            delta.add(factor.table[index + change * item.stride], factor.table[index]);
        }
        return delta;
    }

    Delta combine(const State& state, int first, int first_choice, const Delta& left,
                  int second, int second_choice, const Delta& right) const {
        Delta delta;
        for (int scenario = 0; scenario < 4; ++scenario) {
            delta.loss[scenario] = left.loss[scenario] + right.loss[scenario];
            delta.flux[scenario] = left.flux[scenario] + right.flux[scenario];
        }
        delta.cost = left.cost + right.cost;
        delta.invalid = left.invalid + right.invalid;
        for (const Shared& item : shared[first][second]) {
            const Entry* table = factors[item.factor].table;
            int index = state.indices[item.factor];
            int left_step = (first_choice - state.choices[first]) * item.first_stride;
            int right_step = (second_choice - state.choices[second]) * item.second_stride;
            delta.add(table[index + left_step + right_step], table[index + left_step]);
            delta.add(table[index], table[index + right_step]);
        }
        return delta;
    }

    bool feasible(const State& state, const Delta& delta) const {
        if (state.cost + delta.cost > budget || delta.invalid > 0.5) return false;
        for (int scenario = 0; scenario < 4; ++scenario)
            if (std::abs(delta.flux[scenario]) > 1e-6) return false;
        return true;
    }

    bool valid(const State& state) const {
        if (state.cost > budget || state.invalid > 0.5) return false;
        for (int scenario = 0; scenario < 4; ++scenario)
            if (std::abs(state.flux[scenario] - target_flux[scenario]) > 1e-6) return false;
        return true;
    }

    void record(const State& state) {
        if (state.objective < best.objective - 1e-12 && valid(state)) best = state;
    }

    double trial(const State& state, const Delta& delta) const {
        double losses[4];
        for (int scenario = 0; scenario < 4; ++scenario)
            losses[scenario] = state.loss[scenario] + delta.loss[scenario];
        return objective(losses);
    }

    void change(State& state, int vertex, int choice) const {
        int difference = choice - state.choices[vertex];
        for (const Incidence& item : incident[vertex]) state.indices[item.factor] += difference * item.stride;
        state.choices[vertex] = choice;
    }

    void apply(State& state, int first, int first_choice, int second, int second_choice, const Delta& delta) {
        change(state, first, first_choice);
        if (second >= 0) change(state, second, second_choice);
        state.cost += delta.cost;
        for (int scenario = 0; scenario < 4; ++scenario) {
            state.loss[scenario] += delta.loss[scenario];
            state.flux[scenario] += delta.flux[scenario];
        }
        state.invalid += delta.invalid;
        state.objective = objective(state.loss);
        record(state);
    }

    void descent(State& state) {
        ++descents;
        Delta moves[MAX_VERTICES][4];
        while (!expired()) {
            int selected_first = -1, selected_second = -1;
            int selected_first_choice = -1, selected_second_choice = -1;
            Delta selected_delta;
            double selected_objective = state.objective - 1e-12;
            for (int vertex : free_vertices) {
                for (int choice = 0; choice < 4; ++choice) {
                    if (choice == state.choices[vertex]) continue;
                    moves[vertex][choice] = single(state, vertex, choice);
                    const Delta& delta = moves[vertex][choice];
                    if (!feasible(state, delta)) continue;
                    double value = trial(state, delta);
                    if (value < selected_objective) {
                        selected_objective = value;
                        selected_first = vertex;
                        selected_first_choice = choice;
                        selected_second = -1;
                        selected_delta = delta;
                    }
                }
            }
            for (size_t first_index = 0; first_index < free_vertices.size(); ++first_index) {
                int first = free_vertices[first_index];
                for (size_t second_index = first_index + 1; second_index < free_vertices.size(); ++second_index) {
                    int second = free_vertices[second_index];
                    for (int first_choice = 0; first_choice < 4; ++first_choice) {
                        if (first_choice == state.choices[first]) continue;
                        const Delta& left = moves[first][first_choice];
                        for (int second_choice = 0; second_choice < 4; ++second_choice) {
                            if (second_choice == state.choices[second]) continue;
                            const Delta& right = moves[second][second_choice];
                            if (state.cost + left.cost + right.cost > budget) continue;
                            Delta delta = combine(state, first, first_choice, left, second, second_choice, right);
                            if (!feasible(state, delta)) continue;
                            double value = trial(state, delta);
                            ++evaluations;
                            if (value < selected_objective) {
                                selected_objective = value;
                                selected_first = first;
                                selected_first_choice = first_choice;
                                selected_second = second;
                                selected_second_choice = second_choice;
                                selected_delta = delta;
                            }
                        }
                    }
                }
            }
            if (selected_first < 0) return;
            apply(state, selected_first, selected_first_choice, selected_second, selected_second_choice, selected_delta);
        }
    }

    void perturb(State& state, int count, double temperature) {
        int accepted = 0;
        for (int attempt = 0; attempt < count * 100 && accepted < count; ++attempt) {
            int first = free_vertices[random() % free_vertices.size()];
            int first_choice = (state.choices[first] + 1 + random() % 3) % 4;
            Delta delta = single(state, first, first_choice);
            int second = -1;
            int second_choice = -1;
            if (random() % 4 != 0) {
                second = free_vertices[random() % free_vertices.size()];
                if (second == first) continue;
                second_choice = (state.choices[second] + 1 + random() % 3) % 4;
                Delta right = single(state, second, second_choice);
                delta = combine(state, first, first_choice, delta, second, second_choice, right);
            }
            if (!feasible(state, delta)) continue;
            double difference = trial(state, delta) - state.objective;
            double uniform = (random() >> 11) * 0x1.0p-53;
            if (difference > 0 && uniform > std::exp(-difference / temperature)) continue;
            apply(state, first, first_choice, second, second_choice, delta);
            ++accepted;
        }
    }

    double penalty(const State& state, double cost_penalty, double topology_penalty) const {
        double value = cost_penalty * std::max(0, state.cost - budget) + 2.0 * state.invalid;
        for (int scenario = 0; scenario < 4; ++scenario)
            value += topology_penalty * std::abs(state.flux[scenario] - target_flux[scenario]) / (2.0 * M_PI);
        return value;
    }

    void anneal(State& state, int steps, double starting_temperature, bool hard_budget) {
        double log_decay = std::log(0.00002 / starting_temperature);
        double temperature = starting_temperature;
        double cost_penalty = 0.008;
        double topology_penalty = 0.04;
        for (int step = 0; step < steps; ++step) {
            if (step % 256 == 0) {
                if (expired()) return;
                double progress = static_cast<double>(step) / steps;
                temperature = starting_temperature * std::exp(log_decay * progress);
                cost_penalty = 0.008 + 0.09 * progress * progress;
                topology_penalty = 0.04 + 0.30 * progress;
            }
            double old_value = state.objective + penalty(state, cost_penalty, topology_penalty);
            double uniform = (random() >> 11) * 0x1.0p-53;
            if (step % 128 == 0) {
                auto choices = state.choices;
                int start = random() % vertices;
                int width = 1 + random() % nx;
                int height = 1 + random() % ny;
                int rank = random() % 6;
                rank = std::max(0, rank - 2);
                for (int offset_y = 0; offset_y < height; ++offset_y) {
                    for (int offset_x = 0; offset_x < width; ++offset_x) {
                        int vertex = ((start / nx + offset_y) % ny) * nx + (start % nx + offset_x) % nx;
                        if (anchors[vertex] < 0) choices[vertex] = ranked[vertex][rank];
                    }
                }
                State proposal = initialize(choices.data());
                if (hard_budget && proposal.cost > budget) continue;
                double difference = proposal.objective + penalty(proposal, cost_penalty, topology_penalty) - old_value;
                if (difference < 0 || uniform < std::exp(-difference / temperature)) {
                    state = proposal;
                    record(state);
                }
                continue;
            }
            int first = free_vertices[random() % free_vertices.size()];
            int first_choice = (state.choices[first] + 1 + random() % 3) % 4;
            Delta delta = single(state, first, first_choice);
            int second = -1;
            int second_choice = -1;
            if (random() % 2 == 0) {
                second = free_vertices[random() % free_vertices.size()];
                if (second == first) continue;
                second_choice = (state.choices[second] + 1 + random() % 3) % 4;
                Delta right = single(state, second, second_choice);
                delta = combine(state, first, first_choice, delta, second, second_choice, right);
            }
            if (hard_budget && state.cost + delta.cost > budget) continue;
            double value = trial(state, delta);
            value += cost_penalty * std::max(0, state.cost + delta.cost - budget);
            value += 2.0 * (state.invalid + delta.invalid);
            for (int scenario = 0; scenario < 4; ++scenario)
                value += topology_penalty * std::abs(state.flux[scenario] + delta.flux[scenario] - target_flux[scenario]) / (2.0 * M_PI);
            double difference = value - old_value;
            if (difference < 0 || uniform < std::exp(-difference / temperature))
                apply(state, first, first_choice, second, second_choice, delta);
        }
    }

    void run(const int* initial, int* output) {
        best = initialize(initial);
        for (int scenario = 0; scenario < 4; ++scenario) target_flux[scenario] = best.flux[scenario];
        State current = best;
        descent(current);
        long long iteration = 0;
        while (!expired()) {
            if (iteration % 4 != 3) {
                current = best;
                double temperature = 0.008 * std::pow(2.0, static_cast<double>(random() % 5));
                anneal(current, 60000, temperature, iteration % 2 == 0);
                if (valid(current)) descent(current);
                else current = best;
            } else {
                int strength = 3 + random() % 48;
                double temperature = 0.003 * std::pow(2.0, static_cast<double>(random() % 5));
                perturb(current, strength, temperature);
                descent(current);
            }
            if (current.objective > best.objective + 0.025) current = best;
            ++iteration;
        }
        for (int vertex = 0; vertex < vertices; ++vertex) output[vertex] = best.choices[vertex];
        if (std::getenv("ATLAS_DEBUG"))
            std::fprintf(stderr, "objective %.12f descents %lld evaluations %lld\n", best.objective, descents, evaluations);
    }
};

extern "C" void optimize(int vertices, int factor_count, const int* widths, const int* members,
                         const double* tables, const int* costs, const int* anchors,
                         const int* initial, const double* weights, int budget,
                         double seconds, uint64_t seed, int* output) {
    Optimizer optimizer(vertices, factor_count, widths, members, tables, costs, anchors,
                        weights, budget, seconds, seed);
    optimizer.run(initial, output);
}
