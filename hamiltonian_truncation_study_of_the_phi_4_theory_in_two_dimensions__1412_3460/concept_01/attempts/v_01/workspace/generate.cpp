#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <string>
#include <unordered_map>
#include <vector>

using namespace std;

struct Tuple {
    vector<int> indices;
    double energy;
    double factor;
};

struct State {
    string occupation;
    double energy;
};

const double factorials[] = {1, 1, 2, 6, 24};

struct Generator {
    double length, mass, cutoff;
    int boundary, momentum, parity, momentum_window;
    vector<int> modes, order;
    vector<double> frequencies;
    vector<State> states;
    unordered_map<string, int> lookup;
    map<pair<int, int>, vector<Tuple>> creations;

    Generator(double input_length, double input_mass, int input_boundary, double input_cutoff,
              int input_momentum, int input_parity, int input_window = 1000000)
        : length(input_length), mass(input_mass), cutoff(input_cutoff), boundary(input_boundary),
          momentum(input_momentum), parity(input_parity), momentum_window(input_window) {
        int maximum = int(length * sqrt(cutoff * cutoff - mass * mass) / M_PI + 1e-8);
        for (int mode = -maximum; mode <= maximum; ++mode) {
            if (abs(mode) % 2 != boundary) continue;
            modes.push_back(mode);
            frequencies.push_back(hypot(mass, M_PI * mode / length));
        }
        order.resize(modes.size());
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int first, int second) {
            return frequencies[first] < frequencies[second];
        });
    }

    void enumerate_states(string& occupation, int start, double energy, int total_momentum,
                          int number) {
        if ((momentum == 1000000 || total_momentum == momentum) && abs(total_momentum) <= momentum_window &&
            (parity < 0 || number % 2 == parity)) states.push_back({occupation, energy});
        for (int position = start; position < int(order.size()); ++position) {
            int mode = order[position];
            double next_energy = energy + frequencies[mode];
            if (next_energy > cutoff + 1e-9) break;
            occupation[mode]++;
            enumerate_states(occupation, position, next_energy, total_momentum + modes[mode], number + 1);
            occupation[mode]--;
        }
    }

    void enumerate_creations(vector<int>& indices, int start, int remaining,
                             double energy, int total_momentum, double factor) {
        if (remaining == 0) {
            double divisor = 1;
            for (size_t position = 0; position < indices.size();) {
                size_t next = position + 1;
                while (next < indices.size() && indices[next] == indices[position]) ++next;
                divisor *= factorials[next - position];
                position = next;
            }
            creations[{int(indices.size()), total_momentum}].push_back({indices, energy, factor / divisor});
            return;
        }
        for (int mode = start; mode < int(modes.size()); ++mode) {
            double next_energy = energy + frequencies[mode];
            if (next_energy + (remaining - 1) * mass > cutoff + 1e-9) continue;
            indices.push_back(mode);
            enumerate_creations(indices, mode, remaining - 1, next_energy, total_momentum + modes[mode],
                                factor / sqrt(2 * length * frequencies[mode]));
            indices.pop_back();
        }
    }

    void prepare(bool operators = true) {
        string occupation(modes.size(), 0);
        enumerate_states(occupation, 0, 0, 0, 0);
        sort(states.begin(), states.end(), [](const State& first, const State& second) {
            if (first.energy != second.energy) return first.energy < second.energy;
            return first.occupation < second.occupation;
        });
        lookup.reserve(states.size() * 2);
        for (int index = 0; index < int(states.size()); ++index) lookup.emplace(states[index].occupation, index);
        if (!operators) return;
        vector<int> indices;
        for (int number = 0; number <= 4; ++number) enumerate_creations(indices, 0, number, 0, 0, 1);
        for (auto& entry : creations) sort(entry.second.begin(), entry.second.end(),
            [](const Tuple& first, const Tuple& second) { return first.energy < second.energy; });
    }

    void annihilate(int column, int degree, int transfer, int remaining, int start,
                    string& occupation, double energy, int total_momentum, double factor,
                    vector<int>& indices, vector<int32_t>& rows, vector<int32_t>& columns,
                    vector<double>& values) {
        if (remaining == 0) {
            double divisor = 1;
            for (size_t position = 0; position < indices.size();) {
                size_t next = position + 1;
                while (next < indices.size() && indices[next] == indices[position]) ++next;
                divisor *= factorials[next - position];
                position = next;
            }
            auto found = creations.find({degree - int(indices.size()), total_momentum + transfer});
            if (found == creations.end()) return;
            for (const auto& creation : found->second) {
                if (energy + creation.energy > cutoff + 1e-9) break;
                double amplitude = length * factorials[degree] * factor * creation.factor / divisor;
                for (int mode : creation.indices) {
                    occupation[mode]++;
                    amplitude *= sqrt(int(occupation[mode]));
                }
                auto target = lookup.find(occupation);
                if (target != lookup.end()) {
                    rows.push_back(target->second);
                    columns.push_back(column);
                    values.push_back(amplitude);
                }
                for (int mode : creation.indices) occupation[mode]--;
            }
            return;
        }
        for (int mode = start; mode < int(modes.size()); ++mode) {
            if (!occupation[mode]) continue;
            double next_factor = factor * sqrt(int(occupation[mode]) / (2 * length * frequencies[mode]));
            occupation[mode]--;
            indices.push_back(mode);
            annihilate(column, degree, transfer, remaining - 1, mode, occupation,
                       energy - frequencies[mode], total_momentum + modes[mode], next_factor,
                       indices, rows, columns, values);
            indices.pop_back();
            occupation[mode]++;
        }
    }

    void save_basis(const string& prefix) {
        ofstream stream(prefix + "_basis.bin", ios::binary);
        int64_t dimension = states.size(), count_modes = modes.size();
        stream.write(reinterpret_cast<char*>(&dimension), 8);
        stream.write(reinterpret_cast<char*>(&count_modes), 8);
        stream.write(reinterpret_cast<char*>(modes.data()), 4 * modes.size());
        for (const auto& state : states) stream.write(reinterpret_cast<const char*>(&state.energy), 8);
        for (const auto& state : states) stream.write(state.occupation.data(), state.occupation.size());
    }

    void save_operator(int degree, int transfer, const string& prefix) {
        vector<int32_t> rows, columns;
        vector<double> values;
        vector<int> indices;
        for (int column = 0; column < int(states.size()); ++column) {
            string occupation = states[column].occupation;
            for (int number = 0; number <= degree; ++number)
                annihilate(column, degree, transfer, number, 0, occupation, states[column].energy,
                           0, 1, indices, rows, columns, values);
        }
        ofstream stream(prefix + "_v" + to_string(degree) + "_q" + to_string(transfer) + ".bin", ios::binary);
        int64_t nonzero = values.size();
        stream.write(reinterpret_cast<char*>(&nonzero), 8);
        stream.write(reinterpret_cast<char*>(rows.data()), 4 * rows.size());
        stream.write(reinterpret_cast<char*>(columns.data()), 4 * columns.size());
        stream.write(reinterpret_cast<char*>(values.data()), 8 * values.size());
    }
};

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    ifstream input(argv[1]);
    double length, mass, cutoff;
    int boundary, momentum, parity, count_terms, momentum_window = 1000000;
    input >> length >> mass >> boundary >> cutoff >> momentum >> parity >> count_terms;
    vector<pair<int, int>> keys;
    for (int term = 0; term < count_terms; ++term) {
        int degree, transfer;
        input >> degree >> transfer;
        keys.push_back({degree, transfer});
    }
    input >> momentum_window;
    Generator generator(length, mass, boundary, cutoff, momentum, parity, momentum_window);
    generator.prepare(count_terms > 0);
    generator.save_basis(argv[2]);
    for (auto key : keys) generator.save_operator(key.first, key.second, argv[2]);
    cout << generator.states.size() << endl;
}
