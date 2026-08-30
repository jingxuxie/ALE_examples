#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <queue>
#include <memory>
#include <unordered_map>

struct Layer {
    Circuit gates;
};

struct Group {
    vector<Layer> layers;
    vector<uint16_t> matrices;
    array<int,65536> index;
    vector<vector<int>> transitions;
    vector<uint8_t> distances;
    vector<array<uint8_t,16>> inverse_combinations;
    vector<uint16_t> visits;

    uint16_t apply(uint16_t matrix, const Layer& layer) {
        for (auto [control,target] : layer.gates) matrix ^= ((matrix >> (4*control)) & 15) << (4*target);
        return matrix;
    }

    Group(int edge_mask) {
        vector<Gate> edges;
        int bit = 0;
        for (int control = 0; control < 4; ++control) for (int target = control+1; target < 4; ++target,++bit) if (edge_mask >> bit & 1) edges.emplace_back(control,target);
        for (auto [control,target] : edges) {
            layers.push_back({{{control,target}}});
            layers.push_back({{{target,control}}});
        }
        for (int first = 0; first < int(edges.size()); ++first) for (int second = first+1; second < int(edges.size()); ++second) {
            auto [control,target] = edges[first];
            auto [other_control,other_target] = edges[second];
            if (control == other_control || control == other_target || target == other_control || target == other_target) continue;
            for (int direction = 0; direction < 4; ++direction)
                layers.push_back({{{direction & 1 ? target : control,direction & 1 ? control : target},
                                   {direction & 2 ? other_target : other_control,direction & 2 ? other_control : other_target}}});
        }
        index.fill(-1);
        matrices.push_back(0x8421);
        distances.push_back(0);
        index[0x8421] = 0;
        for (int position = 0; position < int(matrices.size()); ++position) {
            uint16_t matrix = matrices[position];
            vector<int> nexts;
            for (const Layer& layer : layers) {
                uint16_t next = apply(matrix,layer);
                if (index[next] == -1) {
                    index[next] = matrices.size();
                    matrices.push_back(next);
                    distances.push_back(distances[position]+1);
                }
                nexts.push_back(index[next]);
            }
            transitions.push_back(nexts);
        }
        for (uint16_t matrix : matrices) {
            Matrix rows(4);
            uint16_t visited = 0;
            for (int wire = 0; wire < 4; ++wire) { rows[wire] = matrix >> (wire*4) & 15; visited |= 1u << rows[wire]; }
            Matrix inversed = inverse(rows);
            array<uint8_t,16> combinations;
            for (Mask mask = 0; mask < 16; ++mask) combinations[mask] = transform(mask,inversed);
            inverse_combinations.push_back(combinations);
            visits.push_back(visited);
        }
    }

    int distance_to(int state, uint16_t target) {
        const auto& combination = inverse_combinations[state];
        uint16_t relative = 0;
        for (int wire = 0; wire < 4; ++wire) relative |= combination[(target >> (wire*4)) & 15] << (wire*4);
        return distances[index[relative]];
    }
};

unordered_map<int,unique_ptr<Group>> groups;
int local_mode = 0;

pair<Group*,vector<int>> get_group(const Case& instance, vector<int> subset) {
    sort(subset.begin(),subset.end());
    int best_mask = 1000;
    vector<int> best_order;
    do {
        int mask = 0, bit = 0;
        for (int control = 0; control < 4; ++control) for (int target = control+1; target < 4; ++target,++bit)
            if (find(instance.adjacency[subset[control]].begin(),instance.adjacency[subset[control]].end(),subset[target]) != instance.adjacency[subset[control]].end()) mask |= 1 << bit;
        if (mask < best_mask) { best_mask = mask; best_order = subset; }
    } while (next_permutation(subset.begin(),subset.end()));
    if (!groups.count(best_mask)) groups[best_mask] = make_unique<Group>(best_mask);
    return {groups[best_mask].get(),best_order};
}

struct SearchNode {
    int state;
    uint16_t seen;
    int distance, count, previous, action;
};

