#include "evaluator.cpp"
#include <chrono>
#include <fstream>
#include <iostream>

#ifndef SAMPLE_COUNT
#define SAMPLE_COUNT 64
#endif
static constexpr int Count = SAMPLE_COUNT;
static std::array<std::array<uint64_t, 64>, Count> bases{};
static std::array<uint64_t, (Count + 63) / 64> active;
static std::array<std::array<unsigned char, 24>, Count> flags{};
static int remaining = Count;
static int cutoff = 28;
static int axes[24];
static uint64_t nodes = 0, leaves = 0;
static std::unique_ptr<Samples> validation, final_samples;
static std::ofstream results;
static std::chrono::steady_clock::time_point started;
static int best = 0;
static double density = .32;
static uint64_t seed = 8721382;
static std::string tag = "bounded";
static int order_style = 0;
static int cross_order[24] = {0, 1, 2, 3, 4, 5, 6, 12, 18, 7, 13, 19, 8, 14, 20, 9, 15, 21, 10, 16, 22, 11, 17, 23};
static std::string restriction;
static std::ofstream raw_results;
static bool canonical = false;

void visit(int depth) {
    ++nodes;
    if (nodes % 1000000 == 0) {
        std::cerr << "nodes " << nodes << " leaves " << leaves << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << " prefix ";
        for (int index = 0; index < depth; ++index) std::cerr << axes[order_style ? cross_order[index] : index];
        std::cerr << std::endl;
    }
    if (depth == 24) {
        ++leaves;
        if (raw_results.is_open()) {
            for (int axis : axes) raw_results << axis;
            raw_results << " " << remaining << '\n';
        }
        if (evaluate<1>(*validation, axes, nullptr) < (density < .31 ? 250 : 140)) return;
        int score = evaluate<1>(*final_samples, axes, nullptr);
        if (score < (density < .31 ? 4000 : 2300)) return;
        results << "{\"score\":" << score / 8192.0 << ",\"z_image\":[";
        for (int cell = 0; cell < 24; ++cell) results << (cell ? "," : "") << axes[cell];
        results << "]}" << std::endl;
        if (score > best) {
            best = score;
            std::cerr << "BEST " << score / 8192.0 << " ";
            for (int axis : axes) std::cerr << axis;
            std::cerr << std::endl;
        }
        return;
    }
    int cell = order_style ? cross_order[depth] : depth;
    for (int axis = 0; axis < 3; ++axis) {
        if (!restriction.empty() && restriction[cell] != '?' && restriction[cell] != '0' + axis) continue;
        if (canonical && cell > 0 && cell % 3 == 0 && axis < axes[0]) continue;
        std::array<std::pair<unsigned char, unsigned char>, 6 * Count> undo;
        int undo_count = 0;
        auto previous_active = active;
        int previous_remaining = remaining;
        axes[cell] = axis;
        for (int block = 0; block < (Count + 63) / 64; ++block) {
          uint64_t pending = active[block];
          while (pending) {
            int sample = block * 64 + __builtin_ctzll(pending);
            pending &= pending - 1;
            int mask = flags[sample][cell];
            while (mask) {
                int phase = __builtin_ctz(mask);
                mask &= mask - 1;
                uint64_t vector = cases[0].columns[3 * (phase * 24 + cell) + axis][0];
                while (vector >= 16) {
                    int pivot = 63 - __builtin_clzll(vector);
                    if (!bases[sample][pivot]) {
                        bases[sample][pivot] = vector;
                        undo[undo_count++] = {sample, pivot};
                        vector = 0;
                        break;
                    }
                    vector ^= bases[sample][pivot];
                }
                if (vector) {
                    active[block] &= ~(uint64_t(1) << (sample % 64));
                    --remaining;
                    break;
                }
            }
            if (remaining < cutoff) break;
          }
          if (remaining < cutoff) break;
        }
        if (remaining >= cutoff) visit(depth + 1);
        for (int index = 0; index < undo_count; ++index)
            bases[undo[index].first][undo[index].second] = 0;
        active = previous_active;
        remaining = previous_remaining;
    }
}

int main(int argc, char** argv) {
    if (argc > 1) cutoff = atoi(argv[1]);
    if (argc > 2) density = atof(argv[2]);
    if (argc > 3) seed = strtoull(argv[3], nullptr, 10);
    if (argc > 4) tag = argv[4];
    if (argc > 5) order_style = atoi(argv[5]);
    load_cases(".");
    std::unique_ptr<Samples> training(make_samples(0, seed, Count, density));
    validation.reset(make_samples(0, 57183492, 512, density));
    final_samples.reset(make_samples(0, 623742892, 8192, density));
    for (int sample = 0; sample < Count; ++sample)
        for (unsigned slot : training->records[sample])
            flags[sample][slot % 24] |= 1 << (slot / 24);
    if (argc > 6 && std::string(argv[6]) != "-") {
        std::ifstream support_stream(argv[6], std::ios::binary);
        support_stream.read(reinterpret_cast<char*>(flags.data()), sizeof(flags));
        if (support_stream.gcount() != sizeof(flags)) return 2;
    }
    active.fill(~uint64_t(0));
    if (Count % 64) active.back() = (uint64_t(1) << (Count % 64)) - 1;
    results.open(tag + ".jsonl");
    if (argc > 7) {
        restriction = argv[7];
        if (restriction.size() != 24) return 2;
        raw_results.open(tag + ".raw");
    }
    if (argc > 8) canonical = atoi(argv[8]);
    started = std::chrono::steady_clock::now();
    visit(0);
    std::cerr << "DONE " << nodes << " " << leaves << std::endl;
}
