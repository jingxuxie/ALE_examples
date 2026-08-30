#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <limits>
#include <memory>
#include <map>
#include <numeric>
#include <queue>
#include <random>
#include <string>
#include <utility>
#include <vector>

using namespace std;

constexpr int INF = 1000000000;
constexpr int MAX_N = 28;

struct Edge {
    int first, second, weight;
};

struct Operation {
    int kind, first, second;
};

struct Block {
    vector<int> gates;
    vector<int> logical;
    int counts[4][4]{};
    vector<int> values;
    vector<int16_t> policy;
    vector<int> goals;
    vector<int> goal_work;
    uint32_t mask = 0;
};

struct State {
    array<int, MAX_N> positions{};
    array<int, MAX_N> occupants{};
    array<int, MAX_N> depths{};
    vector<Operation> operations;
    long long work = 0;
    int depth = 0;
    vector<int> completed;
    vector<int> boundaries;
    double cost() const { return work * 0.0001 + 0.05 * depth; }
};

struct Solver {
    struct Forward {
        vector<int> distances;
        vector<int16_t> previous;
        vector<int> settled_goals;
        int source;
    };
    int count, edge_count, gate_count;
    vector<Edge> edges;
    vector<pair<int, int>> gates;
    vector<int> adjacency[MAX_N];
    int weights[MAX_N][MAX_N]{};
    int edge_index[MAX_N][MAX_N];
    int powers[5];
    vector<Block> blocks;
    vector<int> visited;
    int visit_epoch = 0;
    map<pair<int, int>, shared_ptr<Forward>> forward_cache;
    State initial;
    mt19937 generator{719283};
    chrono::steady_clock::time_point started = chrono::steady_clock::now();
    double budget = 7.5;

    double elapsed() const {
        return chrono::duration<double>(chrono::steady_clock::now() - started).count();
    }

    void read() {
        cin >> count >> edge_count >> gate_count;
        for (auto &row : edge_index) fill(begin(row), end(row), -1);
        for (int index = 0; index < edge_count; ++index) {
            Edge edge;
            cin >> edge.first >> edge.second >> edge.weight;
            edges.push_back(edge);
            adjacency[edge.first].push_back(index);
            adjacency[edge.second].push_back(index);
            weights[edge.first][edge.second] = weights[edge.second][edge.first] = edge.weight;
            edge_index[edge.first][edge.second] = edge_index[edge.second][edge.first] = index;
        }
        for (int logical = 0; logical < count; ++logical) {
            cin >> initial.positions[logical];
            initial.occupants[initial.positions[logical]] = logical;
        }
        gates.resize(gate_count);
        for (auto &gate : gates) cin >> gate.first >> gate.second;
        powers[0] = 1;
        for (int index = 1; index <= 4; ++index) powers[index] = powers[index - 1] * count;
        if (const char *setting = getenv("ROUTER_BUDGET")) budget = max(0.1, min(9.0, atof(setting)));
    }

    void prepare(Block &block) {
        block.logical.clear();
        block.mask = 0;
        for (auto &row : block.counts) fill(begin(row), end(row), 0);
        for (int gate_index : block.gates) {
            block.mask |= (1u << gates[gate_index].first) | (1u << gates[gate_index].second);
        }
        for (int logical = 0; logical < count; ++logical)
            if (block.mask & (1u << logical)) block.logical.push_back(logical);
        for (int gate_index : block.gates) {
            int first = find(block.logical.begin(), block.logical.end(), gates[gate_index].first) - block.logical.begin();
            int second = find(block.logical.begin(), block.logical.end(), gates[gate_index].second) - block.logical.begin();
            ++block.counts[first][second];
            ++block.counts[second][first];
        }
    }

