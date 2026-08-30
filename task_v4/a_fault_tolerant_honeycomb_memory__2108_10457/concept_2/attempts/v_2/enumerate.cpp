#include "evaluator.cpp"
#include <chrono>
#include <fstream>
#include <iostream>
#include <queue>

struct Clause {
    std::vector<int> literals;
};

static std::vector<Clause> clauses;
static std::array<std::vector<int>, 72> incidence;
static std::unique_ptr<Samples> first_samples, second_samples, third_samples;
static uint64_t nodes = 0, leaves = 0, screened = 0;
static int best = 0;
static std::ofstream candidates;
static std::chrono::steady_clock::time_point started;

bool propagate(std::array<unsigned char, 24>& domains, std::vector<int> queue) {
    while (!queue.empty()) {
        int literal = queue.back();
        queue.pop_back();
        for (int clause_index : incidence[literal]) {
            int remaining = 0;
            int final_literal = -1;
            for (int member : clauses[clause_index].literals) {
                unsigned char domain = domains[member / 3];
                unsigned char bit = 1 << (member % 3);
                if (!(domain & bit)) {
                    remaining = 99;
                    break;
                }
                if (domain != bit) {
                    ++remaining;
                    final_literal = member;
                }
            }
            if (!remaining) return false;
            if (remaining == 1) {
                unsigned char& domain = domains[final_literal / 3];
                domain &= ~(1 << (final_literal % 3));
                if (!domain) return false;
                if (__builtin_popcount(domain) == 1)
                    queue.push_back(3 * (final_literal / 3) + __builtin_ctz(domain));
            }
        }
    }
    return true;
}

void visit(const std::array<unsigned char, 24>& domains) {
    ++nodes;
    if (nodes % 1000000 == 0) {
        double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
        std::cerr << "nodes " << nodes << " leaves " << leaves << " screened " << screened << " seconds " << seconds << std::endl;
    }
    int variable = -1;
    int smallest = 4;
    for (int cell = 0; cell < 24; ++cell) {
        int count = __builtin_popcount(domains[cell]);
        if (count > 1 && count < smallest) {
            variable = cell;
            smallest = count;
        }
    }
    if (variable == -1) {
        ++leaves;
        int axes[24];
        for (int cell = 0; cell < 24; ++cell) axes[cell] = __builtin_ctz(domains[cell]);
        if (evaluate<1>(*first_samples, axes, nullptr) < 28) return;
        if (evaluate<1>(*second_samples, axes, nullptr) < 225) return;
        ++screened;
        int correct = evaluate<1>(*third_samples, axes, nullptr);
        if (correct < 3600) return;
        candidates << "{\"score\":" << correct / 8192.0 << ",\"z_image\":[";
        for (int cell = 0; cell < 24; ++cell) candidates << (cell ? "," : "") << axes[cell];
        candidates << "]}" << std::endl;
        if (correct > best) {
            best = correct;
            std::cerr << "BEST " << best / 8192.0 << " ";
            for (int axis : axes) std::cerr << axis;
            std::cerr << std::endl;
        }
        return;
    }
    for (int axis = 0; axis < 3; ++axis) {
        if (!(domains[variable] & (1 << axis))) continue;
        auto updated = domains;
        updated[variable] = 1 << axis;
        if (propagate(updated, {3 * variable + axis})) visit(updated);
    }
}

int main() {
    load_cases(".");
    std::ifstream stream("clauses.txt");
    int count;
    stream >> count;
    clauses.resize(count);
    for (int index = 0; index < count; ++index) {
        int size;
        stream >> size;
        clauses[index].literals.resize(size);
        for (int& literal : clauses[index].literals) {
            stream >> literal;
            incidence[literal].push_back(index);
        }
    }
    first_samples.reset(make_samples(0, 8721382, 64, .32));
    second_samples.reset(make_samples(0, 57183492, 512, .32));
    third_samples.reset(make_samples(0, 623742892, 8192, .32));
    candidates.open("enumerated.jsonl");
    started = std::chrono::steady_clock::now();
    std::array<unsigned char, 24> domains;
    domains.fill(7);
    visit(domains);
    std::cerr << "DONE " << nodes << " " << leaves << " " << screened << std::endl;
}
