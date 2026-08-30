#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

struct Edge { int left; int right; };
struct Config {
    int horizon;
    double decay;
    int mode;
    std::array<int, 32> ranks;
    std::array<int, 16> labels;
    std::array<double, 200> weights;
};
static std::vector<Edge> edges;
static std::array<std::vector<int>, 16> neighbors;
static int distances[16][16];
static std::vector<Config> configs;

extern "C" void initialize(int edge_count, const int* edge_data, int config_count,
                           const int* horizons, const double* decays, const int* modes,
                           const int* ranks, const int* labels) {
    edges.clear();
    configs.clear();
    for (auto& adjacent : neighbors) adjacent.clear();
    for (int index = 0; index < edge_count; ++index) {
        Edge edge{edge_data[2*index], edge_data[2*index+1]};
        edges.push_back(edge);
        neighbors[edge.left].push_back(edge.right);
        neighbors[edge.right].push_back(edge.left);
    }
    for (int source = 0; source < 16; ++source) {
        for (int target = 0; target < 16; ++target) distances[source][target] = source == target ? 0 : 32;
        for (int target : neighbors[source]) distances[source][target] = 1;
    }
    for (int middle = 0; middle < 16; ++middle)
        for (int source = 0; source < 16; ++source)
            for (int target = 0; target < 16; ++target)
                distances[source][target] = std::min(distances[source][target], distances[source][middle] + distances[middle][target]);
    for (int index = 0; index < config_count; ++index) {
        Config config;
        config.horizon = horizons[index];
        config.decay = decays[index];
        config.mode = modes[index];
        for (int edge = 0; edge < edge_count; ++edge) config.ranks[edge] = ranks[index*edge_count+edge];
        for (int node = 0; node < 16; ++node) config.labels[node] = labels[index*16+node];
        for (int level = 0; level < 200; ++level) config.weights[level] = std::pow(config.decay, level);
        configs.push_back(config);
    }
}

struct Circuit {
    int count;
    std::array<Edge, 200> gates;
    int parents[200][2];
    explicit Circuit(int gate_count, const int* data) : count(gate_count) {
        int previous[16];
        std::fill(previous, previous+16, -1);
        for (int index = 0; index < count; ++index) {
            gates[index] = {data[2*index], data[2*index+1]};
            parents[index][0] = previous[gates[index].left];
            parents[index][1] = previous[gates[index].right];
            previous[gates[index].left] = previous[gates[index].right] = index;
        }
    }
};

static int route_count(const Circuit& circuit, const Config& config, int cap) {
    int position[16], occupants[16];
    for (int node = 0; node < 16; ++node) position[node] = occupants[node] = node;
    bool pending[200];
    std::fill(pending, pending+200, true);
    int remaining = circuit.count;
    int swaps = 0, stalled = 0;
    auto state_key = [&]() {
        uint64_t state = 0;
        for (int node = 0; node < 16; ++node) state |= uint64_t(position[node]) << (4*node);
        return state;
    };
    std::vector<uint64_t> visited{state_key()};
    auto apply = [&](int left, int right) {
        std::swap(occupants[left], occupants[right]);
        position[occupants[left]] = left;
        position[occupants[right]] = right;
        ++swaps;
    };
    while (remaining && swaps < cap) {
        std::vector<int> front, executable;
        for (int index = 0; index < circuit.count; ++index) {
            if (!pending[index]) continue;
            int first = circuit.parents[index][0], second = circuit.parents[index][1];
            if ((first < 0 || !pending[first]) && (second < 0 || !pending[second])) {
                front.push_back(index);
                auto gate = circuit.gates[index];
                if (distances[position[gate.left]][position[gate.right]] == 1) executable.push_back(index);
            }
        }
        if (!executable.empty()) {
            for (int index : executable) { pending[index] = false; --remaining; }
            visited = {state_key()};
            stalled = 0;
            continue;
        }
        int depth[200] = {};
        std::vector<std::vector<Edge>> layers(config.horizon);
        int level_count = 0;
        for (int index = 0; index < circuit.count; ++index) {
            if (!pending[index]) continue;
            int level = 0;
            for (int parent : circuit.parents[index])
                if (parent >= 0 && pending[parent]) level = std::max(level, depth[parent]+1);
            depth[index] = level;
            if (level < config.horizon) {
                layers[level].push_back(circuit.gates[index]);
                level_count = std::max(level_count, level+1);
            }
        }
        bool active[16] = {};
        for (int index : front) {
            active[position[circuit.gates[index].left]] = true;
            active[position[circuit.gates[index].right]] = true;
        }
        int chosen = -1;
        double best_score = 0;
        std::array<double, 200> best_values{};
        for (int edge_index = 0; edge_index < int(edges.size()); ++edge_index) {
            auto edge = edges[edge_index];
            if (!active[edge.left] && !active[edge.right]) continue;
            int first = occupants[edge.left], second = occupants[edge.right];
            std::swap(position[first], position[second]);
            uint64_t state = state_key();
            if (std::find(visited.begin(), visited.end(), state) == visited.end()) {
                std::array<double, 200> values{};
                double score = 0;
                for (int level = 0; level < level_count; ++level) {
                    int total = 0;
                    for (auto gate : layers[level]) total += distances[position[gate.left]][position[gate.right]] - 1;
                    values[level] = double(total) / std::max(size_t(1), layers[level].size());
                    score += values[level] * config.weights[level];
                }
                int comparison = 0;
                if (chosen >= 0) {
                    if (config.mode) {
                        for (int level = 0; level < level_count; ++level) {
                            if (values[level] != best_values[level]) {
                                comparison = values[level] < best_values[level] ? -1 : 1;
                                break;
                            }
                        }
                    } else comparison = score < best_score ? -1 : (score > best_score ? 1 : 0);
                }
                if (chosen < 0 || comparison < 0 || (comparison == 0 && config.ranks[edge_index] < config.ranks[chosen])) {
                    chosen = edge_index;
                    best_score = score;
                    best_values = values;
                }
            }
            std::swap(position[first], position[second]);
        }
        if (chosen >= 0 && stalled < 32) {
            apply(edges[chosen].left, edges[chosen].right);
            visited.push_back(state_key());
            ++stalled;
        } else {
            int selected = front.front();
            for (int index : front) {
                auto candidate = circuit.gates[index], incumbent = circuit.gates[selected];
                if (distances[position[candidate.left]][position[candidate.right]] < distances[position[incumbent.left]][position[incumbent.right]]) selected = index;
            }
            auto gate = circuit.gates[selected];
            int current = position[gate.left], destination = position[gate.right];
            while (distances[current][destination] > 1) {
                int next_node = -1;
                for (int neighbor : neighbors[current])
                    if (distances[neighbor][destination] == distances[current][destination]-1 &&
                        (next_node < 0 || config.labels[neighbor] < config.labels[next_node])) next_node = neighbor;
                apply(current, next_node);
                current = next_node;
            }
            pending[selected] = false;
            --remaining;
            visited = {state_key()};
            stalled = 0;
        }
    }
    return swaps;
}

extern "C" int evaluate(int gate_count, const int* data, int setting_count,
                         const int* setting_indices, int cap, int reject_below, int* output) {
    Circuit circuit(gate_count, data);
    for (int index = 0; index < setting_count; ++index) {
        output[index] = route_count(circuit, configs[setting_indices[index]], cap);
        if (output[index] < reject_below) return index+1;
    }
    return setting_count;
}
