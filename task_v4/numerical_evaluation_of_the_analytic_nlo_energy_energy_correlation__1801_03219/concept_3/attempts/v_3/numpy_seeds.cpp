#include <algorithm>
#include <cstdint>
#include <vector>

extern "C" int consumed(const int64_t* order) {
    bool occupied[4096] = {};
    int count = 0;
    for (int rank = 0; rank < 4096; ++rank) {
        int index = order[rank];
        if (!occupied[index] && !occupied[(index + 1) & 4095] && !occupied[(index + 4095) & 4095]) {
            occupied[index] = true;
            if (++count == 768) return rank + 1;
        }
    }
    return 4096;
}

extern "C" int test_compressed(const int64_t* order, int64_t* candidate, const int64_t* expected) {
    int labels[] = {0, 1, 2};
    int counts[] = {2560, 512, 256};
    do {
        std::fill(candidate, candidate + 4096, 0);
        std::vector<int> occupied;
        int position = 0;
        for (int rank = 0; rank < 3328; ++rank) {
            int index = order[rank];
            int value = index < counts[labels[0]] ? labels[0] : index < counts[labels[0]] + counts[labels[1]] ? labels[1] : labels[2];
            candidate[position] = value;
            if (value) occupied.push_back(position);
            position += value ? 2 : 1;
        }
        bool matching = true;
        for (int lag = 2; lag <= 2048; ++lag) {
            int actual = 0;
            for (int index : occupied) actual += candidate[index] * candidate[(index + lag) & 4095];
            if (actual != expected[lag]) { matching = false; break; }
        }
        if (matching) return 1;
    } while (std::next_permutation(labels, labels + 3));
    return 0;
}

extern "C" int test_order(const int64_t* order, const int64_t* weights, int64_t* candidate, const int64_t* expected) {
    std::vector<int> occupied;
    std::fill(candidate, candidate + 4096, 0);
    for (int rank = 0; rank < 4096 && occupied.size() < 768; ++rank) {
        int index = order[rank];
        if (!candidate[index] && !candidate[(index + 1) & 4095] && !candidate[(index + 4095) & 4095]) {
            candidate[index] = 1;
            occupied.push_back(index);
        }
    }
    if (occupied.size() != 768) return 0;
    auto sorted = occupied;
    std::sort(sorted.begin(), sorted.end());
    for (int variant = 0; variant < 6; ++variant) {
        std::fill(candidate, candidate + 4096, 0);
        auto& support = variant % 2 ? sorted : occupied;
        for (int rank = 0; rank < 768; ++rank)
            candidate[support[rank]] = variant < 2 ? (rank < 256 ? 2 : 1) : variant < 4 ? (rank >= 512 ? 2 : 1) : weights[rank];
        bool matching = true;
        for (int lag : {2, 3, 4, 5}) {
            int actual = 0;
            for (int index : occupied) actual += candidate[index] * candidate[(index + lag) & 4095];
            if (actual != expected[lag]) { matching = false; break; }
        }
        if (!matching) continue;
        for (int lag = 6; lag <= 2048; ++lag) {
            int actual = 0;
            for (int index : occupied) actual += candidate[index] * candidate[(index + lag) & 4095];
            if (actual != expected[lag]) { matching = false; break; }
        }
        if (matching) return variant + 1;
    }
    return 0;
}
