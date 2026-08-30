#define main old_main
#include "search_mt.cpp"
#undef main
#include <fstream>
#include <unordered_set>

int main(int argc, char** argv) {
    std::unordered_set<int> patterns;
    std::ifstream input("patterns.txt");
    int packed;
    while (input >> packed) patterns.insert(packed);
    uint32_t begin = argc > 1 ? std::strtoul(argv[1], nullptr, 10) : 0;
    uint32_t end = argc > 2 ? std::strtoul(argv[2], nullptr, 10) : 1000000;
    PythonRandom generator(0);
    for (uint32_t seed = begin; seed < end; ++seed) {
        generator.state[0] = seed;
        generator.position = 624;
        for (int index = 1; index < 624; ++index)
            generator.state[index] = 1812433253U * (generator.state[index-1] ^ (generator.state[index-1] >> 30)) + index;
        int values[120];
        packed = 0;
        for (int index = 0; index < 6; ++index) {
            uint32_t value;
            do {value = generator.next() & 15U;} while (value >= 11);
            values[index] = int(value) - 5;
            packed = packed * 11 + value;
        }
        if (!patterns.count(packed)) continue;
        std::printf("%u %d", seed, packed);
        for (int index = 0; index < 120; ++index) {
            if (index >= 6) {
                uint32_t value;
                do {value = generator.next() & 15U;} while (value >= 11);
                values[index] = int(value) - 5;
            }
            std::printf(" %d", values[index]);
        }
        std::printf("\n");
        std::fflush(stdout);
    }
}
