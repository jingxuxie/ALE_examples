#define OPTIMIZE_LIBRARY
#include "optimize.cpp"
#include <queue>

struct FastState {
    array<Mask,20> residual, reversed;
    array<Mask,34> front_parities, back_parities;
    array<uint16_t,20> front_clock{}, back_clock{};
    uint64_t unvisited;
    double score;
    int history;
};

struct History { int previous, action; };
struct FastWeights { double native, exponent, parity, clock; };

double fast_score(const Case& instance, const FastState& state, const vector<float>& metric, const FastWeights& parameters) {
    double result = 0;
    int maximum = 0, total_clock = 0;
    for (int wire = 0; wire < instance.size; ++wire) {
        Mask forward = state.residual[wire], backward = state.reversed[wire];
        result += metric[forward] + metric[backward];
        if (!(forward >> wire & 1)) result += 0.8 + parameters.native * (instance.steiner[forward | (1u << wire)] - instance.steiner[forward]);
        if (!(backward >> wire & 1)) result += 0.8 + parameters.native * (instance.steiner[backward | (1u << wire)] - instance.steiner[backward]);
        maximum = max(maximum,int(state.front_clock[wire])+state.back_clock[wire]);
        total_clock += state.front_clock[wire]+state.back_clock[wire];
    }
    for (int index = 0; index < instance.parity_count; ++index) if (state.unvisited >> index & 1)
        result += parameters.parity * (0.2+min(metric[state.front_parities[index]],metric[state.back_parities[index]]));
    return result + parameters.clock * (maximum + 0.025 * total_clock);
}

uint64_t fast_hash(const Case& instance, const FastState& state) {
    uint64_t hash = state.unvisited * 0x9e3779b97f4a7c15ull;
    for (int wire = 0; wire < instance.size; ++wire) hash = (hash ^ state.residual[wire]) * 0x9e3779b97f4a7c15ull;
    for (int index = 0; index < instance.parity_count; ++index) if (state.unvisited >> index & 1) {
        hash = (hash ^ state.front_parities[index]) * 0x9e3779b97f4a7c15ull;
        hash = (hash ^ state.back_parities[index]) * 0x9e3779b97f4a7c15ull;
    }
    return hash;
}

void fast_move(const Case& instance, FastState& state, Action action) {
    int control = action.control, target = action.target;
    auto& columns = action.side ? state.reversed : state.residual;
    auto& rows = action.side ? state.residual : state.reversed;
    auto& parities = action.side ? state.back_parities : state.front_parities;
    for (int wire = 0; wire < instance.size; ++wire) if (columns[wire] >> target & 1) columns[wire] ^= 1u << control;
    rows[target] ^= rows[control];
    for (int index = 0; index < instance.parity_count; ++index) if (state.unvisited >> index & 1) {
        Mask& mask = parities[index];
        if (mask >> target & 1) mask ^= 1u << control;
        if (weight(mask) == 1) state.unvisited &= ~(1ull << index);
    }
    auto& clocks = action.side ? state.back_clock : state.front_clock;
    clocks[control] = clocks[target] = 1 + max(clocks[control],clocks[target]);
}

Circuit materialize(const Case& instance, const FastState& state, const vector<History>& history, const vector<Action>& actions) {
    vector<Action> path;
    for (int cursor = state.history; cursor >= 0; cursor = history[cursor].previous) path.push_back(actions[history[cursor].action]);
    reverse(path.begin(),path.end());
    End front{identity(instance.size),identity(instance.size),{},vector<int>(instance.size)};
    End back{instance.target,inverse(instance.target),{},vector<int>(instance.size)};
    for (Action action : path) append(action.side ? back : front,{{action.control,action.target}});
    vector<Mask> remaining;
    for (int index = 0; index < instance.parity_count; ++index) if (state.unvisited >> index & 1) remaining.push_back(instance.parities[index]);
    while (!remaining.empty()) {
        double best = 1e9;
        int chosen_side = -1;
        Circuit chosen;
        for (int side = 0; side < 2; ++side) {
            End& endpoint = side ? back : front;
            End& other = side ? front : back;
            for (Mask parity : remaining) {
                Mask mask = transform(parity,endpoint.inverse_rows);
                for (int root = 0; root < instance.size; ++root) if (mask >> root & 1) {
                    Tree tree = make_tree(instance,mask,root,(1u << instance.size)-1,0.3);
                    Circuit gates = reduce_vector(tree,mask);
                    for (Gate& gate : gates) swap(gate.first,gate.second);
                    End trial = endpoint;
                    append(trial,gates);
                    int maximum = 0;
                    for (int wire = 0; wire < instance.size; ++wire) maximum = max(maximum,trial.clocks[wire]+other.clocks[wire]);
                    double score = gates.size()+0.5*maximum+0.1*simple_cost(multiply(other.rows,trial.inverse_rows));
                    for (Mask other_parity : remaining) score += 0.5*min(weight(transform(other_parity,trial.inverse_rows)),weight(transform(other_parity,other.inverse_rows)));
                    if (score < best) { best = score; chosen_side = side; chosen = gates; }
                }
            }
        }
        End& endpoint = chosen_side ? back : front;
        for (Gate gate : chosen) { append(endpoint,{gate}); mark_visited(endpoint,remaining); }
    }
    Circuit bridge = finish_matrix(instance,multiply(back.rows,front.inverse_rows),uniform());
    Circuit result = front.gates;
    result.insert(result.end(),bridge.begin(),bridge.end());
    result.insert(result.end(),back.gates.rbegin(),back.gates.rend());
    return result;
}

