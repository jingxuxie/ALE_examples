#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

using Pair = std::array<int, 2>;

struct Graph {
    int edge_count;
    Pair edges[24];
    int distances[16][16];
    int physical[6][16];
    int rank[6][3][24];
    double weights[2][16];
} graph;

extern "C" void setup(int edge_count, const int* edges, const int* physical,
                      const int* ranks) {
    graph.edge_count = edge_count;
    for (int node = 0; node < 16; ++node) {
        for (int other = 0; other < 16; ++other)
            graph.distances[node][other] = node == other ? 0 : 17;
        for (int family = 0; family < 6; ++family)
            graph.physical[family][node] = physical[family * 16 + node];
    }
    for (int index = 0; index < edge_count; ++index) {
        int left = edges[2 * index], right = edges[2 * index + 1];
        graph.edges[index] = {left, right};
        graph.distances[left][right] = graph.distances[right][left] = 1;
        for (int family = 0; family < 6; ++family)
            for (int tie = 0; tie < 3; ++tie)
                graph.rank[family][tie][index] = ranks[(family * 3 + tie) * edge_count + index];
    }
    for (int middle = 0; middle < 16; ++middle)
        for (int left = 0; left < 16; ++left)
            for (int right = 0; right < 16; ++right)
                graph.distances[left][right] = std::min(graph.distances[left][right],
                    graph.distances[left][middle] + graph.distances[middle][right]);
    for (int level = 0; level < 16; ++level) {
        graph.weights[0][level] = std::pow(0.5, level);
        graph.weights[1][level] = std::pow(0.9, level);
    }
}

struct Circuit {
    int size;
    Pair gates[200];
    Pair parents[200];
    std::vector<int> incident[16];
    Circuit(int count, const int* values) : size(count) {
        int previous[16];
        std::fill(previous, previous + 16, -1);
        for (int index = 0; index < size; ++index) {
            int left = values[index * 2], right = values[index * 2 + 1];
            gates[index] = {left, right};
            parents[index] = {previous[left], previous[right]};
            previous[left] = previous[right] = index;
            incident[left].push_back(index);
            incident[right].push_back(index);
        }
    }
};

