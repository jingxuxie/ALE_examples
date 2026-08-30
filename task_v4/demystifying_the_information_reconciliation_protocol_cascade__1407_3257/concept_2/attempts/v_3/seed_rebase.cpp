#define main unused_shuffle_main
#include "seed_shuffle.cpp"
#undef main

int main(int argc, char** argv) {
    std::string path = argv[1];
    int first_seed = std::stoi(argv[2]);
    int last_seed = std::stoi(argv[3]);
    int initial_offsets = std::stoi(argv[4]);
    std::array<std::array<int, 20>, 10> targets;
    std::ifstream input(path + "/shuffle_targets.txt");
    for (auto& target : targets) for (int& position : target) input >> position;
    auto started = std::chrono::steady_clock::now();
    std::array<int, 8192> permutation;
    std::array<uint32_t, 2100> words;
    for (int seed = first_seed; seed < last_seed; ++seed) {
        for (int initial = 0; initial < initial_offsets; ++initial) {
            PythonMT generator(seed);
            for (int offset = 0; offset < initial; ++offset) generator.next();
            for (int position = 0; position < 8192; ++position) permutation[position] = position;
            for (int position = 8191; position > 0; --position) {
                int bits = 32 - __builtin_clz(position + 1);
                int other = position + 1;
                while (other > position) other = generator.next() >> (32 - bits);
                std::swap(permutation[position], permutation[other]);
            }
            for (auto& word : words) word = generator.next();
            for (int method = 0; method < 2; ++method) {
                std::array<int, 20> target;
                for (int offset = 0; offset < 20; ++offset) target[offset] = permutation[method ? 8191 - targets[method][offset] : targets[method][offset]];
                for (int start = 0; start < 2000; ++start) {
                    if (int(words[start] >> 18) != target[0]) continue;
                    std::array<int, 20> keys, values;
                    int cursor = start, matches = 0;
                    for (int offset = 0; offset < 20; ++offset) {
                        int position = 8192;
                        while (position >= 8192 - offset) position = words[cursor++] >> (offset == 0 ? 18 : 19);
                        int value = position, replacement = 8191 - offset;
                        for (int previous = offset - 1; previous >= 0; --previous) if (keys[previous] == position) { value = values[previous]; break; }
                        for (int previous = offset - 1; previous >= 0; --previous) if (keys[previous] == 8191 - offset) { replacement = values[previous]; break; }
                        keys[offset] = position;
                        values[offset] = replacement;
                        matches += value == target[offset];
                        if (offset == 3 && matches < 3) break;
                    }
                    if (matches < 17) continue;
                    std::cout << "FOUND " << seed << ' ' << initial << ' ' << start << ' ' << method << ' ' << matches << std::endl;
                    std::ofstream output(path + "/rebase_match.json");
                    output << "{\"seed\":" << seed << ",\"initial\":" << initial << ",\"between\":" << start << ",\"method\":" << method << "}\n";
                    return 0;
                }
            }
        }
        if ((seed - first_seed) % 100 == 0) std::cout << "PROGRESS " << seed << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
    }
}
