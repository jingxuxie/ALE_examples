#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <limits>
#include <queue>
#include <sstream>
#include <utility>
#include <vector>

using namespace std;

constexpr int MAX_N = 28;
constexpr int MAX_G = 256;
constexpr int METRICS = 9;

struct Random {
    uint64_t state = 0x123456789abcdefULL;
    uint64_t next() {
        state ^= state >> 12;
        state ^= state << 25;
        state ^= state >> 27;
        return state * 2685821657736338717ULL;
    }
    double uniform() { return (next() >> 11) * 0x1.0p-53; }
    int integer(int bound) { return next() % bound; }
};

struct Edge { int first, second; double weight; };
struct Gate {
    int first, second;
    vector<int> successors;
    int predecessors = 0;
    int next_first, next_second;
};
struct Operation { int kind, first, second; };
struct Result {
    vector<Operation> operations;
    double cost = 1e100;
    double work = 0;
    int depth = 0;
    int swaps = 0;
};
struct Parameters {
    int metric = 0;
    int lookahead = 24;
    double future = 0.7;
    double cost = 0.1;
    double decay = 0.0;
    double noise = 0.0;
    double discount = 1.0;
    double jitter = 0.0;
    double priority = 0.0;
};

struct BeamState {
    array<int, MAX_N> positions, occupants, depths, next;
    int completed = 0, depth = 0, trace = -1;
    double work = 0, score = 0;
    uint64_t hash = 0;
};

struct Trace { Operation operation; int parent; };

struct Router {
    int count, gate_count, edge_count;
    vector<Edge> edges;
    vector<Gate> gates;
    vector<int> adjacency[MAX_N];
    int edge_index[MAX_N][MAX_N];
    int initial[MAX_N];
    double distance[METRICS][MAX_N][MAX_N];
    uint64_t zobrist[MAX_N][MAX_N];
    uint64_t gate_hash[MAX_G];
    vector<vector<int>> paths[MAX_N][MAX_N];
    int first_gate[MAX_N];
    chrono::steady_clock::time_point stop_time = chrono::steady_clock::time_point::max();
    Random random;

    Router() {
        cin >> count >> gate_count >> edge_count;
        for (int logical = 0; logical < count; ++logical) cin >> initial[logical];
        fill(&edge_index[0][0], &edge_index[0][0] + MAX_N * MAX_N, -1);
        for (int index = 0; index < edge_count; ++index) {
            Edge edge;
            cin >> edge.first >> edge.second >> edge.weight;
            edges.push_back(edge);
            adjacency[edge.first].push_back(index);
            adjacency[edge.second].push_back(index);
            edge_index[edge.first][edge.second] = edge_index[edge.second][edge.first] = index;
            random.state ^= uint64_t(edge.weight * 10000 + 123) << (index % 40);
        }
        gates.resize(gate_count);
        int latest[MAX_N];
        fill(latest, latest + count, -1);
        for (int index = 0; index < gate_count; ++index) {
            Gate &gate = gates[index];
            cin >> gate.first >> gate.second;
            int previous_first = latest[gate.first], previous_second = latest[gate.second];
            if (previous_first >= 0) { gates[previous_first].successors.push_back(index); ++gate.predecessors; }
            if (previous_second >= 0 && previous_second != previous_first) {
                gates[previous_second].successors.push_back(index); ++gate.predecessors;
            }
            latest[gate.first] = latest[gate.second] = index;
            random.state ^= uint64_t(index * 32 + gate.first * 127 + gate.second * 513 + 1);
            random.next();
        }
        for (int logical = 0; logical < count; ++logical)
            for (int physical = 0; physical < count; ++physical) zobrist[logical][physical] = random.next();
        fill(first_gate, first_gate + count, gate_count);
        for (int gate_id = gate_count - 1; gate_id >= 0; --gate_id) {
            Gate &gate = gates[gate_id];
            gate.next_first = first_gate[gate.first];
            gate.next_second = first_gate[gate.second];
            first_gate[gate.first] = first_gate[gate.second] = gate_id;
            gate_hash[gate_id] = random.next();
        }
        prepare_distances();
        prepare_paths();
    }