    bool embeddable(const Block &block) {
        array<int, 4> locations{};
        function<bool(int, uint32_t)> visit = [&](int index, uint32_t used) {
            if (index == int(block.logical.size())) return true;
            for (int physical = 0; physical < count; ++physical) {
                if (used & (1u << physical)) continue;
                bool valid = true;
                for (int other = 0; other < index; ++other)
                    if (block.counts[index][other] && !weights[physical][locations[other]]) valid = false;
                if (!valid) continue;
                locations[index] = physical;
                if (visit(index + 1, used | (1u << physical))) return true;
            }
            return false;
        };
        return visit(0, 0);
    }

    void partition() {
        Block current;
        uint32_t mask = 0;
        for (int index = 0; index < gate_count; ++index) {
            uint32_t added = (1u << gates[index].first) | (1u << gates[index].second);
            bool exceeds = __builtin_popcount(mask | added) > 4;
            if (!exceeds) {
                current.gates.push_back(index);
                prepare(current);
                exceeds = !embeddable(current);
                current.gates.pop_back();
            }
            if (exceeds && !current.gates.empty()) {
                prepare(current);
                blocks.push_back(move(current));
                current = Block();
                mask = 0;
            }
            current.gates.push_back(index);
            mask |= added;
        }
        if (!current.gates.empty()) {
            prepare(current);
            blocks.push_back(move(current));
        }
        for (int first = 0; first < int(blocks.size()); ++first) {
            for (int second = first + 1; second < int(blocks.size()); ++second) {
                if (blocks[first].mask == blocks[second].mask) {
                    Block merged;
                    merged.gates = blocks[first].gates;
                    merged.gates.insert(merged.gates.end(), blocks[second].gates.begin(), blocks[second].gates.end());
                    prepare(merged);
                    if (embeddable(merged)) {
                        blocks[first] = move(merged);
                        blocks.erase(blocks.begin() + second);
                        --second;
                        continue;
                    }
                }
                if (blocks[first].mask & blocks[second].mask) break;
            }
        }
    }

    bool compute(Block &block, bool limited = true) {
        int active_count = block.logical.size();
        int size = powers[active_count];
        block.values.assign(size, INF);
        block.policy.assign(size, -2);
        priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> queue;
        array<int, 4> locations{};
        function<void(int, uint32_t, int, int)> visit = [&](int index, uint32_t used, int code, int work) {
            if (index == active_count) {
                block.values[code] = work;
                block.policy[code] = -1;
                block.goals.push_back(code);
                block.goal_work.push_back(work);
                queue.emplace(work, code);
                return;
            }
            for (int physical = 0; physical < count; ++physical) {
                if (used & (1u << physical)) continue;
                bool valid = true;
                int added = 0;
                for (int other = 0; other < index; ++other) {
                    if (block.counts[index][other] && !weights[physical][locations[other]]) valid = false;
                    added += block.counts[index][other] * weights[physical][locations[other]];
                }
                if (!valid) continue;
                locations[index] = physical;
                visit(index + 1, used | (1u << physical), code + physical * powers[index], work + added);
            }
        };
        visit(0, 0, 0, 0);
        array<int, MAX_N> token_at;
        int iterations = 0;
        while (!queue.empty()) {
            auto [cost, code] = queue.top();
            queue.pop();
            if (cost != block.values[code]) continue;
            if (limited && (++iterations & 8191) == 0 && elapsed() > min(5.5, budget - 0.35)) return false;
            token_at.fill(-1);
            int remainder = code;
            for (int token = 0; token < active_count; ++token) {
                locations[token] = remainder % count;
                remainder /= count;
                token_at[locations[token]] = token;
            }
            for (int token = 0; token < active_count; ++token) {
                int first = locations[token];
                for (int edge_id : adjacency[first]) {
                    const Edge &edge = edges[edge_id];
                    int second = edge.first ^ edge.second ^ first;
                    int other = token_at[second];
                    if (other >= 0 && other < token) continue;
                    int following = code + (second - first) * powers[token];
                    if (other >= 0) following += (first - second) * powers[other];
                    int next_cost = cost + 3 * edge.weight;
                    if (next_cost < block.values[following]) {
                        block.values[following] = next_cost;
                        block.policy[following] = edge_id;
                        queue.emplace(next_cost, following);
                    }
                }
            }
        }
        return true;
    }

