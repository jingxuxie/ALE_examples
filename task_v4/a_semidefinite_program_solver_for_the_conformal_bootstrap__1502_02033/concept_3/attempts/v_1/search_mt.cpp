#include <array>
#include <cstdint>
#include <cstdio>
#include <cstdlib>

struct PythonRandom {
    std::array<uint32_t, 624> state;
    int position = 624;
    explicit PythonRandom(uint32_t seed) {
        state[0] = 19650218U;
        for (int index = 1; index < 624; ++index)
            state[index] = 1812433253U * (state[index-1] ^ (state[index-1] >> 30)) + index;
        int index = 1;
        for (int count = 624; count; --count) {
            state[index] = (state[index] ^ ((state[index-1] ^ (state[index-1] >> 30)) * 1664525U)) + seed;
            if (++index == 624) {state[0] = state[623]; index = 1;}
        }
        for (int count = 623; count; --count) {
            state[index] = (state[index] ^ ((state[index-1] ^ (state[index-1] >> 30)) * 1566083941U)) - index;
            if (++index == 624) {state[0] = state[623]; index = 1;}
        }
        state[0] = 0x80000000U;
    }
    uint32_t next() {
        if (position == 624) {
            for (int index = 0; index < 624; ++index) {
                uint32_t mixed = (state[index] & 0x80000000U) | (state[(index+1)%624] & 0x7fffffffU);
                state[index] = state[(index+397)%624] ^ (mixed >> 1) ^ ((mixed & 1) ? 0x9908b0dfU : 0U);
            }
            position = 0;
        }
        uint32_t value = state[position++];
        value ^= value >> 11;
        value ^= (value << 7) & 0x9d2c5680U;
        value ^= (value << 15) & 0xefc60000U;
        value ^= value >> 18;
        return value;
    }
    int draw() {
        uint32_t value;
        do {value = next() >> 28;} while (value >= 11);
        return int(value)-5;
    }
};

bool match(const int* values, int rows, int columns, const int* wanted, int checked) {
    for (int first = 0; first < checked; ++first)
        for (int second = 0; second <= first; ++second) {
            int actual = 0;
            for (int row = 0; row < rows; ++row)
                actual += values[row*columns+first]*values[row*columns+second];
            if (actual != wanted[first*checked+second]) return false;
        }
    return true;
}

int main(int argc, char** argv) {
    uint32_t begin = argc > 1 ? std::strtoul(argv[1], nullptr, 10) : 0;
    uint32_t end = argc > 2 ? std::strtoul(argv[2], nullptr, 10) : 1000000;
    int gram1[] = {17,-8,-9,-8,4,4,-9,4,5};
    int gram2[] = {11,1,23,1,35,-11,23,-11,59};
    int gram3[] = {50,-10,5,-10,26,1,5,1,34};
    int lead1[] = {25,20,15,20,41,-3,15,-3,18};
    int lead2[] = {29,-20,33,-20,16,0,33,0,45};
    int lead3[] = {25,-22,11,-22,29,-5,11,-5,43};
    for (uint32_t seed = begin; seed < end; ++seed) {
        PythonRandom generator(seed);
        int values[120];
        for (int index = 0; index < 12; ++index) values[index] = generator.draw();
        bool first = match(values, 2, 3, gram1, 3);
        bool second = match(values, 3, 3, gram2, 3);
        bool third = match(values, 3, 4, gram3, 3);
        if (!(first || second || third)) continue;
        for (int index = 12; index < 120; ++index) values[index] = generator.draw();
        std::printf("candidate %u cases %d %d %d lead %d %d %d\n", seed, first, second, third,
                    first && match(values+36, 2, 3, lead1, 3),
                    second && match(values+45, 3, 3, lead2, 3),
                    third && match(values+108, 3, 4, lead3, 3));
        std::fflush(stdout);
    }
}
