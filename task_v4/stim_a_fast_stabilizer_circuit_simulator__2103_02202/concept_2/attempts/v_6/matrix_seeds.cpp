#define main original_seed_main
#include "seed_search.cpp"
#undef main

int main(int argc, char** argv) {
    uint64_t end = argc > 1 ? std::strtoull(argv[1], nullptr, 0) : 16777216;
    int seconds = argc > 2 ? std::atoi(argv[2]) : 420;
    uint64_t begin = argc > 3 ? std::strtoull(argv[3], nullptr, 0) : 0;
    std::vector<uint64_t> selected_seeds;
    if (argc > 4) {
        std::ifstream selected_input(argv[4]);
        uint64_t selected;
        while (selected_input >> selected) selected_seeds.push_back(selected);
        begin = 0;
        end = selected_seeds.size();
    }
    std::ifstream state_input;
    if (argc > 5) state_input.open(argv[5]);
    std::string output_path = argc > 6 ? argv[6] : "matrix_seed.json";
    std::ifstream input("columns.txt");
    for (int fault = 0; fault < 512; ++fault) input >> std::hex >> columns[fault][0] >> columns[fault][1] >> columns[fault][2] >> observable[fault];
    if (!input) return 2;
    std::vector<uint64_t> patterns;
    for (int layout = 0; layout < 8; ++layout) {
        uint64_t pattern = 0;
        for (int position = 0; position < 64; ++position) {
            int fault;
            int row;
            if (layout < 4) {
                fault = layout & 2 ? 511 : 0;
                row = layout & 1 ? 191 - position : position;
            } else {
                fault = layout & 1 ? 511 - position : position;
                row = layout & 2 ? 191 : 0;
            }
            pattern = (pattern << 1) | ((columns[fault][row >> 6] >> (row & 63)) & 1);
        }
        patterns.push_back(pattern);
        patterns.push_back(~pattern);
    }
    std::array<uint8_t, 65536> filter{};
    for (uint64_t pattern : patterns) {
        uint16_t suffix = pattern;
        filter[suffix] = 1;
        for (int bit = 0; bit < 16; ++bit) filter[suffix ^ (1 << bit)] = 1;
    }
    auto started = std::chrono::steady_clock::now();
    for (uint64_t cursor = begin; cursor < end; ++cursor) {
        uint64_t seed = selected_seeds.empty() ? cursor : selected_seeds[cursor];
        if ((cursor & 8191) == 0 && std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count() >= seconds) break;
        PythonRandom random(seed);
        if (state_input.is_open()) {
            for (uint32_t& value : random.state) state_input >> value;
            state_input >> random.position;
            if (!state_input) return 3;
        }
        uint64_t streams[5] = {};
        int lengths[5] = {};
        auto append = [&](int mode, int bit, int offset) {
            streams[mode] = (streams[mode] << 1) | bit;
            ++lengths[mode];
            if (lengths[mode] < 64 || !filter[uint16_t(streams[mode])]) return false;
            for (size_t pattern = 0; pattern < patterns.size(); ++pattern) {
                if (__builtin_popcountll(patterns[pattern] ^ streams[mode]) <= 1) {
                    std::ofstream output(output_path);
                    output << "{\"seed\":" << seed << ",\"mode\":" << mode << ",\"offset\":" << offset << ",\"pattern\":" << pattern << "}\n";
                    std::cerr << "MATCH seed=" << seed << " mode=" << mode << " offset=" << offset << " pattern=" << pattern << '\n';
                    return true;
                }
            }
            return false;
        };
        for (int offset = 0; offset < 384; ++offset) {
            uint32_t word = random.next();
            if (append(0, word >> 31, offset)) return 0;
            if (append(1 + (offset & 1), word >> 31, offset)) return 0;
            if ((word >> 30) < 2 && append(3, word >> 30, offset)) return 0;
            if (append(4, word & 1, offset)) return 0;
        }
        if ((seed & 1048575) == 0) std::cerr << "seed=" << seed << " seconds=" << std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count() << '\n';
    }
    std::cerr << "completed seconds=" << std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count() << '\n';
    return 1;
}
