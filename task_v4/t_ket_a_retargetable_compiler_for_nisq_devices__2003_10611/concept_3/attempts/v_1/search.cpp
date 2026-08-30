#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <queue>
#include <random>
#include <string>
#include <unordered_set>
#include <vector>

using Mask = uint32_t;
using Gate = std::pair<int, int>;
std::mt19937_64 random_engine(427);
double uniform() { return std::generate_canonical<double, 53>(random_engine); }
int weight(Mask mask) { return __builtin_popcount(mask); }
double phase_bonus = 1.0;
double matrix_weight = 1.0;
double steiner_weight = 1.0;

struct Case {
    std::string name;
    int size, edge_count, parity_count, count_budget, depth_budget;
    std::vector<Gate> edges, directed;
    std::vector<Mask> targets, parities;
    std::vector<std::vector<int>> adjacent;
    std::vector<std::vector<std::vector<Gate>>> remote;
    std::vector<uint8_t> steiner, cost;
    void prepare() {
        adjacent.resize(size);
        for (auto [first, second] : edges) {
            adjacent[first].push_back(second);
            adjacent[second].push_back(first);
            directed.push_back({first, second});
            directed.push_back({second, first});
        }
        std::vector<Mask> neighbors(size);
        for (int wire = 0; wire < size; ++wire)
            for (int neighbor : adjacent[wire]) neighbors[wire] |= 1u << neighbor;
        remote.resize(size, std::vector<std::vector<Gate>>(size));
        for (int control = 0; control < size; ++control) {
            std::vector<int> parent(size, -1), order{control};
            parent[control] = control;
            for (int position = 0; position < int(order.size()); ++position)
                for (int neighbor : adjacent[order[position]])
                    if (parent[neighbor] < 0) { parent[neighbor] = order[position]; order.push_back(neighbor); }
            for (int target = 0; target < size; ++target) {
                if (control == target) continue;
                std::vector<int> path{target};
                while (path.back() != control) path.push_back(parent[path.back()]);
                std::reverse(path.begin(), path.end());
                int length = path.size() - 1;
                auto& gates = remote[control][target];
                for (int index = 0; index < length; ++index) gates.push_back({path[index], path[index + 1]});
                for (int index = length - 2; index >= 0; --index) gates.push_back({path[index], path[index + 1]});
                for (int index = 1; index < length; ++index) gates.push_back({path[index], path[index + 1]});
                for (int index = length - 2; index >= 1; --index) gates.push_back({path[index], path[index + 1]});
            }
        }
        steiner.assign(1 << size, size);
        for (Mask mask = 1; mask < (1u << size); ++mask) {
            Mask reached = mask & -mask, frontier = reached;
            while (frontier) {
                int vertex = __builtin_ctz(frontier);
                frontier &= frontier - 1;
                Mask added = neighbors[vertex] & mask & ~reached;
                frontier |= added;
                reached |= added;
            }
            if (reached == mask) steiner[mask] = weight(mask);
        }
        for (int bit = 0; bit < size; ++bit)
            for (Mask mask = 1; mask < (1u << size); ++mask)
                if (!(mask & (1u << bit))) steiner[mask] = std::min(steiner[mask], steiner[mask | (1u << bit)]);
        cost.resize(1 << size);
        for (Mask mask = 1; mask < (1u << size); ++mask) cost[mask] = 2 * steiner[mask] - weight(mask) - 1;
    }
};

struct State {
    std::array<Mask, 20> matrix{}, inverse{};
    std::array<Mask, 34> forward_parities{}, backward_parities{};
    uint64_t remaining = 0;
    std::array<int, 20> front_clock{}, back_clock{};
    int front_depth = 0, back_depth = 0;
    std::vector<Gate> front, back;
};

std::array<Mask, 20> invert(std::array<Mask, 20> matrix, int size) {
    std::array<Mask, 20> inverse{};
    for (int wire = 0; wire < size; ++wire) inverse[wire] = 1u << wire;
    for (int column = 0; column < size; ++column) {
        int pivot = column;
        while (!(matrix[pivot] & (1u << column))) ++pivot;
        std::swap(matrix[column], matrix[pivot]);
        std::swap(inverse[column], inverse[pivot]);
        for (int row = 0; row < size; ++row)
            if (row != column && (matrix[row] & (1u << column))) {
                matrix[row] ^= matrix[column];
                inverse[row] ^= inverse[column];
            }
    }
    return inverse;
}

