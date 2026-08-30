#include <algorithm>
#include <array>
#include <bitset>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

using namespace std;
using Mask = uint32_t;
using Gate = pair<int,int>;
using Circuit = vector<Gate>;
using Matrix = vector<Mask>;

mt19937_64 rng(57813);
double uniform() { return (rng() >> 11) * 0x1.0p-53; }
int weight(Mask mask) { return __builtin_popcount(mask); }
int firstbit(Mask mask) { return __builtin_ctz(mask); }

struct Case {
    string id;
    int size, edge_count, parity_count, count_budget, depth_budget;
    vector<Gate> edges;
    vector<vector<int>> adjacency;
    Matrix target, parities;
    int distance[20][20];
    vector<uint8_t> steiner;
};

Matrix identity(int size) {
    Matrix result(size);
    for (int wire = 0; wire < size; ++wire) result[wire] = 1u << wire;
    return result;
}

Matrix inverse(Matrix matrix) {
    int size = matrix.size();
    Matrix result = identity(size);
    for (int column = 0; column < size; ++column) {
        int pivot = column;
        while (!(matrix[pivot] >> column & 1)) ++pivot;
        swap(matrix[column], matrix[pivot]);
        swap(result[column], result[pivot]);
        for (int row = 0; row < size; ++row) if (row != column && (matrix[row] >> column & 1)) {
            matrix[row] ^= matrix[column];
            result[row] ^= result[column];
        }
    }
    return result;
}

Mask transform(Mask mask, const Matrix& matrix) {
    Mask result = 0;
    while (mask) {
        int wire = firstbit(mask);
        result ^= matrix[wire];
        mask &= mask - 1;
    }
    return result;
}

Matrix multiply(const Matrix& left, const Matrix& right) {
    Matrix result;
    for (Mask row : left) result.push_back(transform(row, right));
    return result;
}

int depth(const Circuit& circuit, int size) {
    vector<int> clocks(size);
    for (auto [control,target] : circuit) clocks[control] = clocks[target] = 1 + max(clocks[control],clocks[target]);
    return *max_element(clocks.begin(),clocks.end());
}

bool valid(const Case& instance, const Circuit& circuit) {
    Matrix rows = identity(instance.size);
    unordered_set<Mask> visited(rows.begin(),rows.end());
    for (auto [control,target] : circuit) {
        if (find(instance.adjacency[control].begin(), instance.adjacency[control].end(), target) == instance.adjacency[control].end()) return false;
        rows[target] ^= rows[control];
        visited.insert(rows[target]);
    }
    if (rows != instance.target) return false;
    for (Mask parity : instance.parities) if (!visited.count(parity)) return false;
    return true;
}

struct Tree {
    vector<int> parent, order;
    Mask vertices;
};

Tree make_tree(const Case& instance, Mask support, int root, Mask allowed, double randomness = 0) {
    int size = instance.size;
    Tree result;
    result.parent.assign(size,-1);
    result.order.push_back(root);
    result.vertices = 1u << root;
    while (support & ~result.vertices) {
        vector<double> distances(size, 1e9);
        vector<int> parents(size,-1);
        Mask processed = 0;
        for (int wire = 0; wire < size; ++wire) if (result.vertices >> wire & 1) distances[wire] = 0;
        int finish = -1;
        for (int step = 0; step < size; ++step) {
            int chosen = -1;
            for (int wire = 0; wire < size; ++wire) if ((allowed >> wire & 1) && !(processed >> wire & 1) && (chosen == -1 || distances[wire] < distances[chosen])) chosen = wire;
            if (chosen == -1 || distances[chosen] == 1e9) break;
            processed |= 1u << chosen;
            if ((support >> chosen & 1) && !(result.vertices >> chosen & 1)) { finish = chosen; break; }
            for (int neighbor : instance.adjacency[chosen]) if (allowed >> neighbor & 1) {
                double candidate = distances[chosen] + 1 + randomness * uniform();
                if (candidate < distances[neighbor]) {
                    distances[neighbor] = candidate;
                    parents[neighbor] = chosen;
                }
            }
        }
        if (finish == -1) throw runtime_error("tree disconnected");
        vector<int> path;
        for (int wire = finish; !(result.vertices >> wire & 1); wire = parents[wire]) path.push_back(wire);
        reverse(path.begin(),path.end());
        for (int wire : path) {
            result.parent[wire] = parents[wire];
            result.order.push_back(wire);
            result.vertices |= 1u << wire;
        }
    }
    return result;
}

