#define main unused_annealing_main
#include "search.cpp"
#undef main

int main(int argc, char** argv) {
    std::string path = argv[1];
    int seed = argc > 2 ? std::stoi(argv[2]) : 1;
    int duration = argc > 3 ? std::stoi(argv[3]) : 600;
    generator.seed(seed);
    std::ifstream input(path + "/signatures.txt");
    std::array<int, 384> counts{};
    for (int position = 0; position < size; ++position) {
        for (int pass = 0; pass < 6; ++pass) {
            int block;
            input >> block;
            int check = 64 * pass + block;
            checks[position][pass] = check;
            neighbors[check][counts[check]++] = position;
        }
    }
    std::vector<float> messages(6 * size), replies(6 * size), next_replies(6 * size);
    std::array<float, size> channels, posterior;
    auto started = std::chrono::steady_clock::now();
    int best_weight = 8192;
    int best_score = 8192;
    for (int trial = 0;; ++trial) {
        double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
        if (elapsed > duration) break;
        int anchor = generator() % size;
        for (int position = 0; position < size; ++position) channels[position] = 0.5f + float(generator() % 1000) / 1000.0f;
        channels[anchor] = -1000.0f;
        replies.assign(6 * size, 0.0f);
        for (int pass = 0; pass < 6; ++pass) for (int position = 0; position < size; ++position) messages[pass * size + position] = channels[position];
        float scale = seed % 2 ? 0.8f : 1.0f;
        for (int iteration = 0; iteration < 300; ++iteration) {
            for (int check = 0; check < 384; ++check) {
                int base = (check / 64) * size;
                float minimum = 10000.0f, second_minimum = 10000.0f;
                int minimum_position = -1;
                bool sign = false;
                for (int position : neighbors[check]) {
                    float message = messages[base + position];
                    sign ^= message < 0;
                    float absolute = std::abs(message);
                    if (absolute < minimum) {
                        second_minimum = minimum;
                        minimum = absolute;
                        minimum_position = position;
                    } else if (absolute < second_minimum) second_minimum = absolute;
                }
                for (int position : neighbors[check]) {
                    float message = scale * (position == minimum_position ? second_minimum : minimum);
                    if (sign ^ (messages[base + position] < 0)) message = -message;
                    next_replies[base + position] = 0.5f * replies[base + position] + 0.5f * message;
                }
            }
            replies.swap(next_replies);
            std::vector<int> support;
            parity.fill(0);
            selected.fill(false);
            for (int position = 0; position < size; ++position) {
                float value = channels[position];
                for (int pass = 0; pass < 6; ++pass) value += replies[pass * size + position];
                posterior[position] = value;
                for (int pass = 0; pass < 6; ++pass) messages[pass * size + position] = std::max(-1000.0f, std::min(1000.0f, value - replies[pass * size + position]));
                if (value >= 0) continue;
                support.push_back(position);
                selected[position] = true;
                for (int check : checks[position]) parity[check] ^= 1;
            }
            int unsatisfied = 0;
            for (int value : parity) unsatisfied += value;
            int score = unsatisfied + std::max(0, int(support.size()) - 18);
            if (score < best_score) {
                best_score = score;
                std::cout << "SCORE " << score << " weight " << support.size() << " syndrome " << unsatisfied << " trial " << trial << " iteration " << iteration << std::endl;
            }
            if (support.size() >= 8 && support.size() <= 32 && iteration % 20 == 0 && expand(support, path, seed)) return 0;
            if (unsatisfied == 0 && support.size() >= 8 && int(support.size()) < best_weight) {
                best_weight = support.size();
                std::ofstream output(path + "/bp_core_" + std::to_string(seed) + ".json");
                output << "{\"errors\":[";
                for (size_t index = 0; index < support.size(); ++index) {
                    if (index) output << ',';
                    output << support[index];
                }
                output << "]}\n";
                std::cout << "CODEWORD " << best_weight << " trial " << trial << " seconds " << elapsed << std::endl;
                if (best_weight <= 18) return 0;
                break;
            }
        }
        if (trial % 100 == 0) std::cout << "PROGRESS " << trial << " best " << best_weight << " seconds " << elapsed << std::endl;
    }
}