Circuit gatebeam(const Case& instance, int width, int variant, int seconds) {
    FastWeights parameters{0.3,0.6,1.8,0.12};
    if (variant) parameters = {uniform()*0.8,0.4+uniform()*0.5,0.7+uniform()*3,0.05+uniform()*0.35};
    vector<float> metric(1 << instance.size);
    for (Mask mask = 1; mask < metric.size(); ++mask) {
        double amount = (1-parameters.native) * (weight(mask)-1) + parameters.native * (2*instance.steiner[mask]-weight(mask)+1);
        metric[mask] = pow(amount,parameters.exponent);
    }
    FastState initial;
    Matrix reversed = inverse(instance.target);
    for (int wire = 0; wire < instance.size; ++wire) { initial.residual[wire] = instance.target[wire]; initial.reversed[wire] = reversed[wire]; }
    initial.unvisited = (1ull << instance.parity_count)-1;
    for (int index = 0; index < instance.parity_count; ++index) {
        initial.front_parities[index] = instance.parities[index];
        initial.back_parities[index] = transform(instance.parities[index],reversed);
        if (weight(initial.front_parities[index]) == 1 || weight(initial.back_parities[index]) == 1) initial.unvisited &= ~(1ull << index);
    }
    initial.score = fast_score(instance,initial,metric,parameters);
    initial.history = -1;
    vector<Action> actions;
    for (int side = 0; side < 2; ++side) for (auto [control,target] : instance.edges) {
        actions.push_back({side,control,target}); actions.push_back({side,target,control});
    }
    vector<History> history;
    vector<FastState> beam{initial};
    Circuit best;
    double best_score = 1e9;
    auto started = chrono::steady_clock::now();
    unordered_set<uint64_t> recent;
    for (int step = 0; step < instance.count_budget && !beam.empty(); ++step) {
        if (chrono::duration<double>(chrono::steady_clock::now()-started).count() > seconds) break;
        struct Entry { double score; int parent, action; uint64_t hash; bool operator<(const Entry& other) const { return score < other.score; } };
        priority_queue<Entry> heap;
        unordered_set<uint64_t> keys;
        for (int parent = 0; parent < int(beam.size()); ++parent) {
            int last = beam[parent].history < 0 ? -1 : history[beam[parent].history].action;
            for (int index = 0; index < int(actions.size()); ++index) if (index != last) {
                FastState child = beam[parent];
                fast_move(instance,child,actions[index]);
                double score = fast_score(instance,child,metric,parameters);
                if (int(heap.size()) == width && score >= heap.top().score) continue;
                uint64_t hash = fast_hash(instance,child);
                if (keys.count(hash) || recent.count(hash)) continue;
                if (int(heap.size()) == width) { keys.erase(heap.top().hash); heap.pop(); }
                heap.push({score,parent,index,hash}); keys.insert(hash);
            }
        }
        vector<FastState> next;
        unordered_set<uint64_t> next_recent;
        while (!heap.empty()) {
            Entry entry = heap.top(); heap.pop();
            FastState child = beam[entry.parent];
            fast_move(instance,child,actions[entry.action]);
            history.push_back({beam[entry.parent].history,entry.action});
            child.history = history.size()-1;
            child.score = entry.score;
            next_recent.insert(entry.hash);
            if (heap.size() < 3 && __builtin_popcountll(child.unvisited) <= 12 && step % 10 == 9) {
                Circuit circuit = materialize(instance,child,history,actions);
                circuit = stripped(cancel(schedule(cancel(annotated(instance,circuit,0)),0)));
                double score = depth(circuit,instance.size)+circuit.size()*0.04;
                if (score < best_score) {
                    best_score = score;
                    best = circuit;
                    cerr << instance.id << " gatebeam step=" << step << " count=" << circuit.size() << " depth=" << depth(circuit,instance.size) << endl;
                    Circuit saved = read_gates("dev/"+instance.id+".global");
                    if (saved.empty() || score < depth(saved,instance.size)+saved.size()*0.04) save_gates("dev/"+instance.id+".global",circuit);
                }
            }
            next.push_back(child);
        }
        recent.insert(next_recent.begin(),next_recent.end());
        beam = std::move(next);
        if (step % 20 == 19 && !beam.empty()) cerr << "step " << step << " heuristic=" << beam.back().score << " remaining=" << __builtin_popcountll(beam.back().unvisited) << endl;
    }
    return best;
}

int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : 2;
    int seconds = argc > 2 ? stoi(argv[2]) : 60;
    int width = argc > 3 ? stoi(argv[3]) : 300;
    if (argc > 4) rng.seed(stoull(argv[4]));
    Case instance = read_cases()[selected];
    prepare_steiner(instance);
    Circuit best = read_gates("dev/"+instance.id+".global");
    double best_score = best.empty() ? 1e9 : depth(best,instance.size)+best.size()*0.04;
    auto started = chrono::steady_clock::now();
    for (int iteration = 0; chrono::duration<double>(chrono::steady_clock::now()-started).count() < seconds; ++iteration) {
        Circuit result = gatebeam(instance,width,iteration,max(1,seconds-int(chrono::duration<double>(chrono::steady_clock::now()-started).count())));
        if (result.empty()) continue;
        if (!valid(instance,result)) throw runtime_error("invalid gatebeam result");
        double score = depth(result,instance.size)+result.size()*0.04;
        if (score < best_score) { best_score = score; save_gates("dev/"+instance.id+".global",result); }
    }
}
