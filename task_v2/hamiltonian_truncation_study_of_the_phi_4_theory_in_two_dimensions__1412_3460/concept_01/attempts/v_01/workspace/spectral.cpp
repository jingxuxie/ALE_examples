#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using namespace std;

const double factorials[] = {1, 1, 2, 6, 24};

struct Spectral {
    double length, mass, cutoff;
    int boundary, degree, transfer;
    vector<int> modes, indices;
    vector<double> frequencies, energies, weights;

    void recurse(int start, int remaining, int momentum, double energy, double factor) {
        if (remaining == 1) {
            int target = transfer - momentum;
            if (target < modes.front() || target > modes.back() || abs(target) % 2 != boundary) return;
            int index = (target - modes.front()) / 2;
            if (index < start || energy + frequencies[index] > cutoff) return;
            indices.push_back(index);
            double divisor = 1;
            for (size_t position = 0; position < indices.size();) {
                size_t next = position + 1;
                while (next < indices.size() && indices[next] == indices[position]) ++next;
                divisor *= factorials[next - position];
                position = next;
            }
            energies.push_back(energy + frequencies[index]);
            weights.push_back(length * factorials[degree] * factor /
                              (divisor * 2 * length * frequencies[index]));
            indices.pop_back();
            return;
        }
        for (int index = start; index < int(modes.size()); ++index) {
            if (momentum + remaining * modes[index] > transfer) break;
            if (energy + frequencies[index] + (remaining - 1) * mass > cutoff) continue;
            indices.push_back(index);
            recurse(index, remaining - 1, momentum + modes[index], energy + frequencies[index],
                    factor / (2 * length * frequencies[index]));
            indices.pop_back();
        }
    }
};

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    ifstream input(argv[1]);
    double length, mass, cutoff;
    int boundary, count;
    input >> length >> mass >> boundary >> cutoff >> count;
    for (int item = 0; item < count; ++item) {
        Spectral spectral;
        spectral.length = length;
        spectral.mass = mass;
        spectral.cutoff = cutoff;
        spectral.boundary = boundary;
        input >> spectral.degree >> spectral.transfer;
        int maximum = int(length * sqrt(cutoff * cutoff - mass * mass) / M_PI);
        for (int mode = -maximum; mode <= maximum; ++mode) {
            if (abs(mode) % 2 != boundary) continue;
            spectral.modes.push_back(mode);
            spectral.frequencies.push_back(hypot(mass, M_PI * mode / length));
        }
        spectral.recurse(0, spectral.degree, 0, 0, 1);
        string filename = string(argv[2]) + "_k" + to_string(spectral.degree) + "_q" + to_string(spectral.transfer) + ".bin";
        ofstream output(filename, ios::binary);
        int64_t count_events = spectral.energies.size();
        output.write(reinterpret_cast<char*>(&count_events), 8);
        output.write(reinterpret_cast<char*>(spectral.energies.data()), count_events * 8);
        output.write(reinterpret_cast<char*>(spectral.weights.data()), count_events * 8);
    }
}
