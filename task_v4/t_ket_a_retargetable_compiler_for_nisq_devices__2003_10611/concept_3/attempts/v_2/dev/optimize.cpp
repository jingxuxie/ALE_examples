#define SOLVER_LIBRARY
#include "solver.cpp"

bool commute(Gate first, Gate second) {
    if (first.second == -1 && second.second == -1) return true;
    if (first.second == -1) return first.first != second.second;
    if (second.second == -1) return second.first != first.second;
    return first.first != second.second && second.first != first.second;
}

Circuit annotated(const Case& instance, const Circuit& circuit, int variant) {
    Matrix rows = identity(instance.size);
    vector<vector<pair<int,int>>> occurrences(instance.parity_count);
    auto check = [&](int position) {
        for (int index = 0; index < instance.parity_count; ++index)
            for (int wire = 0; wire < instance.size; ++wire)
                if (rows[wire] == instance.parities[index]) occurrences[index].emplace_back(position,wire);
    };
    check(0);
    for (int index = 0; index < int(circuit.size()); ++index) {
        auto [control,target] = circuit[index];
        rows[target] ^= rows[control];
        check(index+1);
    }
    vector<vector<int>> phases(circuit.size()+1);
    for (auto& possible : occurrences) {
        if (possible.empty()) throw runtime_error("missing annotation parity");
        auto [position,wire] = possible[variant ? rng()%possible.size() : 0];
        phases[position].push_back(wire);
    }
    Circuit result;
    for (int index = 0; index <= int(circuit.size()); ++index) {
        for (int wire : phases[index]) result.emplace_back(wire,-1);
        if (index < int(circuit.size())) result.push_back(circuit[index]);
    }
    return result;
}

Circuit cancel(Circuit circuit) {
    vector<bool> removed(circuit.size());
    bool changed;
    do {
        changed = false;
        for (int index = 0; index < int(circuit.size()); ++index) if (!removed[index] && circuit[index].second >= 0) {
            for (int previous = index-1; previous >= 0; --previous) if (!removed[previous]) {
                if (circuit[previous] == circuit[index]) {
                    removed[previous] = removed[index] = true;
                    changed = true;
                    break;
                }
                if (!commute(circuit[previous],circuit[index])) break;
            }
        }
    } while (changed);
    Circuit result;
    for (int index = 0; index < int(circuit.size()); ++index) if (!removed[index]) result.push_back(circuit[index]);
    return result;
}

Circuit schedule(const Circuit& circuit, int variant) {
    int size = circuit.size();
    vector<vector<int>> successors(size);
    vector<int> indegrees(size), heights(size), descendants(size);
    for (int first = 0; first < size; ++first) for (int second = first+1; second < size; ++second) if (!commute(circuit[first],circuit[second])) {
        successors[first].push_back(second);
        ++indegrees[second];
    }
    for (int index = size-1; index >= 0; --index) {
        for (int next : successors[index]) heights[index] = max(heights[index],heights[next]);
        heights[index] += circuit[index].second >= 0;
        descendants[index] = successors[index].size();
    }
    vector<bool> done(size);
    Circuit result;
    int completed = 0;
    double descendant_weight = variant ? uniform()*0.15 : 0.03;
    double noise = variant ? uniform()*4 : 0;
    auto finish = [&](int index) {
        done[index] = true;
        ++completed;
        result.push_back(circuit[index]);
        for (int next : successors[index]) --indegrees[next];
    };
    while (completed < size) {
        bool phases;
        do {
            phases = false;
            for (int index = 0; index < size; ++index) if (!done[index] && !indegrees[index] && circuit[index].second == -1) {
                finish(index);
                phases = true;
            }
        } while (phases);
        vector<pair<double,int>> ready;
        for (int index = 0; index < size; ++index) if (!done[index] && !indegrees[index] && circuit[index].second >= 0)
            ready.emplace_back(heights[index] + descendant_weight * descendants[index] + noise * uniform(),index);
        sort(ready.rbegin(),ready.rend());
        Mask used = 0;
        vector<int> selected;
        for (auto [score,index] : ready) {
            auto [control,target] = circuit[index];
            Mask endpoints = (1u << control) | (1u << target);
            if (!(used & endpoints)) { used |= endpoints; selected.push_back(index); }
        }
        for (int index : selected) finish(index);
        if (selected.empty() && completed != size) throw runtime_error("schedule deadlock");
    }
    return result;
}

Circuit stripped(const Circuit& circuit) {
    Circuit result;
    for (Gate gate : circuit) if (gate.second >= 0) result.push_back(gate);
    return result;
}

vector<Case> read_cases() {
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
    }
    return cases;
}

Circuit read_gates(string path) {
    ifstream input(path);
    Circuit result;
    int control,target;
    while (input >> control >> target) result.emplace_back(control,target);
    return result;
}

void save_gates(string path, const Circuit& circuit) {
    ofstream output(path+".tmp");
    for (auto [control,target] : circuit) output << control << ' ' << target << '\n';
    output.close();
    rename((path+".tmp").c_str(),path.c_str());
}

#ifndef OPTIMIZE_LIBRARY
int main(int argc, char** argv) {
    int trials = argc > 1 ? stoi(argv[1]) : 500;
    for (Case& instance : read_cases()) {
        Circuit original = read_gates("dev/" + instance.id + ".gates");
        if (!valid(instance,original)) throw runtime_error("invalid source");
        Circuit best_circuit = original;
        double best = depth(original,instance.size) + original.size()*0.03;
        for (int trial = 0; trial < trials; ++trial) {
            Circuit operations = annotated(instance,trial % 10 ? best_circuit : original,trial);
            operations = cancel(operations);
            operations = schedule(operations,trial);
            operations = cancel(operations);
            Circuit circuit = stripped(operations);
            if (!valid(instance,circuit)) throw runtime_error("invalid optimization");
            double score = depth(circuit,instance.size) + circuit.size()*0.03;
            if (score < best) {
                best = score;
                best_circuit = circuit;
                cerr << instance.id << " schedule " << trial << " count=" << circuit.size() << " depth=" << depth(circuit,instance.size) << endl;
            }
        }
        save_gates("dev/"+instance.id+".optimized",best_circuit);
    }
}
#endif
