#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iostream>
#include <limits>
#include <numeric>
#include <queue>
#include <random>
#include <unordered_map>
#include <utility>
#include <vector>

using Mask = uint32_t;
constexpr int capacity = 28;
constexpr double infinity = 1e30;

struct Gate {
    int control;
    int target;
};

struct Operation {
    int kind;
    int first;
    int second;
};

struct Plan {
    double cost = 0;
    int root = 0;
    std::vector<Gate> gates;
};

struct Instance {
    int size;
    int term_count;
    std::array<std::array<int, capacity>, capacity> errors{};
    std::array<std::array<int, capacity>, capacity> durations{};
    std::vector<Mask> terms;
    std::vector<Gate> edges;

    double cost(const std::vector<Operation>& operations) const {
        std::array<int, capacity> ready{};
        int error = 0;
        for (const auto& operation : operations) {
            if (operation.kind == 0) {
                int control = operation.first;
                int target = operation.second;
                error += errors[control][target];
                ready[control] = ready[target] = std::max(ready[control], ready[target]) + durations[control][target];
            }
        }
        return error + 0.2 * *std::max_element(ready.begin(), ready.begin() + size);
    }

    bool valid(const std::vector<Operation>& operations) const {
        if (operations.size() > 100000) return false;
        std::array<Mask, capacity> rows{};
        std::vector<bool> seen(term_count, false);
        for (int qubit = 0; qubit < size; ++qubit) rows[qubit] = Mask(1) << qubit;
        for (const auto& operation : operations) {
            int first = operation.first;
            int second = operation.second;
            if (first < 0 || first >= size) return false;
            if (operation.kind == 0) {
                if (second < 0 || second >= size || !errors[first][second]) return false;
                rows[second] ^= rows[first];
            } else {
                if (second < 0 || second >= term_count || seen[second] || rows[first] != terms[second]) return false;
                seen[second] = true;
            }
        }
        for (int qubit = 0; qubit < size; ++qubit) if (rows[qubit] != (Mask(1) << qubit)) return false;
        return std::all_of(seen.begin(), seen.end(), [](bool value) { return value; });
    }
};

std::vector<Operation> simplify(const std::vector<Operation>& input) {
    std::vector<Operation> result;
    result.reserve(input.size());
    for (const auto& operation : input) {
        bool canceled = false;
        if (operation.kind == 0) {
            for (int position = int(result.size()) - 1; position >= 0; --position) {
                const auto& previous = result[position];
                if (previous.kind == 1) {
                    if (previous.first == operation.second) break;
                } else if (previous.first == operation.first && previous.second == operation.second) {
                    result.erase(result.begin() + position);
                    canceled = true;
                    break;
                } else if (previous.first == operation.second || previous.second == operation.first) {
                    break;
                }
            }
        }
        if (!canceled) result.push_back(operation);
    }
    return result;
}

