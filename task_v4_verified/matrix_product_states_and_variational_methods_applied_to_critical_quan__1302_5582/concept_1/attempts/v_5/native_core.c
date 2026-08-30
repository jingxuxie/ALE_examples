#include <math.h>
#include <stdlib.h>
#include <string.h>

typedef void (*gemm_function)(char *, char *, int *, int *, int *, double *,
                              double *, int *, double *, int *, double *, double *, int *);
typedef void (*syev_function)(char *, char *, int *, double *, int *, double *,
                              double *, int *, int *);

static void site_action(int left, int physical, int right, const double *diagonal,
                        double *left_position, double *position, double *right_position,
                        double left_coupling, double right_coupling, const double *vector,
                        double *image, double *physical_input, double *physical_output,
                        double *position_tensor, gemm_function gemm) {
    int size = left * physical * right;
    int physical_stride = left * right;
    int combined_right = physical * right;
    int combined_left = left * physical;
    char normal = 'N';
    double unity = 1.0;
    double zero = 0.0;
    for (int physical_index = 0; physical_index < physical; physical_index++) {
        for (int left_index = 0; left_index < left; left_index++) {
            memcpy(physical_input + (physical_index * left + left_index) * right,
                   vector + (left_index * physical + physical_index) * right,
                   right * sizeof(double));
        }
    }
    gemm(&normal, &normal, &physical_stride, &physical, &physical, &unity,
         physical_input, &physical_stride, position, &physical, &zero,
         physical_output, &physical_stride);
    for (int left_index = 0; left_index < left; left_index++) {
        for (int physical_index = 0; physical_index < physical; physical_index++) {
            memcpy(position_tensor + (left_index * physical + physical_index) * right,
                   physical_output + (physical_index * left + left_index) * right,
                   right * sizeof(double));
        }
    }
    for (int index = 0; index < size; index++) image[index] = diagonal[index] * vector[index];
    if (left_coupling != 0.0) {
        double coefficient = -left_coupling;
        gemm(&normal, &normal, &combined_right, &left, &left, &coefficient,
             position_tensor, &combined_right, left_position, &left, &unity,
             image, &combined_right);
    }
    if (right_coupling != 0.0) {
        double coefficient = -right_coupling;
        gemm(&normal, &normal, &right, &combined_left, &right, &coefficient,
             right_position, &right, position_tensor, &right, &unity, image, &right);
    }
}

double site_lowest(int left, int physical, int right, const double *diagonal,
                   double *left_position, double *position, double *right_position,
                   double left_coupling, double right_coupling, const double *initial,
                   double tolerance, int steps, double *output,
                   void *gemm_pointer, void *syev_pointer) {
    gemm_function gemm = (gemm_function)gemm_pointer;
    syev_function syev = (syev_function)syev_pointer;
    int size = left * physical * right;
    int capacity = steps;
    if (capacity < 1 || capacity > 32) return NAN;
    size_t allocation = (size_t)(2 * capacity + 8) * size
                        + 2 * capacity * capacity + 5 * capacity;
    double *storage = (double *)calloc(allocation, sizeof(double));
    if (!storage) return NAN;
    double *basis = storage;
    double *images = basis + (size_t)capacity * size;
    double *image = images + (size_t)capacity * size;
    double *residual = image + size;
    double *direction = residual + size;
    double *physical_input = direction + size;
    double *physical_output = physical_input + size;
    double *position_tensor = physical_output + size;
    double *projected = position_tensor + size;
    double *eigenvectors = projected + capacity * capacity;
    double *eigenvalues = eigenvectors + capacity * capacity;
    double *work = eigenvalues + capacity;
    double norm = 0.0;
    for (int index = 0; index < size; index++) norm += initial[index] * initial[index];
    norm = sqrt(norm);
    if (!(norm > 0.0)) { free(storage); return NAN; }
    for (int index = 0; index < size; index++) basis[index] = initial[index] / norm;
    site_action(left, physical, right, diagonal, left_position, position, right_position,
                left_coupling, right_coupling, basis, images, physical_input,
                physical_output, position_tensor, gemm);
    double energy = 0.0;
    for (int index = 0; index < size; index++) energy += basis[index] * images[index];
    projected[0] = energy;
    int count = 1;
    char vectors = 'V';
    char lower = 'L';
    int work_size = 4 * capacity;
    for (int iteration = 0; iteration < steps; iteration++) {
        memcpy(eigenvectors, projected, capacity * capacity * sizeof(double));
        int status = 0;
        syev(&vectors, &lower, &count, eigenvectors, &capacity, eigenvalues, work, &work_size, &status);
        if (status != 0) { energy = NAN; break; }
        energy = eigenvalues[0];
        memset(output, 0, size * sizeof(double));
        memset(image, 0, size * sizeof(double));
        for (int column = 0; column < count; column++) {
            double weight = eigenvectors[column];
            const double *basis_column = basis + (size_t)column * size;
            const double *image_column = images + (size_t)column * size;
            for (int index = 0; index < size; index++) {
                output[index] += weight * basis_column[index];
                image[index] += weight * image_column[index];
            }
        }
        double residual_norm = 0.0;
        for (int index = 0; index < size; index++) {
            residual[index] = image[index] - energy * output[index];
            residual_norm += residual[index] * residual[index];
        }
        if (residual_norm < tolerance * tolerance || iteration + 1 == steps) break;
        for (int index = 0; index < size; index++) {
            direction[index] = residual[index] / fmax(diagonal[index] - energy, 1e-3);
        }
        for (int repeat = 0; repeat < 2; repeat++) {
            for (int column = 0; column < count; column++) {
                const double *basis_column = basis + (size_t)column * size;
                double overlap = 0.0;
                for (int index = 0; index < size; index++) overlap += basis_column[index] * direction[index];
                for (int index = 0; index < size; index++) direction[index] -= overlap * basis_column[index];
            }
        }
        norm = 0.0;
        for (int index = 0; index < size; index++) norm += direction[index] * direction[index];
        norm = sqrt(norm);
        if (norm < 1e-13) break;
        double *new_basis = basis + (size_t)count * size;
        double *new_image = images + (size_t)count * size;
        for (int index = 0; index < size; index++) new_basis[index] = direction[index] / norm;
        site_action(left, physical, right, diagonal, left_position, position, right_position,
                    left_coupling, right_coupling, new_basis, new_image, physical_input,
                    physical_output, position_tensor, gemm);
        for (int column = 0; column <= count; column++) {
            double overlap = 0.0;
            const double *basis_column = basis + (size_t)column * size;
            for (int index = 0; index < size; index++) overlap += basis_column[index] * new_image[index];
            projected[count + column * capacity] = overlap;
        }
        count++;
    }
    free(storage);
    return energy;
}
