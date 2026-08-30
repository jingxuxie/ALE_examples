#include <algorithm>
#include <cstdint>
#include "setorder.h"

extern "C" void set_order(int64_t* positions) {
    std::vector<int> values(positions,positions+768);
    python_set_order(values);
    std::copy(values.begin(),values.end(),positions);
}

extern "C" int select_support(const int64_t* ordering, int64_t* positions, int length) {
    int occupied[4096] = {};
    int count = 0;
    for (int index = 0; index < length; ++index) {
        int position = ordering[index];
        if (occupied[position] || occupied[(position+4095)&4095] || occupied[(position+1)&4095]) continue;
        positions[count++] = position;
        occupied[position] = 1;
        if (count == 768) return index+1;
    }
    return -1;
}

extern "C" bool test_support(const int64_t* positions, const int64_t* weights, int64_t* result) {
    std::fill(result,result+4096,0);
    for (int index = 0; index < 768; ++index) result[positions[index]] = weights[index];
    int wanted[] = {1536, 0, 259, 249, 191, 302, 279, 271, 267, 244};
    for (int lag = 2; lag < 10; ++lag) {
        int total = 0;
        for (int index = 0; index < 4096; ++index) total += result[index] * result[(index+lag)&4095];
        if (total != wanted[lag]) return false;
    }
    return true;
}
