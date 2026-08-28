#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <vector>

namespace program { double fractional_electric_field_strength = 1.0; }
namespace spin_transport {
double total_resistance = 0.0;
double total_current = 0.0;
namespace internal {
bool enabled = true;
bool sublattice = true;
int num_sublattices = 0;
uint64_t total_num_cells = 0;
uint64_t first_stack = 0;
uint64_t last_stack = 0;
int cell_increment = 1;
double voltage = 0.0;
std::vector<uint64_t> stack_start_index, stack_final_index, atom_in_cell;
std::vector<int> atom_sublattice;
std::vector<bool> sl_magnetic;
std::vector<double> cell_sl_magnetization_x, cell_sl_magnetization_y, cell_sl_magnetization_z;
std::vector<double> cell_sl_spin_torque_fields_x, cell_sl_spin_torque_fields_y, cell_sl_spin_torque_fields_z;
std::vector<double> cell_sl_resistance, cell_sl_spin_resistance, cell_sl_isaturation;
std::vector<double> cell_sl_alpha, cell_sl_relaxation_torque_rj, cell_sl_precession_torque_pj;
std::vector<double> cell_spin_torque_fields, cell_resistance, stack_resistance, stack_current;
std::vector<double> observed_channel_resistance;
}
}
namespace st = spin_transport;