    int encode(const Block &block, const State &state) const {
        int code = 0;
        for (int token = 0; token < int(block.logical.size()); ++token)
            code += powers[token] * state.positions[block.logical[token]];
        return code;
    }

    void swap_positions(State &state, int edge_id) const {
        const Edge &edge = edges[edge_id];
        int logical_first = state.occupants[edge.first];
        int logical_second = state.occupants[edge.second];
        swap(state.occupants[edge.first], state.occupants[edge.second]);
        state.positions[logical_first] = edge.second;
        state.positions[logical_second] = edge.first;
    }

    void emit_swap(State &state, int edge_id) const {
        const Edge &edge = edges[edge_id];
        state.work += 3 * edge.weight;
        int finish = max(state.depths[edge.first], state.depths[edge.second]) + 3;
        state.depths[edge.first] = state.depths[edge.second] = finish;
        state.depth = max(state.depth, finish);
        swap_positions(state, edge_id);
        state.operations.push_back({1, edge.first, edge.second});
    }

    void emit_gate(State &state, int gate_id) const {
        int first = state.positions[gates[gate_id].first];
        int second = state.positions[gates[gate_id].second];
        state.work += weights[first][second];
        int finish = max(state.depths[first], state.depths[second]) + 1;
        state.depths[first] = state.depths[second] = finish;
        state.depth = max(state.depth, finish);
        state.operations.push_back({0, gate_id, 0});
    }

    int gate_work(const Block &block, const State &state) const {
        int work = 0;
        for (int first = 0; first < int(block.logical.size()); ++first) {
            for (int second = 0; second < first; ++second) {
                int weight = weights[state.positions[block.logical[first]]][state.positions[block.logical[second]]];
                if (block.counts[first][second] && !weight) return INF;
                work += block.counts[first][second] * weight;
            }
        }
        return work;
    }

    vector<vector<int>> orders() {
        int block_count = blocks.size();
        vector<vector<int>> result;
        if (block_count > 20) {
            vector<int> order(block_count);
            iota(order.begin(), order.end(), 0);
            result.push_back(order);
            return result;
        }
        vector<uint32_t> predecessors(block_count);
        for (int later = 0; later < block_count; ++later)
            for (int earlier = 0; earlier < later; ++earlier)
                if (blocks[later].mask & blocks[earlier].mask) predecessors[later] |= 1u << earlier;
        vector<int> order;
        function<void(uint32_t)> visit = [&](uint32_t done) {
            if (result.size() >= 64) return;
            if (int(order.size()) == block_count) {
                result.push_back(order);
                return;
            }
            for (int index = 0; index < block_count; ++index) {
                if ((done & (1u << index)) || (predecessors[index] & ~done)) continue;
                order.push_back(index);
                visit(done | (1u << index));
                order.pop_back();
            }
        };
        visit(0);
        return result;
    }

    double potential(const State &state, const vector<int> &order, int step, double discount) const {
        double result = 0, coefficient = 1;
        for (int following = step + 1; following < int(order.size()); ++following) {
            const Block &block = blocks[order[following]];
            result += coefficient * block.values[encode(block, state)];
            coefficient *= discount;
        }
        return result;
    }

