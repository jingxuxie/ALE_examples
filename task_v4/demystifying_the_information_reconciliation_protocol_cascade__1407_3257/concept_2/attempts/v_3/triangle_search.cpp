#define main unused_annealing_main
#include "search.cpp"
#undef main

int main(int argc, char** argv) {
    std::string path = argv[1];
    int first_start = std::stoi(argv[2]), first_stop = std::stoi(argv[3]);
    generator.seed(first_start + 123);
    std::ifstream input(path + "/signatures.txt");
    std::array<int, 384> counts{};
    for (int position = 0; position < size; ++position) for (int pass = 0; pass < 6; ++pass) {
        int block; input >> block;
        int check = 64 * pass + block;
        checks[position][pass] = check;
        neighbors[check][counts[check]++] = position;
    }
    std::array<std::array<std::vector<std::vector<int>>, 6>, 6> pair_groups;
    for (int left = 0; left < 6; ++left) for (int right = 0; right < 6; ++right) if (left != right) {
        pair_groups[left][right].resize(4096);
        for (int position = 0; position < size; ++position) pair_groups[left][right][64 * (checks[position][left] % 64) + checks[position][right] % 64].push_back(position);
    }
    std::array<uint32_t, 8192> stamps{}, excluded_stamps{};
    std::array<unsigned char, 8192> masks{};
    uint32_t stamp = 0;
    auto started = std::chrono::steady_clock::now();
    long long triangles = 0;
    for (int first = first_start; first < first_stop; ++first) {
        for (int shared = 0; shared < 6; ++shared) for (int second : neighbors[checks[first][shared]]) {
            if (second <= first) continue;
            int shared_count = 0;
            for (int pass = 0; pass < 6; ++pass) shared_count += checks[first][pass] == checks[second][pass];
            if (shared_count != 1) continue;
            for (int left = 0; left < 6; ++left) if (left != shared) for (int right = 0; right < 6; ++right) if (right != shared && right != left) {
                int key = 64 * (checks[first][left] % 64) + checks[second][right] % 64;
                for (int third : pair_groups[left][right][key]) {
                    if (third <= second) continue;
                    int first_shared = 0, second_shared = 0;
                    for (int pass = 0; pass < 6; ++pass) {
                        first_shared += checks[first][pass] == checks[third][pass];
                        second_shared += checks[second][pass] == checks[third][pass];
                    }
                    if (first_shared != 1 || second_shared != 1) continue;
                    ++triangles;
                    ++stamp;
                    std::array<unsigned char, 384> roots{};
                    std::vector<int> support{first, second, third}, pool = support, touched;
                    touched.reserve(2304);
                    for (int anchor = 0; anchor < 3; ++anchor) for (int check : checks[support[anchor]]) roots[check] |= 1 << anchor;
                    for (int anchor = 0; anchor < 3; ++anchor) for (int check : checks[support[anchor]]) {
                        unsigned char mask = roots[check];
                        if (mask & (mask - 1)) {
                            for (int position : neighbors[check]) excluded_stamps[position] = stamp;
                        } else {
                            for (int position : neighbors[check]) {
                                if (stamps[position] != stamp) { stamps[position] = stamp; masks[position] = 0; touched.push_back(position); }
                                masks[position] |= mask;
                            }
                        }
                    }
                    for (int position : touched) {
                        int mask = masks[position];
                        if (!(mask & (mask - 1)) || excluded_stamps[position] == stamp) continue;
                        pool.push_back(position);
                    }
                    if (expand(support, path, 100 + first_start, &pool)) return 0;
                }
            }
        }
        if ((first - first_start) % 16 == 0) std::cout << "PROGRESS " << first << " triangles " << triangles << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
    }
}
