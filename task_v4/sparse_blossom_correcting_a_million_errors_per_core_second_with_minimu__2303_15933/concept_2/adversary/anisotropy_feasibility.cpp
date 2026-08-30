#define main generation_one_private_main
#include "search.cpp"
#undef main

extern "C" void batch_metrics(const double* input, int count, unsigned syndrome, double* output) {
    for (int sample = 0; sample < count; ++sample) {
        Rates rates;
        std::copy(input + sample * edge_count, input + (sample + 1) * edge_count, rates.begin());
        Metrics result = evaluate(rates, syndrome, 1.0);
        double sign = result.physical == 0 ? 1.0 : -1.0;
        output[3 * sample] = sign * result.gap;
        output[3 * sample + 1] = sign * std::log(result.opposite / (1 - result.opposite));
        output[3 * sample + 2] = std::log(result.mass);
    }
}
