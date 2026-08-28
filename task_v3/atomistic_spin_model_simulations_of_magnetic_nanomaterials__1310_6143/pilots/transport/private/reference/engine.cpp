#include <iomanip>
#include <stdexcept>
#include "shim/reference_state.hpp"
#include "instrumented_resistance.cpp"
#include "upstream/sublattice-magnetization.cpp"
#include "upstream/field.cpp"

std::vector<double> cross_product(const std::vector<double>& left, const std::vector<double>& right) {
    return {left[1]*right[2]-left[2]*right[1], left[2]*right[0]-left[0]*right[2], left[0]*right[1]-left[1]*right[0]};
}

void emit(const std::vector<double>& values) {
    for (double value : values) std::cout << value << ' ';
    std::cout << '\n';
}

int main() {
    using namespace spin_transport::internal;
    unsigned int num_atoms;
    double length, area;
    if (!(std::cin >> total_num_cells >> num_sublattices >> last_stack >> num_atoms >> cell_increment >> voltage >> length >> area)) return 2;
    const size_t channel_count = total_num_cells * num_sublattices;
    stack_start_index.resize(last_stack);
    stack_final_index.resize(last_stack);
    stack_resistance.resize(last_stack);
    stack_current.resize(last_stack);
    for (uint64_t stack = 0; stack < last_stack; ++stack) {
        uint64_t lower, upper;
        std::cin >> lower >> upper;
        stack_start_index[stack] = cell_increment > 0 ? lower : upper;
        stack_final_index[stack] = cell_increment > 0 ? upper : lower;
    }
    cell_resistance.assign(total_num_cells, 0.0);
    cell_spin_torque_fields.assign(3*total_num_cells, 0.0);
    for (auto* values : {&cell_sl_magnetization_x, &cell_sl_magnetization_y, &cell_sl_magnetization_z, &cell_sl_spin_torque_fields_x, &cell_sl_spin_torque_fields_y, &cell_sl_spin_torque_fields_z, &cell_sl_resistance, &cell_sl_spin_resistance, &cell_sl_isaturation, &cell_sl_alpha, &cell_sl_relaxation_torque_rj, &cell_sl_precession_torque_pj}) values->assign(channel_count, 0.0);
    sl_magnetic.assign(channel_count, false);
    atom_in_cell.resize(num_atoms);
    atom_sublattice.resize(num_atoms);
    std::vector<double> spin_x(num_atoms), spin_y(num_atoms), spin_z(num_atoms), moments(num_atoms), damping(num_atoms);
    std::vector<double> field_x(num_atoms), field_y(num_atoms), field_z(num_atoms);
    std::vector<int> material_ids(num_atoms), counts(channel_count), cell_counts(total_num_cells);
    for (unsigned int atom = 0; atom < num_atoms; ++atom) {
        double rho, spin_rho, eta, beta;
        std::cin >> atom_in_cell[atom] >> atom_sublattice[atom] >> rho >> spin_rho >> moments[atom] >> damping[atom] >> eta >> beta >> spin_x[atom] >> spin_y[atom] >> spin_z[atom];
        const size_t channel = atom_in_cell[atom]*num_sublattices + atom_sublattice[atom];
        ++counts[channel];
        ++cell_counts[atom_in_cell[atom]];
        cell_sl_resistance[channel] += rho;
        cell_sl_spin_resistance[channel] += spin_rho;
        cell_sl_isaturation[channel] += moments[atom];
        cell_sl_alpha[channel] += damping[atom];
        cell_sl_relaxation_torque_rj[channel] += eta;
        cell_sl_precession_torque_pj[channel] += beta;
    }
    if (!std::cin) return 3;
    for (size_t channel = 0; channel < channel_count; ++channel) {
        if (!counts[channel]) continue;
        const double count = counts[channel];
        const double fraction = count / cell_counts[channel/num_sublattices];
        const double geometry = length/(fraction*area);
        sl_magnetic[channel] = true;
        cell_sl_resistance[channel] *= geometry/count;
        cell_sl_spin_resistance[channel] *= geometry/count;
        cell_sl_isaturation[channel] = 1.0/cell_sl_isaturation[channel];
        cell_sl_alpha[channel] /= count;
        cell_sl_relaxation_torque_rj[channel] /= count;
        cell_sl_precession_torque_pj[channel] /= count;
    }
    observed_channel_resistance = cell_sl_resistance;
    calculate_cell_sublattice_magnetization(num_atoms, spin_x, spin_y, spin_z, moments);
    calculate_sublattice_resistance();
    spin_transport::calculate_field(0, num_atoms, field_x, field_y, field_z, material_ids);
    std::cout << std::setprecision(17);
    emit({spin_transport::total_resistance, spin_transport::total_current});
    emit(stack_resistance);
    emit(stack_current);
    emit(cell_resistance);
    std::vector<double> channel_currents(channel_count);
    for (uint64_t stack = 0; stack < last_stack; ++stack) {
        const uint64_t lower = std::min(stack_start_index[stack], stack_final_index[stack]);
        const uint64_t upper = std::max(stack_start_index[stack], stack_final_index[stack]);
        for (uint64_t cell = lower; cell <= upper; ++cell) {
            for (int sublattice_id = 0; sublattice_id < num_sublattices; ++sublattice_id) {
                const size_t channel = cell*num_sublattices+sublattice_id;
                if (observed_channel_resistance[channel] > 0.0) channel_currents[channel] = stack_current[stack]*cell_resistance[cell]/observed_channel_resistance[channel];
            }
        }
    }
    emit(channel_currents);
    for (unsigned int atom = 0; atom < num_atoms; ++atom) emit({field_x[atom], field_y[atom], field_z[atom]});
    for (unsigned int atom = 0; atom < num_atoms; ++atom) {
        const std::vector<double> spin = {spin_x[atom], spin_y[atom], spin_z[atom]};
        const auto first_cross = cross_product(spin, {field_x[atom], field_y[atom], field_z[atom]});
        const auto second_cross = cross_product(spin, first_cross);
        const double factor = -1.760859e11/(1.0+damping[atom]*damping[atom]);
        emit({factor*(first_cross[0]+damping[atom]*second_cross[0]), factor*(first_cross[1]+damping[atom]*second_cross[1]), factor*(first_cross[2]+damping[atom]*second_cross[2])});
    }
}
