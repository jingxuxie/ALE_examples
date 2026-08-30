#include <algorithm>
#include <array>
#include <cmath>
#include <complex>
#include <vector>

extern "C" void dsyev_(const char*, const char*, const int*, double*, const int*, double*, double*, const int*, int*);

using Values = std::vector<double>;
using Complex = std::complex<double>;
constexpr int length = 14;
constexpr double pi = 3.1415926535897932384626433832795;

int wrap(int site) { return (site % length + length) % length; }
double mean(const Values& values) {
    double total = 0;
    for (double value : values) total += value;
    return total / values.size();
}
double minimum(const Values& values) { return *std::min_element(values.begin(), values.end()); }
double maximum(const Values& values) { return *std::max_element(values.begin(), values.end()); }
double deviation(const Values& values) {
    double center = mean(values), total = 0;
    for (double value : values) total += (value - center) * (value - center);
    return std::sqrt(total / values.size());
}
double quantile(Values values, double probability) {
    std::sort(values.begin(), values.end());
    double position = probability * (values.size() - 1);
    int index = int(position);
    double weight = position - index;
    return values[index] * (1 - weight) + values[std::min(index + 1, int(values.size()) - 1)] * weight;
}
void add(Values& output, std::initializer_list<double> values) { output.insert(output.end(), values); }
void quantiles(Values& output, const Values& values) {
    for (int index = 0; index < 7; ++index) output.push_back(quantile(values, index / 6.));
}
struct Spectrum {
    std::array<double, length * length> vectors;
    std::array<double, length> energies;
};
Spectrum diagonalize(std::array<double, length * length> matrix) {
    Spectrum result;
    result.vectors = matrix;
    double work[1024];
    int workspace = 1024, dimension = length, status = 0;
    char vectors = 'V', triangle = 'U';
    dsyev_(&vectors, &triangle, &dimension, result.vectors.data(), &dimension,
           result.energies.data(), work, &workspace, &status);
    return result;
}
Spectrum laplacian(const Values& weights) {
    std::array<double, length * length> matrix{};
    for (int site = 0; site < length; ++site) {
        int previous = wrap(site - 1);
        matrix[site + previous * length] = -weights[site];
        matrix[previous + site * length] = -weights[site];
        matrix[site + site * length] = weights[site] + weights[wrap(site + 1)];
    }
    return diagonalize(matrix);
}
Values describe(const double* input, bool spectral) {
    Values values(input, input + length), output;
    output.reserve(889);
    double center = mean(values);
    for (double& value : values) value -= center;
    double scale = deviation(values), variance = scale * scale;
    Values normal(length), absolute(length), bonds(length), log_bonds(length);
    std::array<Complex, length> modes, transform{};
    for (int site = 0; site < length; ++site) {
        normal[site] = values[site] / std::max(scale, 1e-12);
        absolute[site] = std::abs(values[site]);
        bonds[site] = values[site] - values[wrap(site - 1)];
        log_bonds[site] = std::log1p(bonds[site] * bonds[site]);
        modes[site] = std::polar(1., 2 * pi * site / length);
    }
    for (int harmonic = 0; harmonic < length; ++harmonic)
        for (int site = 0; site < length; ++site)
            transform[harmonic] += values[site] * std::polar(1., -2 * pi * harmonic * site / length) / double(length);
    double third = 0, fourth = 0;
    for (double value : normal) { third += value * value * value; fourth += std::pow(value, 4); }
    add(output, {double(length), scale, maximum(values) - minimum(values), mean(absolute), fourth / length, std::abs(third / length)});
    quantiles(output, absolute);
    Values sorted = values, spacings;
    std::sort(sorted.begin(), sorted.end());
    for (int index = 1; index < length; ++index) spacings.push_back(sorted[index] - sorted[index - 1]);
    quantiles(output, spacings);
    for (int harmonic = 1; harmonic < 7; ++harmonic) {
        double power = std::norm(transform[harmonic]);
        add(output, {power, power / std::max(variance, 1e-12)});
    }
    for (int distance = 1; distance < 7; ++distance) {
        Values differences(length), magnitudes(length), shifted(length), products(length), normalized(length);
        for (int site = 0; site < length; ++site) {
            differences[site] = values[site] - values[wrap(site - distance)];
            magnitudes[site] = std::abs(differences[site]);
            products[site] = values[site] * values[wrap(site - distance)];
            normalized[site] = normal[site] * normal[wrap(site - distance)];
            shifted[site] = std::min({magnitudes[site], std::abs(magnitudes[site] - 1), std::abs(magnitudes[site] - 2)});
        }
        quantiles(output, magnitudes);
        add(output, {mean(magnitudes), deviation(magnitudes), mean(products), mean(normalized)});
        for (double width : {.25, .5, 1., 2.}) {
            Values resonance(length), logarithms(length);
            for (int site = 0; site < length; ++site) {
                resonance[site] = width * width / (width * width + differences[site] * differences[site]);
                logarithms[site] = std::log(resonance[site]);
            }
            add(output, {mean(resonance), minimum(resonance), mean(logarithms)});
        }
        Values proximity(length);
        for (int site = 0; site < length; ++site) proximity[site] = 1 / (1 + shifted[site] * shifted[site]);
        add(output, {mean(proximity), minimum(shifted)});
    }
    Values absolute_bonds(length);
    for (int site = 0; site < length; ++site) absolute_bonds[site] = std::abs(bonds[site]);
    sorted = absolute_bonds;
    std::sort(sorted.begin(), sorted.end());
    for (int index = length - 4; index < length; ++index) output.push_back(sorted[index]);
    for (int window : {2, 3, 4, 5, 6}) {
        Values spread(length), averages(length), minima(length), maxima(length), sums(length);
        for (int site = 0; site < length; ++site) {
            Values patch, barriers;
            sums[site] = 0;
            for (int offset = 0; offset < window; ++offset) {
                patch.push_back(values[wrap(site - offset)]);
                barriers.push_back(absolute_bonds[wrap(site - offset)]);
                sums[site] += log_bonds[wrap(site - offset)];
            }
            spread[site] = deviation(patch);
            averages[site] = std::abs(mean(patch));
            minima[site] = minimum(barriers);
            maxima[site] = maximum(barriers);
        }
        add(output, {minimum(spread), mean(spread), maximum(spread), maximum(averages), mean(averages),
                     maximum(minima), minimum(maxima), maximum(sums)});
    }
    if (spectral) {
    std::array<Spectrum, 4> bare_spectra;
    int width_index = 0;
    for (double width : {.25, .5, 1., 2.}) {
        Values weights(length), products(length);
        for (int site = 0; site < length; ++site) weights[site] = width * width / (width * width + bonds[site] * bonds[site]);
        Spectrum spectrum = laplacian(weights);
        bare_spectra[width_index++] = spectrum;
        for (int index = 1; index < 5; ++index) output.push_back(spectrum.energies[index]);
        for (int distance : {1, 2}) {
            for (int site = 0; site < length; ++site) products[site] = weights[site] * weights[wrap(site - distance)];
            output.push_back(mean(products));
        }
    }
    for (double hopping : {.35, .5, .75, 1., 1.5, 2., 3., 4.}) {
        std::array<double, length * length> matrix{}, probabilities{};
        for (int site = 0; site < length; ++site) {
            matrix[site + site * length] = values[site];
            matrix[site + wrap(site + 1) * length] = hopping;
            matrix[wrap(site + 1) + site * length] = hopping;
        }
        Spectrum spectrum = diagonalize(matrix);
        Values memory(length), participation(length);
        for (int state = 0; state < length; ++state) {
            Complex moment = 0;
            for (int site = 0; site < length; ++site) {
                double probability = std::pow(spectrum.vectors[site + state * length], 2);
                probabilities[site + state * length] = probability;
                moment += probability * modes[site];
                participation[state] += probability * probability;
            }
            memory[state] = std::norm(moment);
        }
        add(output, {mean(memory), deviation(memory), minimum(memory), maximum(memory),
                     mean(participation), maximum(participation), minimum(participation)});
        for (int distance : {1, 2, 3, 7}) {
            Values overlap(length);
            for (int site = 0; site < length; ++site)
                for (int state = 0; state < length; ++state)
                    overlap[site] += probabilities[site + state * length] * probabilities[wrap(site + distance) + state * length];
            add(output, {mean(overlap), minimum(overlap), maximum(overlap)});
        }
        for (double probability : {.25, .5, .75}) output.push_back(quantile(memory, probability));
    }
    width_index = 0;
    for (double width : {.25, .5, 1., 2.}) {
        for (int interacting = 0; interacting < 2; ++interacting) {
            Values weights(length), logs(length), inverse(length);
            for (int site = 0; site < length; ++site) {
                double detuning = bonds[site], squared = width * width;
                double resonance = squared / (squared + detuning * detuning);
                weights[site] = interacting ? (2 * resonance + squared / (squared + std::pow(detuning - 1, 2))
                                              + squared / (squared + std::pow(detuning + 1, 2))) / 4 : resonance;
                logs[site] = std::log(weights[site]);
                inverse[site] = 1 / weights[site];
            }
            Spectrum spectrum = interacting ? laplacian(weights) : bare_spectra[width_index];
            Values projection(length);
            for (int state = 0; state < length; ++state) {
                Complex moment = 0;
                for (int site = 0; site < length; ++site) moment += spectrum.vectors[site + state * length] * modes[site];
                projection[state] = std::norm(moment) / length;
            }
            for (double lifetime : {1., 4., 16., 64., 256., 1024.}) {
                double memory = 0;
                for (int state = 0; state < length; ++state) memory += projection[state] / (1 + lifetime * spectrum.energies[state]);
                output.push_back(memory);
            }
            add(output, {mean(weights), mean(logs), mean(inverse)});
            for (int window : {2, 3, 4, 6}) {
                Values products(length, 1.);
                for (int site = 0; site < length; ++site)
                    for (int offset = 0; offset < window; ++offset) products[site] *= weights[wrap(site - offset)];
                add(output, {mean(products), maximum(products), minimum(products)});
            }
        }
        ++width_index;
    }
    } else {
        output.insert(output.end(), 368, 0.);
    }
    double total_log = mean(log_bonds) * length;
    for (int distance = 1; distance <= 7; ++distance) {
        Values path(length), detuning(length);
        for (int site = 0; site < length; ++site) {
            for (int offset = 0; offset < distance; ++offset) path[site] += log_bonds[wrap(site - offset)];
            path[site] = std::min(path[site], total_log - path[site]);
            detuning[site] = values[site] - values[wrap(site - distance)];
        }
        for (double width : {.25, .5, 1., 2.})
            for (double factor : {.25, .5, 1.}) {
                Values connected(length);
                for (int site = 0; site < length; ++site)
                    connected[site] = width * width / (width * width + detuning[site] * detuning[site]) * std::exp(-factor * path[site]);
                add(output, {mean(connected), maximum(connected)});
            }
    }
    for (int first = 1; first <= 4; ++first)
        for (int second = first; second <= 4; ++second) {
            Complex product = transform[first] * transform[second] * std::conj(transform[first + second]) / std::pow(std::max(scale, 1e-12), 3);
            add(output, {std::abs(product.real()), std::abs(product.imag())});
        }
    double stagger = transform[7].real();
    Values residual(length), residual_abs(length);
    for (int site = 0; site < length; ++site) {
        residual[site] = values[site] - stagger * (site % 2 ? -1 : 1) - 2 * (transform[1] * modes[site]).real();
        residual_abs[site] = std::abs(residual[site]);
    }
    double residual_rms = 0;
    for (double value : residual) residual_rms += value * value;
    residual_rms = std::sqrt(residual_rms / length);
    add(output, {scale, std::abs(stagger), 2 * std::abs(transform[1]), residual_rms, maximum(residual_abs),
                 std::abs(stagger) / std::max(scale, 1e-12), residual_rms / std::max(scale, 1e-12)});
    for (int blocks : {2, 3}) {
        double best_error = 1e300;
        Values best_centers, best_deviations, best_slopes;
        for (int offset = 0; offset < length; ++offset) {
            Values centers, deviations, slopes;
            double error = 0;
            int start = 0;
            for (int block = 0; block < blocks; ++block) {
                int count = length / blocks + (block < length % blocks ? 1 : 0);
                Values patch;
                double numerator = 0, denominator = 0;
                for (int position = 0; position < count; ++position) {
                    double value = values[wrap(start + position - offset)];
                    double coordinate = -1 + 2. * position / (count - 1);
                    patch.push_back(value);
                    numerator += value * coordinate;
                    denominator += coordinate * coordinate;
                }
                double block_center = mean(patch);
                for (double value : patch) error += (value - block_center) * (value - block_center);
                centers.push_back(block_center);
                deviations.push_back(deviation(patch));
                slopes.push_back(std::abs(numerator / denominator));
                start += count;
            }
            if (error < best_error) {
                best_error = error;
                best_centers = centers; best_deviations = deviations; best_slopes = slopes;
            }
        }
        Values centers_abs, detuning;
        for (int block = 0; block < blocks; ++block) {
            centers_abs.push_back(std::abs(best_centers[block]));
            detuning.push_back(std::abs(best_centers[block] - best_centers[(block + blocks - 1) % blocks]));
        }
        add(output, {std::sqrt(best_error / length), best_error / std::max(length * variance, 1e-12)});
        for (const Values& group : {centers_abs, best_deviations, best_slopes, detuning})
            add(output, {minimum(group), mean(group), maximum(group)});
    }
    std::array<int, length> order;
    for (int site = 0; site < length; ++site) order[site] = site;
    std::sort(order.begin(), order.end(), [&](int first, int second) { return values[first] < values[second]; });
    Values mismatch, pair_distance;
    for (int pair = 0; pair < length / 2; ++pair) {
        int first = order[2 * pair], second = order[2 * pair + 1];
        mismatch.push_back(values[second] - values[first]);
        int distance = std::abs(second - first);
        pair_distance.push_back(std::min(distance, length - distance));
    }
    add(output, {mean(mismatch), maximum(mismatch), mean(mismatch) / std::max(scale, 1e-12)});
    for (double width : {.1, .3, 1.}) {
        Values paired(7), weighted(7), modes_weighted(7);
        for (int pair = 0; pair < 7; ++pair) {
            paired[pair] = width * width / (width * width + mismatch[pair] * mismatch[pair]);
            weighted[pair] = paired[pair] * pair_distance[pair];
            modes_weighted[pair] = paired[pair] * std::pow(std::sin(pi * pair_distance[pair] / length), 2);
        }
        add(output, {mean(paired), mean(weighted), mean(modes_weighted)});
    }
    for (int separation : {2, 3, 4, 5, 6}) {
        Values detuning(length), coupling(length);
        for (int site = 0; site < length; ++site) {
            double first = bonds[site], second = bonds[wrap(site - separation)];
            detuning[site] = std::min(std::abs(first - second), std::abs(first + second));
            coupling[site] = 1 / std::sqrt((1 + first * first) * (1 + second * second));
        }
        for (double width : {.25, .5, 1., 2.}) {
            Values resonance(length), weighted(length);
            for (int site = 0; site < length; ++site) {
                resonance[site] = width * width / (width * width + detuning[site] * detuning[site]);
                weighted[site] = coupling[site] * resonance[site];
            }
            add(output, {mean(resonance), mean(weighted), maximum(weighted)});
        }
    }
    return output;
}

extern "C" int feature_batch(const double* input, double* output, int count, int spectral) {
    for (int sample = 0; sample < count; ++sample) {
        Values features = describe(input + sample * length, spectral != 0);
        if (features.size() != 889) return int(features.size());
        std::copy(features.begin(), features.end(), output + sample * 889);
    }
    return 0;
}
