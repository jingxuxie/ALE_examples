#include <array>
constexpr int length = 4096;
constexpr int checks = 768;
constexpr int syndrome_words = 12;
constexpr int max_block_size = 32;
constexpr int matrix_rank = 763;
constexpr std::array<int, 6> group_counts = {128, 128, 128, 128, 128, 128};
constexpr std::array<int, 6> check_offsets = {0, 128, 256, 384, 512, 640};
