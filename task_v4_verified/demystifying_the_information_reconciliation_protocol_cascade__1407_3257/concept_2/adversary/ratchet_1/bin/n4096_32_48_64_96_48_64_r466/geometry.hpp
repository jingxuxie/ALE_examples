#include <array>
constexpr int length = 4096;
constexpr int checks = 471;
constexpr int syndrome_words = 8;
constexpr int max_block_size = 96;
constexpr int matrix_rank = 466;
constexpr std::array<int, 6> group_counts = {128, 86, 64, 43, 86, 64};
constexpr std::array<int, 6> check_offsets = {0, 128, 214, 278, 321, 407};