    void prepare_paths() {
        for (int variant = 0; variant < 6; ++variant) {
            double lengths[MAX_N * MAX_N];
            for (int edge_id = 0; edge_id < edge_count; ++edge_id) {
                double exponent = variant == 0 ? 0.0 : variant == 1 ? 1.0 : variant == 2 ? 0.5 : 0.0;
                lengths[edge_id] = pow(edges[edge_id].weight, exponent);
                if (variant >= 3) lengths[edge_id] *= 1.0 + random.uniform() * 0.7;
                else lengths[edge_id] += random.uniform() * 1e-5;
            }
            for (int source = 0; source < count; ++source) {
                double distances[MAX_N];
                int parent[MAX_N];
                bool settled[MAX_N] = {};
                fill(distances, distances + count, 1e100);
                distances[source] = 0; parent[source] = -1;
                for (int iteration = 0; iteration < count; ++iteration) {
                    int current = -1;
                    for (int physical = 0; physical < count; ++physical)
                        if (!settled[physical] && (current < 0 || distances[physical] < distances[current])) current = physical;
                    settled[current] = true;
                    for (int edge_id : adjacency[current]) {
                        const Edge &edge = edges[edge_id];
                        int neighbor = edge.first ^ edge.second ^ current;
                        if (distances[current] + lengths[edge_id] < distances[neighbor]) {
                            distances[neighbor] = distances[current] + lengths[edge_id]; parent[neighbor] = current;
                        }
                    }
                }
                for (int target = 0; target < count; ++target) {
                    if (source == target) continue;
                    vector<int> path;
                    for (int current = target; current >= 0; current = parent[current]) path.push_back(current);
                    reverse(path.begin(), path.end());
                    auto &options = paths[source][target];
                    if (find(options.begin(), options.end(), path) == options.end()) options.push_back(move(path));
                }
            }
        }
    }

    void beam_close(BeamState &state, vector<Operation> &operations) {
        bool changed = true;
        while (changed) {
            changed = false;
            for (int logical = 0; logical < count; ++logical) {
                int gate_id = state.next[logical];
                if (gate_id == gate_count) continue;
                const Gate &gate = gates[gate_id];
                if (gate.first != logical || state.next[gate.second] != gate_id) continue;
                int first = state.positions[gate.first], second = state.positions[gate.second];
                int edge_id = edge_index[first][second];
                if (edge_id < 0) continue;
                state.work += edges[edge_id].weight;
                int finish = max(state.depths[first], state.depths[second]) + 1;
                state.depths[first] = state.depths[second] = finish;
                state.depth = max(state.depth, finish);
                state.next[gate.first] = gate.next_first;
                state.next[gate.second] = gate.next_second;
                state.hash ^= gate_hash[gate_id];
                ++state.completed;
                operations.push_back({0, gate_id, 0});
                changed = true;
            }
        }
    }

    void beam_swap(BeamState &state, int first, int second, vector<Operation> &operations) {
        int logical_first = state.occupants[first], logical_second = state.occupants[second];
        state.hash ^= zobrist[logical_first][first] ^ zobrist[logical_first][second]
            ^ zobrist[logical_second][first] ^ zobrist[logical_second][second];
        swap(state.occupants[first], state.occupants[second]);
        state.positions[logical_first] = second; state.positions[logical_second] = first;
        state.work += 3 * edges[edge_index[first][second]].weight;
        int finish = max(state.depths[first], state.depths[second]) + 3;
        state.depths[first] = state.depths[second] = finish;
        state.depth = max(state.depth, finish);
        operations.push_back({1, first, second});
        beam_close(state, operations);
    }

    double beam_heuristic(const BeamState &state, int metric, double discount, double scale) {
        int levels[MAX_N] = {};
        double powers[MAX_G];
        powers[0] = 1;
        for (int level = 1; level < gate_count; ++level) powers[level] = powers[level - 1] * discount;
        double estimate = 0;
        for (int gate_id = 0; gate_id < gate_count; ++gate_id) {
            const Gate &gate = gates[gate_id];
            if (gate_id < state.next[gate.first]) continue;
            int level = max(levels[gate.first], levels[gate.second]);
            levels[gate.first] = levels[gate.second] = level + 1;
            if (powers[level] < 0.001) continue;
            estimate += powers[level] * distance[metric][state.positions[gate.first]][state.positions[gate.second]];
        }
        return state.work + 0.05 * state.depth + scale * estimate;
    }