Mask multiply(Mask mask, const std::array<Mask, 20>& matrix) {
    Mask result = 0;
    while (mask) {
        int bit = __builtin_ctz(mask);
        mask &= mask - 1;
        result ^= matrix[bit];
    }
    return result;
}

State initial(const Case& instance) {
    State state;
    std::copy(instance.targets.begin(), instance.targets.end(), state.matrix.begin());
    state.inverse = invert(state.matrix, instance.size);
    state.remaining = (1ull << instance.parity_count) - 1;
    for (int index = 0; index < instance.parity_count; ++index) {
        state.forward_parities[index] = instance.parities[index];
        state.backward_parities[index] = multiply(instance.parities[index], state.inverse);
        if (weight(state.forward_parities[index]) == 1 || weight(state.backward_parities[index]) == 1)
            state.remaining &= ~(1ull << index);
    }
    return state;
}

void apply(State& state, const Case& instance, int direction, bool backward, bool record = true) {
    auto [control, target] = instance.directed[direction];
    auto& matrix = backward ? state.inverse : state.matrix;
    auto& inverse = backward ? state.matrix : state.inverse;
    auto& parities = backward ? state.backward_parities : state.forward_parities;
    auto& clock = backward ? state.back_clock : state.front_clock;
    auto& depth = backward ? state.back_depth : state.front_depth;
    for (int row = 0; row < instance.size; ++row)
        if (matrix[row] & (1u << target)) matrix[row] ^= 1u << control;
    inverse[target] ^= inverse[control];
    for (uint64_t pending = state.remaining; pending; pending &= pending - 1) {
        int index = __builtin_ctzll(pending);
        if (parities[index] & (1u << target)) parities[index] ^= 1u << control;
        if (weight(parities[index]) == 1) state.remaining &= ~(1ull << index);
    }
    clock[control] = clock[target] = 1 + std::max(clock[control], clock[target]);
    depth = std::max(depth, clock[target]);
    if (record) (backward ? state.back : state.front).push_back({control, target});
}

double evaluate(const State& state, const Case& instance, double parity_weight, double root_weight) {
    double result = 0;
    for (int wire = 0; wire < instance.size; ++wire) {
        Mask first = state.matrix[wire], second = state.inverse[wire], root = 1u << wire;
        result += steiner_weight * (instance.cost[first] + instance.cost[second])
            + (1 - steiner_weight) * (weight(first) + weight(second) - 2);
        result += root_weight * (2 * (instance.steiner[first | root] - instance.steiner[first]) + !(first & root));
        result += root_weight * (2 * (instance.steiner[second | root] - instance.steiner[second]) + !(second & root));
    }
    result *= matrix_weight;
    for (uint64_t pending = state.remaining; pending; pending &= pending - 1) {
        int index = __builtin_ctzll(pending);
        int first = instance.cost[state.forward_parities[index]], second = instance.cost[state.backward_parities[index]];
        result += parity_weight * (std::min(first, second) + phase_bonus);
    }
    return result;
}

uint64_t fingerprint(const State& state, const Case& instance) {
    uint64_t result = state.remaining + 0x9e3779b97f4a7c15ull;
    for (int wire = 0; wire < instance.size; ++wire)
        result = (result ^ state.matrix[wire]) * 0x100000001b3ull;
    for (uint64_t pending = state.remaining; pending; pending &= pending - 1) {
        int index = __builtin_ctzll(pending);
        result = (result ^ state.forward_parities[index]) * 0x100000001b3ull;
        result = (result ^ state.backward_parities[index]) * 0x100000001b3ull;
    }
    return result;
}

bool finished(const State& state, const Case& instance) {
    if (state.remaining) return false;
    for (int wire = 0; wire < instance.size; ++wire)
        if (state.matrix[wire] != (1u << wire)) return false;
    return true;
}

double depth_cost(const State& state, const Case& instance) {
    double maximum = 0, total = 0;
    for (int wire = 0; wire < instance.size; ++wire) {
        double clock = state.front_clock[wire] + state.back_clock[wire];
        maximum = std::max(maximum, clock);
        total += clock;
    }
    double exponential = 0;
    for (int wire = 0; wire < instance.size; ++wire)
        exponential += std::exp((state.front_clock[wire] + state.back_clock[wire] - maximum) * 0.5);
    return maximum + std::log(exponential) * 2 + total / instance.size;
}

std::vector<Gate> circuit(const State& state) {
    auto result = state.front;
    result.insert(result.end(), state.back.rbegin(), state.back.rend());
    return result;
}

