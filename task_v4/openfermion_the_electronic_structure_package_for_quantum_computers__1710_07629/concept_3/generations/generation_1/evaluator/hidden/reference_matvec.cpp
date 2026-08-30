#include <algorithm>
#include <cstdint>

static void transpose_values(const double* source, double* destination, int rows, int columns) {
    for (int first = 0; first < rows; first += 32) {
        for (int second = 0; second < columns; second += 32) {
            for (int row = first; row < std::min(rows, first + 32); ++row) {
                for (int column = second; column < std::min(columns, second + 32); ++column) {
                    destination[column * rows + row] = source[row * columns + column];
                }
            }
        }
    }
}

static void multiply_spin(int rows, int width, const std::int32_t* offsets,
                          const std::int32_t* columns, const double* values,
                          const double* vector, double* result) {
    for (int row = 0; row < rows; ++row) {
        double* destination = result + row * width;
        for (int index = offsets[row]; index < offsets[row + 1]; ++index) {
            const double* source = vector + columns[index] * width;
            double value = values[index];
            for (int column = 0; column < width; ++column) {
                destination[column] += value * source[column];
            }
        }
    }
}

extern "C" void apply_sector(int up_size, int down_size,
    const std::int32_t* up_offsets, const std::int32_t* up_columns, const double* up_values,
    const std::int32_t* down_offsets, const std::int32_t* down_columns, const double* down_values,
    const double* diagonal, const double* vector, double* result,
    double* transposed, double* product) {
    std::int64_t dimension = std::int64_t(up_size) * down_size;
    for (std::int64_t index = 0; index < dimension; ++index) {
        result[index] = diagonal[index] * vector[index];
        product[index] = 0.0;
    }
    multiply_spin(up_size, down_size, up_offsets, up_columns, up_values, vector, result);
    transpose_values(vector, transposed, up_size, down_size);
    multiply_spin(down_size, up_size, down_offsets, down_columns, down_values, transposed, product);
    transpose_values(product, transposed, down_size, up_size);
    for (std::int64_t index = 0; index < dimension; ++index) {
        result[index] += transposed[index];
    }
}