    Result beam_route(int width, int metric, double discount, double scale, int path_limit = 3,
                      chrono::steady_clock::time_point deadline = chrono::steady_clock::time_point::max()) {
        vector<vector<BeamState>> beams(gate_count + 1);
        vector<Trace> traces;
        traces.reserve(gate_count * width * 50);
        BeamState initial_state{};
        initial_state.depths.fill(0);
        for (int logical = 0; logical < count; ++logical) {
            initial_state.positions[logical] = initial[logical];
            initial_state.occupants[initial[logical]] = logical;
            initial_state.next[logical] = first_gate[logical];
            initial_state.hash ^= zobrist[logical][initial[logical]];
        }
        vector<Operation> prefix;
        beam_close(initial_state, prefix);
        for (const Operation &operation : prefix) {
            traces.push_back({operation, initial_state.trace}); initial_state.trace = int(traces.size()) - 1;
        }
        initial_state.score = beam_heuristic(initial_state, metric, discount, scale);
        beams[initial_state.completed].push_back(initial_state);
        Result result;
        for (int completed = initial_state.completed; completed < gate_count; ++completed) {
            if (chrono::steady_clock::now() > deadline) return result;
            for (const BeamState &parent_state : beams[completed]) {
                if (chrono::steady_clock::now() > deadline) return result;
                vector<int> ready;
                for (int logical = 0; logical < count; ++logical) {
                    int gate_id = parent_state.next[logical];
                    if (gate_id == gate_count) continue;
                    const Gate &gate = gates[gate_id];
                    if (gate.first == logical && parent_state.next[gate.second] == gate_id) ready.push_back(gate_id);
                }
                for (int gate_id : ready) {
                    const Gate &gate = gates[gate_id];
                    int source = parent_state.positions[gate.first], target = parent_state.positions[gate.second];
                    const auto &options = paths[source][target];
                    for (int path_id = 0; path_id < min(int(options.size()), path_limit); ++path_id) {
                        const auto &path = options[path_id];
                        for (int meeting = 0; meeting < int(path.size()) - 1; ++meeting) {
                            BeamState child = parent_state;
                            vector<Operation> operations;
                            operations.reserve(path.size() * 2 + 10);
                            for (int offset = 0; offset < meeting && child.next[gate.first] <= gate_id; ++offset)
                                beam_swap(child, path[offset], path[offset + 1], operations);
                            for (int offset = int(path.size()) - 1; offset > meeting + 1 && child.next[gate.first] <= gate_id; --offset)
                                beam_swap(child, path[offset], path[offset - 1], operations);
                            if (child.completed <= completed) continue;
                            child.score = beam_heuristic(child, metric, discount, scale);
                            auto &destination = beams[child.completed];
                            int replace = -1;
                            bool duplicate = false;
                            for (int offset = 0; offset < int(destination.size()); ++offset) {
                                if (destination[offset].hash == child.hash) {
                                    duplicate = true;
                                    if (child.score + 1e-8 < destination[offset].score) replace = offset;
                                    break;
                                }
                            }
                            if (duplicate && replace < 0) continue;
                            if (!duplicate && int(destination.size()) >= width) {
                                for (int offset = 0; offset < int(destination.size()); ++offset)
                                    if (replace < 0 || destination[offset].score > destination[replace].score) replace = offset;
                                if (destination[replace].score <= child.score) continue;
                            }
                            for (const Operation &operation : operations) {
                                traces.push_back({operation, child.trace}); child.trace = int(traces.size()) - 1;
                            }
                            if (replace >= 0) destination[replace] = child;
                            else destination.push_back(child);
                        }
                    }
                }
            }
            vector<BeamState>().swap(beams[completed]);
        }
        for (const BeamState &state : beams[gate_count]) {
            double cost = state.work + 0.05 * state.depth;
            if (cost >= result.cost) continue;
            result.cost = cost; result.work = state.work; result.depth = state.depth;
            result.operations.clear(); result.swaps = 0;
            for (int trace = state.trace; trace >= 0; trace = traces[trace].parent) {
                result.operations.push_back(traces[trace].operation);
                result.swaps += traces[trace].operation.kind;
            }
            reverse(result.operations.begin(), result.operations.end());
        }
        return result;
    }

    Result evaluate(const vector<Operation> &operations) {
        Result result;
        result.operations = operations;
        int positions[MAX_N], occupants[MAX_N], depths[MAX_N] = {};
        for (int logical = 0; logical < count; ++logical) {
            positions[logical] = initial[logical]; occupants[initial[logical]] = logical;
        }
        for (const Operation &operation : operations) {
            int first, second, duration;
            if (operation.kind) { first = operation.first; second = operation.second; duration = 3; }
            else {
                const Gate &gate = gates[operation.first];
                first = positions[gate.first]; second = positions[gate.second]; duration = 1;
            }
            int edge_id = edge_index[first][second];
            if (edge_id < 0) return result;
            result.work += duration * edges[edge_id].weight;
            int finish = max(depths[first], depths[second]) + duration;
            depths[first] = depths[second] = finish;
            result.depth = max(result.depth, finish);
            if (operation.kind) {
                ++result.swaps;
                swap(occupants[first], occupants[second]);
                positions[occupants[first]] = first; positions[occupants[second]] = second;
            }
        }
        result.cost = result.work + 0.05 * result.depth;
        return result;
    }

