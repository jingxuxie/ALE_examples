#include <algorithm>
#include <cmath>
#include <cstring>
#include <chrono>
#include <limits>
#include <vector>

static constexpr int maximum = 20;
static constexpr int maximum_entries = maximum * maximum;
static constexpr int maximum_storage = maximum_entries * maximum;

using BlasFunction = void (*)(char*, char*, int*, int*, int*, double*, double*, int*, double*, int*, double*, double*, int*);
static BlasFunction blas_multiply = nullptr;

extern "C" void set_blas(BlasFunction function) {
    blas_multiply = function;
}

static void multiply(const double* __restrict first, const double* __restrict second,
                     double* __restrict result, int rows, int inner, int columns) {
    if (blas_multiply) {
        char normal = 'N';
        double alpha = 1.0, beta = 0.0;
        blas_multiply(&normal, &normal, &columns, &rows, &inner, &alpha,
                      const_cast<double*>(second), &columns, const_cast<double*>(first), &inner,
                      &beta, result, &columns);
        return;
    }
    std::fill(result, result + rows * columns, 0.0);
    for (int row = 0; row < rows; ++row) {
        for (int middle = 0; middle < inner; ++middle) {
            double value = first[row * inner + middle];
            for (int column = 0; column < columns; ++column) {
                result[row * columns + column] += value * second[middle * columns + column];
            }
        }
    }
}

static void transpose(const double* source, double* destination, int rows, int columns) {
    for (int row = 0; row < rows; ++row) {
        for (int column = 0; column < columns; ++column) {
            destination[column * rows + row] = source[row * columns + column];
        }
    }
}

static void cayley(int dimension, const double* parameters, double* rotation, double* inverse) {
    double augmented[maximum][2 * maximum] = {};
    int parameter = 0;
    for (int row = 0; row < dimension; ++row) {
        augmented[row][row] = 1.0;
        augmented[row][dimension + row] = 1.0;
        for (int column = row + 1; column < dimension; ++column) {
            augmented[row][column] = -parameters[parameter];
            augmented[column][row] = parameters[parameter++];
        }
    }
    for (int pivot = 0; pivot < dimension; ++pivot) {
        int best = pivot;
        for (int row = pivot + 1; row < dimension; ++row) {
            if (std::abs(augmented[row][pivot]) > std::abs(augmented[best][pivot])) best = row;
        }
        if (best != pivot) {
            for (int column = pivot; column < 2 * dimension; ++column)
                std::swap(augmented[pivot][column], augmented[best][column]);
        }
        double scale = 1.0 / augmented[pivot][pivot];
        for (int column = pivot; column < 2 * dimension; ++column) augmented[pivot][column] *= scale;
        for (int row = 0; row < dimension; ++row) {
            if (row == pivot) continue;
            double value = augmented[row][pivot];
            for (int column = pivot + 1; column < 2 * dimension; ++column)
                augmented[row][column] -= value * augmented[pivot][column];
            augmented[row][pivot] = 0.0;
        }
    }
    for (int row = 0; row < dimension; ++row) {
        for (int column = 0; column < dimension; ++column) {
            inverse[row * dimension + column] = augmented[row][dimension + column];
            rotation[row * dimension + column] = 2 * augmented[row][dimension + column] - (row == column);
        }
    }
}

