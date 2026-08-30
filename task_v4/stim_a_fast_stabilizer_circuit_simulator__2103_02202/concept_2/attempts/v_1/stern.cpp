#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

using Word = uint64_t;

struct alignas(64) Row {
    Word words[8];
};

struct Column {
    Word words[3];
    uint32_t key;
};

struct Pair {
    Word words[3];
    uint32_t indices;
    int next;
};

static Word random_state;

Word random_word() {
    random_state ^= random_state >> 12;
    random_state ^= random_state << 25;
    random_state ^= random_state >> 27;
    return random_state * 2685821657736338717ULL;
}

int main(int argc, char **argv) {
    const std::string directory = argc > 1 ? argv[1] : ".";
    const int key_bits = argc > 2 ? std::atoi(argv[2]) : 18;
    const double time_limit = argc > 3 ? std::atof(argv[3]) : 2400;
    random_state = argc > 4 ? std::strtoull(argv[4], nullptr, 10) : 8719231127ULL;
    const int pivot_count = 192 - key_bits;
    const int free_count = 512 - pivot_count;
    const int left_count = free_count / 2;
    const int tail_bits = pivot_count - 128;
    const Word tail_mask = (Word(1) << tail_bits) - 1;
    const Word parity_mask = Word(1) << 63;
    const int table_size = 1 << key_bits;
    Row original[193]{};
    Row reduced[193];
    std::array<std::array<Word, 3>, 512> input_columns{};
    std::array<int, 512> input_logical{};
    std::ifstream input(directory + "/matrix.txt");
    for (int column = 0; column < 512; ++column) {
        std::string text;
        int logical;
        if (!(input >> text >> logical)) {
            std::cerr << "Invalid matrix input\n";
            return 2;
        }
        for (int block = 0; block < 3; ++block) {
            input_columns[column][block] = std::stoull(text.substr(32 - block * 16, 16), nullptr, 16);
        }
        input_logical[column] = logical;
        for (int row = 0; row < 192; ++row) {
            if ((input_columns[column][row / 64] >> (row % 64)) & 1) {
                original[row].words[column / 64] |= Word(1) << (column % 64);
            }
        }
        if (logical) original[192].words[column / 64] |= Word(1) << (column % 64);
    }
    std::array<int, 512> permutation;
    std::iota(permutation.begin(), permutation.end(), 0);
    std::vector<int> heads(table_size);
    std::vector<Pair> pairs(left_count * (left_count - 1) / 2);
    std::vector<Column> columns(free_count);
    int best_weight = 193;
    uint64_t iterations = 0;
    uint64_t candidate_count = 0;
    const auto start = std::chrono::steady_clock::now();
    auto elapsed = [&]() {
        return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    };
    while (elapsed() < time_limit) {
        ++iterations;
        for (int index = 511; index > 0; --index) {
            const int other = random_word() % (index + 1);
            std::swap(permutation[index], permutation[other]);
        }
        std::memcpy(reduced, original, sizeof(reduced));
        bool independent = true;
        for (int pivot = 0; pivot < pivot_count; ++pivot) {
            const int column = permutation[pivot];
            const int block = column / 64;
            const Word mask = Word(1) << (column % 64);
            int selected_row = pivot;
            while (selected_row < 192 && !(reduced[selected_row].words[block] & mask)) ++selected_row;
            if (selected_row == 192) {
                independent = false;
                break;
            }
            if (selected_row != pivot) std::swap(reduced[pivot], reduced[selected_row]);
            for (int row = 0; row < 193; ++row) {
                if (row != pivot && (reduced[row].words[block] & mask)) {
                    for (int word = 0; word < 8; ++word) {
                        reduced[row].words[word] ^= reduced[pivot].words[word];
                    }
                }
            }
        }
        if (!independent) continue;
        for (int index = 0; index < free_count; ++index) {
            const int column = permutation[pivot_count + index];
            const int block = column / 64;
            const int offset = column % 64;
            Column &value = columns[index];
            for (int word = 0; word < 3; ++word) {
                Word bits = 0;
                for (int bit = 0; bit < 64; ++bit) {
                    bits |= ((reduced[word * 64 + bit].words[block] >> offset) & 1) << bit;
                }
                value.words[word] = bits;
            }
            value.key = value.words[2] >> tail_bits;
            value.words[2] &= tail_mask;
            value.words[2] |= ((reduced[192].words[block] >> offset) & 1) << 63;
        }
        std::fill(heads.begin(), heads.end(), -1);
        int pair_count = 0;
        for (int first = 0; first < left_count; ++first) {
            for (int second = first + 1; second < left_count; ++second) {
                const uint32_t key = columns[first].key ^ columns[second].key;
                Pair &pair = pairs[pair_count];
                for (int word = 0; word < 3; ++word) {
                    pair.words[word] = columns[first].words[word] ^ columns[second].words[word];
                }
                pair.indices = first | (second << 16);
                pair.next = heads[key];
                heads[key] = pair_count++;
            }
        }
        for (int first = left_count; first < free_count; ++first) {
            for (int second = first + 1; second < free_count; ++second) {
                const uint32_t key = columns[first].key ^ columns[second].key;
                Word right_words[3];
                for (int word = 0; word < 3; ++word) {
                    right_words[word] = columns[first].words[word] ^ columns[second].words[word];
                }
                for (int pair_index = heads[key]; pair_index >= 0; pair_index = pairs[pair_index].next) {
                    ++candidate_count;
                    const Pair &pair = pairs[pair_index];
                    Word syndrome[3];
                    syndrome[2] = pair.words[2] ^ right_words[2];
                    if (!(syndrome[2] & parity_mask)) continue;
                    syndrome[2] &= tail_mask;
                    syndrome[0] = pair.words[0] ^ right_words[0];
                    int weight = 4 + __builtin_popcountll(syndrome[0]);
                    if (weight >= best_weight) continue;
                    syndrome[1] = pair.words[1] ^ right_words[1];
                    weight += __builtin_popcountll(syndrome[1]);
                    if (weight >= best_weight) continue;
                    weight += __builtin_popcountll(syndrome[2]);
                    if (weight >= best_weight) continue;
                    std::vector<int> support{
                        permutation[pivot_count + (pair.indices & 65535)],
                        permutation[pivot_count + (pair.indices >> 16)],
                        permutation[pivot_count + first],
                        permutation[pivot_count + second]
                    };
                    for (int pivot = 0; pivot < pivot_count; ++pivot) {
                        if ((syndrome[pivot / 64] >> (pivot % 64)) & 1) support.push_back(permutation[pivot]);
                    }
                    std::sort(support.begin(), support.end());
                    std::array<Word, 3> check{};
                    int logical = 0;
                    for (int column : support) {
                        for (int word = 0; word < 3; ++word) check[word] ^= input_columns[column][word];
                        logical ^= input_logical[column];
                    }
                    if (check[0] || check[1] || check[2] || logical != 1 || weight != int(support.size())) {
                        std::cerr << "Internal verification failed\n";
                        return 3;
                    }
                    best_weight = weight;
                    std::ofstream output(directory + "/witness.json");
                    output << "{\"faults\": [";
                    for (size_t index = 0; index < support.size(); ++index) {
                        if (index) output << ", ";
                        output << support[index];
                    }
                    output << "]}\n";
                    output.close();
                    std::cout << "BEST weight=" << weight << " iteration=" << iterations
                              << " seconds=" << elapsed() << " support=";
                    for (int column : support) std::cout << column << ',';
                    std::cout << std::endl;
                    if (weight <= 20) return 0;
                }
            }
        }
        if (iterations % 10000 == 0) {
            std::cout << "PROGRESS iterations=" << iterations << " seconds=" << elapsed()
                      << " candidates=" << candidate_count << " best=" << best_weight << std::endl;
        }
    }
    std::cout << "TIMEOUT iterations=" << iterations << " seconds=" << elapsed()
              << " candidates=" << candidate_count << " best=" << best_weight << std::endl;
    return 1;
}
