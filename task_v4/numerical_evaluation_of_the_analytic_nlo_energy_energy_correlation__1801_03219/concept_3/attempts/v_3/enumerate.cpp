#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <vector>

extern "C" int enumerate_basis(const int64_t* basis, const double* gram, const double* mu, int size, int64_t norm, const int64_t* wanted, int64_t* output, int maximum, double seconds) {
    std::vector<int64_t> coefficients(size), candidate(size);
    auto started = std::chrono::steady_clock::now();
    int found = 0;
    long nodes = 0;
    bool finished = false;
    auto recurse = [&](auto&& self, int level, double remaining) -> void {
        if (finished) return;
        if ((++nodes & 16383) == 0 && std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() > seconds) { finished = true; return; }
        if (level < 0) {
            int64_t actual_norm = 0;
            for (int index = 0; index < size; ++index) {
                int64_t value = 0;
                for (int row = 0; row < size; ++row) value += coefficients[row] * basis[row * size + index];
                candidate[index] = value;
                actual_norm += value * value;
            }
            if (actual_norm != norm) return;
            for (int lag = 1; lag < size / 2; ++lag) {
                int64_t actual = 0;
                for (int index = 0; index < size; ++index) actual += candidate[index] * candidate[(index + lag) % size] * (index + lag < size ? 1 : -1);
                if (actual != wanted[lag]) return;
            }
            for (int index = 0; index < size; ++index) output[found * size + index] = candidate[index];
            if (++found == maximum) finished = true;
            return;
        }
        double center = 0;
        for (int row = level + 1; row < size; ++row) center -= coefficients[row] * mu[row * size + level];
        double radius = std::sqrt(std::max(0.0, remaining / gram[level]));
        int64_t lower = std::ceil(center - radius - 1e-7), upper = std::floor(center + radius + 1e-7);
        int64_t middle = std::llround(center);
        for (int64_t offset = 0; offset <= std::max(middle - lower, upper - middle); ++offset) {
            for (int side = 0; side < (offset ? 2 : 1); ++side) {
                int64_t value = middle + (side ? -offset : offset);
                if (value < lower || value > upper) continue;
                coefficients[level] = value;
                double cost = (value - center) * (value - center) * gram[level];
                if (cost <= remaining + 1e-5) self(self, level - 1, remaining - cost);
                if (finished) return;
            }
        }
    };
    recurse(recurse, size - 1, norm + 1e-5);
    return found;
}