std::vector<Operation> schedule(const Instance& instance, const std::vector<Operation>& input, int mode) {
    int count = int(input.size());
    std::vector<std::vector<int>> successors(count);
    std::vector<int> indegree(count, 0);
    std::vector<int> marker(count, -1);
    std::array<int, capacity> last_kind;
    last_kind.fill(-1);
    std::array<std::vector<int>, capacity> current_batch;
    std::array<std::vector<int>, capacity> previous_batch;
    for (int index = 0; index < count; ++index) {
        auto access = [&](int qubit, int kind) {
            if (last_kind[qubit] != kind) {
                previous_batch[qubit] = std::move(current_batch[qubit]);
                current_batch[qubit].clear();
                last_kind[qubit] = kind;
            }
            for (int parent : previous_batch[qubit]) {
                if (marker[parent] != index) {
                    marker[parent] = index;
                    successors[parent].push_back(index);
                    ++indegree[index];
                }
            }
            current_batch[qubit].push_back(index);
        };
        access(input[index].first, 0);
        if (input[index].kind == 0) access(input[index].second, 1);
    }
    std::vector<int> height(count, 0);
    for (int index = count - 1; index >= 0; --index) {
        for (int child : successors[index]) height[index] = std::max(height[index], height[child]);
        if (input[index].kind == 0) height[index] += instance.durations[input[index].first][input[index].second];
    }
    std::vector<int> available;
    for (int index = 0; index < count; ++index) if (!indegree[index]) available.push_back(index);
    std::array<int, capacity> ready{};
    std::vector<Operation> result;
    result.reserve(count);
    while (!available.empty()) {
        int selected = 0;
        double best_score = infinity;
        for (int position = 0; position < int(available.size()); ++position) {
            int index = available[position];
            const auto& operation = input[index];
            double value;
            if (operation.kind == 1) value = -infinity;
            else {
                int start = std::max(ready[operation.first], ready[operation.second]);
                if (mode == 0) value = 100000.0 * start - height[index];
                else if (mode == 1) value = start - 0.35 * height[index];
                else value = 0.3 * start - height[index];
            }
            if (value < best_score) {
                best_score = value;
                selected = position;
            }
        }
        int index = available[selected];
        available[selected] = available.back();
        available.pop_back();
        auto operation = input[index];
        result.push_back(operation);
        if (operation.kind == 0) ready[operation.first] = ready[operation.second] = std::max(ready[operation.first], ready[operation.second]) + instance.durations[operation.first][operation.second];
        for (int child : successors[index]) if (!--indegree[child]) available.push_back(child);
    }
    return simplify(result);
}

std::vector<Gate> remote_sequence(const std::vector<int>& path) {
    std::vector<Gate> result;
    int length = int(path.size()) - 1;
    if (length == 1) return {{path[0], path[1]}};
    for (int position = 0; position < length; ++position) result.push_back({path[position], path[position + 1]});
    for (int position = length - 2; position >= 0; --position) result.push_back({path[position], path[position + 1]});
    for (int position = 1; position < length; ++position) result.push_back({path[position], path[position + 1]});
    for (int position = length - 2; position >= 1; --position) result.push_back({path[position], path[position + 1]});
    return result;
}

struct Router {
    const Instance& instance;
    std::array<std::array<double, capacity>, capacity> weights{};
    std::array<std::array<double, capacity>, capacity> costs{};
    std::array<std::array<std::vector<Gate>, capacity>, capacity> sequences;
    double typical = 1;

    Router(const Instance& problem, double duration_factor) : instance(problem) {
        std::vector<double> samples;
        for (int source = 0; source < instance.size; ++source) {
            weights[source].fill(infinity);
            costs[source].fill(infinity);
        }
        for (auto edge : instance.edges) {
            weights[edge.control][edge.target] = instance.errors[edge.control][edge.target] + duration_factor * instance.durations[edge.control][edge.target];
            samples.push_back(weights[edge.control][edge.target]);
        }
        std::sort(samples.begin(), samples.end());
        typical = samples[samples.size() / 2];
        for (int source = 0; source < instance.size; ++source) {
            std::array<double, capacity> distances;
            std::array<int, capacity> previous;
            std::array<bool, capacity> done{};
            distances.fill(infinity);
            previous.fill(-1);
            distances[source] = 0;
            done[source] = true;
            for (int target = 0; target < instance.size; ++target) {
                if (instance.errors[source][target]) {
                    distances[target] = 2 * weights[source][target];
                    previous[target] = source;
                }
            }
            for (int iteration = 1; iteration < instance.size; ++iteration) {
                int current = -1;
                for (int qubit = 0; qubit < instance.size; ++qubit) {
                    if (!done[qubit] && (current == -1 || distances[qubit] < distances[current])) current = qubit;
                }
                if (current == -1) break;
                done[current] = true;
                for (int neighbor = 0; neighbor < instance.size; ++neighbor) {
                    if (!done[neighbor] && instance.errors[current][neighbor]) {
                        double distance = distances[current] + 4 * weights[current][neighbor];
                        if (distance < distances[neighbor]) {
                            distances[neighbor] = distance;
                            previous[neighbor] = current;
                        }
                    }
                }
            }
            for (int target = 0; target < instance.size; ++target) {
                if (source == target) continue;
                if (instance.errors[source][target]) {
                    costs[source][target] = weights[source][target];
                    sequences[source][target] = {{source, target}};
                }
                for (int before = 0; before < instance.size; ++before) {
                    if (before == source || !instance.errors[before][target]) continue;
                    double candidate = distances[before] + 2 * weights[before][target];
                    if (candidate >= costs[source][target]) continue;
                    std::vector<int> path;
                    int current = before;
                    bool legal = true;
                    while (current != source) {
                        if (current == target || current < 0) {
                            legal = false;
                            break;
                        }
                        path.push_back(current);
                        current = previous[current];
                    }
                    if (!legal) continue;
                    path.push_back(source);
                    std::reverse(path.begin(), path.end());
                    path.push_back(target);
                    sequences[source][target] = remote_sequence(path);
                    costs[source][target] = candidate;
                }
            }
        }
    }
};

