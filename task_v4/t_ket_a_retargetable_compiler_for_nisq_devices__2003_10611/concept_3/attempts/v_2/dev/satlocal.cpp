#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <z3++.h>
int layer_mode = 0;

Circuit exact_block(int size, const vector<Gate>& edges, const Circuit& operations, int bound, int count_bound, int timeout) {
    Matrix target = identity(size);
    unordered_set<Mask> required;
    for (auto [control,output] : operations) {
        if (output < 0) required.insert(target[control]);
        else target[output] ^= target[control];
    }
    z3::context context;
    z3::solver solver(context,"QF_BV");
    z3::params parameters(context);
    parameters.set("timeout",unsigned(timeout));
    parameters.set("random_seed",unsigned(rng()%1000000));
    solver.set(parameters);
    vector<vector<z3::expr>> gates(bound), rows(bound+1), used(bound);
    vector<Gate> directed;
    for (auto [control,output] : edges) { directed.emplace_back(control,output); directed.emplace_back(output,control); }
    for (int layer = 0; layer <= bound; ++layer) for (int wire = 0; wire < size; ++wire)
        rows[layer].push_back(context.bv_const(("r"+to_string(layer)+"_"+to_string(wire)).c_str(),size));
    z3::expr_vector all_gates(context);
    for (int layer = 0; layer < bound; ++layer) {
        for (int index = 0; index < int(directed.size()); ++index) {
            gates[layer].push_back(context.bool_const(("g"+to_string(layer)+"_"+to_string(index)).c_str()));
            all_gates.push_back(gates[layer].back());
        }
        for (int wire = 0; wire < size; ++wire) {
            z3::expr_vector incident(context);
            z3::expr incoming = context.bv_val(0,size);
            for (int index = 0; index < int(directed.size()); ++index) {
                auto [control,output] = directed[index];
                if (wire == control || wire == output) incident.push_back(gates[layer][index]);
                if (wire == output) incoming = incoming ^ z3::ite(gates[layer][index],rows[layer][control],context.bv_val(0,size));
            }
            solver.add(z3::atmost(incident,1));
            used[layer].push_back(z3::mk_or(incident));
            solver.add(rows[layer+1][wire] == (rows[layer][wire] ^ incoming));
        }
        if (layer) for (int index = 0; index < int(directed.size()); ++index) {
            auto [control,output] = directed[index];
            solver.add(z3::implies(gates[layer][index],used[layer-1][control] || used[layer-1][output]));
        }
    }
    solver.add(z3::atmost(all_gates,count_bound));
    for (int wire = 0; wire < size; ++wire) {
        solver.add(rows[0][wire] == context.bv_val(1u << wire,size));
        solver.add(rows[bound][wire] == context.bv_val(target[wire],size));
    }
    for (Mask parity : required) if (weight(parity) > 1) {
        z3::expr_vector visits(context);
        for (int layer = 1; layer <= bound; ++layer) for (int wire = 0; wire < size; ++wire)
            visits.push_back(rows[layer][wire] == context.bv_val(parity,size));
        solver.add(z3::mk_or(visits));
    }
    auto result = solver.check();
    if (result != z3::sat) return {{-1,-1}};
    auto model = solver.get_model();
    Circuit circuit;
    Matrix state = identity(size);
    auto phases = [&]() {
        for (int wire = 0; wire < size; ++wire) if (required.erase(state[wire])) circuit.emplace_back(wire,-1);
    };
    phases();
    for (int layer = 0; layer < bound; ++layer) for (int index = 0; index < int(directed.size()); ++index)
        if (model.eval(gates[layer][index],true).is_true()) {
            Gate gate = directed[index];
            circuit.push_back(gate);
            state[gate.second] ^= state[gate.first];
            phases();
        }
    if (state != target || !required.empty()) throw runtime_error("invalid SAT block");
    return circuit;
}

Circuit replace_layers(const Case& instance, const Circuit& original, int timeout) {
    vector<int> clocks(instance.size);
    vector<pair<pair<int,int>,Gate>> timed;
    for (Gate gate : original) {
        int level;
        if (gate.second < 0) level = clocks[gate.first];
        else {
            level = 1+max(clocks[gate.first],clocks[gate.second]);
            clocks[gate.first] = clocks[gate.second] = level;
        }
        timed.push_back({{level,gate.second < 0 ? 1 : 0},gate});
    }
    stable_sort(timed.begin(),timed.end(),[](const auto& first,const auto& second) { return first.first < second.first; });
    int circuit_depth = *max_element(clocks.begin(),clocks.end());
    int span = min(circuit_depth,4+int(rng()%7));
    int start = 1+rng()%(circuit_depth-span+1), finish = start+span-1;
    Circuit before, block, after;
    for (auto [time,gate] : timed) {
        if (time.first < start) before.push_back(gate);
        else if (time.first > finish) after.push_back(gate);
        else block.push_back(gate);
    }
    int count_bound = stripped(block).size()+6;
    Circuit replacement = exact_block(instance.size,instance.edges,block,span-1,count_bound,timeout);
    if (!replacement.empty() && replacement[0].first < 0) return original;
    before.insert(before.end(),replacement.begin(),replacement.end());
    before.insert(before.end(),after.begin(),after.end());
    return before;
}