    State route(const vector<int> &order, double beta, double discount, double temperature, bool relaxed = false,
                int start_step = 0, const State *prefix = nullptr) {
        State state = prefix ? *prefix : initial;
        for (int step = start_step; step < int(order.size()); ++step) {
            const Block &block = blocks[order[step]];
            int swaps = 0;
            ++visit_epoch;
            while (true) {
                int code = encode(block, state);
                visited[code] = visit_epoch;
                int current_value = block.values[code];
                int best_edge = block.policy[code];
                if ((beta == 0 && temperature == 0) || swaps >= 120) {
                    if (best_edge == -1) break;
                    emit_swap(state, best_edge);
                    continue;
                }
                double current_potential = potential(state, order, step, discount);
                int work = gate_work(block, state);
                double best_score = work < INF ? work - current_value : INF;
                best_edge = -1;
                vector<int> candidates;
                uint64_t seen = 0;
                for (int logical : block.logical) {
                    for (int edge_id : adjacency[state.positions[logical]]) {
                        if (edge_count <= 64) {
                            if (seen & (1ull << edge_id)) continue;
                            seen |= 1ull << edge_id;
                        } else if (find(candidates.begin(), candidates.end(), edge_id) != candidates.end()) continue;
                        candidates.push_back(edge_id);
                    }
                }
                for (int edge_id : candidates) {
                    swap_positions(state, edge_id);
                    int next_code = encode(block, state);
                    int next_value = block.values[next_code];
                    if ((next_value < current_value || relaxed) && (!relaxed || visited[next_code] != visit_epoch)) {
                        double score = next_value + 3 * edges[edge_id].weight - current_value;
                        if (beta) score += beta * (potential(state, order, step, discount) - current_potential);
                        if (temperature) score += temperature * 10000 * log((generator() + 1.0) / (generator.max() + 2.0));
                        if (score < best_score || (score == best_score && edge_id == block.policy[code])) {
                            best_score = score;
                            best_edge = edge_id;
                        }
                    }
                    swap_positions(state, edge_id);
                }
                if (best_edge < 0) {
                    if (work < INF) break;
                    best_edge = block.policy[code];
                    swaps = 120;
                }
                emit_swap(state, best_edge);
                ++swaps;
            }
            for (int gate_id : block.gates) emit_gate(state, gate_id);
            state.completed.push_back(order[step]);
            state.boundaries.push_back(state.operations.size());
        }
        return state;
    }

    int change_code(int code, int active_count, int edge_id) const {
        const Edge &edge = edges[edge_id];
        int remainder = code, result = code;
        for (int token = 0; token < active_count; ++token) {
            int location = remainder % count;
            remainder /= count;
            if (location == edge.first) result += (edge.second - edge.first) * powers[token];
            if (location == edge.second) result += (edge.first - edge.second) * powers[token];
        }
        return result;
    }

    shared_ptr<Forward> forward_search(int block_id, const State &prefix) {
        const Block &block = blocks[block_id];
        int source = encode(block, prefix);
        auto key = make_pair(block_id, source);
        auto cached = forward_cache.find(key);
        if (cached != forward_cache.end()) return cached->second;
        auto result = make_shared<Forward>();
        result->source = source;
        int active_count = block.logical.size();
        int size = powers[active_count];
        result->distances.assign(size, INF);
        result->previous.assign(size, -1);
        vector<int> goal_index(size, -1);
        for (int index = 0; index < int(block.goals.size()); ++index) goal_index[block.goals[index]] = index;
        priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> queue;
        result->distances[source] = 0;
        queue.emplace(block.values[source], source);
        array<int, MAX_N> token_at;
        array<int, 4> locations{};
        int iterations = 0;
        while (!queue.empty()) {
            auto [priority, code] = queue.top();
            queue.pop();
            int distance = result->distances[code];
            if (priority != distance + block.values[code]) continue;
            if (goal_index[code] >= 0) result->settled_goals.push_back(goal_index[code]);
            if ((++iterations & 8191) == 0 && elapsed() > budget - 0.08) break;
            token_at.fill(-1);
            int remainder = code;
            for (int token = 0; token < active_count; ++token) {
                locations[token] = remainder % count;
                remainder /= count;
                token_at[locations[token]] = token;
            }
            for (int token = 0; token < active_count; ++token) {
                int first = locations[token];
                for (int edge_id : adjacency[first]) {
                    const Edge &edge = edges[edge_id];
                    int second = edge.first ^ edge.second ^ first;
                    int other = token_at[second];
                    if (other >= 0 && other < token) continue;
                    int following = code + (second - first) * powers[token];
                    if (other >= 0) following += (first - second) * powers[other];
                    int next_distance = distance + 3 * edge.weight;
                    if (next_distance < result->distances[following]) {
                        result->distances[following] = next_distance;
                        result->previous[following] = edge_id;
                        queue.emplace(next_distance + block.values[following], following);
                    }
                }
            }
        }
        if (forward_cache.size() >= 32) forward_cache.clear();
        forward_cache[key] = result;
        return result;
    }

