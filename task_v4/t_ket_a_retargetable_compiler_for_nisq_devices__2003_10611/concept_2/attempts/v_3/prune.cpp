#define main search_entry
#include "search.cpp"
#undef main

struct PruneState {
    array<int, 16> position, occupants;
    array<bool, 200> completed{};
    int remaining;
};

Circuit original;
vector<Edge> swaps_to_try;
vector<array<int, 3>> pruning_route, best_route;
array<int, 16> best_mapping;
int best_swap_count;
long long nodes = 0;

void drain(PruneState &state) {
    bool progress = true;
    while (progress) {
        progress = false;
        for (int index = 0; index < int(original.gates.size()); ++index) {
            if (state.completed[index]) continue;
            auto parents = original.predecessors[index];
            if ((parents[0] >= 0 && !state.completed[parents[0]]) || (parents[1] >= 0 && !state.completed[parents[1]])) continue;
            auto gate = original.gates[index];
            int first = state.position[gate.first], second = state.position[gate.second];
            if (distances[first][second] != 1) continue;
            state.completed[index] = true;
            --state.remaining;
            pruning_route.push_back({index, first, second});
            progress = true;
        }
    }
}

void explore(PruneState state, int next, int chosen) {
    ++nodes;
    int route_size = pruning_route.size();
    drain(state);
    if (!state.remaining) {
        if (chosen < best_swap_count) {
            best_swap_count = chosen;
            best_route = pruning_route;
            best_mapping = state.position;
            cerr << "pruned to " << chosen << " at node " << nodes << endl;
        }
        pruning_route.resize(route_size);
        return;
    }
    if (chosen + 1 >= best_swap_count || next == int(swaps_to_try.size())) {
        pruning_route.resize(route_size);
        return;
    }
    for (int index = next; index < int(swaps_to_try.size()); ++index) {
        auto edge = swaps_to_try[index];
        PruneState changed = state;
        swap(changed.position[changed.occupants[edge.first]], changed.position[changed.occupants[edge.second]]);
        swap(changed.occupants[edge.first], changed.occupants[edge.second]);
        pruning_route.push_back({-1, edge.first, edge.second});
        explore(changed, index + 1, chosen + 1);
        pruning_route.pop_back();
        if (best_swap_count <= 8) break;
    }
    pruning_route.resize(route_size);
}

int main(int argc, char **argv) {
    initialize(argv[1]);
    ifstream input(argv[2]);
    int kind, edge_index;
    while (input >> kind >> edge_index) original.operations.push_back({kind, edge_index});
    if (!rebuild(original)) return 1;
    for (auto operation : original.operations) if (operation.swap) swaps_to_try.push_back(edges[operation.edge]);
    PruneState initial;
    iota(initial.position.begin(), initial.position.end(), 0);
    iota(initial.occupants.begin(), initial.occupants.end(), 0);
    initial.remaining = original.gates.size();
    best_swap_count = swaps_to_try.size() + 1;
    explore(initial, 0, 0);
    if (best_route.empty()) return 2;
    while (best_swap_count < 8) {
        auto edge = edges.front();
        best_route.push_back({-1, edge.first, edge.second});
        for (auto &node : best_mapping) {
            if (node == edge.first) node = edge.second;
            else if (node == edge.second) node = edge.first;
        }
        ++best_swap_count;
    }
    ofstream output(argv[3]);
    output << "{\"version\":1,\"hardware\":\"" << graph_name << "\",\"gates\":[";
    for (int index = 0; index < int(original.gates.size()); ++index) {
        if (index) output << ',';
        output << '[' << original.gates[index].first << ',' << original.gates[index].second << ']';
    }
    output << "],\"route\":[";
    for (int index = 0; index < int(best_route.size()); ++index) {
        if (index) output << ',';
        auto operation = best_route[index];
        if (operation[0] < 0) output << "[\"swap\"," << operation[1] << ',' << operation[2] << ']';
        else output << "[\"gate\"," << operation[0] << ',' << operation[1] << ',' << operation[2] << ']';
    }
    output << "],\"final_mapping\":[";
    for (int wire = 0; wire < 16; ++wire) { if (wire) output << ','; output << best_mapping[wire]; }
    output << "]}\n";
    cerr << "DONE nodes=" << nodes << " swaps=" << best_swap_count << endl;
}
