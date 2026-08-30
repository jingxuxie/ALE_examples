#include <cstring>

extern "C" void tensor_generic(int count, const int* word, const double* values, double* result, double* jacobian) {
    double first[5] = {}, second[25] = {}, third[125] = {};
    double first_gradient[5][33] = {}, second_gradient[25][33] = {}, third_gradient[125][33] = {};
    for (int stage = 0; stage < 2 * count - 1; ++stage) {
        int variable = stage < count ? stage : 2 * count - 2 - stage;
        int component = word[variable];
        double multiplier = stage == count - 1 ? 2. : 1.;
        double value = values[variable] * multiplier;
        for (int left = 0; left < 5; ++left) {
            for (int middle = 0; middle < 5; ++middle) {
                int pair = left * 5 + middle;
                int triple = pair * 5 + component;
                third[triple] += second[pair] * value;
                for (int parameter = 0; parameter < count; ++parameter)
                    third_gradient[triple][parameter] += second_gradient[pair][parameter] * value;
                third_gradient[triple][variable] += second[pair] * multiplier;
            }
            int triple = left * 25 + component * 5 + component;
            third[triple] += first[left] * value * value / 2;
            for (int parameter = 0; parameter < count; ++parameter)
                third_gradient[triple][parameter] += first_gradient[left][parameter] * value * value / 2;
            third_gradient[triple][variable] += first[left] * value * multiplier;
        }
        int triple = component * 31;
        third[triple] += value * value * value / 6;
        third_gradient[triple][variable] += value * value * multiplier / 2;
        for (int left = 0; left < 5; ++left) {
            int pair = left * 5 + component;
            second[pair] += first[left] * value;
            for (int parameter = 0; parameter < count; ++parameter)
                second_gradient[pair][parameter] += first_gradient[left][parameter] * value;
            second_gradient[pair][variable] += first[left] * multiplier;
        }
        int pair = component * 6;
        second[pair] += value * value / 2;
        second_gradient[pair][variable] += value * multiplier;
        first[component] += value;
        first_gradient[component][variable] += multiplier;
    }
    for (int entry = 0; entry < 125; ++entry) {
        result[entry] = third[entry] - 1. / 6;
        for (int parameter = 0; parameter < count; ++parameter)
            jacobian[entry * count + parameter] = third_gradient[entry][parameter];
    }
}
