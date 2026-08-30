#define main unused_seed_main
#include "seed_search.cpp"
#undef main

int main(int argc, char** argv) {
    uint32_t begin = std::strtoul(argv[1], nullptr, 0), end = std::strtoul(argv[2], nullptr, 0);
    int length = argc > 3 ? std::atoi(argv[3]) : 4096;
    int max_gap = argc > 4 ? std::atoi(argv[4]) : 256;
    std::array<int, 8> masks{1064, 1034, 2096, 1030, 41, 76, 304, 1044};
    int total = length + max_gap * 8 + 256;
    auto started = std::chrono::steady_clock::now();
    #pragma omp parallel for schedule(dynamic, 64)
    for (uint32_t seed = begin; seed < end; ++seed) {
        PythonRandom random(seed);
        std::vector<unsigned char> stream(total);
        for (auto& value : stream) value = random.next() >> 28;
        stream[total - 1] = 0;
        std::array<std::vector<int>, 3> next;
        for (int amount = 0; amount < 3; ++amount) {
            next[amount].resize(total);
            int accepted = total - 1;
            for (int position = total - 1; position >= 0; --position) {
                if (stream[position] < 12 - amount) accepted = position;
                next[amount][position] = accepted;
            }
        }
        std::vector<int> samples(total), ends(total);
        for (int start = 0; start < total - 128; ++start) {
            int first_position = next[0][start];
            int second_position = next[1][first_position + 1];
            int third_position = next[2][second_position + 1];
            int first = stream[first_position], second = stream[second_position], third = stream[third_position];
            int second_value = second == first ? 11 : second;
            int third_value = third == second ? (first == 10 ? 11 : 10) : (third == first ? 11 : third);
            samples[start] = (1 << first) | (1 << second_value) | (1 << third_value);
            ends[start] = third_position + 1;
        }
        for (int start = 0; start < length; ++start) {
            if (samples[start] != masks[0]) continue;
            for (int gap = 0; gap <= max_gap; ++gap) {
                int position = ends[start] + gap;
                if (samples[position] != masks[1]) continue;
                bool valid = true;
                for (int output = 2; output < 8; ++output) {
                    position = ends[position] + gap;
                    if (samples[position] != masks[output]) { valid = false; break; }
                }
                if (valid) {
                    #pragma omp critical
                    std::cout << "MATCH seed " << seed << " start " << start << " gap " << gap << std::endl;
                }
            }
        }
    }
    std::cerr << "seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
}
