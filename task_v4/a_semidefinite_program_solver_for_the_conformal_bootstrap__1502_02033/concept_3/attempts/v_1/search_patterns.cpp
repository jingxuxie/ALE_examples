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
    for (uint32_t seed = begin; seed < end; ++seed) {
        PythonRandom generator(seed);
        int values[120];
        packed = 0;
        for (int index = 0; index < 6; ++index) {
            values[index] = generator.draw();
            packed = packed * 11 + values[index] + 5;
        }
        if (!patterns.count(packed)) continue;
        std::printf("%u %d", seed, packed);
        for (int index = 0; index < 120; ++index) {
            if (index >= 6) values[index] = generator.draw();
            std::printf(" %d", values[index]);
        }
        std::printf("\n");
        std::fflush(stdout);
    }
}