Circuit replace_sat(const Case& instance, const Circuit& original, int timeout) {
    if (layer_mode) return replace_layers(instance,original,timeout);
    int start = rng()%original.size();
    int local_size = 5 + (uniform() < 0.4);
    vector<int> subset{original[start].first};
    if (original[start].second >= 0) subset.push_back(original[start].second);
    while (int(subset.size()) < local_size) {
        vector<int> candidates;
        for (int wire : subset) for (int neighbor : instance.adjacency[wire]) if (find(subset.begin(),subset.end(),neighbor) == subset.end()) candidates.push_back(neighbor);
        subset.push_back(candidates[rng()%candidates.size()]);
    }
    vector<int> local(instance.size,-1);
    for (int wire = 0; wire < local_size; ++wire) local[subset[wire]] = wire;
    vector<Gate> edges;
    for (auto [control,output] : instance.edges) if (local[control] >= 0 && local[output] >= 0) edges.emplace_back(local[control],local[output]);
    Circuit block, outsiders;
    int finish = start;
    int limit = 8 + rng()%18;
    for (; finish < int(original.size()) && finish-start < 80; ++finish) {
        Gate gate = original[finish];
        bool inside = local[gate.first] >= 0 && (gate.second < 0 || local[gate.second] >= 0);
        if (inside) for (Gate other : outsiders) if (!commute(gate,other)) { inside = false; break; }
        if (inside) {
            block.emplace_back(local[gate.first],gate.second < 0 ? -1 : local[gate.second]);
            if (int(block.size()) >= limit) { ++finish; break; }
        } else outsiders.push_back(gate);
    }
    Circuit old_gates = stripped(block);
    if (old_gates.size() < 5) return original;
    int old_depth = depth(old_gates,local_size);
    if (old_depth < 4) return original;
    int bound = old_depth - (uniform() < 0.75);
    int count_bound = old_gates.size() + (uniform() < 0.3 ? 2 : 0);
    Circuit replacement = exact_block(local_size,edges,block,bound,count_bound,timeout);
    if (!replacement.empty() && replacement[0].first < 0) return original;
    for (Gate& gate : replacement) {
        gate.first = subset[gate.first];
        if (gate.second >= 0) gate.second = subset[gate.second];
    }
    Circuit result(original.begin(),original.begin()+start);
    result.insert(result.end(),replacement.begin(),replacement.end());
    result.insert(result.end(),outsiders.begin(),outsiders.end());
    result.insert(result.end(),original.begin()+finish,original.end());
    return result;
}

double sat_quality(const Case& instance, const Circuit& circuit) {
    Circuit gates = stripped(circuit);
    return depth(gates,instance.size) + 0.04 * gates.size();
}

int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : 0;
    int seconds = argc > 2 ? stoi(argv[2]) : 120;
    if (argc > 3) rng.seed(stoull(argv[3]));
    if (argc > 4) layer_mode = stoi(argv[4]);
    Case instance = read_cases()[selected];
    Circuit best;
    double best_score = 1e9;
    for (string extension : {"optimized","local","satlocal","beam","satgates","hot","global","layers"}) {
        Circuit candidate = read_gates("dev/"+instance.id+"."+extension);
        if (!candidate.empty() && sat_quality(instance,candidate) < best_score) { best = candidate; best_score = sat_quality(instance,candidate); }
    }
    if (!valid(instance,best)) throw runtime_error("invalid SAT local input");
    Circuit current = annotated(instance,best,0);
    double current_score = best_score;
    auto started = chrono::steady_clock::now();
    for (int iteration = 0; chrono::duration<double>(chrono::steady_clock::now()-started).count() < seconds; ++iteration) {
        Circuit candidate = replace_sat(instance,current,layer_mode ? 1200 : 200);
        candidate = cancel(schedule(cancel(candidate),iteration));
        double score = sat_quality(instance,candidate);
        double temperature = 0.3;
        if (score <= current_score || uniform() < exp((current_score-score)/temperature)) { current = candidate; current_score = score; }
        if (score < best_score) {
            best = stripped(candidate);
            if (!valid(instance,best)) throw runtime_error("invalid SAT local result");
            best_score = score;
            save_gates("dev/"+instance.id+(layer_mode ? ".layers" : ".satlocal"),best);
            cerr << instance.id << " satlocal " << iteration << " count=" << best.size() << " depth=" << depth(best,instance.size) << endl;
        }
        if (iteration % 400 == 399) { current = annotated(instance,best,1); current_score = best_score; }
    }
}
