#define main reference_driver
#include "engine.cpp"
#undef main

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    unsetenv("REFERENCE_HOT_START");
    std::vector<std::string> arguments={argv[0],argv[1],"1.0","0.3","0","0","200","71"};
    std::vector<char*> pointers;
    for (auto &argument : arguments) pointers.push_back(argument.data());
    if (reference_driver(8,pointers.data())) return 3;
    std::ifstream state(argv[2]);
    for (int index=0; index<atoms::num_atoms; ++index) {
        state >> atoms::x_spin_array[index] >> atoms::y_spin_array[index] >> atoms::z_spin_array[index];
    }
    if (!state) return 4;
    const auto observation=observables(0.3);
    const double exponent=sim::calculate_spin_energy(31)*mp::material[0].mu_s_SI*1.07828231e23*9.27400915e-24/(sim::temperature*1.3806503e-23);
    std::cout << observation[0]*atoms::num_atoms << ' ' << observation[2]*atoms::num_atoms << ' '
              << local_energy(31) << ' ' << exponent << '\n';
    return 0;
}