struct Planner {
    const Instance& instance;
    const Router& router;
    std::array<std::array<double, capacity>, capacity> distances;
    std::array<std::array<double, capacity>, capacity> metric;
    std::array<std::array<int, capacity>, capacity> next;
    std::unordered_map<Mask, std::vector<Plan>> cache;
    int start_variant;

    Planner(const Instance& problem, const Router& route, int variant, uint32_t seed) : instance(problem), router(route), start_variant(variant / 4) {
        std::mt19937 randomizer(seed);
        std::uniform_real_distribution<double> jitter(0.88, 1.12);
        double mixing = variant % 4 == 0 ? 0.2 : variant % 4 == 1 ? 0.7 : variant % 4 == 2 ? 1.2 : 0.0;
        bool virtual_edges = variant >= 8;
        for (int source = 0; source < instance.size; ++source) {
            for (int target = 0; target < instance.size; ++target) {
                distances[source][target] = infinity;
                metric[source][target] = infinity;
                next[source][target] = -1;
                if (source == target) distances[source][target] = 0;
            }
        }
        for (int source = 0; source < instance.size; ++source) {
            for (int target = source + 1; target < instance.size; ++target) {
                if (!virtual_edges && !instance.errors[source][target]) continue;
                double first = router.costs[source][target];
                double second = router.costs[target][source];
                double value = std::min(first, second) + mixing * std::max(first, second);
                if (variant >= 4) value *= jitter(randomizer);
                metric[source][target] = metric[target][source] = value;
                distances[source][target] = distances[target][source] = value;
                next[source][target] = target;
                next[target][source] = source;
            }
        }
        for (int through = 0; through < instance.size; ++through) {
            for (int source = 0; source < instance.size; ++source) {
                for (int target = 0; target < instance.size; ++target) {
                    double candidate = distances[source][through] + distances[through][target];
                    if (candidate + 1e-9 < distances[source][target]) {
                        distances[source][target] = candidate;
                        next[source][target] = next[source][through];
                    }
                }
            }
        }
        cache.reserve(4096);
    }

