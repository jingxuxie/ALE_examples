#define OPTIMIZE_LIBRARY
#include "optimize.cpp"

int main(int argc, char** argv) {
    std::ifstream input("instances.txt");
    int case_count;
    input >> case_count;
    int chosen = argc > 1 ? std::stoi(argv[1]) : 0;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 120;
    random_engine.seed(argc > 3 ? std::stoull(argv[3]) : 712);
    beam_enabled = argc > 4 ? std::stoi(argv[4]) : false;
    std::string output_prefix = argc > 5 ? argv[5] : "generated_";
    for (int case_index = 0; case_index < case_count; ++case_index) {
        Case instance;
        input >> instance.name >> instance.size >> instance.edge_count >> instance.parity_count >> instance.count_budget >> instance.depth_budget;
        instance.edges.resize(instance.edge_count);
        instance.targets.resize(instance.size);
        instance.parities.resize(instance.parity_count);
        for (auto& edge : instance.edges) input >> edge.first >> edge.second;
        for (auto& mask : instance.targets) input >> mask;
        for (auto& mask : instance.parities) input >> mask;
        if (case_index != chosen) continue;
        instance.prepare();
        auto start = std::chrono::steady_clock::now();
        double best_score = 1e100;
        for (int attempt = 0; std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds; ++attempt) {
            phase_bonus = std::pow(2.0, 5.0 * uniform());
            matrix_weight = 0.3 + 1.7 * uniform();
            steiner_weight = uniform();
            State state = initial(instance);
            double parity_weight = 0.2 + 3.0 * uniform(), root_weight = 0.3 + 1.5 * uniform(), depth_weight = 0.05 + 3.0 * uniform();
            if (uniform() < 0.9) walk(instance, state, instance.count_budget, parity_weight, root_weight, depth_weight, 0.1 + uniform());
            if (!finished(state, instance)) {
                complete_parities(state, instance, parity_weight, root_weight, depth_weight);
                complete_linear(state, instance, root_weight, depth_weight);
            }
            auto candidate = normalize(instance, circuit(state));
            double score = objective(instance, candidate);
            if (score < best_score) {
                best_score = score;
                save(instance, candidate, output_prefix);
                std::cout << instance.name << " attempt " << attempt << " count " << candidate.size() << " depth " << get_depth(candidate, instance.size) << " score " << score << std::endl;
            }
        }
    }
}
