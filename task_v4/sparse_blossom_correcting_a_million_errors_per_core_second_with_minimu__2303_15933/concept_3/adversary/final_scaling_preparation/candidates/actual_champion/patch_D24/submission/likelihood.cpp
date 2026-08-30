#include <cmath>
#include <vector>
#include <algorithm>
#include <cstdint>

static void walsh(double* values, int states) {
    for (int width = 1; width < states; width *= 2) {
        for (int start = 0; start < states; start += 2 * width) {
            double* left = values + start;
            double* right = left + width;
            for (int index = 0; index < width; ++index) {
                double first = left[index];
                double second = right[index];
                left[index] = first + second;
                right[index] = first - second;
            }
        }
    }
}

extern "C" double likelihood(int actions, int blocks, int channels, int states,
    const int32_t* masks, const double* exposures, const double* weights,
    const double* alternates, const double* log_rates, const double* counts,
    double* gradient, double* probabilities, double* derivatives) {
    std::vector<double> rates(channels), coefficients(2 * channels * 4), slopes(2 * channels * 4);
    std::vector<double> spectra(2 * states), probability(states), adjoint(states), temporary(states);
    std::fill(gradient, gradient + channels, 0.0);
    for (int channel = 0; channel < channels; ++channel) rates[channel] = std::exp(log_rates[channel]);
    double value = 0;
    for (int action = 0; action < actions; ++action) {
        if (counts && !probabilities) {
            double total = 0;
            for (int state = 0; state < states; ++state) total += counts[(size_t)action * blocks * states + state];
            if (total == 0) continue;
        }
        for (int mode = 0; mode < 2; ++mode) {
            for (int channel = 0; channel < channels; ++channel) {
                double scaled = 2 * exposures[(action * 2 + mode) * channels + channel] * rates[channel];
                double alternate = alternates[action * channels + channel];
                double attenuation = std::exp(-scaled);
                double first = alternate + (1 - alternate) * attenuation;
                double second = 1 - alternate + alternate * attenuation;
                double log_first = std::log(std::max(first, 1e-300));
                double log_second = std::log(std::max(second, 1e-300));
                double slope_first = -scaled * (1 - alternate) * attenuation / std::max(first, 1e-300);
                double slope_second = -scaled * alternate * attenuation / std::max(second, 1e-300);
                if (alternate == 0) {log_first = -scaled; slope_first = -scaled;}
                if (alternate == 1) {log_second = -scaled; slope_second = -scaled;}
                int offset = (mode * channels + channel) * 4;
                coefficients[offset] = (log_first + log_second - scaled) * 0.25;
                coefficients[offset + 1] = (-log_first + log_second + scaled) * 0.25;
                coefficients[offset + 2] = (log_first - log_second + scaled) * 0.25;
                coefficients[offset + 3] = (-log_first - log_second - scaled) * 0.25;
                slopes[offset] = (slope_first + slope_second - scaled) * 0.25;
                slopes[offset + 1] = (-slope_first + slope_second + scaled) * 0.25;
                slopes[offset + 2] = (slope_first - slope_second + scaled) * 0.25;
                slopes[offset + 3] = (-slope_first - slope_second - scaled) * 0.25;
            }
        }
        for (int block = 0; block < blocks; ++block) {
            size_t location = ((size_t)action * blocks + block) * states;
            for (int mode = 0; mode < 2; ++mode) {
                double* spectrum = spectra.data() + mode * states;
                std::fill(spectrum, spectrum + states, 0.0);
                for (int channel = 0; channel < channels; ++channel) {
                    int primary = masks[(block * channels + channel) * 2];
                    int alternate = masks[(block * channels + channel) * 2 + 1];
                    int offset = (mode * channels + channel) * 4;
                    spectrum[0] += coefficients[offset];
                    spectrum[primary] += coefficients[offset + 1];
                    spectrum[alternate] += coefficients[offset + 2];
                    spectrum[primary ^ alternate] += coefficients[offset + 3];
                }
                walsh(spectrum, states);
                for (int state = 0; state < states; ++state) spectrum[state] = weights[action * 2 + mode] * std::exp(spectrum[state]);
            }
            for (int state = 0; state < states; ++state) probability[state] = spectra[state] + spectra[states + state];
            walsh(probability.data(), states);
            for (int state = 0; state < states; ++state) {
                probability[state] = std::max(probability[state] / states, 1e-18);
                if (probabilities) probabilities[location + state] = probability[state];
                if (counts) {
                    double count = counts[location + state];
                    if (count) value -= count * std::log(probability[state]);
                    adjoint[state] = -count / probability[state] / states;
                }
            }
            if (counts) {
                walsh(adjoint.data(), states);
                for (int mode = 0; mode < 2; ++mode) {
                    for (int state = 0; state < states; ++state) temporary[state] = adjoint[state] * spectra[mode * states + state];
                    walsh(temporary.data(), states);
                    for (int channel = 0; channel < channels; ++channel) {
                        int primary = masks[(block * channels + channel) * 2];
                        int alternate = masks[(block * channels + channel) * 2 + 1];
                        int offset = (mode * channels + channel) * 4;
                        gradient[channel] += slopes[offset] * temporary[0] + slopes[offset + 1] * temporary[primary]
                            + slopes[offset + 2] * temporary[alternate] + slopes[offset + 3] * temporary[primary ^ alternate];
                    }
                }
            }
            if (derivatives) {
                for (int channel = 0; channel < channels; ++channel) {
                    int primary = masks[(block * channels + channel) * 2];
                    int alternate = masks[(block * channels + channel) * 2 + 1];
                    for (int state = 0; state < states; ++state) {
                        double primary_sign = __builtin_parity((unsigned)(state & primary)) ? -1.0 : 1.0;
                        double alternate_sign = __builtin_parity((unsigned)(state & alternate)) ? -1.0 : 1.0;
                        double derivative = 0;
                        for (int mode = 0; mode < 2; ++mode) {
                            int offset = (mode * channels + channel) * 4;
                            derivative += spectra[mode * states + state] * (slopes[offset] + slopes[offset + 1] * primary_sign
                                + slopes[offset + 2] * alternate_sign + slopes[offset + 3] * primary_sign * alternate_sign);
                        }
                        temporary[state] = derivative;
                    }
                    walsh(temporary.data(), states);
                    double* target = derivatives + (((size_t)action * blocks + block) * channels + channel) * states;
                    for (int state = 0; state < states; ++state) target[state] = temporary[state] / states;
                }
            }
        }
    }
    return value;
}
