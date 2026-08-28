#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace atoms {
int num_atoms;
std::vector<double> x_spin_array, y_spin_array, z_spin_array, m_spin_array;
std::vector<int> type_array;
}
namespace err { bool check = false; }
namespace vmath { double sign(double value) { return value < 0 ? -1.0 : 1.0; } }
namespace mp {
struct Material { double temperature_rescaling_alpha = 1.0; double temperature_rescaling_Tc = 0.0; double mu_s_SI = 9.27400915e-24; };
int num_materials = 1;
std::vector<Material> material(1);
}
namespace mtrandom {
std::mt19937_64 generator;
std::normal_distribution<double> normal(0.0, 1.0);
double grnd() { return std::generate_canonical<double, 53>(generator); }
double gaussian() { return normal(generator); }
}
struct Bond { int other; double exchange; double axial; };
std::vector<std::vector<Bond>> neighbors;
std::vector<std::array<double, 7>> onsite;
constexpr double unit_scale = 1000.0 * 1.3806503e-23 / (9.27400915e-24 * 9.27400915e-24 * 1.07828231e23);

std::array<double, 3> spin_at(int index) {
    return {atoms::x_spin_array[index], atoms::y_spin_array[index], atoms::z_spin_array[index]};
}

double local_energy(int index) {
    const auto spin = spin_at(index);
    const auto &tensor = onsite[index];
    double energy = -tensor[0]*spin[0]*spin[0] - tensor[1]*spin[1]*spin[1] - tensor[2]*spin[2]*spin[2]
        - 2*tensor[3]*spin[0]*spin[1] - 2*tensor[4]*spin[0]*spin[2] - 2*tensor[5]*spin[1]*spin[2]
        - tensor[6]*(std::pow(spin[0],4)+std::pow(spin[1],4)+std::pow(spin[2],4));
    for (const auto &bond : neighbors[index]) {
        const auto other = spin_at(bond.other);
        energy -= bond.exchange*(spin[0]*other[0]+spin[1]*other[1]+spin[2]*other[2]) + bond.axial*spin[2]*other[2];
    }
    return energy;
}
namespace sim {
double temperature;
double calculate_spin_energy(int index) { return unit_scale * local_energy(index); }
}
namespace montecarlo {
enum Algorithm { adaptive, angle };
Algorithm algorithm = angle;
void CMCinit() { throw std::runtime_error("Uninitialized CMC shim"); }
namespace cmc {
bool is_initialised = true;
double mc_success=0, mc_total=0, sphere_reject=0, energy_reject=0;
std::vector<std::vector<double>> polar_vector(1, std::vector<double>(3));
std::vector<std::vector<double>> polar_matrix(3, std::vector<double>(3));
std::vector<std::vector<double>> polar_matrix_tp(3, std::vector<double>(3));
}
namespace internal {
double delta_angle = 0.3, adaptive_sigma = 0.3;
#include "official_angle.inc"
void mc_move(const std::vector<double>& previous, std::vector<double>& proposed) { mc_angle(previous, proposed, delta_angle); }
}
#include "official_cmc.inc"
}

std::array<double, 5> observables(double theta) {
    double torque = 0.0, energy = 0.0;
    std::array<double, 3> magnetization{};
    double norm_error = 0.0;
    for (int index=0; index<atoms::num_atoms; ++index) {
        const auto spin = spin_at(index);
        const auto &tensor = onsite[index];
        const double field_x = 2*(tensor[0]*spin[0]+tensor[3]*spin[1]+tensor[4]*spin[2])+4*tensor[6]*std::pow(spin[0],3);
        const double field_z = 2*(tensor[4]*spin[0]+tensor[5]*spin[1]+tensor[2]*spin[2])+4*tensor[6]*std::pow(spin[2],3);
        torque += spin[2]*field_x-spin[0]*field_z;
        energy += local_energy(index);
        for (const auto &bond : neighbors[index]) {
            if (index < bond.other) {
                const auto other = spin_at(bond.other);
                energy += bond.exchange*(spin[0]*other[0]+spin[1]*other[1]+spin[2]*other[2])+bond.axial*spin[2]*other[2];
                torque -= bond.axial*(spin[0]*other[2]+spin[2]*other[0]);
            }
        }
        for (int component=0; component<3; ++component) magnetization[component] += spin[component];
        norm_error = std::max(norm_error, std::abs(spin[0]*spin[0]+spin[1]*spin[1]+spin[2]*spin[2]-1));
    }
    const double count=atoms::num_atoms;
    const double parallel=(std::sin(theta)*magnetization[0]+std::cos(theta)*magnetization[2])/count;
    const double perpendicular=std::hypot(std::cos(theta)*magnetization[0]-std::sin(theta)*magnetization[2], magnetization[1])/count;
    return {torque/count, parallel, energy/count, perpendicular, norm_error};
}

int main(int argc, char **argv) {
    if (argc != 8) return 2;
    std::ifstream input(argv[1]);
    int bond_count;
    input >> atoms::num_atoms >> bond_count;
    const int count=atoms::num_atoms;
    onsite.resize(count);
    neighbors.resize(count);
    for (auto &tensor : onsite) for (auto &value : tensor) input >> value;
    for (int index=0; index<bond_count; ++index) {
        int first, second;
        double exchange, axial;
        input >> first >> second >> exchange >> axial;
        neighbors[first].push_back({second, exchange, axial});
        neighbors[second].push_back({first, exchange, axial});
    }
    if (!input || count < 2) return 3;
    const double temperature=std::stod(argv[2]), theta=std::stod(argv[3]);
    const int burn=std::stoi(argv[4]), sweeps=std::stoi(argv[5]), block=std::stoi(argv[6]);
    mtrandom::generator.seed(std::stoull(argv[7]));
    sim::temperature=1000*temperature;
    atoms::x_spin_array.assign(count, std::sin(theta));
    atoms::y_spin_array.assign(count, 0);
    atoms::z_spin_array.assign(count, std::cos(theta));
    atoms::m_spin_array.assign(count, 1);
    atoms::type_array.assign(count, 0);
    auto &matrix=montecarlo::cmc::polar_matrix;
    matrix[0]={std::cos(theta),0,-std::sin(theta)};
    matrix[1]={0,1,0};
    matrix[2]={std::sin(theta),0,std::cos(theta)};
    montecarlo::cmc::polar_vector[0]=matrix[2];
    for (int row=0; row<3; ++row) for (int col=0; col<3; ++col) montecarlo::cmc::polar_matrix_tp[row][col]=matrix[col][row];
    std::cout << std::setprecision(17);
    if (std::getenv("REFERENCE_HOT_START")) {
        sim::temperature=1400;
        for (int sweep=0; sweep<2000; ++sweep) montecarlo::cmc_step();
        sim::temperature=1000*temperature;
    }
    for (int sweep=0; sweep<burn; ++sweep) montecarlo::cmc_step();
    std::array<double,5> sums{};
    int samples=0;
    for (int sweep=1; sweep<=sweeps; ++sweep) {
        montecarlo::cmc_step();
        if (sweep%5 == 0) {
            const auto observation=observables(theta);
            for (int component=0; component<5; ++component) sums[component] += observation[component];
            ++samples;
        }
        if (sweep%block == 0) {
            for (double value : sums) std::cout << value/samples << ' ';
            std::cout << montecarlo::cmc::mc_success/montecarlo::cmc::mc_total << '\n';
            sums.fill(0);
            samples=0;
        }
    }
    return 0;
}
