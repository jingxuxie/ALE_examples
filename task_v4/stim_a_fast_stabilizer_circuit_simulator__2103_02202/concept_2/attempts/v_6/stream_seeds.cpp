#define main original_seed_main
#include "seed_search.cpp"
#undef main

struct Window {
    std::array<uint16_t, 512> counts{};
    std::vector<int> queue;
    size_t front = 0;
    int distinct = 0;
    uint64_t low = 0;
    int target = 36;
    bool fixed_last = false;

    explicit Window(int length, bool fixed) : queue(), target(fixed ? 35 : 36), fixed_last(fixed) {
        queue.reserve(length);
    }

    void reset() {
        counts.fill(0);
        queue.clear();
        front = 0;
        distinct = 0;
        low = fixed_last ? columns[511][0] : 0;
    }

    void append(int value, uint64_t seed, int offset) {
        queue.push_back(value);
        if (counts[value]++ == 0) {
            ++distinct;
            low ^= columns[value][0];
        }
        if (distinct == target) {
            if (low == 0) {
                std::vector<int> support;
                for (int fault = 0; fault < 512; ++fault) if (counts[fault]) support.push_back(fault);
                if (fixed_last) support.push_back(511);
                found(support, seed, offset, fixed_last ? 6 : 5);
            }
            do {
                int removed = queue[front++];
                if (--counts[removed] == 0) {
                    --distinct;
                    low ^= columns[removed][0];
                }
            } while (distinct == target);
        }
    }
};

int main(int argc, char** argv) {
    uint64_t begin = argc > 1 ? std::strtoull(argv[1], nullptr, 0) : 0;
    uint64_t end = argc > 2 ? std::strtoull(argv[2], nullptr, 0) : 1000000;
    int length = argc > 3 ? std::atoi(argv[3]) : 6000;
    std::vector<uint64_t> selected_seeds;
    if (argc > 4) {
        std::ifstream selected_input(argv[4]);
        uint64_t selected;
        while (selected_input >> selected) selected_seeds.push_back(selected);
        begin = 0;
        end = selected_seeds.size();
    }
    std::ifstream input("columns.txt");
    for (int fault = 0; fault < 512; ++fault) input >> std::hex >> columns[fault][0] >> columns[fault][1] >> columns[fault][2] >> observable[fault];
    if (!input) return 2;
    Window full(length, false);
    Window fixed(length, true);
    std::ifstream state_input;
    if (argc > 5) state_input.open(argv[5]);
    auto start = std::chrono::steady_clock::now();
    for (uint64_t cursor = begin; cursor < end && !success; ++cursor) {
        uint64_t seed = selected_seeds.empty() ? cursor : selected_seeds[cursor];
        PythonRandom random(seed);
        if (state_input.is_open()) {
            for (uint32_t& value : random.state) state_input >> value;
            state_input >> random.position;
            if (!state_input) return 3;
        }
        full.reset();
        fixed.reset();
        for (int offset = 0; offset < length && !success; ++offset) {
            uint32_t word = random.next();
            int wide = word >> 22;
            if (wide < 512) full.append(wide, seed, offset);
            int narrow = word >> 23;
            if (narrow < 511) fixed.append(narrow, seed, offset);
        }
        if ((cursor & 16383) == 0) {
            double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            std::cerr << "seed=" << seed << " seconds=" << elapsed << '\n';
        }
    }
    std::cerr << "completed seconds=" << std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count() << '\n';
    return success ? 0 : 1;
}
