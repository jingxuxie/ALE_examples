#define main unused_shuffle_main
#include "seed_shuffle.cpp"
#undef main

int main(int argc, char** argv) {
    std::string path = argv[1];
    int first_seed = std::stoi(argv[2]), last_seed = std::stoi(argv[3]);
    int offsets = std::stoi(argv[4]);
    std::array<std::array<int, 20>, 10> targets;
    std::ifstream input(path + "/shuffle_targets.txt");
    for (auto& target : targets) for (int& value : target) input >> value;
    std::array<std::vector<int>, 8192> first_matches;
    for (int target = 0; target < 10; ++target) {
        for (int value = std::max(0, targets[target][0] - 24); value <= targets[target][0]; ++value) first_matches[value].push_back(target);
    }
    std::vector<uint32_t> words(offsets + 100);
    auto started = std::chrono::steady_clock::now();
    for (int seed = first_seed; seed < last_seed; ++seed) {
        PythonMT generator(seed);
        for (auto& word : words) word = generator.next();
        for (int start = 0; start < offsets; ++start) {
            int first = words[start] >> 19;
            for (int target_index : first_matches[first]) {
                const auto& target = targets[target_index];
                std::array<int, 20> keys, values;
                int cursor = start, matches = 0;
                for (int offset = 0; offset < 20; ++offset) {
                    int position = 8192;
                    while (position >= 8176 - offset) position = words[cursor++] >> 19;
                    int value = position, replacement = 8175 - offset;
                    for (int previous = offset - 1; previous >= 0; --previous) if (keys[previous] == position) { value = values[previous]; break; }
                    for (int previous = offset - 1; previous >= 0; --previous) if (keys[previous] == 8175 - offset) { replacement = values[previous]; break; }
                    keys[offset] = position;
                    values[offset] = replacement;
                    matches += value <= target[offset] && target[offset] <= value + 24;
                    if (offset == 3 && matches < 3) break;
                }
                if (matches < 17) continue;
                std::cout << "FOUND " << seed << ' ' << start << ' ' << target_index << ' ' << matches << std::endl;
                std::ofstream output(path + "/background_match.json");
                output << "{\"seed\":" << seed << ",\"offset\":" << start << ",\"pass\":" << target_index / 2 + 1 << ",\"method\":\"" << (target_index % 2 ? "sample" : "shuffle") << "\"}\n";
                return 0;
            }
        }
        if ((seed - first_seed) % 10000 == 0) std::cout << "PROGRESS " << seed << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
    }
}