    const std::vector<Plan>& plans(Mask mask) {
        auto found = cache.find(mask);
        if (found != cache.end()) return found->second;
        std::vector<int> support;
        for (int qubit = 0; qubit < instance.size; ++qubit) if (mask & (Mask(1) << qubit)) support.push_back(qubit);
        if (support.size() == 1) {
            Plan plan;
            plan.root = support[0];
            return cache.emplace(mask, std::vector<Plan>{plan}).first->second;
        }
        int initial = start_variant == 0 ? 0 : ((mask * 2654435761u + uint32_t(start_variant) * 12345u) >> 8) % support.size();
        Mask reached = Mask(1) << support[initial];
        std::array<std::vector<int>, capacity> tree;
        while ((reached & mask) != mask) {
            int best_source = -1;
            int best_target = -1;
            double best_distance = infinity;
            for (int source = 0; source < instance.size; ++source) {
                if (!(reached & (Mask(1) << source))) continue;
                for (int target : support) {
                    if (reached & (Mask(1) << target)) continue;
                    if (distances[source][target] < best_distance) {
                        best_distance = distances[source][target];
                        best_source = source;
                        best_target = target;
                    }
                }
            }
            int current = best_target;
            while (!(reached & (Mask(1) << current))) {
                int neighbor = next[current][best_source];
                tree[current].push_back(neighbor);
                tree[neighbor].push_back(current);
                reached |= Mask(1) << current;
                current = neighbor;
            }
        }
        std::vector<Plan> result;
        for (int root = 0; root < instance.size; ++root) {
            if (!(reached & (Mask(1) << root))) continue;
            Plan plan;
            plan.root = root;
            std::function<void(int, int)> gather = [&](int qubit, int parent) {
                std::vector<int> children;
                for (int neighbor : tree[qubit]) if (neighbor != parent) children.push_back(neighbor);
                bool active = mask & (Mask(1) << qubit);
                if (!active) {
                    std::sort(children.begin(), children.end(), [&](int first, int second) { return router.costs[qubit][first] < router.costs[qubit][second]; });
                }
                for (int child : children) {
                    gather(child, qubit);
                    if (!active) {
                        plan.gates.push_back({qubit, child});
                        plan.cost += router.costs[qubit][child];
                        active = true;
                    }
                    plan.gates.push_back({child, qubit});
                    plan.cost += router.costs[child][qubit];
                }
            };
            gather(root, -1);
            result.push_back(std::move(plan));
        }
        std::stable_sort(result.begin(), result.end(), [](const Plan& first, const Plan& second) { return first.cost < second.cost; });
        return cache.emplace(mask, std::move(result)).first->second;
    }
};

struct Compilation {
    std::vector<Operation> prefix;
    std::vector<Gate> history;
    std::array<Mask, capacity> rows{};
};

struct Checkpoint {
    size_t history_size;
    std::vector<Mask> masks;
    std::vector<double> costs;
    std::array<Mask, capacity> rows;
};

