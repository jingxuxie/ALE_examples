#include <array>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstdint>
struct Candidates {
    std::vector<uint64_t> keys;
    int count = 0;
    float best = 1e30f;
    std::array<double, 16> masses{};
    std::array<float, 16> minima;
    Candidates() : keys(16384, 0) {minima.fill(1e30f);}
    void add(uint64_t key, int label, float score) {
        if (score > best + 20) return;
        best = std::min(best, score);
        if (!key) key = 1;
        size_t slot = key & (keys.size() - 1);
        while (keys[slot] && keys[slot] != key) slot = (slot + 1) & (keys.size() - 1);
        if (keys[slot]) return;
        keys[slot] = key;
        masses[label] += std::exp(-double(score));
        minima[label] = std::min(minima[label], score);
        if (++count * 2 > int(keys.size())) {
            std::vector<uint64_t> larger(keys.size() * 2, 0);
            for (uint64_t value : keys) if (value) {
                size_t dest = value & (larger.size() - 1);
                while (larger[dest]) dest = (dest + 1) & (larger.size() - 1);
                larger[dest] = value;
            }
            keys.swap(larger);
        }
    }
};
