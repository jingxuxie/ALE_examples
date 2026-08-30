#define LOCAL_LIBRARY
#include "local.cpp"
double structural_bias = 1;

double structural_energy(const Case& instance, const Circuit& operations) {
    vector<int> heights(operations.size()), usage(instance.size);
    int critical = 0, count = 0;
    for (int index = 0; index < int(operations.size()); ++index) {
        int previous = 0;
        for (int earlier = 0; earlier < index; ++earlier) if (!commute(operations[earlier],operations[index])) previous = max(previous,heights[earlier]);
        heights[index] = previous+(operations[index].second >= 0);
        critical = max(critical,heights[index]);
        if (operations[index].second >= 0) { ++usage[operations[index].first]; ++usage[operations[index].second]; ++count; }
    }
    double energy = depth(stripped(operations),instance.size)+0.3*structural_bias*critical+0.25*structural_bias*(*max_element(usage.begin(),usage.end()))+0.02*count;
    for (int amount : usage) energy += 0.0005*structural_bias*amount*amount;
    return energy;
}

int main(int argc, char** argv) {
    int selected = argc > 1 ? stoi(argv[1]) : 4;
    int seconds = argc > 2 ? stoi(argv[2]) : 300;
    if (argc > 4) structural_bias = stod(argv[4]);
    if (argc > 5) rng.seed(stoull(argv[5]));
    Case instance = read_cases()[selected];
    Circuit best;
    double best_score = 1e9;
    for (string extension : {"optimized","local","satlocal","beam","satgates","hot","global","layers","population","scheduled","structural","balanced"}) {
        Circuit candidate = read_gates("dev/"+instance.id+"."+extension);
        if (!candidate.empty() && quality(instance,candidate) < best_score) { best = candidate; best_score = quality(instance,candidate); }
    }
    Circuit initial = argc > 3 ? read_gates(argv[3]) : best;
    if (!valid(instance,initial)) throw runtime_error("invalid structural input");
    Circuit current = annotated(instance,initial,0), elite = current;
    double current_energy = structural_energy(instance,current), elite_energy = current_energy;
    auto started = chrono::steady_clock::now();
    local_mode = 1;
    for (int iteration = 0; chrono::duration<double>(chrono::steady_clock::now()-started).count() < seconds; ++iteration) {
        Circuit candidate = replace_block(instance,current,3000);
        candidate = cancel(schedule(cancel(candidate),iteration));
        double energy = structural_energy(instance,candidate);
        double temperature = 0.3+0.8*(0.5+0.5*sin(iteration*0.001));
        if (energy <= current_energy || uniform() < exp((current_energy-energy)/temperature)) { current = candidate; current_energy = energy; }
        if (energy < elite_energy) { elite = candidate; elite_energy = energy; }
        double score = quality(instance,candidate);
        if (score < best_score) {
            best = stripped(candidate);
            if (!valid(instance,best)) throw runtime_error("invalid structural candidate");
            best_score = score;
            save_gates("dev/"+instance.id+(structural_bias > 1 ? ".balanced" : ".structural"),best);
            cerr << instance.id << " structural " << iteration << " count=" << best.size() << " depth=" << depth(best,instance.size) << " energy=" << energy << endl;
        }
        if (iteration % 3000 == 2999) { current = annotated(instance,stripped(elite),1); current_energy = structural_energy(instance,current); }
    }
    save_gates("dev/"+instance.id+(structural_bias > 1 ? ".balanced_energy" : ".energy"),stripped(elite));
}