    State prefix_of(const State &state, int steps) const {
        State prefix = initial;
        int operation_count = steps ? state.boundaries[steps - 1] : 0;
        for (int index = 0; index < operation_count; ++index) {
            const Operation &operation = state.operations[index];
            if (operation.kind) emit_swap(prefix, edge_index[operation.first][operation.second]);
            else emit_gate(prefix, operation.first);
        }
        prefix.completed.assign(state.completed.begin(), state.completed.begin() + steps);
        prefix.boundaries.assign(state.boundaries.begin(), state.boundaries.begin() + steps);
        return prefix;
    }

    vector<State> parking_options(const State &prefix, const vector<int> &order, int step) {
        const Block &block = blocks[order[step]];
        uint32_t introduced = 0;
        for (int following = step + 1; following < int(order.size()); ++following) {
            if (blocks[order[following]].mask & block.mask) {
                introduced = blocks[order[following]].mask & ~block.mask;
                break;
            }
        }
        vector<State> options{prefix};
        uint32_t blocked = 0;
        for (int logical : block.logical) blocked |= 1u << prefix.positions[logical];
        for (int logical = 0; logical < count; ++logical) {
            if (!(introduced & (1u << logical))) continue;
            int source = prefix.positions[logical];
            vector<int> distances(count, INF), previous(count, -1);
            vector<bool> settled(count, false);
            distances[source] = 0;
            for (int iteration = 0; iteration < count; ++iteration) {
                int current = -1;
                for (int physical = 0; physical < count; ++physical)
                    if (!settled[physical] && (current < 0 || distances[physical] < distances[current])) current = physical;
                if (current < 0 || distances[current] == INF) break;
                settled[current] = true;
                for (int edge_id : adjacency[current]) {
                    const Edge &edge = edges[edge_id];
                    int neighbor = edge.first ^ edge.second ^ current;
                    if (blocked & (1u << neighbor)) continue;
                    int next_distance = distances[current] + 3 * edge.weight;
                    if (next_distance < distances[neighbor]) {
                        distances[neighbor] = next_distance;
                        previous[neighbor] = edge_id;
                    }
                }
            }
            for (int destination = 0; destination < count; ++destination) {
                if (destination == source || distances[destination] == INF) continue;
                vector<int> path;
                int current = destination;
                while (current != source) {
                    int edge_id = previous[current];
                    path.push_back(edge_id);
                    current ^= edges[edge_id].first ^ edges[edge_id].second;
                }
                State state = prefix;
                for (auto iterator = path.rbegin(); iterator != path.rend(); ++iterator) emit_swap(state, *iterator);
                options.push_back(move(state));
            }
        }
        return options;
    }

