#include <z3++.h>
#include <array>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv) {
    std::string path = argv[1];
    int seed = argc > 2 ? std::stoi(argv[2]) : 1;
    int weight = argc > 3 ? std::stoi(argv[3]) : 18;
    int seconds = argc > 4 ? std::stoi(argv[4]) : 600;
    int anchor = argc > 5 ? std::stoi(argv[5]) : -1;
    int mode = argc > 6 ? std::stoi(argv[6]) : 0;
    z3::context context;
    z3::solver solver = mode ? (z3::tactic(context, "simplify") & z3::tactic(context, "sat")).mk_solver() : z3::solver(context);
    if (mode == 4) solver = (z3::tactic(context, "simplify") & z3::tactic(context, "pb2bv") & z3::tactic(context, "bit-blast") & z3::tactic(context, "sat")).mk_solver();
    z3::params parameters(context);
    parameters.set("random_seed", unsigned(seed));
    parameters.set("timeout", unsigned(seconds * 1000));
    if (mode) {
        parameters.set("cardinality.solver", true);
        parameters.set("pb.solver", "solver");
    }
    if (mode == 2) {
        parameters.set("phase", "always_true");
        parameters.set("pb.lemma_format", "pb");
    }
    if (mode == 3) parameters.set("local_search", true);
    if (mode == 4) {
        parameters.set("pb.solver", "circuit");
        parameters.set("cardinality.solver", false);
        parameters.set("ddfw_search", true);
    }
    solver.set(parameters);
    z3::expr_vector variables(context);
    for (int position = 0; position < 8192; ++position) variables.push_back(context.bool_const(("bit_" + std::to_string(position)).c_str()));
    std::array<std::vector<int>, 384> blocks;
    std::ifstream input(path + "/signatures.txt");
    for (int position = 0; position < 8192; ++position) {
        for (int pass = 0; pass < 6; ++pass) {
            int block;
            input >> block;
            blocks[64 * pass + block].push_back(position);
        }
    }
    for (int check = 0; check < 384; ++check) {
        z3::expr_vector terms(context);
        std::vector<int> coefficients;
        for (int position : blocks[check]) {
            terms.push_back(variables[position]);
            coefficients.push_back(1);
        }
        terms.push_back(!context.bool_const(("active_" + std::to_string(check)).c_str()));
        coefficients.push_back(2);
        solver.add(z3::pbeq(terms, coefficients.data(), 2));
    }
    std::vector<int> coefficients(8192, 1);
    if (weight) solver.add(z3::pbeq(variables, coefficients.data(), weight));
    else {
        solver.add(z3::pbge(variables, coefficients.data(), 8));
        solver.add(z3::pble(variables, coefficients.data(), 18));
    }
    if (anchor >= 0) solver.add(variables[anchor]);
    std::cout << "Starting seed " << seed << " weight " << weight << " anchor " << anchor << std::endl;
    auto result = solver.check();
    std::cout << result << "\n" << solver.reason_unknown() << "\n" << solver.statistics() << std::endl;
    if (result == z3::sat) {
        auto model = solver.get_model();
        std::ofstream output(path + "/sat_core_" + std::to_string(seed) + ".json");
        output << "{\"errors\":[";
        bool first = true;
        for (int position = 0; position < 8192; ++position) {
            if (!model.eval(variables[position]).is_true()) continue;
            if (!first) output << ',';
            output << position;
            first = false;
        }
        output << "]}\n";
    }
}