Circuit reduce_vector(const Tree& tree, Mask mask) {
    Circuit result;
    for (int index = int(tree.order.size()) - 1; index > 0; --index) {
        int child = tree.order[index], parent = tree.parent[child];
        if (!(mask >> child & 1)) throw runtime_error("unexpected tree bit");
        if (!(mask >> parent & 1)) {
            result.emplace_back(child,parent);
            mask ^= 1u << parent;
        }
    }
    for (int index = int(tree.order.size()) - 1; index > 0; --index) {
        int child = tree.order[index], parent = tree.parent[child];
        result.emplace_back(parent,child);
    }
    return result;
}

bool connected(const Case& instance, Mask vertices) {
    if (!vertices) return true;
    Mask reached = 1u << firstbit(vertices), previous = 0;
    while (previous != reached) {
        previous = reached;
        for (int wire = 0; wire < instance.size; ++wire) if (reached >> wire & 1)
            for (int neighbor : instance.adjacency[wire]) if (vertices >> neighbor & 1) reached |= 1u << neighbor;
    }
    return reached == vertices;
}

Circuit finish_matrix(const Case& instance, Matrix matrix, double random_scale) {
    Mask remaining = (1u << instance.size) - 1;
    Circuit forward, backward;
    while (weight(remaining) > 1) {
        vector<int> possible;
        for (int wire = 0; wire < instance.size; ++wire) if ((remaining >> wire & 1) && connected(instance,remaining ^ (1u << wire))) possible.push_back(wire);
        int chosen = -1;
        Circuit chosen_rows, chosen_columns;
        double best = 1e9;
        for (int pivot : possible) {
            Matrix trial = matrix;
            Mask column = 0;
            for (int wire = 0; wire < instance.size; ++wire) if (trial[wire] >> pivot & 1) column |= 1u << wire;
            Tree tree = make_tree(instance,column,pivot,remaining,random_scale * 0.4);
            Circuit rows = reduce_vector(tree,column);
            for (auto [control,target] : rows) trial[target] ^= trial[control];
            Tree second = make_tree(instance,trial[pivot],pivot,remaining,random_scale * 0.4);
            Circuit columns = reduce_vector(second,trial[pivot]);
            double cost = rows.size() + columns.size() + uniform() * random_scale * 8;
            if (cost < best) { best = cost; chosen = pivot; chosen_rows = rows; chosen_columns = columns; }
        }
        for (auto [control,target] : chosen_rows) { matrix[target] ^= matrix[control]; backward.emplace_back(control,target); }
        for (auto [control,target] : chosen_columns) {
            for (Mask& row : matrix) if (row >> control & 1) row ^= 1u << target;
            forward.emplace_back(target,control);
        }
        remaining ^= 1u << chosen;
    }
    if (matrix != identity(instance.size)) throw runtime_error("finish failed");
    reverse(backward.begin(),backward.end());
    forward.insert(forward.end(),backward.begin(),backward.end());
    return forward;
}

struct End {
    Matrix rows, inverse_rows;
    Circuit gates;
    vector<int> clocks;
};

void append(End& endpoint, const Circuit& gates) {
    for (auto [control,target] : gates) {
        endpoint.rows[target] ^= endpoint.rows[control];
        for (Mask& row : endpoint.inverse_rows) if (row >> target & 1) row ^= 1u << control;
        endpoint.clocks[control] = endpoint.clocks[target] = 1 + max(endpoint.clocks[control],endpoint.clocks[target]);
        endpoint.gates.emplace_back(control,target);
    }
}

void mark_visited(const End& endpoint, vector<Mask>& remaining) {
    remaining.erase(remove_if(remaining.begin(),remaining.end(), [&](Mask mask) { return find(endpoint.rows.begin(),endpoint.rows.end(),mask) != endpoint.rows.end(); }), remaining.end());
}

double simple_cost(const Matrix& rows) {
    double result = 0;
    for (Mask row : rows) result += weight(row) - 1;
    return result;
}

