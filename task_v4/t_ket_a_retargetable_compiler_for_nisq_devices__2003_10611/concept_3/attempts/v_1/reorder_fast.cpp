#define OPTIMIZE_LIBRARY
#include "optimize.cpp"

int main(int argc, char** argv) {
    int chosen = argc > 1 ? std::stoi(argv[1]) : 4;
    int seconds = argc > 2 ? std::stoi(argv[2]) : 120;
    std::string source = argc > 3 ? argv[3] : "macroopt_";
    std::ifstream input("instances.txt");
    int case_count;
    input >> case_count;
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
        auto current = load(source + instance.name + ".txt");
        if (current.empty()) return 1;
        auto best = current;
        double record = objective(instance, best);
        auto start = std::chrono::steady_clock::now();
        for (int attempt = 0; std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count() < seconds; ++attempt) {
            auto candidate = normalize(instance, current);
            double score = objective(instance, candidate);
            if (score < record) {
                record = score;
                best = candidate;
                save(instance, best, "reordered_");
                std::cout << instance.name << ' ' << attempt << " count " << best.size() << " depth " << get_depth(best, instance.size) << std::endl;
            }
            if (score < record + 0.05 || candidate.size() < current.size()) current = candidate;
            if (attempt % 100 == 0) current = best;
        }
        save(instance, best, "reordered_");
    }
}
