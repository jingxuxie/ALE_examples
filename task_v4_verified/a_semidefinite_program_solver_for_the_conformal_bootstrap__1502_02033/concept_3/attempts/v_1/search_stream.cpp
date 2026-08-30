#define main old_main
#include "search_mt.cpp"
#undef main
#include <fstream>
#include <unordered_set>

int main(int argc, char** argv) {
    std::unordered_set<uint64_t> patterns;
    std::ifstream input("stream_patterns.txt");
    uint64_t packed;
    while (input >> packed) patterns.insert(packed);
    uint32_t begin = argc > 1 ? std::strtoul(argv[1], nullptr, 10) : 0;
    uint32_t end = argc > 2 ? std::strtoul(argv[2], nullptr, 10) : 1000000;
    int count = argc > 3 ? std::atoi(argv[3]) : 400;
    int mode = argc > 4 ? std::atoi(argv[4]) : 0;
    uint64_t modulus = 1;
    for (int index = 0; index < 11; ++index) modulus *= 11;
    for (uint32_t seed = begin; seed < end; ++seed) {
        PythonRandom generator(seed);
        if (mode & 1) {
            generator.state[0] = seed;
            for (int index = 1; index < 624; ++index)
                generator.state[index] = 1812433253U * (generator.state[index-1] ^ (generator.state[index-1] >> 30)) + index;
        }
        packed = 0;
        for (int index = 0; index < count; ++index) {
            uint32_t value;
            if (mode >= 2) {
                uint32_t first = generator.next() >> 5;
                uint32_t second = generator.next() >> 6;
                value = uint32_t((first * 67108864.0 + second) * (11.0 / 9007199254740992.0));
            } else {
                do {value = mode ? generator.next() & 15U : generator.next() >> 28;} while (value >= 11);
            }
            packed = (packed % modulus) * 11 + value;
            if (index >= 11 && patterns.count(packed)) {
                std::printf("MATCH %u %d %llu %d\n", seed, index-11, (unsigned long long)packed, mode);
                std::fflush(stdout);
            }
        }
    }
}