Circuit solve_trees(const Case& instance, int variant) {
    End forward{identity(instance.size),identity(instance.size),{},vector<int>(instance.size)};
    End backward{instance.target,inverse(instance.target),{},vector<int>(instance.size)};
    vector<Mask> remaining = instance.parities;
    mark_visited(forward,remaining);
    mark_visited(backward,remaining);
    double noise = variant ? 0.1 + 1.8 * uniform() : 0;
    double balance = variant ? 0.1 + uniform() : 0.5;
    double lookahead = variant ? uniform() * 3 : 0.8;
    double matrix_weight = variant ? uniform() * 1.5 : 0.3;
    while (!remaining.empty()) {
        double best = 1e9;
        Circuit chosen;
        int chosen_end = 0;
        for (int side = 0; side < 2; ++side) {
            End& endpoint = side ? backward : forward;
            End& other = side ? forward : backward;
            Matrix coefficients;
            for (Mask mask : remaining) coefficients.push_back(transform(mask,endpoint.inverse_rows));
            for (Mask coefficient : coefficients) {
                for (int root = 0; root < instance.size; ++root) if (coefficient >> root & 1) {
                    Tree tree = make_tree(instance,coefficient,root,(1u << instance.size)-1,noise * 0.3);
                    Circuit reduce = reduce_vector(tree,coefficient);
                    Circuit gates;
                    for (auto [control,target] : reduce) gates.emplace_back(target,control);
                    End trial = endpoint;
                    append(trial,gates);
                    double after = 0;
                    for (Mask mask : remaining) {
                        int amount = min(weight(transform(mask,trial.inverse_rows)),weight(transform(mask,other.inverse_rows))) - 1;
                        after += amount;
                    }
                    int maximum = 0, total_clock = 0;
                    for (int wire = 0; wire < instance.size; ++wire) {
                        maximum = max(maximum,trial.clocks[wire] + other.clocks[wire]);
                        total_clock += trial.clocks[wire];
                    }
                    double cost = gates.size() + balance * maximum + 0.025 * total_clock + lookahead * after;
                    cost += matrix_weight * simple_cost(multiply(other.rows,trial.inverse_rows));
                    cost += noise * uniform() * 3;
                    if (cost < best) { best = cost; chosen = gates; chosen_end = side; }
                }
            }
        }
        End& endpoint = chosen_end ? backward : forward;
        for (Gate gate : chosen) { append(endpoint,{gate}); mark_visited(endpoint,remaining); }
    }
    Circuit best_finish;
    double best_cost = 1e9;
    for (int trial = 0; trial < 8; ++trial) {
        Circuit bridge = finish_matrix(instance,multiply(backward.rows,forward.inverse_rows),trial ? uniform() : 0);
        Circuit result = forward.gates;
        result.insert(result.end(),bridge.begin(),bridge.end());
        result.insert(result.end(),backward.gates.rbegin(),backward.gates.rend());
        double cost = depth(result,instance.size) + result.size() * 0.05;
        if (cost < best_cost) { best_cost = cost; best_finish = result; }
    }
    return best_finish;
}

void prepare_steiner(Case& instance) {
    int limit = 1 << instance.size;
    instance.steiner.assign(limit,instance.size);
    vector<Mask> adjacent(instance.size);
    for (auto [control,target] : instance.edges) {
        adjacent[control] |= 1u << target;
        adjacent[target] |= 1u << control;
    }
    instance.steiner[0] = 0;
    for (Mask mask = 1; mask < Mask(limit); ++mask) {
        Mask reached = mask & -mask, frontier = reached;
        while (frontier) {
            Mask next = 0;
            while (frontier) {
                int wire = firstbit(frontier);
                frontier &= frontier-1;
                next |= adjacent[wire];
            }
            frontier = next & mask & ~reached;
            reached |= frontier;
        }
        if (reached == mask) instance.steiner[mask] = weight(mask)-1;
    }
    for (int wire = 0; wire < instance.size; ++wire)
        for (Mask mask = 1; mask < Mask(limit); ++mask) if (!(mask >> wire & 1))
            instance.steiner[mask] = min(instance.steiner[mask],instance.steiner[mask | (1u << wire)]);
}

struct WalkState {
    Matrix residual, inverse_residual, forward_parities, backward_parities;
    uint64_t unvisited;
    vector<int> front_clock, back_clock;
};

struct Action { int side, control, target; };

void move(WalkState& state, Action action) {
    int control = action.control, target = action.target;
    Matrix& columns = action.side ? state.inverse_residual : state.residual;
    Matrix& rows = action.side ? state.residual : state.inverse_residual;
    Matrix& parities = action.side ? state.backward_parities : state.forward_parities;
    for (Mask& mask : columns) if (mask >> target & 1) mask ^= 1u << control;
    rows[target] ^= rows[control];
    for (int index = 0; index < int(parities.size()); ++index) if (state.unvisited >> index & 1) {
        Mask& mask = parities[index];
        if (mask >> target & 1) mask ^= 1u << control;
        if (weight(mask) == 1) state.unvisited &= ~(1ull << index);
    }
    vector<int>& clocks = action.side ? state.back_clock : state.front_clock;
    clocks[control] = clocks[target] = 1 + max(clocks[control],clocks[target]);
}

