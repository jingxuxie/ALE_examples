#include <cmath>
#include <cstring>

extern "C" void tensor(const int* word, const double* values, double* result, double* jacobian) {
    double first[5] = {}, second[25] = {}, third[125] = {};
    double first_gradient[5][17] = {}, second_gradient[25][17] = {}, third_gradient[125][17] = {};
    for (int stage = 0; stage < 33; ++stage) {
        int variable = stage < 17 ? stage : 32 - stage;
        int component = word[variable];
        double multiplier = stage == 16 ? 2. : 1.;
        double value = values[variable] * multiplier;
        for (int left = 0; left < 5; ++left) {
            for (int middle = 0; middle < 5; ++middle) {
                int pair = left * 5 + middle;
                int triple = pair * 5 + component;
                third[triple] += second[pair] * value;
                for (int parameter = 0; parameter < 17; ++parameter)
                    third_gradient[triple][parameter] += second_gradient[pair][parameter] * value;
                third_gradient[triple][variable] += second[pair] * multiplier;
            }
            int triple = left * 25 + component * 5 + component;
            third[triple] += first[left] * value * value / 2;
            for (int parameter = 0; parameter < 17; ++parameter)
                third_gradient[triple][parameter] += first_gradient[left][parameter] * value * value / 2;
            third_gradient[triple][variable] += first[left] * value * multiplier;
        }
        int triple = component * 31;
        third[triple] += value * value * value / 6;
        third_gradient[triple][variable] += value * value * multiplier / 2;
        for (int left = 0; left < 5; ++left) {
            int pair = left * 5 + component;
            second[pair] += first[left] * value;
            for (int parameter = 0; parameter < 17; ++parameter)
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
        for (int parameter = 0; parameter < 17; ++parameter)
            jacobian[entry * 17 + parameter] = third_gradient[entry][parameter];
    }
}