int get_depth(const std::vector<Gate>& gates, int size) {
    std::vector<int> clocks(size);
    for (auto [control, target] : gates) clocks[control] = clocks[target] = 1 + std::max(clocks[control], clocks[target]);
    return *std::max_element(clocks.begin(), clocks.end());
}

bool validate(const Case& instance, const std::vector<Gate>& gates) {
    std::vector<Mask> rows(instance.size);
    std::unordered_set<Mask> visited;
    for (int wire = 0; wire < instance.size; ++wire) visited.insert(rows[wire] = 1u << wire);
    for (auto [control, target] : gates) visited.insert(rows[target] ^= rows[control]);
    if (rows != instance.targets) return false;
    for (auto parity : instance.parities) if (!visited.count(parity)) return false;
    return true;
}

void save(const Case& instance, const std::vector<Gate>& gates, const std::string& prefix = "best_") {
    if (!validate(instance, gates)) { std::cerr << "INVALID\n"; std::abort(); }
    std::ofstream output(prefix + instance.name + ".txt");
    for (auto [control, target] : gates) output << control << ' ' << target << '\n';
}

#ifndef SEARCH_LIBRARY
int main(int argc, char** argv) {
    std::ifstream input("instances.txt");
    int case_count;
    input >> case_count;
    int chosen = argc > 1 ? std::stoi(argv[1]) : 0;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 60;
    for (int case_index = 0; case_index < case_count; ++case_index) {
        Case instance;
        input >> instance.name >> instance.size >> instance.edge_count >> instance.parity_count >> instance.count_budget >> instance.depth_budget;
        instance.edges.resize(instance.edge_count);
        instance.targets.resize(instance.size);
        instance.parities.resize(instance.parity_count);
        for (auto& edge : instance.edges) input >> edge.first >> edge.second;
        for (auto& mask : instance.targets) input >> mask;
        for (auto& mask : instance.parities) input >> mask;
        if (case_index != chosen) continue;
        instance.prepare();
        auto start = std::chrono::steady_clock::now();
        double best = 1e100, lowest = 1e100;
        int attempts = 0, successes = 0;
        while (std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds) {
            State state = initial(instance);
            std::unordered_set<uint64_t> visited;
            visited.insert(fingerprint(state, instance));
            double parity_weight = 0.3 + 3.0 * uniform();
            double root_weight = 0.3 + 1.5 * uniform();
            double depth_weight = 0.1 + 6.0 * uniform();
            double noise = 0.15 + 1.5 * uniform();
            int stale = 0;
            double best_cost = evaluate(state, instance, parity_weight, root_weight);
            for (int step = 0; step < 3 * instance.count_budget; ++step) {
                if (finished(state, instance)) {
                    ++successes;
                    auto gates = circuit(state);
                    int depth = get_depth(gates, instance.size);
                    double score = std::max(double(gates.size()) / instance.count_budget, double(depth) / instance.depth_budget)
                        + 0.02 * (double(gates.size()) / instance.count_budget + double(depth) / instance.depth_budget);
                    if (score < best) {
                        best = score;
                        save(instance, gates);
                        std::cout << instance.name << " attempt " << attempts << " count " << gates.size() << " depth " << depth << " score " << best << std::endl;
                    }
                    break;
                }
                double choice_cost = 1e100;
                int choice = -1;
                bool choice_back = false;
                double old_depth_cost = depth_cost(state, instance);
                for (int side = 0; side < 2; ++side) {
                    for (int direction = 0; direction < int(instance.directed.size()); ++direction) {
                        State next = state;
                        apply(next, instance, direction, side, false);
                        uint64_t hash = fingerprint(next, instance);
                        if (visited.count(hash)) continue;
                        double value = evaluate(next, instance, parity_weight, root_weight)
                            + depth_weight * (depth_cost(next, instance) - old_depth_cost)
                            + noise * uniform();
                        if (value < choice_cost) { choice_cost = value; choice = direction; choice_back = side; }
                    }
                }
                if (choice == -1) break;
                apply(state, instance, choice, choice_back);
                visited.insert(fingerprint(state, instance));
                double current = evaluate(state, instance, parity_weight, root_weight);
                lowest = std::min(lowest, current);
                if (current + 0.1 < best_cost) { best_cost = current; stale = 0; } else ++stale;
                if (stale > 60) break;
            }
            ++attempts;
            if (attempts % 100 == 0) std::cout << "progress " << instance.name << ' ' << attempts << " success " << successes << " low " << lowest << std::endl;
        }
    }
    return 0;
}
#endif