struct Weights {
    double native_weight, exponent, parity_weight, noise, clock_weight, target_weight;
};

double heuristic(const Case& instance, const WalkState& state, const Weights& coefficients) {
    double result = 0;
    auto metric = [&](Mask mask, int root) {
        double amount = weight(mask) - 1;
        double tree = 2 * instance.steiner[root < 0 ? mask : mask | (1u << root)] - weight(mask) + 1;
        double distance = amount * (1-coefficients.native_weight) + tree * coefficients.native_weight;
        if (root >= 0 && !(mask >> root & 1)) distance += 0.5;
        return pow(distance,coefficients.exponent);
    };
    for (int wire = 0; wire < instance.size; ++wire) {
        result += coefficients.target_weight * (metric(state.residual[wire],wire) + metric(state.inverse_residual[wire],wire));
    }
    for (int index = 0; index < instance.parity_count; ++index) if (state.unvisited >> index & 1) {
        double front = metric(state.forward_parities[index],-1);
        double back = metric(state.backward_parities[index],-1);
        result += coefficients.parity_weight * min(front,back);
    }
    return result;
}

Circuit solve_walk(const Case& instance, int variant) {
    Matrix target_inverse = inverse(instance.target);
    WalkState state{instance.target,target_inverse,instance.parities,multiply(instance.parities,target_inverse),
                    (1ull << instance.parity_count)-1, vector<int>(instance.size),vector<int>(instance.size)};
    for (int index = 0; index < instance.parity_count; ++index)
        if (weight(state.forward_parities[index]) == 1 || weight(state.backward_parities[index]) == 1) state.unvisited &= ~(1ull << index);
    Weights parameters;
    parameters.native_weight = uniform() * 0.8;
    parameters.exponent = 0.5 + uniform() * 0.7;
    parameters.parity_weight = 1 + 4 * uniform();
    parameters.noise = 0.05 + 0.5 * uniform();
    parameters.clock_weight = 0.02 + 0.2 * uniform();
    parameters.target_weight = 0.5 + 1.5 * uniform();
    vector<Action> actions;
    for (int side = 0; side < 2; ++side) for (auto [control,target] : instance.edges) {
        actions.push_back({side,control,target});
        actions.push_back({side,target,control});
    }
    Circuit forward, backward;
    int stale = 0, last = -1;
    double best_seen = 1e9;
    int total_limit = instance.count_budget;
    for (int iteration = 0; iteration < total_limit; ++iteration) {
        double current = heuristic(instance,state,parameters);
        if (current < best_seen - 0.01) { best_seen = current; stale = 0; } else ++stale;
        if (state.residual == identity(instance.size) && !state.unvisited) break;
        double best = 1e9;
        int chosen = -1;
        vector<pair<double,int>> candidates;
        for (int index = 0; index < int(actions.size()); ++index) if (index != last) {
            WalkState trial = state;
            move(trial,actions[index]);
            double score = heuristic(instance,trial,parameters);
            int clock_sum = 0, maximum = 0;
            for (int wire = 0; wire < instance.size; ++wire) {
                maximum = max(maximum,trial.front_clock[wire]+trial.back_clock[wire]);
                clock_sum += trial.front_clock[wire] + trial.back_clock[wire];
            }
            double adjusted = score + parameters.clock_weight * (maximum + 0.1 * clock_sum) + parameters.noise * uniform();
            candidates.emplace_back(adjusted,index);
            if (adjusted < best) { best = adjusted; chosen = index; }
        }
        if (stale > 4) {
            sort(candidates.begin(),candidates.end());
            double best_pair = 1e9;
            for (int candidate = 0; candidate < 5; ++candidate) {
                int index = candidates[candidate].second;
                WalkState middle = state;
                move(middle,actions[index]);
                for (int second = 0; second < int(actions.size()); ++second) if (second != index) {
                    WalkState trial = middle;
                    move(trial,actions[second]);
                    double score = heuristic(instance,trial,parameters) + parameters.noise * uniform();
                    if (score < best_pair) { best_pair = score; chosen = index; }
                }
            }
        }
        if (stale > 18) break;
        Action action = actions[chosen];
        move(state,action);
        (action.side ? backward : forward).emplace_back(action.control,action.target);
        last = chosen;
    }
    End front_end{identity(instance.size),identity(instance.size),{},vector<int>(instance.size)};
    End back_end{instance.target,target_inverse,{},vector<int>(instance.size)};
    append(front_end,forward);
    append(back_end,backward);
    vector<Mask> remaining;
    for (int index = 0; index < instance.parity_count; ++index) if (state.unvisited >> index & 1) remaining.push_back(instance.parities[index]);
    while (!remaining.empty()) {
        double best = 1e9;
        int chosen_side = -1;
        Circuit chosen_gates;
        for (int side = 0; side < 2; ++side) {
            End& endpoint = side ? back_end : front_end;
            End& other = side ? front_end : back_end;
            for (Mask parity : remaining) {
                Mask mask = transform(parity,endpoint.inverse_rows);
                for (int root = 0; root < instance.size; ++root) if (mask >> root & 1) {
                    Tree tree = make_tree(instance,mask,root,(1u << instance.size)-1,0.2);
                    Circuit gates = reduce_vector(tree,mask);
                    for (Gate& gate : gates) swap(gate.first,gate.second);
                    End trial = endpoint;
                    append(trial,gates);
                    int maximum = 0;
                    for (int wire = 0; wire < instance.size; ++wire) maximum = max(maximum,trial.clocks[wire]+other.clocks[wire]);
                    double score = gates.size() + 0.5 * maximum + 0.1 * simple_cost(multiply(other.rows,trial.inverse_rows));
                    for (Mask other_parity : remaining) score += 0.6 * min(weight(transform(other_parity,trial.inverse_rows)),weight(transform(other_parity,other.inverse_rows)));
                    if (score < best) { best = score; chosen_side = side; chosen_gates = gates; }
                }
            }
        }
        End& endpoint = chosen_side ? back_end : front_end;
        for (Gate gate : chosen_gates) { append(endpoint,{gate}); mark_visited(endpoint,remaining); }
    }
    Circuit best_circuit;
    double best_cost = 1e9;
    for (int trial = 0; trial < 5; ++trial) {
        Circuit bridge = finish_matrix(instance,multiply(back_end.rows,front_end.inverse_rows),trial ? uniform() : 0);
        Circuit circuit = front_end.gates;
        circuit.insert(circuit.end(),bridge.begin(),bridge.end());
        circuit.insert(circuit.end(),back_end.gates.rbegin(),back_end.gates.rend());
        double cost = depth(circuit,instance.size) + 0.03 * circuit.size();
        if (cost < best_cost) { best_cost = cost; best_circuit = circuit; }
    }
    return best_circuit;
}

