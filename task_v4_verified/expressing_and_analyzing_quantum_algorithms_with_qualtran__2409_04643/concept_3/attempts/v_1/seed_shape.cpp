#define main unused_seed_main
#include "seed_search.cpp"
#undef main

int signature(int first, int second, int third) {
    if (first > second) std::swap(first, second);
    if (second > third) std::swap(second, third);
    if (first > second) std::swap(first, second);
    return first | (second << 8) | (third << 16);
}

int main(int argc, char** argv) {
    uint32_t begin = std::strtoul(argv[1], nullptr, 0), end = std::strtoul(argv[2], nullptr, 0);
    int length = argc > 3 ? std::atoi(argv[3]) : 4096;
    int width = 12;
    std::vector<int> masks{1064, 1034, 2096, 1030, 41, 76, 304, 1044};
    std::array<int, 12> expected_incidence{};
    std::vector<int> expected_signatures;
    for (int output = 0; output < 8; ++output) {
        std::vector<int> patterns;
        for (int bit = 0; bit < width; ++bit) if (masks[output] >> bit & 1) {
            patterns.push_back(expected_incidence[bit]);
            expected_incidence[bit] |= 1 << output;
        }
        expected_signatures.push_back(signature(patterns[0], patterns[1], patterns[2]));
    }
    auto started = std::chrono::steady_clock::now();
    #pragma omp parallel for schedule(dynamic, 64)
    for (uint32_t seed = begin; seed < end; ++seed) {
        PythonRandom random(seed);
        std::vector<unsigned char> stream(length + 128);
        for (auto& value : stream) value = random.next() >> 28;
        for (int start = 0; start < length; ++start) {
            if (stream[start] >= width) continue;
            std::array<int, 12> incidence{};
            int position = start;
            bool valid = true;
            for (int output = 0; output < 8; ++output) {
                int pool[12], chosen[3];
                for (int bit = 0; bit < width; ++bit) pool[bit] = bit;
                for (int amount = 0; amount < 3; ++amount) {
                    int choice;
                    do { choice = stream[position++]; } while (choice >= width - amount && position < length + 120);
                    if (position >= length + 120) { valid = false; break; }
                    chosen[amount] = pool[choice];
                    pool[choice] = pool[width - amount - 1];
                }
                if (!valid || signature(incidence[chosen[0]], incidence[chosen[1]], incidence[chosen[2]]) != expected_signatures[output]) { valid = false; break; }
                for (int bit : chosen) incidence[bit] |= 1 << output;
            }
            if (valid) {
                #pragma omp critical
                {
                    std::cout << "MATCH seed " << seed << " start " << start << " end " << position << " mapping";
                    for (int bit = 0; bit < width; ++bit) {
                        for (int target = 0; target < width; ++target) if (incidence[bit] == expected_incidence[target]) { std::cout << ' ' << target; break; }
                    }
                    std::cout << std::endl;
                }
            }
        }
    }
    std::cerr << "seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
}