    void explore_goals(const State &prefix, const vector<int> &order, int step, State &best) {
        int block_id = order[step];
        const Block &block = blocks[block_id];
        auto paths = forward_search(block_id, prefix);
        auto parking = parking_options(prefix, order, step);
        struct Candidate {
            double estimate;
            int path, parking;
        };
        vector<Candidate> candidates;
        vector<vector<int>> goal_moves;
        for (int goal_index : paths->settled_goals) {
            int code = block.goals[goal_index];
            double cost = (prefix.work + paths->distances[code] + block.goal_work[goal_index]) * 0.0001;
            if (cost >= best.cost()) continue;
            vector<int> moves;
            while (code != paths->source) {
                int edge_id = paths->previous[code];
                moves.push_back(edge_id);
                code = change_code(code, block.logical.size(), edge_id);
            }
            for (int parking_index = 0; parking_index < int(parking.size()); ++parking_index) {
                State state = parking[parking_index];
                for (auto iterator = moves.rbegin(); iterator != moves.rend(); ++iterator) emit_swap(state, *iterator);
                for (int gate_id : block.gates) emit_gate(state, gate_id);
                double estimate = state.cost() + potential(state, order, step, 0.85) * 0.0001;
                candidates.push_back({estimate, int(goal_moves.size()), parking_index});
            }
            goal_moves.push_back(move(moves));
            if (elapsed() > budget - 0.1) break;
        }
        sort(candidates.begin(), candidates.end(), [](const auto &first, const auto &second) {
            return first.estimate < second.estimate;
        });
        int evaluated = 0;
        for (const auto &candidate : candidates) {
            if (elapsed() > budget - 0.025 && evaluated > 0) break;
            State prefix_candidate = parking[candidate.parking];
            const auto &moves = goal_moves[candidate.path];
            for (auto iterator = moves.rbegin(); iterator != moves.rend(); ++iterator) emit_swap(prefix_candidate, *iterator);
            for (int gate_id : block.gates) emit_gate(prefix_candidate, gate_id);
            prefix_candidate.completed.push_back(block_id);
            prefix_candidate.boundaries.push_back(prefix_candidate.operations.size());
            for (double beta : {0.0, 0.35, 0.8, 1.5}) {
                State state = route(order, beta, 0.6, 0.0, false, step + 1, &prefix_candidate);
                if (state.cost() < best.cost()) best = move(state);
            }
            if (++evaluated >= 512) break;
        }
    }

