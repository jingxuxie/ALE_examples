#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <z3++.h>

Circuit exact_schedule(const Case& instance, const Circuit& operations, int bound, int timeout) {
    int size = operations.size();
    vector<vector<int>> successors(size);
    vector<int> earliest(size), remaining(size);
    for (int first = 0; first < size; ++first) for (int second = first+1; second < size; ++second)
        if (!commute(operations[first],operations[second])) successors[first].push_back(second);
    for (int index = 0; index < size; ++index) {
        earliest[index] += operations[index].second >= 0;
        for (int next : successors[index]) earliest[next] = max(earliest[next],earliest[index]);
    }
    for (int index = size-1; index >= 0; --index) {
        for (int next : successors[index]) remaining[index] = max(remaining[index],remaining[next]);
        remaining[index] += operations[index].second >= 0;
    }
    int lower_bound = *max_element(earliest.begin(),earliest.end());
    if (lower_bound > bound) return {};
    z3::context context;
    z3::solver solver = z3::tactic(context,"sat").mk_solver();
    z3::params parameters(context);
    parameters.set("timeout",unsigned(timeout));
    parameters.set("random_seed",unsigned(rng()%100000));
    solver.set(parameters);
    vector<vector<z3::expr>> before(size);
    for (int index = 0; index < size; ++index) {
        int latest = bound - remaining[index] + (operations[index].second >= 0);
        if (latest < earliest[index]) return {};
        for (int time = 0; time <= bound; ++time) {
            if (time < earliest[index]) before[index].push_back(context.bool_val(false));
            else if (time >= latest) before[index].push_back(context.bool_val(true));
            else before[index].push_back(context.bool_const(("b"+to_string(index)+"_"+to_string(time)).c_str()));
            if (time) solver.add(z3::implies(before[index][time-1],before[index][time]));
        }
    }
    if (size >= 1024) throw runtime_error("schedule too large");
    vector<bitset<1024>> reachable(size);
    for (int index = size-1; index >= 0; --index) {
        for (int next : successors[index]) if (!reachable[index][next]) {
            reachable[index] |= reachable[next];
            reachable[index].set(next);
            int amount = operations[next].second >= 0 ? 1 : 0;
            for (int time = 0; time <= bound; ++time)
                solver.add(z3::implies(before[next][time],time < amount ? context.bool_val(false) : before[index][time-amount]));
        }
    }
    for (int wire = 0; wire < instance.size; ++wire) for (int time = 1; time <= bound; ++time) {
        z3::expr_vector incident(context);
        for (int index = 0; index < size; ++index) if (operations[index].second >= 0 && (operations[index].first == wire || operations[index].second == wire))
            incident.push_back(before[index][time] && !before[index][time-1]);
        if (incident.size() > 1) solver.add(z3::atmost(incident,1));
    }
    auto result = solver.check();
    cerr << instance.id << " scheduling depth=" << bound << " lower=" << lower_bound << " " << result << endl;
    if (result != z3::sat) return {};
    auto model = solver.get_model();
    vector<pair<int,Gate>> timed;
    for (int index = 0; index < size; ++index) if (operations[index].second >= 0) {
        int time = 1;
        while (!model.eval(before[index][time],true).is_true()) ++time;
        timed.push_back({time,operations[index]});
    }
    sort(timed.begin(),timed.end());
    Circuit circuit;
    for (auto [time,gate] : timed) circuit.push_back(gate);
    if (!valid(instance,circuit)) throw runtime_error("invalid exact schedule");
    return circuit;
}

int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : 4;
    int seconds = argc > 2 ? stoi(argv[2]) : 120;
    int requested = argc > 3 ? stoi(argv[3]) : -1;
    Case instance = read_cases()[selected];
    Circuit best;
    double best_score = 1e9;
    for (string extension : {"optimized","local","satlocal","beam","satgates","hot","global","layers","population","scheduled"}) {
        Circuit candidate = read_gates("dev/"+instance.id+"."+extension);
        double score = depth(candidate,instance.size)+candidate.size()*0.04;
        if (!candidate.empty() && score < best_score) { best = candidate; best_score = score; }
    }
    if (!valid(instance,best)) throw runtime_error("invalid scheduling input");
    if (argc > 4) best = read_gates(argv[4]);
    int current_depth = depth(best,instance.size);
    vector<int> bounds;
    if (requested > 0) for (int bound = requested; bound < current_depth; ++bound) bounds.push_back(bound);
    else for (int bound = current_depth-1; bound >= max(instance.depth_budget,current_depth-15); --bound) bounds.push_back(bound);
    auto started = chrono::steady_clock::now();
    for (int bound : bounds) {
        int remaining_seconds = seconds-int(chrono::duration<double>(chrono::steady_clock::now()-started).count());
        if (remaining_seconds <= 0) break;
        Circuit result = exact_schedule(instance,cancel(annotated(instance,best,0)),bound,min(60000,remaining_seconds*1000));
        if (!result.empty()) {
            Circuit saved = read_gates("dev/"+instance.id+".scheduled");
            if (saved.empty() || depth(result,instance.size)+result.size()*0.04 < depth(saved,instance.size)+saved.size()*0.04) save_gates("dev/"+instance.id+".scheduled",result);
            cerr << "RESULT count=" << result.size() << " depth=" << depth(result,instance.size) << endl;
            best = result;
            if (requested > 0) break;
        }
    }
}