extern "C" double evaluate(int dimension, int rank, const double* one_body, const double* factors,
                           double smoothing, const double* parameters, double* gradient) {
    int entries = dimension * dimension;
    int split = dimension * (dimension - 1) / 2;
    double orbital[maximum_entries], auxiliary[maximum_entries];
    double orbital_inverse[maximum_entries], auxiliary_inverse[maximum_entries];
    double orbital_transpose[maximum_entries], auxiliary_transpose[maximum_entries];
    double body_right[maximum_entries], body_rotated[maximum_entries], body_gradient[maximum_entries];
    double factors_right[maximum_storage], factors_rotated[maximum_storage];
    double factors_interleaved[maximum_storage], rotated_interleaved[maximum_storage];
    double mixed[maximum_storage], mixed_gradient[maximum_storage], factor_gradient[maximum_storage];
    double gradient_orbital[maximum_entries], gradient_auxiliary[maximum_entries];
    double temporary[maximum_entries], temporary_second[maximum_entries];
    double transposed_factors[maximum_storage];
    cayley(dimension, parameters, orbital, orbital_inverse);
    cayley(rank, parameters + split, auxiliary, auxiliary_inverse);
    transpose(orbital, orbital_transpose, dimension, dimension);
    transpose(auxiliary, auxiliary_transpose, rank, rank);
    multiply(one_body, orbital, body_right, dimension, dimension, dimension);
    multiply(orbital_transpose, body_right, body_rotated, dimension, dimension, dimension);
    multiply(factors, orbital, factors_right, rank * dimension, dimension, dimension);
    for (int row = 0; row < dimension; ++row) {
        for (int factor = 0; factor < rank; ++factor) {
            for (int column = 0; column < dimension; ++column) {
                factors_interleaved[(row * rank + factor) * dimension + column] = factors_right[(factor * dimension + row) * dimension + column];
            }
        }
    }
    multiply(orbital_transpose, factors_interleaved, rotated_interleaved, dimension, dimension, rank * dimension);
    for (int row = 0; row < dimension; ++row) {
        for (int factor = 0; factor < rank; ++factor) {
            for (int column = 0; column < dimension; ++column) {
                factors_rotated[(factor * dimension + row) * dimension + column] = rotated_interleaved[(row * rank + factor) * dimension + column];
            }
        }
    }
    multiply(auxiliary, factors_rotated, mixed, rank, rank, entries);
    double value = 0.0;
    double squared_smoothing = smoothing * smoothing;
    for (int entry = 0; entry < entries; ++entry) {
        double smooth = std::sqrt(body_rotated[entry] * body_rotated[entry] + squared_smoothing);
        value += smooth;
        body_gradient[entry] = body_rotated[entry] / smooth;
    }
    for (int factor = 0; factor < rank; ++factor) {
        double weight = 0.0;
        int offset = factor * entries;
        for (int entry = 0; entry < entries; ++entry) {
            double smooth = std::sqrt(mixed[offset + entry] * mixed[offset + entry] + squared_smoothing);
            weight += smooth;
            mixed_gradient[offset + entry] = mixed[offset + entry] / smooth;
        }
        value += 0.5 * weight * weight;
        for (int entry = 0; entry < entries; ++entry) mixed_gradient[offset + entry] *= weight;
    }
    multiply(auxiliary_transpose, mixed_gradient, factor_gradient, rank, rank, entries);
    multiply(body_right, body_gradient, gradient_orbital, dimension, dimension, dimension);
    multiply(factors_interleaved, factor_gradient, temporary, dimension, rank * dimension, dimension);
    for (int entry = 0; entry < entries; ++entry) gradient_orbital[entry] += temporary[entry];
    transpose(orbital_inverse, orbital_transpose, dimension, dimension);
    multiply(orbital_transpose, gradient_orbital, temporary, dimension, dimension, dimension);
    multiply(temporary, orbital_transpose, temporary_second, dimension, dimension, dimension);
    int parameter = 0;
    for (int row = 0; row < dimension; ++row) {
        for (int column = row + 1; column < dimension; ++column) {
            gradient[parameter++] = 4 * (temporary_second[row * dimension + column] - temporary_second[column * dimension + row]);
        }
    }
    transpose(factors_rotated, transposed_factors, rank, entries);
    multiply(mixed_gradient, transposed_factors, gradient_auxiliary, rank, entries, rank);
    transpose(auxiliary_inverse, auxiliary_transpose, rank, rank);
    multiply(auxiliary_transpose, gradient_auxiliary, temporary, rank, rank, rank);
    multiply(temporary, auxiliary_transpose, temporary_second, rank, rank, rank);
    for (int row = 0; row < rank; ++row) {
        for (int column = row + 1; column < rank; ++column) {
            gradient[parameter++] = 2 * (temporary_second[row * rank + column] - temporary_second[column * rank + row]);
        }
    }
    return value;
}

using OptimizerFunction = void (*)(int*, int*, double*, double*, double*, int*, double*, double*,
                                  double*, double*, double*, int*, char*, int*, char*, int*, int*,
                                  double*, int*, std::size_t, std::size_t);
static OptimizerFunction optimizer = nullptr;

extern "C" void set_optimizer(OptimizerFunction function) {
    optimizer = function;
}

extern "C" double optimize(int dimension, int rank, const double* one_body, const double* factors,
                           double smoothing, int max_iterations, int corrections, double seconds,
                           double* parameters, int* statistics) {
    int size = dimension * (dimension - 1) / 2 + rank * (rank - 1) / 2;
    auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(seconds);
    std::vector<double> bounds(size, 0.0), gradient(size, 0.0), best_parameters(size, 0.0);
    std::vector<int> bound_types(size, 0), integer_work(3 * size, 0);
    std::vector<double> work(2 * corrections * size + 5 * size + 11 * corrections * corrections + 8 * corrections, 0.0);
    double tolerance = 1e-11 / std::numeric_limits<double>::epsilon();
    double gradient_tolerance = 1e-6;
    double value = 0.0, best_value = std::numeric_limits<double>::infinity();
    int print_level = -1, max_linesearch = 30;
    char task[60], character_state[60];
    std::fill(task, task + 60, ' ');
    std::fill(character_state, character_state + 60, ' ');
    std::memcpy(task, "START", 5);
    int logical_state[4] = {}, integer_state[44] = {};
    double double_state[29] = {};
    int iterations = 0, evaluations = 0;
    while (true) {
        optimizer(&size, &corrections, parameters, bounds.data(), bounds.data(), bound_types.data(),
                  &value, gradient.data(), &tolerance, &gradient_tolerance, work.data(), integer_work.data(),
                  task, &print_level, character_state, logical_state, integer_state, double_state,
                  &max_linesearch, 60, 60);
        if (std::chrono::steady_clock::now() >= deadline) {
            std::copy(best_parameters.begin(), best_parameters.end(), parameters);
            value = best_value;
            break;
        }
        if (task[0] == 'F' && task[1] == 'G') {
            value = evaluate(dimension, rank, one_body, factors, smoothing, parameters, gradient.data());
            ++evaluations;
            if (value < best_value) {
                best_value = value;
                std::copy(parameters, parameters + size, best_parameters.begin());
            }
        } else if (std::memcmp(task, "NEW_X", 5) == 0) {
            ++iterations;
            if (iterations >= max_iterations) break;
        } else {
            break;
        }
    }
    statistics[0] = iterations;
    statistics[1] = evaluations;
    return value;
}