Compilation compile(const Instance& instance, Planner& planner, std::mt19937& randomizer, int mode, double noise, double reset_ratio, bool branching) {
    Compilation result;
    auto masks = instance.terms;
    std::vector<double> original_costs;
    for (Mask mask : masks) original_costs.push_back(planner.plans(mask)[0].cost);
    int remaining = instance.term_count;
    for (int qubit = 0; qubit < instance.size; ++qubit) result.rows[qubit] = Mask(1) << qubit;
    auto emit = [&]() {
        for (int term = 0; term < instance.term_count; ++term) {
            Mask mask = masks[term];
            if (mask && !(mask & (mask - 1))) {
                result.prefix.push_back({1, __builtin_ctz(mask), term});
                masks[term] = 0;
                --remaining;
            }
        }
    };
    emit();
    std::vector<Checkpoint> checkpoints;
    checkpoints.push_back({0, masks, original_costs, result.rows});
    std::uniform_real_distribution<double> jitter(1.0 - noise, 1.0 + noise);
    while (remaining) {
        std::vector<std::pair<double, int>> candidates;
        std::vector<double> current_costs(instance.term_count, 0);
        double current_minimum = infinity;
        for (int term = 0; term < instance.term_count; ++term) {
            if (!masks[term]) continue;
            const auto& options = planner.plans(masks[term]);
            candidates.emplace_back(options[0].cost * jitter(randomizer), term);
            current_costs[term] = options[0].cost;
            current_minimum = std::min(current_minimum, options[0].cost);
        }
        if (reset_ratio > 0 && !result.history.empty()) {
            int checkpoint_index = -1;
            double best_checkpoint = reset_ratio * current_minimum;
            int checkpoint_count = branching ? int(checkpoints.size()) : 1;
            for (int checkpoint = 0; checkpoint < checkpoint_count; ++checkpoint) {
                if (checkpoints[checkpoint].history_size >= result.history.size()) continue;
                double minimum = infinity;
                for (int term = 0; term < instance.term_count; ++term) if (masks[term]) minimum = std::min(minimum, checkpoints[checkpoint].costs[term]);
                if (minimum < best_checkpoint) {
                    best_checkpoint = minimum;
                    checkpoint_index = checkpoint;
                }
            }
            if (checkpoint_index >= 0) {
                const auto& checkpoint = checkpoints[checkpoint_index];
                for (int position = int(result.history.size()) - 1; position >= int(checkpoint.history_size); --position) result.prefix.push_back({0, result.history[position].control, result.history[position].target});
                result.history.resize(checkpoint.history_size);
                for (int term = 0; term < instance.term_count; ++term) if (masks[term]) masks[term] = checkpoint.masks[term];
                result.rows = checkpoint.rows;
                checkpoints.resize(checkpoint_index + 1);
                continue;
            }
        }
        if (branching && checkpoints.back().history_size != result.history.size()) checkpoints.push_back({result.history.size(), masks, current_costs, result.rows});
        std::sort(candidates.begin(), candidates.end());
        const Plan* selected = nullptr;
        double best_score = infinity;
        int candidate_count = mode >= 2 ? std::min(int(candidates.size()), 4) : 1;
        for (int candidate = 0; candidate < candidate_count; ++candidate) {
            int term = candidates[candidate].second;
            const auto& options = planner.plans(masks[term]);
            int root_count = mode == 0 ? 1 : std::min(int(options.size()), 8);
            for (int root_index = 0; root_index < root_count; ++root_index) {
                const auto& option = options[root_index];
                if (option.cost > options[0].cost * 1.35 + 0.5) continue;
                double value = option.cost;
                if (mode == 1) value *= jitter(randomizer);
                if (mode >= 2) {
                    double change = 0;
                    int newly_ready = 0;
                    for (Mask before : masks) {
                        if (!before) continue;
                        Mask after = before;
                        for (auto gate : option.gates) if (after & (Mask(1) << gate.target)) after ^= Mask(1) << gate.control;
                        int old_count = __builtin_popcount(before);
                        int new_count = __builtin_popcount(after);
                        if (mode == 4) change += std::log(double(new_count)) - std::log(double(old_count));
                        else change += new_count - old_count;
                        if (new_count == 1) ++newly_ready;
                    }
                    double strength = mode == 2 ? 0.12 : mode == 3 ? 0.35 : mode == 4 ? 0.8 : 0.7;
                    value += strength * planner.router.typical * change;
                    value -= planner.router.typical * 0.3 * (newly_ready - 1);
                    value *= jitter(randomizer);
                }
                if (value < best_score) {
                    best_score = value;
                    selected = &option;
                }
            }
        }
        auto gates = selected->gates;
        for (auto logical : gates) {
            for (auto gate : planner.router.sequences[logical.control][logical.target]) {
                result.prefix.push_back({0, gate.control, gate.target});
                result.history.push_back(gate);
                result.rows[gate.target] ^= result.rows[gate.control];
                for (Mask& mask : masks) if (mask & (Mask(1) << gate.target)) mask ^= Mask(1) << gate.control;
                emit();
            }
        }
    }
    return result;
}

std::vector<Operation> reverse_finish(const Compilation& compilation) {
    auto result = compilation.prefix;
    for (auto position = compilation.history.rbegin(); position != compilation.history.rend(); ++position) result.push_back({0, position->control, position->target});
    return simplify(result);
}

