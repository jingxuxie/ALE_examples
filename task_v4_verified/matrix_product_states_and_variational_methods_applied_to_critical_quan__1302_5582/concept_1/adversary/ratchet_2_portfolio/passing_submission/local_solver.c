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
static int *index_workspace = NULL;
static size_t index_capacity = 0;

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
    int parity_blocks;
    int left_count[2], right_count[2], physical_count[2];
    int left_indices[2][64], right_indices[2][64];
    int block_offset[4], position_offset[4];
    int *permutation, *full_indices;
    double left_cross[2][1024], right_cross[2][1024], physical_cross[2][256];
} Action;

static int prepare_parity(Action *action) {
    if (!action->allowed || action->left > 64 || action->right > 64 || action->physical > 32)
        return 0;
    size_t required = (size_t)3 * action->full_size;
    if (required > index_capacity) {
        int *grown = realloc(index_workspace, required * sizeof(int));
        if (!grown) return 0;
        index_workspace = grown;
        index_capacity = required;
    }
    action->permutation = index_workspace;
    action->full_indices = index_workspace + action->full_size;
    int *mapping = index_workspace + 2 * action->full_size;
    for (int entry = 0; entry < action->full_size; ++entry) mapping[entry] = -1;
    for (int entry = 0; entry < action->size; ++entry) mapping[action->allowed[entry]] = entry;
    for (int bond = 0; bond < action->left; ++bond) {
        int charge = mapping[bond * action->physical * action->right] < 0;
        action->left_indices[charge][action->left_count[charge]++] = bond;
    }
    int first_charge = mapping[0] < 0;
    for (int bond = 0; bond < action->right; ++bond) {
        int charge = first_charge ^ (mapping[bond] < 0);
        action->right_indices[charge][action->right_count[charge]++] = bond;
    }
    action->physical_count[0] = (action->physical + 1) / 2;
    action->physical_count[1] = action->physical / 2;
    int offset = 0, position_offset = 0;
    for (int left_charge = 0; left_charge < 2; ++left_charge) {
        for (int physical_charge = 0; physical_charge < 2; ++physical_charge) {
            int block = 2 * left_charge + physical_charge;
            int right_charge = left_charge ^ physical_charge;
            action->block_offset[block] = offset;
            action->position_offset[block] = position_offset;
            position_offset += action->left_count[left_charge] * action->physical_count[1 - physical_charge] * action->right_count[right_charge];
            for (int left_index = 0; left_index < action->left_count[left_charge]; ++left_index)
                for (int physical_index = physical_charge; physical_index < action->physical; physical_index += 2)
                    for (int right_index = 0; right_index < action->right_count[right_charge]; ++right_index) {
                        int full_index = (action->left_indices[left_charge][left_index] * action->physical + physical_index) * action->right + action->right_indices[right_charge][right_index];
                        if (mapping[full_index] < 0) return 0;
                        action->permutation[offset] = mapping[full_index];
                        action->full_indices[offset++] = full_index;
                    }
        }
    }
    if (offset != action->size || position_offset > action->full_size) return 0;
    for (int charge = 0; charge < 2; ++charge) {
        for (int row = 0; row < action->left_count[charge]; ++row)
            for (int column = 0; column < action->left_count[1-charge]; ++column)
                action->left_cross[charge][row * action->left_count[1-charge] + column] = action->left_position[action->left_indices[charge][row] * action->left + action->left_indices[1-charge][column]];
        for (int row = 0; row < action->right_count[1-charge]; ++row)
            for (int column = 0; column < action->right_count[charge]; ++column)
                action->right_cross[charge][row * action->right_count[charge] + column] = action->right_position[action->right_indices[1-charge][row] * action->right + action->right_indices[charge][column]];
        for (int row = 0; row < action->physical_count[charge]; ++row)
            for (int column = 0; column < action->physical_count[1-charge]; ++column)
                action->physical_cross[charge][row * action->physical_count[1-charge] + column] = action->position[(2 * row + charge) * action->physical + 2 * column + 1 - charge];
    }
    return 1;
}

static void apply_parity(const Action *action, const double *vector, double *output) {
    for (int entry = 0; entry < action->size; ++entry) {
        action->tensor[entry] = vector[action->permutation[entry]];
        action->result[entry] = action->diagonal[action->full_indices[entry]] * action->tensor[entry];
    }
    for (int left_charge = 0; left_charge < 2; ++left_charge) {
        for (int physical_charge = 0; physical_charge < 2; ++physical_charge) {
            int block = 2 * left_charge + physical_charge;
            int left = action->left_count[left_charge];
            int right = action->right_count[left_charge ^ physical_charge];
            int physical = action->physical_count[physical_charge];
            int target_physical = action->physical_count[1 - physical_charge];
            if (!left || !right || !physical || !target_physical) continue;
            const double *tensor = action->tensor + action->block_offset[block];
            double *positioned = action->positioned + action->position_offset[block];
            for (int bond = 0; bond < left; ++bond)
                for (int state = 0; state < physical; ++state)
                    memcpy(action->physical_input + (state * left + bond) * right,
                           tensor + (bond * physical + state) * right, right * sizeof(double));
            cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, target_physical,
                        left * right, physical, 1., action->physical_cross[1-physical_charge],
                        physical, action->physical_input, left * right, 0.,
                        action->physical_output, left * right);
            for (int bond = 0; bond < left; ++bond)
                for (int state = 0; state < target_physical; ++state)
                    memcpy(positioned + (bond * target_physical + state) * right,
                           action->physical_output + (state * left + bond) * right,
                           right * sizeof(double));
        }
    }
    for (int left_charge = 0; left_charge < 2; ++left_charge) {
        for (int physical_charge = 0; physical_charge < 2; ++physical_charge) {
            int block = 2 * left_charge + physical_charge;
            int right_charge = left_charge ^ physical_charge;
            int left = action->left_count[left_charge];
            int right = action->right_count[right_charge];
            int physical = action->physical_count[physical_charge];
            if (!left || !right || !physical) continue;
            double *result = action->result + action->block_offset[block];
            int other_left = action->left_count[1-left_charge];
            int other_right = action->right_count[1-right_charge];
            if (other_left && action->left_coupling != 0.) {
                int source = 2 * (1-left_charge) + 1-physical_charge;
                cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, left,
                            physical * right, other_left, -action->left_coupling,
                            action->left_cross[left_charge], other_left,
                            action->positioned + action->position_offset[source],
                            physical * right, 1., result, physical * right);
            }
            if (other_right && action->right_coupling != 0.) {
                int source = 2 * left_charge + 1-physical_charge;
                cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, left * physical,
                            right, other_right, -action->right_coupling,
                            action->positioned + action->position_offset[source], other_right,
                            action->right_cross[right_charge], right, 1., result, right);
            }
        }
    }
    for (int entry = 0; entry < action->size; ++entry)
        output[action->permutation[entry]] = action->result[entry];
}

static void apply(const Action *action, const double *vector, double *output) {
    if (action->parity_blocks) {
        apply_parity(action, vector, output);
        return;
    }
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
    Action action = {
        .left = left, .physical = physical, .right = right,
        .full_size = full_size, .size = size, .diagonal = full_diagonal,
        .position = position, .left_position = left_position,
        .right_position = right_position, .allowed = allowed,
        .left_coupling = left_coupling, .right_coupling = right_coupling,
        .tensor = workspace, .physical_input = workspace + full_size,
        .physical_output = workspace + 2 * full_size,
        .positioned = workspace + 3 * full_size, .result = workspace + 4 * full_size
    };
    action.parity_blocks = prepare_parity(&action);
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
