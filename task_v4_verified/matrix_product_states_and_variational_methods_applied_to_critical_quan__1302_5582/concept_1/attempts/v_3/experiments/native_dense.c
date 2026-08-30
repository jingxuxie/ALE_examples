#define _POSIX_C_SOURCE 200809L
#include <cblas.h>
#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

extern void dsyev_(const char *, const char *, const int *, double *, const int *,
                   double *, double *, const int *, int *);

static double *workspace = NULL;
static size_t workspace_capacity = 0;

static double seconds(clockid_t kind) {
    struct timespec stamp;
    clock_gettime(kind, &stamp);
    return stamp.tv_sec + 1e-9 * stamp.tv_nsec;
}

typedef struct {
    int left, physical, right, full_size, size;
    const double *diagonal, *position, *left_position, *right_position;
    const int64_t *allowed;
    double left_coupling, right_coupling;
    double *tensor, *physical_input, *physical_output, *positioned, *result;
} Action;

static void apply(const Action *action, const double *vector, double *output) {
    const int left = action->left;
    const int physical = action->physical;
    const int right = action->right;
    const double *tensor = vector;
    if (action->allowed) {
        memset(action->tensor, 0, action->full_size * sizeof(double));
        for (int entry = 0; entry < action->size; ++entry)
            action->tensor[action->allowed[entry]] = vector[entry];
        tensor = action->tensor;
    }
    for (int bond = 0; bond < left; ++bond)
        for (int state = 0; state < physical; ++state)
            memcpy(action->physical_input + (state * left + bond) * right,
                   tensor + (bond * physical + state) * right, right * sizeof(double));
    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, physical, left * right,
                physical, 1., action->position, physical, action->physical_input,
                left * right, 0., action->physical_output, left * right);
    for (int bond = 0; bond < left; ++bond)
        for (int state = 0; state < physical; ++state)
            memcpy(action->positioned + (bond * physical + state) * right,
                   action->physical_output + (state * left + bond) * right,
                   right * sizeof(double));
    for (int entry = 0; entry < action->full_size; ++entry)
        action->result[entry] = action->diagonal[entry] * tensor[entry];
    if (action->left_coupling != 0.)
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, left, physical * right,
                    left, -action->left_coupling, action->left_position, left,
                    action->positioned, physical * right, 1., action->result, physical * right);
    if (action->right_coupling != 0.)
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, left * physical, right,
                    right, -action->right_coupling, action->positioned, right,
                    action->right_position, right, 1., action->result, right);
    if (action->allowed) {
        for (int entry = 0; entry < action->size; ++entry)
            output[entry] = action->result[action->allowed[entry]];
    } else {
        memcpy(output, action->result, action->size * sizeof(double));
    }
}

double local_lowest(int left, int physical, int right, const double *full_diagonal,
                    const double *position, const double *left_position,
                    const double *right_position, double left_coupling,
                    double right_coupling, const int64_t *allowed, int size,
                    const double *diagonal, const double *start, double tolerance,
                    int max_steps, double cpu_deadline, double wall_deadline,
                    double *output, int *iterations) {
    int capacity = max_steps + 1 < 24 ? max_steps + 1 : 24;
    int full_size = left * physical * right;
    size_t required = (size_t)5 * full_size + (size_t)(2 * capacity + 4) * size;
    if (required > workspace_capacity) {
        double *grown = realloc(workspace, required * sizeof(double));
        if (!grown) {
            *iterations = -1;
            memcpy(output, start, size * sizeof(double));
            return NAN;
        }
        workspace = grown;
        workspace_capacity = required;
    }
    Action action = {left, physical, right, full_size, size, full_diagonal,
                     position, left_position, right_position, allowed,
                     left_coupling, right_coupling, workspace, workspace + full_size,
                     workspace + 2 * full_size, workspace + 3 * full_size,
                     workspace + 4 * full_size};
    double *basis = workspace + 5 * full_size;
    double *images = basis + capacity * size;
    double *vector = images + capacity * size;
    double *image = vector + size;
    double *direction = image + size;
    double *new_image = direction + size;
    double projected[24 * 24] = {0};
    double small_matrix[24 * 24], values[24], weights[24], products[24], work[1024];
    double norm = cblas_dnrm2(size, start, 1);
    for (int entry = 0; entry < size; ++entry) basis[entry] = start[entry] / norm;
    apply(&action, basis, images);
    projected[0] = cblas_ddot(size, basis, 1, images, 1);
    int count = 1;
    double value = projected[0];
    for (int iteration = 0; iteration < max_steps; ++iteration) {
        for (int column = 0; column < count; ++column)
            memcpy(small_matrix + 24 * column, projected + 24 * column, count * sizeof(double));
        int leading = 24, work_size = 1024, info;
        dsyev_("V", "U", &count, small_matrix, &leading, values, work, &work_size, &info);
        if (info) {
            memcpy(output, basis, size * sizeof(double));
            *iterations = -2;
            return projected[0];
        }
        memcpy(weights, small_matrix, count * sizeof(double));
        value = values[0];
        cblas_dgemv(CblasColMajor, CblasNoTrans, size, count, 1., basis, size,
                    weights, 1, 0., vector, 1);
        cblas_dgemv(CblasColMajor, CblasNoTrans, size, count, 1., images, size,
                    weights, 1, 0., image, 1);
        double residual_squared = 0.;
        for (int entry = 0; entry < size; ++entry) {
            double residual = image[entry] - value * vector[entry];
            residual_squared += residual * residual;
            double denominator = diagonal[entry] - value;
            direction[entry] = residual / (denominator > 1e-3 ? denominator : 1e-3);
        }
        *iterations = iteration + 1;
        if (residual_squared < tolerance * tolerance || iteration + 1 == max_steps ||
            seconds(CLOCK_PROCESS_CPUTIME_ID) > cpu_deadline - .025 ||
            seconds(CLOCK_MONOTONIC) > wall_deadline - .025) break;
        if (count == capacity) {
            memcpy(basis, vector, size * sizeof(double));
            memcpy(images, image, size * sizeof(double));
            count = 1;
            projected[0] = value;
        }
        for (int repeat = 0; repeat < 2; ++repeat) {
            cblas_dgemv(CblasColMajor, CblasTrans, size, count, 1., basis, size,
                        direction, 1, 0., products, 1);
            cblas_dgemv(CblasColMajor, CblasNoTrans, size, count, -1., basis, size,
                        products, 1, 1., direction, 1);
        }
        norm = cblas_dnrm2(size, direction, 1);
        if (norm < 1e-13) break;
        cblas_dscal(size, 1. / norm, direction, 1);
        memcpy(basis + count * size, direction, size * sizeof(double));
        apply(&action, direction, new_image);
        memcpy(images + count * size, new_image, size * sizeof(double));
        cblas_dgemv(CblasColMajor, CblasTrans, size, count, 1., basis, size,
                    new_image, 1, 0., products, 1);
        for (int entry = 0; entry < count; ++entry) {
            projected[entry + 24 * count] = products[entry];
            projected[count + 24 * entry] = products[entry];
        }
        projected[count + 24 * count] = cblas_ddot(size, direction, 1, new_image, 1);
        ++count;
    }
    memcpy(output, vector, size * sizeof(double));
    return value;
}