std::vector<Operation> linear_finish(const Instance& instance, const Router& router, const Compilation& compilation, int mode) {
    auto rows = compilation.rows;
    std::vector<Gate> left;
    std::vector<Gate> right;
    auto row_add = [&](int control, int target) {
        rows[target] ^= rows[control];
        left.push_back({control, target});
    };
    auto column_add = [&](int control, int target) {
        for (int qubit = 0; qubit < instance.size; ++qubit) if (rows[qubit] & (Mask(1) << target)) rows[qubit] ^= Mask(1) << control;
        right.push_back({control, target});
    };
    if (mode != 0) {
        for (int iteration = 0; iteration < instance.size * instance.size; ++iteration) {
            std::array<Mask, capacity> columns{};
            for (int qubit = 0; qubit < instance.size; ++qubit) {
                for (int column = 0; column < instance.size; ++column) if (rows[qubit] & (Mask(1) << column)) columns[column] |= Mask(1) << qubit;
            }
            double best_gain = 1e-9;
            Gate selected{-1, -1};
            bool transpose = false;
            for (int control = 0; control < instance.size; ++control) {
                for (int target = 0; target < instance.size; ++target) {
                    if (control == target) continue;
                    double cost = std::pow(router.costs[control][target], mode == 2 ? 0.6 : 1.0);
                    int gain = __builtin_popcount(rows[target] ^ (Mask(1) << target)) - __builtin_popcount(rows[target] ^ rows[control] ^ (Mask(1) << target));
                    if (gain / cost > best_gain) {
                        best_gain = gain / cost;
                        selected = {control, target};
                        transpose = false;
                    }
                    gain = __builtin_popcount(columns[control] ^ (Mask(1) << control)) - __builtin_popcount(columns[control] ^ columns[target] ^ (Mask(1) << control));
                    if (gain / cost > best_gain) {
                        best_gain = gain / cost;
                        selected = {control, target};
                        transpose = true;
                    }
                }
            }
            if (selected.control < 0) break;
            if (transpose) column_add(selected.control, selected.target);
            else row_add(selected.control, selected.target);
        }
    }
    Mask fixed = 0;
    for (int iteration = 0; iteration < instance.size; ++iteration) {
        double best_cost = infinity;
        int pivot = -1;
        int fill = -1;
        for (int qubit = 0; qubit < instance.size; ++qubit) {
            if (fixed & (Mask(1) << qubit)) continue;
            double cost = 0;
            int filling = -1;
            if (!(rows[qubit] & (Mask(1) << qubit))) {
                double best = infinity;
                for (int source = 0; source < instance.size; ++source) {
                    if (!(fixed & (Mask(1) << source)) && (rows[source] & (Mask(1) << qubit)) && router.costs[source][qubit] < best) {
                        best = router.costs[source][qubit];
                        filling = source;
                    }
                }
                cost += best;
            }
            for (int target = 0; target < instance.size; ++target) if (target != qubit && (rows[target] & (Mask(1) << qubit))) cost += router.costs[qubit][target];
            if (cost < best_cost) {
                best_cost = cost;
                pivot = qubit;
                fill = filling;
            }
        }
        if (fill >= 0) row_add(fill, pivot);
        for (int target = 0; target < instance.size; ++target) if (target != pivot && (rows[target] & (Mask(1) << pivot))) row_add(pivot, target);
        fixed |= Mask(1) << pivot;
    }
    auto result = compilation.prefix;
    for (auto logical : left) for (auto native : router.sequences[logical.control][logical.target]) result.push_back({0, native.control, native.target});
    for (auto position = right.rbegin(); position != right.rend(); ++position) for (auto native : router.sequences[position->control][position->target]) result.push_back({0, native.control, native.target});
    return simplify(result);
}

