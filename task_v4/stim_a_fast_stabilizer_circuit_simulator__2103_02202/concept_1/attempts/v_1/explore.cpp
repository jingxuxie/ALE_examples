#define main original_main
#include "engine.cpp"
#undef main

int main(int argc, char **argv) {
    double seconds = argc > 1 ? std::atof(argv[1]) : 30;
    int mode = argc > 2 ? std::atoi(argv[2]) : 0;
    Optimizer optimizer(seconds);
    std::priority_queue<State> candidates;
    uint64_t mask = (1ull << optimizer.budget) - 1;
    uint64_t end = 1ull << optimizer.count;
    int tested = 0;
    while (mask < end) {
        Values difference[128];
        int size = optimizer.distribution(mask, difference);
        double score;
        if (mode == 0) {
            score = optimizer.fit(difference, size);
        } else {
            double minimum = 1;
            for (int regime = 0; regime < optimizer.regimes; ++regime) {
                double correlation = 0;
                for (int syndrome = 0; syndrome < size; ++syndrome)
                    correlation += std::abs(difference[syndrome].value[regime]);
                minimum = std::min(minimum, correlation);
            }
            score = (1 - minimum) * 0.5;
        }
        if (candidates.size() < 1024 || score < candidates.top().score) {
            candidates.push({score, mask});
            if (candidates.size() > 1024) candidates.pop();
        }
        uint64_t lowest = mask & -mask;
        uint64_t next = mask + lowest;
        mask = (((next ^ mask) >> 2) / lowest) | next;
        if ((++tested & 1023) == 0 && Clock::now() >= optimizer.deadline) break;
    }
    std::vector<State> results;
    double proxy = 1;
    while (!candidates.empty()) {
        State state = candidates.top();
        candidates.pop();
        proxy = std::min(proxy, state.score);
        Values difference[128];
        int size = optimizer.distribution(state.mask, difference);
        state.score = optimizer.fit(difference, size, nullptr, true);
        results.push_back(state);
    }
    std::sort(results.begin(), results.end());
    std::cerr << "tested=" << tested << " proxy=" << proxy << " best=" << results[0].score << "\n";
    std::cout << "[";
    for (size_t index = 0; index < std::min<size_t>(96, results.size()); ++index) {
        const auto &state = results[index];
        Values difference[128];
        int table[128];
        int size = optimizer.distribution(state.mask, difference);
        double score = optimizer.fit(difference, size, table, true);
        if (index) std::cout << ",";
        std::cout << "{\"selected\":[";
        bool first = true;
        for (int tap = 0; tap < optimizer.count; ++tap) if ((state.mask >> tap) & 1) {
            if (!first) std::cout << ",";
            first = false;
            std::cout << tap;
        }
        std::cout << "],\"correction\":[";
        for (int syndrome = 0; syndrome < size; ++syndrome) {
            if (syndrome) std::cout << ",";
            std::cout << table[syndrome];
        }
        std::cout << "],\"score\":" << std::setprecision(15) << score << "}";
    }
    std::cout << "]\n";
}
