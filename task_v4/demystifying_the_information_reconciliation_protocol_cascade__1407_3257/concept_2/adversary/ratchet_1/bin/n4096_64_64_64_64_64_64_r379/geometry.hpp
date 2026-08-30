#include <array>
constexpr int length = 4096;
constexpr int checks = 384;
constexpr int syndrome_words = 6;
constexpr int max_block_size = 64;
constexpr int matrix_rank = 379;
constexpr std::array<int, 6> group_counts = {64, 64, 64, 64, 64, 64};
constexpr std::array<int, 6> check_offsets = {0, 64, 128, 192, 256, 320};
