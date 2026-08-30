#include <array>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <chrono>

using Matrix = std::array<double, 16>;
Matrix factors[3][17][16][2];
double couplings[3], targets[3];
int transforms[16][16], sums[16], sequence[8];
int lengths[8], phase_count;
double best = 2;
unsigned long long tested = 0;
auto started = std::chrono::steady_clock::now();

Matrix multiply(const Matrix& left, const Matrix& right) {
    Matrix result{};
    for (int row = 0; row < 4; ++row)
        for (int column = 0; column < 4; ++column)
            for (int inner = 0; inner < 4; ++inner)
                result[row * 4 + column] += left[row * 4 + inner] * right[inner * 4 + column];
    return result;
}

std::array<double, 2> margins(const Matrix& plus, const Matrix& minus, int total, int point) {
    double trace_plus = 0, trace_minus = 0, second = 0;
    for (int site = 0; site < 4; ++site) {
        trace_plus += plus[site * 4 + site];
        trace_minus += minus[site * 4 + site];
        for (int other = site + 1; other < 4; ++other)
            second += plus[site * 4 + site] * plus[other * 4 + other] - plus[site * 4 + other] * plus[other * 4 + site];
    }
    double determinant = std::exp(couplings[point] * total);
    std::array<double, 2> result;
    for (int flavor = 0; flavor < 2; ++flavor) {
        double target = flavor ? 1 / targets[point] : targets[point];
        double rest = target * target + trace_plus * target + determinant * trace_minus / target + determinant / (target * target);
        result[flavor] = 1 + second / rest;
    }
    return result;
}

bool check_other(int point, int total) {
    Matrix plus{}, minus{};
    for (int site = 0; site < 4; ++site) plus[site * 4 + site] = minus[site * 4 + site] = 1;
    for (int phase = 0; phase < phase_count; ++phase) {
        plus = multiply(factors[point][lengths[phase]][sequence[phase]][0], plus);
        minus = multiply(factors[point][lengths[phase]][sequence[phase]][1], minus);
    }
    auto result = margins(plus, minus, total, point);
    return result[0] * result[1] < -1e-9;
}

void search(int depth, const Matrix& plus, const Matrix& minus, int total, unsigned active) {
    for (int state = 0; state < 16; ++state) {
        unsigned next_active = 0;
        bool canonical = true;
        for (int symmetry = 0; symmetry < 16; ++symmetry) {
            if (!(active & (1u << symmetry))) continue;
            if (transforms[symmetry][state] < state) { canonical = false; break; }
            if (transforms[symmetry][state] == state) next_active |= 1u << symmetry;
        }
        if (!canonical) continue;
        sequence[depth] = state;
        Matrix next_plus = multiply(factors[0][lengths[depth]][state][0], plus);
        Matrix next_minus = multiply(factors[0][lengths[depth]][state][1], minus);
        int next_total = total + lengths[depth] * sums[state];
        if (depth != phase_count - 1) { search(depth + 1, next_plus, next_minus, next_total, next_active); continue; }
        ++tested;
        auto result = margins(next_plus, next_minus, next_total, 0);
        double minimum = std::min(result[0], result[1]);
        if (minimum < best - 1e-8) { best = minimum; std::cerr << "Best " << best << " tested " << tested << '\n'; }
        if (result[0] * result[1] < -1e-9 && check_other(1, next_total) && check_other(2, next_total)) {
            std::cout << "FOUND";
            std::cout << ' ' << phase_count;
            for (int phase = 0; phase < phase_count; ++phase) std::cout << ' ' << sequence[phase];
            for (int phase = 0; phase < phase_count; ++phase) std::cout << ' ' << lengths[phase];
            std::cout << std::endl;
            std::exit(0);
        }
        if (tested % 10000000 == 0) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
            std::cerr << "Progress " << tested << " " << best << " " << elapsed << '\n';
            if (elapsed > 180) std::exit(0);
        }
    }
}

int main() {
    for (int point = 0; point < 3; ++point) {
        std::cin >> couplings[point] >> targets[point];
        for (int length = 1; length <= 16; ++length)
        for (int state = 0; state < 16; ++state)
            for (int spin = 0; spin < 2; ++spin)
                for (double& entry : factors[point][length][state][spin]) std::cin >> entry;
    }
    for (int symmetry = 0; symmetry < 16; ++symmetry)
        for (int state = 0; state < 16; ++state) std::cin >> transforms[symmetry][state];
    for (int state = 0; state < 16; ++state) sums[state] = 2 * __builtin_popcount(static_cast<unsigned>(state)) - 4;
    Matrix identity{};
    for (int site = 0; site < 4; ++site) identity[site * 4 + site] = 1;
    while (std::cin >> phase_count) {
        for (int phase = 0; phase < phase_count; ++phase) std::cin >> lengths[phase];
        search(0, identity, identity, 0, 65535);
        std::cerr << "Schedule " << phase_count;
        for (int phase = 0; phase < phase_count; ++phase) std::cerr << ' ' << lengths[phase];
        std::cerr << ' ' << best << '\n';
    }
    std::cerr << "DONE " << tested << " " << best << '\n';
}