int route(const Circuit& circuit, int family, int variant) {
    int horizon = variant < 16 ? (2 << (variant / 4)) : 8;
    int decay = (variant % 4) / 2;
    int tie = variant < 16 ? variant % 2 : (variant == 16 ? 0 : 2);
    bool lexicographic = variant >= 16;
    int position[16], occupants[16];
    uint64_t state = 0;
    for (int node = 0; node < 16; ++node) {
        position[node] = occupants[node] = node;
        state |= uint64_t(node) << (4 * node);
    }
    std::vector<uint64_t> visited{state};
    bool pending[200];
    std::fill(pending, pending + circuit.size, true);
    int remaining = circuit.size, swaps = 0, stalled = 0;
    auto apply_swap = [&](int left, int right) {
        int first = occupants[left], second = occupants[right];
        uint64_t change = left ^ right;
        state ^= (change << (4 * first)) | (change << (4 * second));
        std::swap(occupants[left], occupants[right]);
        std::swap(position[first], position[second]);
        ++swaps;
    };
    while (remaining) {
        std::vector<int> front;
        bool executed = false;
        for (int index = 0; index < circuit.size; ++index) {
            if (!pending[index]) continue;
            auto parents = circuit.parents[index];
            if ((parents[0] >= 0 && pending[parents[0]]) ||
                (parents[1] >= 0 && pending[parents[1]])) continue;
            auto gate = circuit.gates[index];
            if (graph.distances[position[gate[0]]][position[gate[1]]] == 1) {
                pending[index] = false;
                --remaining;
                executed = true;
            } else front.push_back(index);
        }
        if (executed) {
            visited.clear();
            visited.push_back(state);
            stalled = 0;
        }
        if (!remaining) break;
        int depth[200];
        int totals[16] = {}, sizes[16] = {};
        for (int index = 0; index < circuit.size; ++index) {
            depth[index] = -1;
            if (!pending[index]) continue;
            auto parents = circuit.parents[index];
            int level = 0;
            for (int parent : parents)
                if (parent >= 0 && pending[parent]) level = std::max(level, depth[parent] + 1);
            depth[index] = level;
            if (level < horizon) {
                auto gate = circuit.gates[index];
                totals[level] += graph.distances[position[gate[0]]][position[gate[1]]] - 1;
                ++sizes[level];
            }
        }
        unsigned active = 0;
        for (int index : front) {
            auto gate = circuit.gates[index];
            active |= (1u << position[gate[0]]) | (1u << position[gate[1]]);
        }
        int best = -1;
        double best_values[16] = {};
        for (int edge_index = 0; edge_index < graph.edge_count; ++edge_index) {
            auto edge = graph.edges[edge_index];
            int left = edge[0], right = edge[1];
            if (!(active & ((1u << left) | (1u << right)))) continue;
            int first = occupants[left], second = occupants[right];
            uint64_t change = left ^ right;
            uint64_t next_state = state ^ ((change << (4 * first)) | (change << (4 * second)));
            if (std::find(visited.begin(), visited.end(), next_state) != visited.end()) continue;
            int sums[16];
            std::copy(totals, totals + horizon, sums);
            for (int qubit : {first, second}) {
                int old_node = position[qubit], new_node = old_node == left ? right : left;
                for (int index : circuit.incident[qubit]) {
                    int level = depth[index];
                    if (level < 0 || level >= horizon) continue;
                    auto gate = circuit.gates[index];
                    int other = gate[0] ^ gate[1] ^ qubit;
                    if (other == first || other == second) continue;
                    int other_node = position[other];
                    sums[level] += graph.distances[new_node][other_node] - graph.distances[old_node][other_node];
                }
            }
            double values[16] = {};
            for (int level = 0; level < horizon; ++level) {
                double value = double(sums[level]) / std::max(1, sizes[level]);
                if (lexicographic) values[level] = value;
                else values[0] += value * graph.weights[decay][level];
            }
            bool better = best < 0;
            if (best >= 0) {
                int comparison = 0;
                for (int level = 0; level < (lexicographic ? horizon : 1); ++level) {
                    if (values[level] < best_values[level]) { comparison = -1; break; }
                    if (values[level] > best_values[level]) { comparison = 1; break; }
                }
                better = comparison < 0 || (comparison == 0 &&
                    graph.rank[family][tie][edge_index] < graph.rank[family][tie][best]);
            }
            if (better) {
                best = edge_index;
                std::copy(values, values + horizon, best_values);
            }
        }
        if (best >= 0 && stalled < 32) {
            apply_swap(graph.edges[best][0], graph.edges[best][1]);
            visited.push_back(state);
            ++stalled;
        } else {
            int chosen = -1, smallest = 100;
            for (int index : front) {
                auto gate = circuit.gates[index];
                int distance = graph.distances[position[gate[0]]][position[gate[1]]];
                if (distance < smallest) { smallest = distance; chosen = index; }
            }
            auto gate = circuit.gates[chosen];
            int current = position[gate[0]], destination = position[gate[1]];
            while (graph.distances[current][destination] > 1) {
                int next = -1;
                for (int node = 0; node < 16; ++node)
                    if (graph.distances[current][node] == 1 &&
                        graph.distances[node][destination] == graph.distances[current][destination] - 1 &&
                        (next < 0 || graph.physical[family][node] < graph.physical[family][next])) next = node;
                apply_swap(current, next);
                current = next;
            }
            pending[chosen] = false;
            --remaining;
            visited.clear();
            visited.push_back(state);
            stalled = 0;
        }
    }
    return swaps;
}

extern "C" void evaluate(int gate_count, const int* gates, int setting_count,
                         const int* settings, int* results) {
    Circuit circuit(gate_count, gates);
    for (int index = 0; index < setting_count; ++index)
        results[index] = route(circuit, settings[index] / 18, settings[index] % 18);
}
