#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <unordered_set>
#include <vector>
using namespace std;

struct Edge { int first, second; };
struct Policy { int horizon, lex, tie; double decay; array<double, 201> weight; };
struct Family { array<int, 16> physical; array<array<int, 24>, 3> ranks; };
struct Operation { int swap, edge; };
struct Circuit {
    vector<Operation> operations;
    vector<Edge> gates;
    vector<array<int, 2>> predecessors;
    array<int, 16> final_mapping;
    int swaps = 0;
    vector<int> costs;
    double fitness = -1e9;
};
vector<Edge> edges;
vector<Policy> policies;
vector<Family> families;
array<array<int, 16>, 16> distances;
array<vector<int>, 16> neighbors;
mt19937_64 generator;
string graph_name;
int iterations = 0;

int random_int(int upper) { return generator() % upper; }
double random_unit() { return (generator() >> 11) * 0x1.0p-53; }

void initialize(const string &name) {
    graph_name = name;
    ifstream input(name + ".dat");
    int edge_count, family_count, policy_count;
    input >> edge_count;
    edges.resize(edge_count);
    for (auto &edge : edges) {
        input >> edge.first >> edge.second;
        neighbors[edge.first].push_back(edge.second);
        neighbors[edge.second].push_back(edge.first);
    }
    input >> family_count;
    families.resize(family_count);
    for (auto &family : families) {
        for (auto &node : family.physical) input >> node;
        for (auto &ranks : family.ranks)
            for (int index = 0; index < edge_count; ++index) input >> ranks[index];
    }
    input >> policy_count;
    policies.resize(policy_count);
    for (auto &policy : policies) {
        input >> policy.horizon >> policy.decay >> policy.lex >> policy.tie;
        for (int level = 0; level <= 200; ++level) policy.weight[level] = pow(policy.decay, level);
    }
    for (int first = 0; first < 16; ++first)
        for (int second = 0; second < 16; ++second)
            distances[first][second] = first == second ? 0 : 100;
    for (auto edge : edges) distances[edge.first][edge.second] = distances[edge.second][edge.first] = 1;
    for (int middle = 0; middle < 16; ++middle)
        for (int first = 0; first < 16; ++first)
            for (int second = 0; second < 16; ++second)
                distances[first][second] = min(distances[first][second], distances[first][middle] + distances[middle][second]);
}

bool rebuild(Circuit &circuit) {
    array<int, 16> occupants, position, previous, coverage{};
    array<unsigned, 16> partners{};
    array<array<int, 16>, 16> pair_counts{};
    iota(occupants.begin(), occupants.end(), 0);
    iota(position.begin(), position.end(), 0);
    previous.fill(-1);
    circuit.gates.clear();
    circuit.predecessors.clear();
    circuit.swaps = 0;
    bool admissible = true;
    for (auto operation : circuit.operations) {
        auto edge = edges[operation.edge];
        int first = occupants[edge.first], second = occupants[edge.second];
        if (operation.swap) {
            swap(occupants[edge.first], occupants[edge.second]);
            swap(position[first], position[second]);
            ++circuit.swaps;
        } else {
            int index = circuit.gates.size();
            if (previous[first] == previous[second] && previous[first] >= 0) admissible = false;
            circuit.predecessors.push_back({previous[first], previous[second]});
            circuit.gates.push_back({first, second});
            previous[first] = previous[second] = index;
            ++coverage[first]; ++coverage[second];
            partners[first] |= 1u << second;
            partners[second] |= 1u << first;
            if (++pair_counts[min(first, second)][max(first, second)] > 8) admissible = false;
        }
    }
    circuit.final_mapping = position;
    int distinct = 0;
    for (int wire = 0; wire < 16; ++wire) {
        if (coverage[wire] < 4 || coverage[wire] > min(40, (int(circuit.gates.size()) + 3) / 4)) admissible = false;
        if (__builtin_popcount(partners[wire]) < 2) admissible = false;
        distinct += __builtin_popcount(partners[wire]);
    }
    unsigned reached = 1;
    for (int step = 0; step < 16; ++step)
        for (int wire = 0; wire < 16; ++wire)
            if (reached & (1u << wire)) reached |= partners[wire];
    return admissible && reached == 65535 && distinct >= 32 && circuit.swaps >= 8 && circuit.swaps <= 200;
}

