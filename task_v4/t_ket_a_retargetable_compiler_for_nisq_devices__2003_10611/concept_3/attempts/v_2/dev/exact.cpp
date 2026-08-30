#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <z3++.h>

int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : 0;
    int timeout = argc > 2 ? stoi(argv[2]) : 600;
    int seed = argc > 3 ? stoi(argv[3]) : 17;
    int mode = argc > 4 ? stoi(argv[4]) : 0;
    int radius = argc > 5 ? stoi(argv[5]) : 3;
    rng.seed(seed);
    Case instance = read_cases()[selected];
    int size = instance.size, layers = instance.depth_budget;
    z3::context context;
    z3::solver solver(context,"QF_BV");
    z3::params params(context);
    params.set("timeout",unsigned(timeout*1000));
    params.set("random_seed",unsigned(seed));
    solver.set(params);
    vector<vector<z3::expr>> gates(layers), rows(layers+1), used(layers);
    vector<Gate> directed;
    for (auto [control,target] : instance.edges) {
        directed.emplace_back(control,target);
        directed.emplace_back(target,control);
    }
    for (int layer = 0; layer <= layers; ++layer) for (int wire = 0; wire < size; ++wire)
        rows[layer].push_back(context.bv_const(("r_"+to_string(layer)+"_"+to_string(wire)).c_str(),size));
    for (int layer = 0; layer < layers; ++layer) {
        for (int index = 0; index < int(directed.size()); ++index)
            gates[layer].push_back(context.bool_const(("g_"+to_string(layer)+"_"+to_string(index)).c_str()));
        for (int wire = 0; wire < size; ++wire) {
            z3::expr_vector incident(context);
            z3::expr incoming = context.bv_val(0,size);
            for (int index = 0; index < int(directed.size()); ++index) {
                auto [control,target] = directed[index];
                if (wire == control || wire == target) incident.push_back(gates[layer][index]);
                if (wire == target) incoming = incoming ^ z3::ite(gates[layer][index],rows[layer][control],context.bv_val(0,size));
            }
            solver.add(z3::atmost(incident,1));
            used[layer].push_back(z3::mk_or(incident));
            solver.add(rows[layer+1][wire] == (rows[layer][wire] ^ incoming));
        }
        if (layer > 0) for (int index = 0; index < int(directed.size()); ++index) {
            auto [control,target] = directed[index];
            solver.add(z3::implies(gates[layer][index],used[layer-1][control] || used[layer-1][target]));
        }
    }
    for (int wire = 0; wire < size; ++wire) {
        solver.add(rows[0][wire] == context.bv_val(1u << wire,size));
        solver.add(rows[layers][wire] == context.bv_val(instance.target[wire],size));
    }
    z3::expr_vector all_gates(context);
    for (auto& layer : gates) for (auto& gate : layer) all_gates.push_back(gate);
    solver.add(z3::atmost(all_gates,instance.count_budget));
    for (int first = 0; first < size; ++first) for (int second = 0; second < size; ++second)
        instance.distance[first][second] = first == second ? 0 : 100;
    for (auto [control,target] : instance.edges) instance.distance[control][target] = instance.distance[target][control] = 1;
    for (int middle = 0; middle < size; ++middle) for (int first = 0; first < size; ++first) for (int second = 0; second < size; ++second)
        instance.distance[first][second] = min(instance.distance[first][second],instance.distance[first][middle]+instance.distance[middle][second]);
    Matrix target_inverse = inverse(instance.target);
    vector<pair<int,int>> locations(instance.parity_count,{-1,-1});
    vector<int> original_times(instance.parity_count);
    if (mode) {
        Circuit example;
        double best_score = 1e9;
        for (string extension : {"optimized","local","satlocal","beam","global"}) {
            Circuit candidate = read_gates("dev/"+instance.id+"."+extension);
            double score = depth(candidate,size)+candidate.size()*0.04;
            if (!candidate.empty() && score < best_score) { best_score = score; example = candidate; }
        }
        Matrix state = identity(size);
        vector<int> clocks(size);
        int original_depth = depth(example,size);
        for (auto [control,target] : example) {
            state[target] ^= state[control];
            clocks[control] = clocks[target] = 1 + max(clocks[control],clocks[target]);
            for (int index = 0; index < instance.parity_count; ++index)
                if (state[target] == instance.parities[index] && locations[index].first < 0) {
                    locations[index] = {target,max(1,int(round(double(clocks[target])*layers/original_depth)))};
                    original_times[index] = clocks[target];
                }
        }
    }
    if (mode == 4) {
        for (int wire = 0; wire < size; ++wire) {
            vector<int> ordered;
            for (int index = 0; index < instance.parity_count; ++index) if (locations[index].first == wire) ordered.push_back(index);
            sort(ordered.begin(),ordered.end(),[&](int first,int second) { return original_times[first] < original_times[second]; });
            vector<int> earliest(ordered.size()), latest(ordered.size());
            for (int position = 0; position < int(ordered.size()); ++position) {
                int index = ordered[position];
                Mask reverse_mask = transform(instance.parities[index],target_inverse);
                int remaining = 0;
                for (int input = 0; input < size; ++input) {
                    if (instance.parities[index] >> input & 1) earliest[position] = max(earliest[position],instance.distance[wire][input]);
                    if (reverse_mask >> input & 1) remaining = max(remaining,instance.distance[wire][input]);
                }
                latest[position] = layers-remaining;
                if (position) earliest[position] = max(earliest[position],earliest[position-1]+1);
            }
            for (int position = int(ordered.size())-2; position >= 0; --position) latest[position] = min(latest[position],latest[position+1]-1);
            int previous = -1;
            for (int position = 0; position < int(ordered.size()); ++position) {
                int index = ordered[position];
                int proposed = locations[index].second + int(rng()%(radius*2+1))-radius;
                proposed = max(max(earliest[position],previous+1),min(latest[position],proposed));
                locations[index].second = proposed;
                previous = proposed;
            }
        }
    }
    for (int index = 0; index < instance.parity_count; ++index) {
        Mask parity = instance.parities[index];
        z3::expr_vector visits(context);
        Mask reverse_mask = transform(parity,target_inverse);
        for (int wire = 0; wire < size; ++wire) {
            if (mode && locations[index].first >= 0 && mode != 3 && wire != locations[index].first) continue;
            int earliest = 0, latest = 0;
            for (int input = 0; input < size; ++input) {
                if (parity >> input & 1) earliest = max(earliest,instance.distance[wire][input]);
                if (reverse_mask >> input & 1) latest = max(latest,instance.distance[wire][input]);
            }
            for (int layer = earliest; layer <= layers-latest; ++layer) {
                if (mode >= 2 && locations[index].first >= 0 && abs(layer-locations[index].second) > (mode == 4 ? 0 : radius)) continue;
                visits.push_back(rows[layer][wire] == context.bv_val(parity,size));
            }
        }
        solver.add(z3::mk_or(visits));
    }
    cerr << instance.id << " checking " << layers << " layers" << endl;
    auto result = solver.check();
    cerr << result << endl << solver.statistics() << endl;
    if (result == z3::sat) {
        auto model = solver.get_model();
        Circuit circuit;
        for (int layer = 0; layer < layers; ++layer) for (int index = 0; index < int(directed.size()); ++index)
            if (model.eval(gates[layer][index],true).is_true()) circuit.push_back(directed[index]);
        if (!valid(instance,circuit)) throw runtime_error("SAT witness invalid");
        save_gates("dev/"+instance.id+".satgates",circuit);
        cerr << "SOLUTION count=" << circuit.size() << " depth=" << depth(circuit,size) << endl;
    }
}