    State frontier_route(const Block &metric, int lookahead, double future_weight, double decay_weight) {
        State state = initial;
        vector<vector<int>> successors(gate_count);
        vector<int> remaining(gate_count);
        vector<bool> done(gate_count, false);
        array<int, MAX_N> latest;
        latest.fill(-1);
        for (int gate_id = 0; gate_id < gate_count; ++gate_id) {
            int previous_first = latest[gates[gate_id].first];
            int previous_second = latest[gates[gate_id].second];
            if (previous_first >= 0) {
                successors[previous_first].push_back(gate_id);
                ++remaining[gate_id];
            }
            if (previous_second >= 0 && previous_first != previous_second) {
                successors[previous_second].push_back(gate_id);
                ++remaining[gate_id];
            }
            latest[gates[gate_id].first] = latest[gates[gate_id].second] = gate_id;
        }
        array<int, MAX_N> touched{};
        int swap_step = 0, stalled = 0, previous_swap = -1;
        while (true) {
            vector<int> frontier;
            for (int gate_id = 0; gate_id < gate_count; ++gate_id)
                if (!done[gate_id] && remaining[gate_id] == 0) frontier.push_back(gate_id);
            if (frontier.empty()) break;
            bool executed = false;
            for (int gate_id : frontier) {
                int first = state.positions[gates[gate_id].first];
                int second = state.positions[gates[gate_id].second];
                if (!weights[first][second]) continue;
                emit_gate(state, gate_id);
                done[gate_id] = true;
                for (int following : successors[gate_id]) --remaining[following];
                executed = true;
            }
            if (executed) {
                stalled = 0;
                previous_swap = -1;
                continue;
            }
            if (++stalled > 2 * count) {
                int gate_id = frontier.front();
                while (true) {
                    int code = state.positions[gates[gate_id].first] + count * state.positions[gates[gate_id].second];
                    int edge_id = metric.policy[code];
                    if (edge_id < 0) break;
                    emit_swap(state, edge_id);
                    touched[edges[edge_id].first] = touched[edges[edge_id].second] = ++swap_step;
                    previous_swap = edge_id;
                }
                stalled = 0;
                continue;
            }
            vector<int> future, pending = frontier;
            vector<bool> seen_gate(gate_count, false);
            for (int gate_id : frontier) seen_gate[gate_id] = true;
            for (int cursor = 0; cursor < int(pending.size()) && int(future.size()) < lookahead; ++cursor) {
                for (int following : successors[pending[cursor]]) {
                    if (done[following] || seen_gate[following]) continue;
                    seen_gate[following] = true;
                    future.push_back(following);
                    pending.push_back(following);
                    if (int(future.size()) == lookahead) break;
                }
            }
            vector<bool> candidate(edge_count, false);
            for (int gate_id : frontier) {
                for (int edge_id : adjacency[state.positions[gates[gate_id].first]]) candidate[edge_id] = true;
                for (int edge_id : adjacency[state.positions[gates[gate_id].second]]) candidate[edge_id] = true;
            }
            int best_edge = -1;
            double best_score = numeric_limits<double>::infinity();
            for (int edge_id = 0; edge_id < edge_count; ++edge_id) {
                if (!candidate[edge_id]) continue;
                swap_positions(state, edge_id);
                double front_score = 0, future_score = 0;
                for (int gate_id : frontier)
                    front_score += metric.values[state.positions[gates[gate_id].first] + count * state.positions[gates[gate_id].second]];
                for (int gate_id : future)
                    future_score += metric.values[state.positions[gates[gate_id].first] + count * state.positions[gates[gate_id].second]];
                const Edge &edge = edges[edge_id];
                int recency = max(0, 5 - min(swap_step - touched[edge.first], swap_step - touched[edge.second]));
                double score = front_score / frontier.size() + future_weight * future_score / max(size_t(1), future.size());
                score += 0.06 * 3 * edge.weight + decay_weight * 10000 * recency;
                if (edge_id == previous_swap) score += 10000;
                if (score < best_score) {
                    best_score = score;
                    best_edge = edge_id;
                }
                swap_positions(state, edge_id);
            }
            emit_swap(state, best_edge);
            touched[edges[best_edge].first] = touched[edges[best_edge].second] = ++swap_step;
            previous_swap = best_edge;
        }
        return state;
    }

    State fallback_route() {
        State state = initial;
        map<int, unique_ptr<Block>> tables;
        for (int first_gate = 0; first_gate < gate_count;) {
            int logical_first = gates[first_gate].first;
            int logical_second = gates[first_gate].second;
            int following = first_gate + 1;
            while (following < gate_count &&
                   ((gates[following].first == logical_first && gates[following].second == logical_second) ||
                    (gates[following].second == logical_first && gates[following].first == logical_second))) ++following;
            int repetitions = following - first_gate;
            auto found = tables.find(repetitions);
            if (found == tables.end()) {
                auto block = make_unique<Block>();
                block->logical = {0, 1};
                block->counts[0][1] = block->counts[1][0] = repetitions;
                compute(*block, false);
                found = tables.emplace(repetitions, move(block)).first;
            }
            const Block &block = *found->second;
            while (true) {
                int code = state.positions[logical_first] + count * state.positions[logical_second];
                int edge_id = block.policy[code];
                if (edge_id < 0) break;
                emit_swap(state, edge_id);
            }
            for (int gate_id = first_gate; gate_id < following; ++gate_id) emit_gate(state, gate_id);
            first_gate = following;
        }
        if (!tables.count(1)) {
            auto block = make_unique<Block>();
            block->logical = {0, 1};
            block->counts[0][1] = block->counts[1][0] = 1;
            compute(*block, false);
            tables.emplace(1, move(block));
        }
        const Block &metric = *tables.at(1);
        for (auto configuration : {make_pair(12, 0.35), make_pair(32, 0.65), make_pair(64, 1.0)}) {
            State alternative = frontier_route(metric, configuration.first, configuration.second, 0.03);
            if (alternative.cost() < state.cost()) state = move(alternative);
        }
        return state;
    }