uint64_t encode(const array<int, 16> &position) {
    uint64_t result = 0;
    for (int wire = 0; wire < 16; ++wire) result |= uint64_t(position[wire]) << (4 * wire);
    return result;
}

int route_cost(const Circuit &circuit, int family_index, int policy_index, int bound = 100000) {
    const auto &policy = policies[policy_index];
    const auto &family = families[family_index];
    const int gate_count = circuit.gates.size();
    array<int, 16> position, occupants;
    iota(position.begin(), position.end(), 0);
    iota(occupants.begin(), occupants.end(), 0);
    array<bool, 200> completed{};
    int remaining = gate_count, swaps = 0, stalled = 0;
    unordered_set<uint64_t> visited;
    visited.insert(encode(position));
    auto apply_swap = [&](int first, int second) {
        swap(position[occupants[first]], position[occupants[second]]);
        swap(occupants[first], occupants[second]);
        ++swaps;
    };
    while (remaining) {
        array<int, 16> front{};
        int front_count = 0;
        bool executed = false;
        for (int index = 0; index < gate_count; ++index) {
            if (completed[index]) continue;
            auto parents = circuit.predecessors[index];
            if ((parents[0] < 0 || completed[parents[0]]) && (parents[1] < 0 || completed[parents[1]]))
                front[front_count++] = index;
        }
        for (int offset = 0; offset < front_count; ++offset) {
            int index = front[offset];
            auto gate = circuit.gates[index];
            if (distances[position[gate.first]][position[gate.second]] == 1) {
                completed[index] = true;
                --remaining;
                executed = true;
            }
        }
        if (executed) {
            visited.clear(); visited.insert(encode(position)); stalled = 0;
            continue;
        }
        array<int, 200> depth{};
        array<int, 201> layer_count{};
        int levels = 0;
        for (int index = 0; index < gate_count; ++index) {
            if (completed[index]) { depth[index] = -1; continue; }
            auto parents = circuit.predecessors[index];
            int level = max(parents[0] < 0 ? -1 : depth[parents[0]], parents[1] < 0 ? -1 : depth[parents[1]]) + 1;
            depth[index] = level;
            if (level < policy.horizon) { ++layer_count[level]; levels = max(levels, level + 1); }
        }
        unsigned active = 0;
        for (int offset = 0; offset < front_count; ++offset) {
            auto gate = circuit.gates[front[offset]];
            active |= (1u << position[gate.first]) | (1u << position[gate.second]);
        }
        int chosen = -1;
        double best_score = 0;
        array<double, 201> best_values{};
        if (stalled < 32) for (int edge_index = 0; edge_index < int(edges.size()); ++edge_index) {
            auto edge = edges[edge_index];
            if (!(active & ((1u << edge.first) | (1u << edge.second)))) continue;
            int first = occupants[edge.first], second = occupants[edge.second];
            swap(position[first], position[second]);
            uint64_t state = encode(position);
            if (!visited.count(state)) {
                array<int, 201> sums{};
                for (int index = 0; index < gate_count; ++index) {
                    int level = depth[index];
                    if (level < 0 || level >= levels) continue;
                    auto gate = circuit.gates[index];
                    sums[level] += distances[position[gate.first]][position[gate.second]] - 1;
                }
                array<double, 201> values{};
                double score = 0;
                for (int level = 0; level < levels; ++level) {
                    values[level] = double(sums[level]) / max(1, layer_count[level]);
                    score += values[level] * policy.weight[level];
                }
                int comparison = 0;
                if (chosen < 0) comparison = -1;
                else if (policy.lex) {
                    for (int level = 0; level < levels; ++level) {
                        if (values[level] < best_values[level]) { comparison = -1; break; }
                        if (values[level] > best_values[level]) { comparison = 1; break; }
                    }
                } else comparison = score < best_score ? -1 : score > best_score ? 1 : 0;
                if (comparison < 0 || (comparison == 0 && family.ranks[policy.tie][edge_index] < family.ranks[policy.tie][chosen])) {
                    chosen = edge_index; best_score = score; best_values = values;
                }
            }
            swap(position[first], position[second]);
        }
        if (chosen >= 0) {
            auto edge = edges[chosen];
            apply_swap(edge.first, edge.second);
            visited.insert(encode(position));
            ++stalled;
        } else {
            int index = front[0];
            for (int offset = 1; offset < front_count; ++offset) {
                auto current = circuit.gates[index], alternate = circuit.gates[front[offset]];
                if (distances[position[alternate.first]][position[alternate.second]] < distances[position[current.first]][position[current.second]]) index = front[offset];
            }
            auto gate = circuit.gates[index];
            int current = position[gate.first], destination = position[gate.second];
            while (distances[current][destination] > 1) {
                int next = -1;
                for (int neighbor : neighbors[current])
                    if (distances[neighbor][destination] == distances[current][destination] - 1 && (next < 0 || family.physical[neighbor] < family.physical[next])) next = neighbor;
                apply_swap(current, next); current = next;
            }
            completed[index] = true; --remaining;
            visited.clear(); visited.insert(encode(position)); stalled = 0;
        }
        if (swaps >= bound) return swaps;
    }
    return swaps;
}

