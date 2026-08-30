#include <stddef.h>

void quantile_transform(const double *values, const double *knots,
                        const double *references, double *output,
                        size_t rows, size_t columns, size_t quantiles) {
    for (size_t column = 0; column < columns; ++column) {
        const double *grid = knots + column * quantiles;
        for (size_t row = 0; row < rows; ++row) {
            double value = values[row * columns + column];
            double result;
            if (value - 1e-7 < grid[0]) {
                result = 0;
            } else if (value + 1e-7 > grid[quantiles - 1]) {
                result = 1;
            } else {
                size_t lower = 0;
                size_t upper = quantiles;
                while (lower < upper) {
                    size_t middle = lower + (upper - lower) / 2;
                    if (grid[middle] <= value) lower = middle + 1;
                    else upper = middle;
                }
                size_t right = lower;
                size_t left = right - 1;
                if (grid[left] == value) {
                    lower = 0;
                    upper = left;
                    while (lower < upper) {
                        size_t middle = lower + (upper - lower) / 2;
                        if (grid[middle] < value) lower = middle + 1;
                        else upper = middle;
                    }
                    result = (references[lower] + references[left]) / 2;
                } else {
                    result = references[left] + (value - grid[left]) *
                             (references[right] - references[left]) / (grid[right] - grid[left]);
                }
            }
            output[row * columns + column] = result;
        }
    }
}
