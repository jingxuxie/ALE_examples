#include "evaluator.cpp"
#include <chrono>
#include <fstream>
#include <iostream>

struct Basis {
    std::array<uint64_t, 64> pivots{};
    int logical_rank = 0;
    bool add(uint64_t vector, int limit) {
        while (vector) {
            int pivot = 63 - __builtin_clzll(vector);
            if (!pivots[pivot]) {
                pivots[pivot] = vector;
                if (pivot < 4) ++logical_rank;
                return logical_rank <= limit;
            }
            vector ^= pivots[pivot];
        }
        return true;
    }
};

static uint64_t nodes = 0, leaves = 0;
static int rank_limit = 2;
static int protected_mask = 0;
static int axis_order = 0;
static int axes[24];
static std::unique_ptr<Samples> training;
static std::unique_ptr<Samples> screening;
static std::ofstream results;
static std::ofstream all_patterns;
static std::chrono::steady_clock::time_point started;
static double best = 0;

void visit(int depth, const Basis& basis) {
    ++nodes;
    if (nodes % 10000000 == 0) {
        std::cerr << "nodes " << nodes << " leaves " << leaves << " seconds " << std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count() << std::endl;
    }
    if (depth == 24) {
        ++leaves;
        for (int axis : axes) all_patterns << axis;
        all_patterns << '\n';
        if (evaluate<1>(*screening, axes, nullptr) < 12) return;
        double score = evaluate<1>(*training, axes, nullptr) / 4096.0;
        if (score < .3) return;
        results << "{\"score\":" << score << ",\"rank\":" << basis.logical_rank << ",\"z_image\":[";
        for (int cell = 0; cell < 24; ++cell) results << (cell ? "," : "") << axes[cell];
        results << "]}" << std::endl;
        if (score > best) {
            best = score;
            std::cerr << "BEST " << score << " ";
            for (int axis : axes) std::cerr << axis;
            std::cerr << std::endl;
        }
        return;
    }
    int cell = axis_order ? (depth / 8) * 2 + ((depth % 8) / 2) * 6 + depth % 2 : depth;
    for (int axis = 0; axis < 3; ++axis) {
        Basis updated = basis;
        bool valid = true;
        for (int phase = 0; phase < 6; ++phase)
            if (!updated.add(protected_mask ? ((cases[0].columns[(phase * 24 + cell) * 3 + axis][0] >> 4) << 4) | (__builtin_parityll(cases[0].columns[(phase * 24 + cell) * 3 + axis][0] & protected_mask)) : cases[0].columns[(phase * 24 + cell) * 3 + axis][0], rank_limit)) {
                valid = false;
                break;
            }
        if (valid) {
            axes[cell] = axis;
            visit(depth + 1, updated);
        }
    }
}

int main(int argc, char** argv) {
    if (argc > 1) rank_limit = atoi(argv[1]);
    if (argc > 2) protected_mask = atoi(argv[2]);
    if (argc > 3) axis_order = atoi(argv[3]);
    load_cases(".");
    training.reset(make_samples(0, 88283614, 4096, .32));
    screening.reset(make_samples(0, 42862382, 64, .32));
    results.open("protected_" + std::to_string(rank_limit) + "_" + std::to_string(protected_mask) + ".jsonl");
    all_patterns.open("protected_" + std::to_string(rank_limit) + "_" + std::to_string(protected_mask) + ".txt");
    started = std::chrono::steady_clock::now();
    visit(0, Basis());
    std::cerr << "DONE " << nodes << " " << leaves << std::endl;
}