    void output(const State &state) const {
        cout << "{\"operations\":[";
        bool first = true;
        for (const Operation &operation : state.operations) {
            if (!first) cout << ',';
            first = false;
            if (operation.kind) cout << "[\"swap\"," << operation.first << ',' << operation.second << ']';
            else cout << "[\"gate\"," << operation.first << ']';
        }
        cout << "]}\n";
    }

    void solve() {
        State fallback = fallback_route();
        if (gates.empty()) {
            output(fallback);
            return;
        }
        partition();
        visited.assign(powers[4], 0);
        for (Block &block : blocks) {
            if (!compute(block)) {
                if (getenv("ROUTER_DEBUG")) cerr << "fallback blocks=" << blocks.size() << " runtime=" << elapsed() << '\n';
                output(fallback);
                return;
            }
        }
        double preprocessing = elapsed();
        auto alternatives = orders();
        State best;
        best.work = numeric_limits<long long>::max() / 100;
        int trials = 0;
        for (const auto &order : alternatives) {
            State state = route(order, 0, 0, 0);
            if (state.cost() < best.cost()) best = move(state);
            ++trials;
        }
        const double betas[] = {0.15, 0.35, 0.6, 1.0, 1.5, 2.0};
        for (double beta : betas) {
            for (const auto &order : alternatives) {
                State state = route(order, beta, 0.55, 0);
                if (state.cost() < best.cost()) best = move(state);
                ++trials;
            }
        }
        for (int trial = 0; trial < 400 && elapsed() < budget; ++trial) {
            const auto &order = alternatives[generator() % alternatives.size()];
            double beta = (generator() % 201) * 0.01;
            double discount = 0.25 + (generator() % 76) * 0.01;
            double temperature = pow(10.0, -2.0 + (generator() % 301) * 0.01);
            bool relaxed = (generator() & 1) != 0;
            State state = route(order, beta, discount, temperature, relaxed);
            if (state.cost() < best.cost()) best = move(state);
            ++trials;
        }
        for (const auto &order : alternatives) {
            if (elapsed() > budget - 0.2) break;
            explore_goals(initial, order, 0, best);
        }
        int iteration = 0;
        int stagnant = 0;
        while (elapsed() < budget - 0.1) {
            double previous_best = best.cost();
            int step = iteration % blocks.size();
            State prefix = prefix_of(best, step);
            vector<int> order = best.completed;
            explore_goals(prefix, order, step, best);
            for (int trial = 0; trial < 80 && elapsed() < budget - 0.03; ++trial) {
                double beta = (generator() % 201) * 0.01;
                double discount = 0.25 + (generator() % 76) * 0.01;
                double temperature = pow(10.0, -2.0 + (generator() % 301) * 0.01);
                State state = route(order, beta, discount, temperature, false, step, &prefix);
                if (state.cost() < best.cost()) best = move(state);
                ++trials;
            }
            ++iteration;
            stagnant = best.cost() < previous_best ? 0 : stagnant + 1;
            if (stagnant >= int(blocks.size()) * 3 && elapsed() > 2.0) break;
        }
        if (getenv("ROUTER_DEBUG")) {
            cerr << "blocks=" << blocks.size() << " preprocess=" << preprocessing << " trials=" << trials
                 << " searches=" << forward_cache.size() << " cost=" << best.cost() << " runtime=" << elapsed() << '\n';
        }
        output(best.operations.size() <= 30000 && best.cost() < fallback.cost() ? best : fallback);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    Solver solver;
    solver.read();
    solver.solve();
}