    void simplify(Result &result) {
        if (getenv("NO_SIMPLIFY")) return;
        for (int pass = 0; pass < 60; ++pass) {
            if (chrono::steady_clock::now() > stop_time) return;
            int length = result.operations.size();
            vector<array<int, MAX_N>> history(length);
            vector<pair<int, int>> logical_swaps(length, {-1, -1});
            array<int, MAX_N> positions{};
            int occupants[MAX_N];
            for (int logical = 0; logical < count; ++logical) {
                positions[logical] = initial[logical]; occupants[initial[logical]] = logical;
            }
            for (int offset = 0; offset < length; ++offset) {
                history[offset] = positions;
                const Operation &operation = result.operations[offset];
                if (operation.kind) {
                    int first = operation.first, second = operation.second;
                    logical_swaps[offset] = {occupants[first], occupants[second]};
                    swap(occupants[first], occupants[second]);
                    positions[occupants[first]] = first; positions[occupants[second]] = second;
                }
            }
            double best_change = -1e-8;
            int remove_first = -1, remove_second = -1;
            for (int start = 0; start < length; ++start) {
                if (!result.operations[start].kind) continue;
                int logical_first = logical_swaps[start].first, logical_second = logical_swaps[start].second;
                const Operation &operation = result.operations[start];
                double change = -3 * edges[edge_index[operation.first][operation.second]].weight;
                int offset = start + 1;
                for (; offset < length; ++offset) {
                    const Operation &following = result.operations[offset];
                    if (following.kind) {
                        auto pair = logical_swaps[offset];
                        if ((pair.first == logical_first && pair.second == logical_second)
                            || (pair.first == logical_second && pair.second == logical_first)) {
                            double saving = change - 3 * edges[edge_index[following.first][following.second]].weight;
                            if (saving < best_change) {
                                best_change = saving; remove_first = start; remove_second = offset;
                            }
                        }
                    } else {
                        const Gate &gate = gates[following.first];
                        if (gate.first != logical_first && gate.first != logical_second
                            && gate.second != logical_first && gate.second != logical_second) continue;
                        int new_first = gate.first == logical_first ? logical_second : gate.first == logical_second ? logical_first : gate.first;
                        int new_second = gate.second == logical_first ? logical_second : gate.second == logical_second ? logical_first : gate.second;
                        int old_edge = edge_index[history[offset][gate.first]][history[offset][gate.second]];
                        int new_edge = edge_index[history[offset][new_first]][history[offset][new_second]];
                        if (new_edge < 0) break;
                        change += edges[new_edge].weight - edges[old_edge].weight;
                    }
                }
                if (offset == length && change < best_change) {
                    best_change = change; remove_first = start; remove_second = -1;
                }
            }
            if (remove_first < 0) break;
            vector<Operation> operations;
            operations.reserve(length);
            for (int offset = 0; offset < length; ++offset)
                if (offset != remove_first && offset != remove_second) operations.push_back(result.operations[offset]);
            Result candidate = evaluate(operations);
            if (candidate.cost + 1e-8 >= result.cost) break;
            result = move(candidate);
        }
    }

    void prepare_distances() {
        const double exponents[METRICS] = {0.0, 0.3, 0.6, 1.0, 1.4, 0.6, 1.0, 0.0, 1.0};
        const double gate_factors[METRICS] = {0.0, 0.0, 0.0, 0.0, 0.0, 0.333333, 0.333333, 1.0, 0.15};
        for (int metric = 0; metric < METRICS; ++metric) {
            auto &matrix = distance[metric];
            fill(&matrix[0][0], &matrix[0][0] + MAX_N * MAX_N, 1e100);
            using Item = pair<double, int>;
            priority_queue<Item, vector<Item>, greater<Item>> pending;
            for (const Edge &edge : edges) {
                double start = gate_factors[metric] * pow(edge.weight, exponents[metric]);
                matrix[edge.first][edge.second] = matrix[edge.second][edge.first] = start;
                pending.push({start, edge.first * count + edge.second});
                pending.push({start, edge.second * count + edge.first});
            }
            while (!pending.empty()) {
                auto current = pending.top(); pending.pop();
                int first = current.second / count, second = current.second % count;
                if (current.first > matrix[first][second] + 1e-9) continue;
                for (int which = 0; which < 2; ++which) {
                    int moving = which ? second : first, other = which ? first : second;
                    for (int edge_id : adjacency[moving]) {
                        const Edge &edge = edges[edge_id];
                        int destination = edge.first ^ edge.second ^ moving;
                        if (destination == other) continue;
                        int next_first = which ? first : destination, next_second = which ? destination : second;
                        double score = current.first + pow(edge.weight, exponents[metric]);
                        if (score + 1e-9 < matrix[next_first][next_second]) {
                            matrix[next_first][next_second] = score;
                            pending.push({score, next_first * count + next_second});
                        }
                    }
                }
            }
            for (int physical = 0; physical < count; ++physical) matrix[physical][physical] = 0;
        }
    }