Circuit resynthesize(Group& group, uint16_t target, uint16_t required, int bound, int count_bound, int effort) {
    struct Priority {
        double score;
        int index;
        bool operator<(const Priority& other) const { return score > other.score; }
    };
    vector<SearchNode> nodes;
    priority_queue<Priority> queue;
    unordered_map<uint64_t,int> best;
    uint16_t first_seen = group.visits[0] & required;
    nodes.push_back({0,first_seen,0,0,-1,-1});
    queue.push({double(group.distance_to(0,target)),0});
    best[first_seen] = 0;
    int expanded = 0;
    double noise_scale = uniform()*0.04;
    while (!queue.empty() && expanded < effort) {
        int node_index = queue.top().index;
        queue.pop();
        SearchNode node = nodes[node_index];
        if (group.matrices[node.state] == target && node.seen == required) {
            vector<int> path;
            for (int cursor = node_index; nodes[cursor].previous != -1; cursor = nodes[cursor].previous) path.push_back(nodes[cursor].action);
            reverse(path.begin(),path.end());
            Circuit result;
            for (int action : path) for (Gate gate : group.layers[action].gates) result.push_back(gate);
            return result;
        }
        if (node.distance == bound) continue;
        ++expanded;
        vector<int> order(group.layers.size());
        iota(order.begin(),order.end(),0);
        shuffle(order.begin(),order.end(),rng);
        for (int action : order) {
            int next_state = group.transitions[node.state][action];
            int next_distance = node.distance+1, next_count = node.count+group.layers[action].gates.size();
            int lower_bound = group.distance_to(next_state,target);
            if (next_distance + lower_bound > bound || next_count > count_bound) continue;
            uint16_t seen = (node.seen | group.visits[next_state]) & required;
            if (group.layers[action].gates.size() > 1) {
                uint16_t middle = group.apply(group.matrices[node.state],{{group.layers[action].gates[0]}});
                seen |= group.visits[group.index[middle]] & required;
            }
            uint64_t key = (uint64_t(next_state) << 16) | seen;
            int cost = next_distance * 100 + next_count;
            auto existing = best.find(key);
            if (existing != best.end() && existing->second <= cost) continue;
            best[key] = cost;
            int index = nodes.size();
            nodes.push_back({next_state,seen,next_distance,next_count,node_index,action});
            double priority = next_distance+lower_bound + 0.003 * next_count + noise_scale * uniform();
            queue.push({priority,index});
        }
    }
    return {{-1,-1}};
}