int main(int argument_count, char** arguments) {
    auto started = std::chrono::steady_clock::now();
    double budget = argument_count > 1 ? std::atof(arguments[1]) : 8.0;
    int max_iterations = argument_count > 2 ? std::atoi(arguments[2]) : 100000;
    Instance instance;
    int edge_count;
    if (!(std::cin >> instance.size >> edge_count >> instance.term_count)) return 1;
    for (int edge_index = 0; edge_index < edge_count; ++edge_index) {
        int control, target, error, duration;
        std::cin >> control >> target >> error >> duration;
        instance.errors[control][target] = error;
        instance.durations[control][target] = duration;
        instance.edges.push_back({control, target});
    }
    uint32_t seed = 20260828;
    for (int term = 0; term < instance.term_count; ++term) {
        Mask mask;
        std::cin >> mask;
        instance.terms.push_back(mask);
        seed = (seed ^ mask) * 16777619u;
    }
    std::mt19937 randomizer(seed);
    Router router(instance, 0.12);
    std::vector<Operation> best;
    double best_cost = infinity;
    std::string label;
    std::string best_label;
    int iteration = 0;
    auto elapsed = [&]() { return std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count(); };
    auto consider = [&](std::vector<Operation> operations) {
        double cost = instance.cost(operations);
        if (cost < best_cost && instance.valid(operations)) {
            best_cost = cost;
            best_label = label;
            best = std::move(operations);
        }
    };
    {
        Planner initial(instance, router, 0, seed);
        std::vector<Operation> fallback;
        for (int term = 0; term < instance.term_count; ++term) {
            const auto& plan = initial.plans(instance.terms[term])[0];
            std::vector<Gate> history;
            for (auto logical : plan.gates) {
                for (auto native : router.sequences[logical.control][logical.target]) {
                    fallback.push_back({0, native.control, native.target});
                    history.push_back(native);
                }
            }
            fallback.push_back({1, plan.root, term});
            for (auto position = history.rbegin(); position != history.rend(); ++position) fallback.push_back({0, position->control, position->target});
        }
        label = "independent";
        consider(simplify(fallback));
    }
    while (iteration < max_iterations && (best.empty() || elapsed() < budget)) {
        if (best_cost == 0) break;
        const int variants[] = {0, 9, 1, 10, 4, 12, 5, 8, 2, 11, 6, 13, 3, 14, 7, 15};
        int variant = variants[(iteration / 24) % 16];
        Planner planner(instance, router, variant, randomizer());
        for (int repeat = 0; repeat < 24 && iteration < max_iterations; ++repeat, ++iteration) {
            if (!best.empty() && elapsed() >= budget) break;
            if (planner.cache.size() > 12000) planner.cache.clear();
            int mode = repeat % 6;
            double noise = repeat < 6 ? 0.0 : repeat < 12 ? 0.08 : repeat < 18 ? 0.18 : 0.3;
            double reset_ratio = repeat < 6 ? 0.0 : repeat < 18 ? 0.85 : 1.05;
            bool branching = repeat >= 12;
            auto compilation = compile(instance, planner, randomizer, mode, noise, reset_ratio, branching);
            auto operations = reverse_finish(compilation);
            double cost = instance.cost(operations);
            bool promising = cost < best_cost * 1.12;
            label = "v" + std::to_string(variant) + "m" + std::to_string(mode) + "r" + std::to_string(reset_ratio) + (branching ? "b1" : "b0") + "fR";
            consider(std::move(operations));
            if (promising) {
                for (int finish_mode = 0; finish_mode < 3; ++finish_mode) {
                    label.back() = char('0' + finish_mode);
                    consider(linear_finish(instance, router, compilation, finish_mode));
                }
            }
        }
    }
    for (int mode = 0; mode < 3; ++mode) {
        label = best_label + "s" + std::to_string(mode);
        consider(schedule(instance, best, mode));
    }
    if (best_cost == 0) {
        auto selected = *std::min_element(instance.edges.begin(), instance.edges.end(), [&](Gate first, Gate second) { return router.weights[first.control][first.target] < router.weights[second.control][second.target]; });
        best.push_back({0, selected.control, selected.target});
        best.push_back({0, selected.control, selected.target});
        best_cost = instance.cost(best);
    }
    std::cerr << "cost=" << best_cost << " iterations=" << iteration << " seconds=" << elapsed() << " best=" << best_label << '\n';
    if (best.empty()) return 2;
    std::cout << "{\"ops\":[";
    bool first = true;
    for (const auto& operation : best) {
        if (!first) std::cout << ',';
        first = false;
        std::cout << "[\"" << (operation.kind == 0 ? "cx" : "rz") << "\"," << operation.first << ',' << operation.second << ']';
    }
    std::cout << "]}\n";
}