    Result route(const Parameters &parameters, double upper_bound, const Result *prefix = nullptr, int prefix_length = 0) {
        const auto &matrix = distance[parameters.metric];
        int positions[MAX_N], occupants[MAX_N], depths[MAX_N] = {}, touched[MAX_N] = {};
        int remaining[MAX_G];
        bool done[MAX_G] = {};
        vector<int> ready;
        for (int logical = 0; logical < count; ++logical) {
            positions[logical] = initial[logical]; occupants[initial[logical]] = logical;
        }
        for (int index = 0; index < gate_count; ++index) {
            remaining[index] = gates[index].predecessors;
            if (!remaining[index]) ready.push_back(index);
        }
        Result result;
        result.operations.reserve(gate_count * 5);
        int step = 0, previous = -1, stalled = 0, completed = 0;
        uint64_t hash = 0;
        for (int logical = 0; logical < count; ++logical) hash ^= zobrist[logical][positions[logical]];
        vector<uint64_t> recent;
        double interaction[MAX_N][MAX_N] = {};
        vector<pair<int, double>> interactions[MAX_N];
        bool rebuild = true;

        auto emit_swap = [&](int edge_id) {
            const Edge &edge = edges[edge_id];
            int first = edge.first, second = edge.second;
            int logical_first = occupants[first], logical_second = occupants[second];
            hash ^= zobrist[logical_first][first] ^ zobrist[logical_first][second]
                 ^ zobrist[logical_second][first] ^ zobrist[logical_second][second];
            swap(occupants[first], occupants[second]);
            positions[logical_first] = second; positions[logical_second] = first;
            result.work += 3 * edge.weight;
            int finish = max(depths[first], depths[second]) + 3;
            depths[first] = depths[second] = finish;
            result.depth = max(result.depth, finish);
            result.operations.push_back({1, first, second});
            ++result.swaps;
            ++step;
            touched[first] = touched[second] = step;
            previous = edge_id;
        };

        if (prefix) {
            for (int offset = 0; offset < prefix_length; ++offset) {
                const Operation &operation = prefix->operations[offset];
                if (operation.kind == 1) {
                    emit_swap(edge_index[operation.first][operation.second]);
                } else {
                    int gate_id = operation.first;
                    const Gate &gate = gates[gate_id];
                    int first = positions[gate.first], second = positions[gate.second];
                    int edge_id = edge_index[first][second];
                    result.work += edges[edge_id].weight;
                    int finish = max(depths[first], depths[second]) + 1;
                    depths[first] = depths[second] = finish;
                    result.depth = max(result.depth, finish);
                    result.operations.push_back(operation);
                    ready.erase(find(ready.begin(), ready.end(), gate_id));
                    done[gate_id] = true;
                    ++completed;
                    for (int successor : gate.successors) if (!--remaining[successor]) ready.push_back(successor);
                    previous = -1;
                }
            }
        }

        while (completed < gate_count) {
            if ((step & 15) == 0 && upper_bound < 1e90 && chrono::steady_clock::now() > stop_time) return result;
            bool executed = false;
            for (int offset = 0; offset < int(ready.size());) {
                int gate_id = ready[offset];
                const Gate &gate = gates[gate_id];
                int first = positions[gate.first], second = positions[gate.second];
                int edge_id = edge_index[first][second];
                if (edge_id < 0) { ++offset; continue; }
                result.work += edges[edge_id].weight;
                int finish = max(depths[first], depths[second]) + 1;
                depths[first] = depths[second] = finish;
                result.depth = max(result.depth, finish);
                result.operations.push_back({0, gate_id, 0});
                ready.erase(ready.begin() + offset);
                done[gate_id] = true;
                ++completed;
                for (int successor : gate.successors) if (!--remaining[successor]) ready.push_back(successor);
                executed = true;
            }
            if (result.work + 0.05 * result.depth >= upper_bound) return result;
            if (executed) { rebuild = true; stalled = 0; previous = -1; recent.clear(); continue; }
            if (completed == gate_count) break;
            if (++stalled > count * 2) {
                int chosen = ready.front();
                double cheapest = 1e100;
                for (int gate_id : ready) {
                    const Gate &gate = gates[gate_id];
                    double value = distance[3][positions[gate.first]][positions[gate.second]];
                    if (value < cheapest) { cheapest = value; chosen = gate_id; }
                }
                const Gate &gate = gates[chosen];
                while (edge_index[positions[gate.first]][positions[gate.second]] < 0) {
                    int first = positions[gate.first], second = positions[gate.second];
                    int chosen_edge = -1;
                    double best = 1e100;
                    for (int which = 0; which < 2; ++which) {
                        int moving = which ? second : first, other = which ? first : second;
                        for (int edge_id : adjacency[moving]) {
                            const Edge &edge = edges[edge_id];
                            int target = edge.first ^ edge.second ^ moving;
                            if (target == other) continue;
                            double value = edge.weight + distance[3][target][other];
                            if (value < best) { best = value; chosen_edge = edge_id; }
                        }
                    }
                    emit_swap(chosen_edge);
                }
                stalled = 0;
                continue;
            }
            if (rebuild) {
                sort(ready.begin(), ready.end());
                fill(&interaction[0][0], &interaction[0][0] + MAX_N * MAX_N, 0);
                bool visited[MAX_G] = {};
                vector<pair<int, int>> pending;
                for (int gate_id : ready) { pending.push_back({gate_id, 0}); visited[gate_id] = true; }
                vector<pair<int, double>> future;
                double weight_sum = 0;
                for (int offset = 0; offset < int(pending.size()) && int(future.size()) < parameters.lookahead; ++offset) {
                    int gate_id = pending[offset].first, level = pending[offset].second;
                    for (int successor : gates[gate_id].successors) {
                        if (visited[successor] || done[successor]) continue;
                        visited[successor] = true;
                        double weight = pow(parameters.discount, level);
                        future.push_back({successor, weight}); weight_sum += weight;
                        pending.push_back({successor, level + 1});
                        if (int(future.size()) >= parameters.lookahead) break;
                    }
                }
                for (int gate_id : ready) {
                    const Gate &gate = gates[gate_id];
                    double weight = 1.0 + parameters.priority * exp(-double(gate_id - ready.front()) / count);
                    weight *= 1.0 + parameters.jitter * (random.uniform() - 0.5);
                    interaction[gate.first][gate.second] += weight;
                    interaction[gate.second][gate.first] += weight;
                }
                for (auto entry : future) {
                    const Gate &gate = gates[entry.first];
                    double weight = parameters.future * ready.size() * entry.second / max(1e-12, weight_sum);
                    weight *= 1.0 + parameters.jitter * (random.uniform() - 0.5);
                    interaction[gate.first][gate.second] += weight;
                    interaction[gate.second][gate.first] += weight;
                }
                for (int logical = 0; logical < count; ++logical) {
                    interactions[logical].clear();
                    for (int other = 0; other < count; ++other)
                        if (interaction[logical][other] > 0) interactions[logical].push_back({other, interaction[logical][other]});
                }
                rebuild = false;
            }
            recent.push_back(hash);
            bool candidate_edges[MAX_N * MAX_N] = {};
            for (int gate_id : ready) {
                const Gate &gate = gates[gate_id];
                for (int edge_id : adjacency[positions[gate.first]]) candidate_edges[edge_id] = true;
                for (int edge_id : adjacency[positions[gate.second]]) candidate_edges[edge_id] = true;
            }
            double best = 1e100;
            int chosen = -1;
            for (int edge_id = 0; edge_id < edge_count; ++edge_id) {
                if (!candidate_edges[edge_id] || edge_id == previous) continue;
                const Edge &edge = edges[edge_id];
                int first = edge.first, second = edge.second;
                int logical_first = occupants[first], logical_second = occupants[second];
                double score = 0;
                for (auto entry : interactions[logical_first]) {
                    if (entry.first == logical_second) continue;
                    int other = positions[entry.first];
                    score += entry.second * (matrix[second][other] - matrix[first][other]);
                }
                for (auto entry : interactions[logical_second]) {
                    if (entry.first == logical_first) continue;
                    int other = positions[entry.first];
                    score += entry.second * (matrix[first][other] - matrix[second][other]);
                }
                score += parameters.cost * edge.weight;
                int recency = max(0, 5 - min(step - touched[first], step - touched[second]));
                score += parameters.decay * recency * ready.size();
                uint64_t next_hash = hash ^ zobrist[logical_first][first] ^ zobrist[logical_first][second]
                    ^ zobrist[logical_second][first] ^ zobrist[logical_second][second];
                if (find(recent.begin(), recent.end(), next_hash) != recent.end()) score += 10;
                score += parameters.noise * (random.uniform() - 0.5) + random.uniform() * 1e-7;
                if (score < best) { best = score; chosen = edge_id; }
            }
            if (chosen < 0) { stalled = count * 2; continue; }
            emit_swap(chosen);
            if (result.swaps > 10000) return result;
        }
        result.cost = result.work + 0.05 * result.depth;
        return result;
    }

