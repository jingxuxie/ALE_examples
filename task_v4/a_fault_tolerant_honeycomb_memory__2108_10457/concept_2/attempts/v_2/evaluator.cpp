#include <algorithm>
#include <array>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <random>
#include <vector>

struct Case {
    unsigned slots, words;
    std::vector<unsigned> cells;
    std::vector<std::array<uint64_t, 7>> columns;
};

struct Samples {
    int scale;
    std::vector<std::vector<unsigned>> records;
};

static Case cases[3];

extern "C" void load_cases(const char* directory) {
    for (int scale = 0; scale < 3; ++scale) {
        char filename[4096];
        snprintf(filename, sizeof(filename), "%s/case_%d.bin", directory, scale + 1);
        FILE* stream = fopen(filename, "rb");
        Case& data = cases[scale];
        fread(&data.slots, 4, 1, stream);
        fread(&data.words, 4, 1, stream);
        data.cells.resize(data.slots);
        data.columns.resize(3 * data.slots);
        for (unsigned slot = 0; slot < data.slots; ++slot) {
            fread(&data.cells[slot], 4, 1, stream);
            for (unsigned axis = 0; axis < 3; ++axis)
                fread(data.columns[3 * slot + axis].data(), 8, data.words, stream);
        }
        fclose(stream);
    }
}

extern "C" Samples* make_samples(int scale, uint64_t seed, int count, double density) {
    auto* samples = new Samples;
    samples->scale = scale;
    samples->records.resize(count);
    std::mt19937_64 generator(seed);
    uint64_t threshold = static_cast<uint64_t>(density * 18446744073709551616.0);
    for (auto& record : samples->records)
        for (unsigned slot = 0; slot < cases[scale].slots; ++slot)
            if (generator() < threshold) record.push_back(slot);
    return samples;
}

extern "C" Samples* explicit_samples(int scale, int count, const unsigned* offsets, const unsigned* slots) {
    auto* samples = new Samples;
    samples->scale = scale;
    for (int index = 0; index < count; ++index)
        samples->records.emplace_back(slots + offsets[index], slots + offsets[index + 1]);
    return samples;
}

extern "C" void free_samples(Samples* samples) { delete samples; }

template<int Words>
int evaluate(const Samples& samples, const int* axes, unsigned char* output) {
    const auto& data = cases[samples.scale];
    std::vector<std::array<uint64_t, Words>> selected(data.slots);
    for (unsigned slot = 0; slot < data.slots; ++slot)
        std::copy_n(data.columns[3 * slot + axes[data.cells[slot]]].begin(), Words, selected[slot].begin());
    std::array<std::array<uint64_t, Words>, Words * 64> basis;
    std::array<unsigned, Words * 64> tags{};
    unsigned tag = 0;
    int correct = 0;
    for (const auto& record : samples.records) {
        ++tag;
        bool failed = false;
        for (unsigned slot : record) {
            auto vector = selected[slot];
            for (int word = Words - 1; word >= 0; --word) {
                while (vector[word]) {
                    int pivot = 64 * word + 63 - __builtin_clzll(vector[word]);
                    if (pivot < 4) {
                        failed = true;
                        goto finished;
                    }
                    if (tags[pivot] != tag) {
                        tags[pivot] = tag;
                        basis[pivot] = vector;
                        goto next_column;
                    }
                    for (int part = 0; part <= word; ++part)
                        vector[part] ^= basis[pivot][part];
                }
            }
            next_column:;
        }
        finished:
        correct += !failed;
        if (output) output[tag - 1] = !failed;
    }
    return correct;
}

extern "C" int score(const Samples* samples, const int* axes, unsigned char* output) {
    if (samples->scale == 0) return evaluate<1>(*samples, axes, output);
    if (samples->scale == 1) return evaluate<4>(*samples, axes, output);
    return evaluate<7>(*samples, axes, output);
}
