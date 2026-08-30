#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <vector>
#include <omp.h>

struct PythonRandom {
    std::array<uint32_t, 624> state;
    int index = 624;
    explicit PythonRandom(uint32_t seed) {
        state[0] = 19650218u;
        for (int offset = 1; offset < 624; ++offset) state[offset] = 1812433253u * (state[offset - 1] ^ (state[offset - 1] >> 30)) + offset;
        int offset = 1;
        for (int repeat = 0; repeat < 624; ++repeat) {
            state[offset] = (state[offset] ^ ((state[offset - 1] ^ (state[offset - 1] >> 30)) * 1664525u)) + seed;
            if (++offset == 624) { state[0] = state[623]; offset = 1; }
        }
        for (int repeat = 0; repeat < 623; ++repeat) {
            state[offset] = (state[offset] ^ ((state[offset - 1] ^ (state[offset - 1] >> 30)) * 1566083941u)) - offset;
            if (++offset == 624) { state[0] = state[623]; offset = 1; }
        }
        state[0] = 0x80000000u;
    }
    uint32_t next() {
        if (index == 624) {
            for (int offset = 0; offset < 624; ++offset) {
                uint32_t joined = (state[offset] & 0x80000000u) | (state[(offset + 1) % 624] & 0x7fffffffu);
                state[offset] = state[(offset + 397) % 624] ^ (joined >> 1) ^ ((joined & 1) ? 0x9908b0dfu : 0u);
            }
            index = 0;
        }
        uint32_t result = state[index++];
        result ^= result >> 11;
        result ^= (result << 7) & 0x9d2c5680u;
        result ^= (result << 15) & 0xefc60000u;
        result ^= result >> 18;
        return result;
    }
};

int main(int argc, char** argv) {
    if (argc == 2) {
        PythonRandom random(std::strtoul(argv[1], nullptr, 0));
        for (int repeat = 0; repeat < 10; ++repeat) std::cout << random.next() << ' ';
        std::cout << std::endl;
        return 0;
    }
    uint32_t begin = std::strtoul(argv[1], nullptr, 0), end = std::strtoul(argv[2], nullptr, 0);
    int length = argc > 3 ? std::atoi(argv[3]) : 4096;
    int width = argc > 4 ? std::atoi(argv[4]) : 12;
    int gap = argc > 5 ? std::atoi(argv[5]) : 0;
    int mode = argc > 6 ? std::atoi(argv[6]) : 0;
    std::vector<int> masks = width == 12 ? std::vector<int>{1064, 1034, 2096, 1030, 41, 76, 304, 1044} : (width == 11 ? std::vector<int>{266, 552, 392, 352, 1092, 41} : std::vector<int>{776, 164, 328, 104});
    auto started = std::chrono::steady_clock::now();
    #pragma omp parallel for schedule(dynamic, 256)
    for (uint32_t seed = begin; seed < end; ++seed) {
        PythonRandom random(seed);
        std::vector<unsigned char> stream(length + 128);
        for (auto& value : stream) value = random.next() >> 28;
        std::function<int(int, int)> match_tail = [&](int output, int position) -> int {
            if (output == static_cast<int>(masks.size())) return position;
            for (int skip = 0; skip <= (output ? gap : 0); ++skip) {
                int cursor = position + skip, selected = 0;
                int pool[16];
                for (int bit = 0; bit < width; ++bit) pool[bit] = bit;
                bool valid = true;
                for (int amount = 0; amount < 3; ++amount) {
                    int choice;
                    do { choice = stream[cursor++]; } while ((choice >= width - (mode ? 0 : amount) || (mode && (selected >> choice & 1))) && cursor < length + 120);
                    if (cursor >= length + 120) { valid = false; break; }
                    int value = mode ? choice : pool[choice];
                    if (!(masks[output] >> value & 1)) { valid = false; break; }
                    selected |= 1 << value;
                    pool[choice] = pool[width - amount - 1];
                }
                if (valid && selected == masks[output]) {
                    int result = match_tail(output + 1, cursor);
                    if (result >= 0) return result;
                }
            }
            return -1;
        };
        for (int start = 0; start < length; ++start) {
            if (stream[start] >= width || !(masks[0] >> stream[start] & 1)) continue;
            if (gap) {
                int result = match_tail(0, start);
                if (result >= 0) {
                    #pragma omp critical
                    std::cout << "MATCH seed " << seed << " position " << start << " end " << result << " width " << width << " gap " << gap << std::endl;
                }
                continue;
            }
            int position = start;
            bool valid = true;
            for (int mask : masks) {
                int pool[16];
                for (int bit = 0; bit < width; ++bit) pool[bit] = bit;
                int selected = 0;
                for (int amount = 0; amount < 3; ++amount) {
                    int choice;
                    do { choice = stream[position++]; } while ((choice >= width - (mode ? 0 : amount) || (mode && (selected >> choice & 1))) && position < length + 120);
                    if (position >= length + 120) { valid = false; break; }
                    int value = mode ? choice : pool[choice];
                    if (!(mask >> value & 1)) { valid = false; break; }
                    selected |= 1 << value;
                    pool[choice] = pool[width - amount - 1];
                }
                if (!valid || selected != mask) { valid = false; break; }
            }
            if (valid) {
                #pragma omp critical
                std::cout << "MATCH seed " << seed << " position " << start << " end " << position << " width " << width << std::endl;
            }
        }
    }
    std::cerr << "seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
}