    Result solve(double seconds) {
        auto start = chrono::steady_clock::now();
        stop_time = start + chrono::duration_cast<chrono::steady_clock::duration>(chrono::duration<double>(seconds));
        Result best;
        if (getenv("ROUTE_BEAM")) {
            int width = atoi(getenv("ROUTE_BEAM"));
            int metric = getenv("BEAM_METRIC") ? atoi(getenv("BEAM_METRIC")) : 6;
            double discount = getenv("BEAM_DISCOUNT") ? atof(getenv("BEAM_DISCOUNT")) : 0.7;
            double scale = getenv("BEAM_SCALE") ? atof(getenv("BEAM_SCALE")) : 3.0;
            best = beam_route(width, metric, discount, scale);
            simplify(best);
            if (getenv("ROUTE_DEBUG")) cerr << "beam cost " << best.cost << " seconds "
                << chrono::duration<double>(chrono::steady_clock::now() - start).count() << '\n';
            if (getenv("BEAM_ONLY")) return best;
        }
        if (!getenv("OLD_SEARCH")) return portfolio(seconds, start, best);
        Parameters best_parameters;
        int trials = 0;
        while (true) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
            if (trials > 0 && elapsed >= seconds) break;
            Parameters parameters;
            parameters.metric = random.integer(METRICS);
            const int windows[] = {6, 10, 16, 24, 32, 48, 64, 96};
            parameters.lookahead = windows[random.integer(8)];
            parameters.future = 0.15 + random.uniform() * 1.6;
            parameters.cost = random.uniform() * 0.9;
            parameters.decay = random.uniform() < 0.6 ? 0.0 : random.uniform() * 0.04;
            parameters.discount = random.uniform() < 0.5 ? 1.0 : 0.5 + random.uniform() * 0.5;
            parameters.noise = random.uniform() < 0.5 ? 0.0 : random.uniform() * 0.3;
            parameters.jitter = random.uniform() < 0.5 ? 0.0 : random.uniform() * 0.8;
            parameters.priority = random.uniform() < 0.7 ? 0.0 : random.uniform();
            if (trials > 40 && trials % 3 != 0) {
                parameters = best_parameters;
                parameters.future = max(0.05, parameters.future + (random.uniform() - 0.5) * 0.5);
                parameters.cost = max(0.0, min(1.1, parameters.cost + (random.uniform() - 0.5) * 0.3));
                parameters.noise = random.uniform() * 0.25;
                parameters.jitter = random.uniform() * 0.6;
                if (random.uniform() < 0.3) parameters.lookahead = windows[random.integer(8)];
            }
            if (trials < METRICS) {
                parameters = Parameters(); parameters.metric = trials;
            }
            int prefix_length = 0;
            bool use_prefix = trials > 100 && trials % 5 != 0;
            if (use_prefix) {
                double fraction = random.uniform();
                if (trials % 3 == 0) fraction = sqrt(fraction);
                prefix_length = int(fraction * best.operations.size());
            }
            Result candidate = route(parameters, best.cost, use_prefix ? &best : nullptr, prefix_length);
            if (candidate.cost < best.cost) {
                simplify(candidate);
                best = move(candidate); best_parameters = parameters;
                if (getenv("ROUTE_DEBUG")) cerr << "best " << trials << " " << best.cost << " metric " << parameters.metric
                    << " window " << parameters.lookahead << " future " << parameters.future << " cost " << parameters.cost << '\n';
            }
            ++trials;
        }
        if (getenv("ROUTE_DEBUG")) cerr << "trials " << trials << " cost " << best.cost << " swaps " << best.swaps << '\n';
        return best;
    }

    Parameters random_parameters() {
        Parameters parameters;
        parameters.metric = random.integer(METRICS);
        const int windows[] = {6, 10, 16, 24, 32, 48, 64, 96};
        parameters.lookahead = windows[random.integer(8)];
        parameters.future = 0.2 + random.uniform() * 1.6;
        parameters.cost = random.uniform() * 0.95;
        parameters.decay = random.uniform() < 0.65 ? 0.0 : random.uniform() * 0.035;
        parameters.discount = random.uniform() < 0.55 ? 1.0 : 0.5 + random.uniform() * 0.5;
        parameters.noise = random.uniform() < 0.5 ? 0.0 : random.uniform() * 0.25;
        parameters.jitter = random.uniform() < 0.5 ? 0.0 : random.uniform() * 0.8;
        parameters.priority = random.uniform() < 0.8 ? 0.0 : random.uniform();
        return parameters;
    }

    Result portfolio(double seconds, chrono::steady_clock::time_point start, Result best) {
        struct Island { Result result; Parameters parameters; };
        constexpr int islands_count = 8;
        Island islands[islands_count];
        Parameters best_parameters;
        auto elapsed = [&]() { return chrono::duration<double>(chrono::steady_clock::now() - start).count(); };
        auto record = [&](Result &candidate, const Parameters &parameters, const char *label) {
            if (candidate.cost + 1e-8 < best.cost) {
                simplify(candidate);
                best = candidate; best_parameters = parameters;
                if (getenv("ROUTE_DEBUG")) cerr << label << " cost " << best.cost << " seconds " << elapsed() << '\n';
            }
        };
        int trials = 0;
        double initial_budget = min(0.25, seconds * 0.13);
        while (trials == 0 || (trials < 36 && elapsed() < seconds * 0.25) || elapsed() < initial_budget) {
            Parameters parameters = random_parameters();
            if (trials < METRICS) { parameters = Parameters(); parameters.metric = trials; }
            Island &island = islands[trials % islands_count];
            Result candidate = route(parameters, island.result.cost);
            if (candidate.cost < island.result.cost) {
                simplify(candidate);
                island.result = candidate; island.parameters = parameters;
                record(candidate, parameters, "initial");
            }
            ++trials;
        }
        for (Island &island : islands)
            if (island.result.cost > 1e90) island = {best, best_parameters};
        int beam_trials = 0;
        double beam_budget = min(1.8, seconds * 0.44);
        auto beam_deadline = start + chrono::duration_cast<chrono::steady_clock::duration>(chrono::duration<double>(beam_budget));
        const int metric_sequence[] = {6, 3, 0, 6, 8, 3, 0, 6, 8, 2, 6, 3};
        const double discount_sequence[] = {0.7, 0.8, 0.8, 0.55, 0.85, 0.65, 0.9, 0.75, 0.6, 0.75, 0.9, 0.5};
        const double scale_sequence[] = {3, 3, 3, 4.5, 2, 5, 2, 6, 3, 3, 3.5, 3};
        while (elapsed() < beam_budget && !getenv("NO_BEAM_PORTFOLIO")) {
            int variant = beam_trials % 12;
            int width = beam_trials < 12 ? 24 : beam_trials < 24 ? 48 : 96;
            Parameters parameters;
            parameters.metric = metric_sequence[variant];
            parameters.discount = discount_sequence[variant];
            double scale = scale_sequence[variant];
            int path_limit = 3;
            if (beam_trials >= 36) {
                width = 24 << random.integer(3);
                parameters.discount = max(0.35, min(0.95, parameters.discount + (random.uniform() - 0.5) * 0.2));
                scale *= 0.75 + random.uniform() * 0.5;
                path_limit = 3 + random.integer(4);
            }
            Result candidate = beam_route(width, parameters.metric, parameters.discount, scale, path_limit, beam_deadline);
            if (candidate.cost < 1e90) {
                simplify(candidate);
                record(candidate, parameters, "beam");
                int worst = 0;
                for (int index = 1; index < islands_count; ++index)
                    if (islands[index].result.cost > islands[worst].result.cost) worst = index;
                if (candidate.cost < islands[worst].result.cost) islands[worst] = {move(candidate), parameters};
            }
            ++beam_trials;
        }
        while (elapsed() < seconds) {
            int island_id = random.integer(islands_count);
            Island &island = islands[island_id];
            bool greedy = trials % 3 == 0;
            bool fresh = trials % 19 == 0;
            const Result &parent = greedy ? best : island.result;
            Parameters parameters = greedy ? best_parameters : island.parameters;
            if (random.uniform() < 0.25 || fresh) parameters = random_parameters();
            else {
                parameters.future = max(0.05, min(2.5, parameters.future + (random.uniform() - 0.5) * 0.5));
                parameters.cost = max(0.0, min(1.15, parameters.cost + (random.uniform() - 0.5) * 0.35));
                parameters.noise = random.uniform() * 0.22;
                parameters.jitter = random.uniform() * 0.5;
                if (random.uniform() < 0.1) parameters.metric = random.integer(METRICS);
                if (random.uniform() < 0.15) parameters.lookahead = 6 + random.integer(59);
            }
            double fraction = random.uniform();
            if (trials % 3 == 1) fraction = sqrt(fraction);
            int prefix_length = fresh ? 0 : int(fraction * parent.operations.size());
            double temperature = best.cost * (0.001 + 0.018 * (1.0 - min(1.0, elapsed() / seconds)))
                * (0.5 + double(island_id) / islands_count);
            double allowance = greedy ? best.cost : min(best.cost * 1.1, parent.cost - temperature * log(max(1e-12, random.uniform())));
            Result candidate = route(parameters, allowance, fresh ? nullptr : &parent, prefix_length);
            if (candidate.cost < allowance) {
                if (candidate.cost < best.cost) record(candidate, parameters, "refine");
                if (!greedy && candidate.cost < 1e90) island = {move(candidate), parameters};
            }
            if (island.result.cost > best.cost * 1.06 || trials % 997 == 0) island = {best, best_parameters};
            ++trials;
        }
        simplify(best);
        if (getenv("ROUTE_DEBUG")) cerr << "trials " << trials << " beams " << beam_trials << " cost " << best.cost << " swaps " << best.swaps << '\n';
        return best;
    }
};