void save(const Circuit &circuit, const string &path) {
    ofstream output(path);
    output << "{\"version\":1,\"hardware\":\"" << graph_name << "\",\"gates\":[";
    for (int index = 0; index < int(circuit.gates.size()); ++index) {
        if (index) output << ',';
        auto gate = circuit.gates[index];
        output << '[' << gate.first << ',' << gate.second << ']';
    }
    output << "],\"route\":[";
    int gate_index = 0;
    for (int index = 0; index < int(circuit.operations.size()); ++index) {
        if (index) output << ',';
        auto operation = circuit.operations[index];
        auto edge = edges[operation.edge];
        if (operation.swap) output << "[\"swap\"," << edge.first << ',' << edge.second << ']';
        else output << "[\"gate\"," << gate_index++ << ',' << edge.first << ',' << edge.second << ']';
    }
    output << "],\"final_mapping\":[";
    for (int wire = 0; wire < 16; ++wire) { if (wire) output << ','; output << circuit.final_mapping[wire]; }
    output << "]}\n";
}

Circuit generate(int gate_count, int swap_count, int style) {
    Circuit circuit;
    vector<int> swap_slots;
    for (int index = 0; index < swap_count; ++index) {
        int slot;
        if (style == 0) slot = random_int(gate_count);
        else if (style == 1) slot = index < swap_count * 3 / 4 ? 0 : gate_count * 2 / 3;
        else if (style == 2) slot = index < swap_count / 2 ? gate_count / 10 : index < swap_count * 4 / 5 ? gate_count / 2 : gate_count * 4 / 5;
        else if (style == 3) slot = index < swap_count - 2 ? 0 : gate_count * (index - swap_count + 3) / 3;
        else slot = (index / 3) * gate_count / ((swap_count + 2) / 3);
        swap_slots.push_back(slot);
    }
    sort(swap_slots.begin(), swap_slots.end());
    array<int, 16> occupants, previous, coverage{};
    array<array<int, 16>, 16> pair_counts{};
    iota(occupants.begin(), occupants.end(), 0);
    previous.fill(-1);
    int next_swap = 0, last_swap = -1;
    for (int index = 0; index < gate_count; ++index) {
        while (next_swap < swap_count && swap_slots[next_swap] == index) {
            int edge_index = random_int(edges.size());
            while (edge_index == last_swap) edge_index = random_int(edges.size());
            auto edge = edges[edge_index];
            swap(occupants[edge.first], occupants[edge.second]);
            circuit.operations.push_back({1, edge_index});
            ++next_swap; last_swap = edge_index;
        }
        vector<double> weights;
        double total = 0;
        for (auto edge : edges) {
            int first = occupants[edge.first], second = occupants[edge.second];
            double weight = 0;
            if ((previous[first] != previous[second] || previous[first] < 0) && pair_counts[min(first,second)][max(first,second)] < 8)
                weight = 1.0 / pow(2 + coverage[first] + coverage[second], 2);
            total += weight; weights.push_back(weight);
        }
        if (total == 0) return circuit;
        double draw = random_unit() * total;
        int edge_index = 0;
        for (; edge_index < int(edges.size()) - 1; ++edge_index) { draw -= weights[edge_index]; if (draw < 0) break; }
        auto edge = edges[edge_index];
        int first = occupants[edge.first], second = occupants[edge.second];
        previous[first] = previous[second] = index;
        ++coverage[first]; ++coverage[second];
        ++pair_counts[min(first,second)][max(first,second)];
        circuit.operations.push_back({0, edge_index});
    }
    rebuild(circuit);
    return circuit;
}