#ifndef SOLVER_LIBRARY
int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : -1;
    int seconds = argc > 2 ? stoi(argv[2]) : 60;
    if (argc > 3) rng.seed(stoull(argv[3]));
    ifstream input("dev/instances.txt");
    int count;
    input >> count;
    vector<Case> cases(count);
    for (Case& instance : cases) {
        input >> instance.id >> instance.size >> instance.edge_count >> instance.parity_count >> instance.count_budget >> instance.depth_budget;
        instance.adjacency.resize(instance.size);
        for (int index = 0; index < instance.edge_count; ++index) {
            int control,target;
            input >> control >> target;
            instance.edges.emplace_back(control,target);
            instance.adjacency[control].push_back(target);
            instance.adjacency[target].push_back(control);
        }
        instance.target.resize(instance.size);
        instance.parities.resize(instance.parity_count);
        for (Mask& mask : instance.target) input >> mask;
        for (Mask& mask : instance.parities) input >> mask;
        prepare_steiner(instance);
    }
    for (int index = 0; index < count; ++index) if (selected == -1 || selected == index) {
        Case& instance = cases[index];
        double best = 1e9;
        auto started = chrono::steady_clock::now();
        int iteration = 0;
        do {
            Circuit circuit = iteration % 4 == 0 ? solve_trees(instance,iteration) : solve_walk(instance,iteration);
            if (!valid(instance,circuit)) throw runtime_error("invalid candidate");
            int circuit_depth = depth(circuit,instance.size);
            double cost = circuit_depth + 0.03 * circuit.size();
            if (cost < best) {
                best = cost;
                cerr << instance.id << " iteration=" << iteration << " count=" << circuit.size() << " depth=" << circuit_depth << endl;
                ofstream output("dev/" + instance.id + ".gates");
                for (auto [control,target] : circuit) output << control << ' ' << target << '\n';
            }
            ++iteration;
        } while (chrono::duration<double>(chrono::steady_clock::now()-started).count() < seconds);
    }
}
#endif