double remaining_budget(double seconds, double deadline) {
    if (deadline > 0) {
        timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        double remaining = deadline - double(now.tv_sec) - double(now.tv_nsec) * 1e-9;
        seconds = max(0.001, min(seconds, remaining));
    }
    return seconds;
}

string serialize_result(const Result &result) {
    ostringstream output;
    output << "{\"operations\":[";
    bool first = true;
    for (const Operation &operation : result.operations) {
        if (!first) output << ',';
        first = false;
        if (operation.kind == 0) output << "[\"gate\"," << operation.first << ']';
        else output << "[\"swap\"," << operation.first << ',' << operation.second << ']';
    }
    output << "]}\n";
    return output.str();
}

extern "C" const char *route_instance(const char *source, double seconds, double deadline) {
    static string output;
    istringstream input(source);
    streambuf *previous = cin.rdbuf(input.rdbuf());
    cin.clear();
    try {
        Router router;
        cin.rdbuf(previous);
        cin.clear();
        Result result = router.solve(remaining_budget(seconds, deadline));
        output = serialize_result(result);
        return output.c_str();
    } catch (...) {
        cin.rdbuf(previous);
        cin.clear();
        return nullptr;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    Router router;
    double seconds = 4.0, deadline = 0;
    if (const char *setting = getenv("ROUTE_TIME")) seconds = min(5.5, max(0.01, atof(setting)));
    if (const char *setting = getenv("ROUTE_DEADLINE")) deadline = atof(setting);
    cout << serialize_result(router.solve(remaining_budget(seconds, deadline)));
}
