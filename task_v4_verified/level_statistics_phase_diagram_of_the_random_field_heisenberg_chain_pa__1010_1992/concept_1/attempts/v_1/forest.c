#include <math.h>
#include <stdint.h>

void forest_predict(int case_count, int feature_count, int tree_count,
                    const float *samples, const int32_t *roots,
                    const int16_t *features, const double *thresholds,
                    const int32_t *right_children, const float *values,
                    double *means, double *deviations) {
    for (int case_index = 0; case_index < case_count; ++case_index) {
        means[case_index] = 0.0;
        deviations[case_index] = 0.0;
    }
    for (int tree_index = 0; tree_index < tree_count; ++tree_index) {
        for (int case_index = 0; case_index < case_count; ++case_index) {
            const float *sample = samples + case_index * feature_count;
            int32_t node = roots[tree_index];
            while (features[node] >= 0) {
                node = sample[features[node]] <= thresholds[node]
                       ? node + 1 : right_children[node];
            }
            double value = values[node];
            means[case_index] += value;
            deviations[case_index] += value * value;
        }
    }
    for (int case_index = 0; case_index < case_count; ++case_index) {
        means[case_index] /= tree_count;
        double variance = deviations[case_index] / tree_count
                          - means[case_index] * means[case_index];
        deviations[case_index] = sqrt(fmax(variance, 0.0));
    }
}