double target(const Circuit &circuit) {
    return max({2.5 * circuit.swaps, double(circuit.swaps + 16), .11666666666666667 * circuit.gates.size() + 1.35 * circuit.swaps});
}

double assess(Circuit &circuit, vector<int> &tests, double cutoff = -1e9, bool full = false) {
    circuit.fitness = -1e9;
    double goal = target(circuit);
    double minimum = 1e9, total = 0;
    circuit.costs.assign(families.size() * policies.size(), -1);
    int tested = 0;
    for (int identifier : tests) {
        int family = identifier / policies.size(), policy = identifier % policies.size();
        int cost = route_cost(circuit, family, policy, int(goal + 30));
        circuit.costs[identifier] = cost;
        minimum = min(minimum, double(cost));
        total += min(double(cost), goal + 15);
        ++tested;
        if (!full && minimum - goal + .1 < cutoff) return minimum - goal;
    }
    circuit.fitness = minimum - goal + .001 * total / tested;
    return circuit.fitness;
}

int main(int argc, char **argv) {
    string name = argc > 1 ? argv[1] : "grid16";
    int seconds = argc > 2 ? stoi(argv[2]) : 120;
    int seed = argc > 3 ? stoi(argv[3]) : 1;
    generator.seed(seed);
    initialize(name);
    auto start = chrono::steady_clock::now();
    vector<int> tests;
    for (int policy : {12, 20, 22, 10, 6, 0, 16, 28, 34, 40, 46, 52, 58}) tests.push_back(policy);
    if (argc > 5 && string(argv[5]) == "ALL") {
        for (int identifier = 0; identifier < int(families.size() * policies.size()); ++identifier)
            if (find(tests.begin(), tests.end(), identifier) == tests.end()) tests.push_back(identifier);
    } else if (argc > 5) {
        ifstream test_file(argv[5]);
        tests.clear();
        int identifier;
        while (test_file >> identifier) tests.push_back(identifier);
    }
    vector<Circuit> pool;
    Circuit best;
    double best_fitness = -1e9;
    if (argc > 4 && string(argv[4]) != "-") {
        ifstream seed_file(argv[4]);
        Circuit initial;
        int kind, edge_index;
        while (seed_file >> kind >> edge_index) initial.operations.push_back({kind, edge_index});
        if (rebuild(initial)) {
            assess(initial, tests, -1e9, true);
            pool.push_back(initial);
            best = initial;
            best_fitness = initial.fitness;
            cerr << "INITIAL " << best_fitness << " G=" << best.gates.size() << " W=" << best.swaps << endl;
        }
    }
    int generated = 0, valid = 0, evaluated = 0;
    while (chrono::duration<double>(chrono::steady_clock::now() - start).count() < seconds) {
        Circuit candidate;
        bool fresh = pool.empty() || random_unit() < .12;
        if (fresh) {
            int gate_count = 64 + 8 * random_int(9);
            int swap_count = 7 + random_int(11);
            candidate = generate(gate_count, swap_count, random_int(5));
            int first_edge = random_int(edges.size()), second_edge = random_int(edges.size());
            while (first_edge == second_edge || (edges[first_edge].first != edges[second_edge].first && edges[first_edge].first != edges[second_edge].second && edges[first_edge].second != edges[second_edge].first && edges[first_edge].second != edges[second_edge].second)) second_edge = random_int(edges.size());
            candidate.operations.push_back({0, first_edge});
            candidate.operations.push_back({0, second_edge});
            candidate.operations.push_back({1, second_edge});
            candidate.operations.push_back({0, first_edge});
            ++generated;
        } else {
            int parent = random_int(pool.size());
            candidate = pool[parent];
            int mutations = 1 + (random_unit() < .25 ? 1 + random_int(4) : 0);
            for (int mutation = 0; mutation < mutations; ++mutation) {
                int mutable_count = candidate.operations.size() - 4;
                int offset = random_int(mutable_count);
                int kind = random_int(10);
                if (kind < 7) candidate.operations[offset].edge = random_int(edges.size());
                else if (kind < 9) {
                    int other = max(0, min(mutable_count - 1, offset + random_int(13) - 6));
                    swap(candidate.operations[offset], candidate.operations[other]);
                } else {
                    int other = random_int(mutable_count);
                    swap(candidate.operations[offset], candidate.operations[other]);
                }
            }
        }
        ++iterations;
        if (!rebuild(candidate) || candidate.gates.size() < 48 || candidate.gates.size() > 200 || candidate.gates.size() % 4 != 3) continue;
        ++valid;
        double threshold = pool.size() < 16 ? -1e9 : pool.back().fitness - 2.0;
        double fitness = assess(candidate, tests, threshold);
        ++evaluated;
        if (fitness > best_fitness) {
            best_fitness = fitness; best = candidate;
            save(best, name + "_best.json");
            cerr << "BEST " << name << " seed=" << seed << " iter=" << iterations << " valid=" << valid << " G=" << best.gates.size() << " W=" << best.swaps << " target=" << target(best) << " fitness=" << fitness << " costs=";
            for (int test : tests) cerr << best.costs[test] << ',';
            cerr << endl;
            stable_sort(tests.begin(), tests.end(), [&](int first, int second) { return best.costs[first] < best.costs[second]; });
            if (fitness >= -1.0) save(best, name + "_candidate_" + to_string(seed) + "_" + to_string(iterations) + ".json");
        }
        if (candidate.fitness > -1e8 && (pool.size() < 24 || candidate.fitness > pool.back().fitness || random_unit() < .02)) {
            bool duplicate = false;
            for (auto &member : pool) if (member.gates.size() == candidate.gates.size() && member.costs == candidate.costs) duplicate = true;
            if (!duplicate) {
                pool.push_back(candidate);
                sort(pool.begin(), pool.end(), [](auto &first, auto &second) { return first.fitness > second.fitness; });
                if (pool.size() > 24) pool.pop_back();
            }
        }
    }
    cerr << "DONE generated=" << generated << " valid=" << valid << " evaluated=" << evaluated << " iterations=" << iterations << " best=" << best_fitness << endl;
    save(best, name + "_best.json");
    vector<int> full_tests;
    for (int identifier = 0; identifier < int(families.size() * policies.size()); ++identifier) full_tests.push_back(identifier);
    assess(best, full_tests, -1e9, true);
    ofstream costs(name + "_costs.txt");
    for (int family = 0; family < int(families.size()); ++family) {
        for (int policy = 0; policy < int(policies.size()); ++policy) costs << best.costs[family * policies.size() + policy] << ' ';
        costs << '\n';
    }
    return 0;
}
