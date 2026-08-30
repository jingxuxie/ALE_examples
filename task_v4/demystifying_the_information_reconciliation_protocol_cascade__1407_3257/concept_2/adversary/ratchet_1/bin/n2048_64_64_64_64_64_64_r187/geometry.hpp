#include <array>
constexpr int length = 2048;
constexpr int checks = 192;
constexpr int syndrome_words = 3;
constexpr int max_block_size = 64;
constexpr int matrix_rank = 187;
constexpr std::array<int, 6> group_counts = {32, 32, 32, 32, 32, 32};
constexpr std::array<int, 6> check_offsets = {0, 32, 64, 96, 128, 160};