Circuit replace_block(const Case& instance, const Circuit& original, int effort) {
    if (original.empty()) return original;
    int start = rng()%original.size();
    vector<int> subset;
    Gate first = original[start];
    subset.push_back(first.first);
    if (first.second >= 0) subset.push_back(first.second);
    while (subset.size() < 4) {
        vector<int> candidates;
        for (int wire : subset) for (int neighbor : instance.adjacency[wire]) if (find(subset.begin(),subset.end(),neighbor) == subset.end()) candidates.push_back(neighbor);
        if (candidates.empty()) return original;
        subset.push_back(candidates[rng()%candidates.size()]);
    }
    auto [group,order] = get_group(instance,subset);
    vector<int> local(instance.size,-1);
    for (int wire = 0; wire < 4; ++wire) local[order[wire]] = wire;
    Circuit block, outsiders;
    int finish = start;
    int count_limit = 6 + rng()%18;
    for (; finish < int(original.size()) && finish-start < 80; ++finish) {
        Gate gate = original[finish];
        bool inside = local[gate.first] >= 0 && (gate.second < 0 || local[gate.second] >= 0);
        if (inside) for (Gate other : outsiders) if (!commute(gate,other)) { inside = false; break; }
        if (inside) {
            block.emplace_back(local[gate.first],gate.second < 0 ? -1 : local[gate.second]);
            if (int(block.size()) >= count_limit) { ++finish; break; }
        } else outsiders.push_back(gate);
    }
    Circuit old_gates = stripped(block);
    if (old_gates.size() < 3) return original;
    uint16_t target = 0x8421, required = 0;
    for (auto [control,output] : block) {
        if (output < 0) required |= 1u << (target >> (4*control) & 15);
        else target ^= (target >> (4*control) & 15) << (4*output);
    }
    int bound = depth(old_gates,4);
    Circuit gates;
    if (local_mode && uniform() < 0.7) {
        const Layer& layer = group->layers[rng()%group->layers.size()];
        uint16_t prefix_matrix = group->apply(0x8421,layer);
        uint16_t reduced_required = required & ~(group->visits[0] | group->visits[group->index[prefix_matrix]]);
        uint16_t changed_target = target, changed_required = 0;
        for (auto [control,output] : layer.gates) {
            for (int wire = 0; wire < 4; ++wire) if (changed_target >> (wire*4+output) & 1) changed_target ^= 1u << (wire*4+control);
        }
        for (Mask mask = 1; mask < 16; ++mask) if (reduced_required >> mask & 1) {
            Mask transformed = mask;
            for (auto [control,output] : layer.gates) if (transformed >> output & 1) transformed ^= 1u << control;
            changed_required |= 1u << transformed;
        }
        gates = resynthesize(*group,changed_target,changed_required,bound,old_gates.size()+4-layer.gates.size(),effort);
        if (gates.empty() || gates[0].first >= 0) gates.insert(gates.begin(),layer.gates.begin(),layer.gates.end());
    } else {
        gates = resynthesize(*group,target,required,bound,old_gates.size()+(uniform()<0.2 ? 2 : 0),effort);
    }
    if (!gates.empty() && gates[0].first < 0) return original;
    Circuit replacement;
    Matrix rows = identity(4);
    auto phases = [&]() {
        for (int wire = 0; wire < 4; ++wire) if (required >> rows[wire] & 1) {
            replacement.emplace_back(order[wire],-1);
            required &= ~(1u << rows[wire]);
        }
    };
    phases();
    for (auto [control,output] : gates) {
        replacement.emplace_back(order[control],order[output]);
        rows[output] ^= rows[control];
        phases();
    }
    if (required) throw runtime_error("local missing phase");
    Circuit result(original.begin(),original.begin()+start);
    result.insert(result.end(),replacement.begin(),replacement.end());
    result.insert(result.end(),outsiders.begin(),outsiders.end());
    result.insert(result.end(),original.begin()+finish,original.end());
    return result;
}

double quality(const Case& instance, const Circuit& operations) {
    Circuit gates = stripped(operations);
    return depth(gates,instance.size) + gates.size() * 0.04 + 0.8*max(0,int(gates.size())-instance.count_budget);
}

#ifndef LOCAL_LIBRARY
int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : 0;
    int seconds = argc > 2 ? stoi(argv[2]) : 60;
    if (argc > 3) rng.seed(stoull(argv[3]));
    if (argc > 4) local_mode = stoi(argv[4]);
    Case instance = read_cases()[selected];
    Circuit best;
    double input_score = 1e9;
    for (string extension : {"optimized","local","satlocal","beam","satgates","hot","global","layers"}) {
        Circuit candidate = read_gates("dev/"+instance.id+"."+extension);
        if (!candidate.empty() && quality(instance,candidate) < input_score) { best = candidate; input_score = quality(instance,candidate); }
    }
    if (!valid(instance,best)) throw runtime_error("invalid local input");
    Circuit current = annotated(instance,best,0);
    double best_score = quality(instance,best), current_score = best_score;
    auto started = chrono::steady_clock::now();
    for (int iteration = 0; chrono::duration<double>(chrono::steady_clock::now()-started).count() < seconds; ++iteration) {
        Circuit candidate = replace_block(instance,current,3000);
        candidate = cancel(candidate);
        candidate = schedule(candidate,iteration);
        double score = quality(instance,candidate);
        double temperature = 0.1 + (local_mode ? 1.6 : 0.5) * (0.5+0.5*sin(iteration*0.007));
        if (score <= current_score || uniform() < exp((current_score-score)/temperature)) {
            current = candidate;
            current_score = score;
        }
        if (score < best_score) {
            best = stripped(candidate);
            if (!valid(instance,best)) throw runtime_error("local invalid result");
            best_score = score;
            save_gates("dev/"+instance.id+(local_mode ? ".hot" : ".local"),best);
            cerr << instance.id << " local " << iteration << " count=" << best.size() << " depth=" << depth(best,instance.size) << endl;
        }
        if (iteration % 1000 == 999) {
            current = annotated(instance,best,1);
            current_score = best_score;
        }
    }
}
#endif
