#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <limits>
#include <new>
#include <vector>
#include <utility>

extern "C" int infer_many(const double* probabilities, const unsigned* masks,
                         unsigned edge_count, unsigned detector_count,
                         unsigned target, unsigned cases, double* output) {
    if (detector_count > 20 || edge_count > 64 || target >= (1U << detector_count)) return 1;
    try {
        std::array<unsigned, 21> pivot_masks{}, pivot_codes{};
        std::vector<unsigned> independent;
        std::vector<std::pair<unsigned, unsigned>> dependent;
        for (unsigned edge = 0; edge < edge_count; ++edge) {
            unsigned remaining = masks[edge], code = 0;
            if (remaining == 0 || remaining >= (1U << (detector_count + 1))) return 2;
            bool inserted = false;
            for (int bit = static_cast<int>(detector_count); bit >= 0; --bit) {
                if (!(remaining & (1U << bit))) continue;
                if (pivot_masks[bit]) {
                    remaining ^= pivot_masks[bit];
                    code ^= pivot_codes[bit];
                } else {
                    pivot_masks[bit] = remaining;
                    pivot_codes[bit] = code ^ (1U << independent.size());
                    independent.push_back(edge);
                    inserted = true;
                    break;
                }
            }
            if (!inserted) dependent.emplace_back(edge, code);
        }
        const unsigned states = 1U << independent.size();
        std::array<unsigned, 2> targets{};
        std::array<bool, 2> reachable{};
        for (unsigned logical = 0; logical < 2; ++logical) {
            unsigned remaining = target | (logical << detector_count), code = 0;
            for (int bit = static_cast<int>(detector_count); bit >= 0; --bit) {
                if (remaining & (1U << bit)) {
                    remaining ^= pivot_masks[bit];
                    code ^= pivot_codes[bit];
                }
            }
            targets[logical] = code;
            reachable[logical] = remaining == 0;
        }
        std::vector<double> mass(states), cost(states);
        for (unsigned sample = 0; sample < cases; ++sample) {
            std::array<double, 64> weights{};
            for (unsigned edge = 0; edge < edge_count; ++edge) {
                const double probability = probabilities[sample * edge_count + edge];
                if (!std::isfinite(probability) || probability <= 0 || probability >= 0.5) return 2;
                weights[edge] = std::log1p(-probability) - std::log(probability);
            }
            mass[0] = 1.0;
            cost[0] = 0.0;
            for (unsigned basis = 0; basis < independent.size(); ++basis) {
                const unsigned edge = independent[basis], previous_states = 1U << basis;
                const double probability = probabilities[sample * edge_count + edge];
                for (unsigned state = 0; state < previous_states; ++state) {
                    mass[state + previous_states] = probability * mass[state];
                    mass[state] *= 1 - probability;
                    cost[state + previous_states] = cost[state] + weights[edge];
                }
            }
            for (const auto& entry : dependent) {
                const unsigned edge = entry.first, mask = entry.second;
                const double probability = probabilities[sample * edge_count + edge];
                const double complement = 1.0 - probability;
                const double weight = weights[edge];
                const unsigned half_block = mask & (0U - mask);
                for (unsigned block = 0; block < states; block += 2 * half_block) {
                    for (unsigned offset = 0; offset < half_block; ++offset) {
                        const unsigned first = block + offset;
                        const unsigned second = first ^ mask;
                        const double first_mass = mass[first], second_mass = mass[second];
                        const double first_cost = cost[first], second_cost = cost[second];
                        mass[first] = complement * first_mass + probability * second_mass;
                        mass[second] = complement * second_mass + probability * first_mass;
                        cost[first] = std::min(first_cost, weight + second_cost);
                        cost[second] = std::min(second_cost, weight + first_cost);
                    }
                }
            }
            for (unsigned logical = 0; logical < 2; ++logical) {
                output[sample * 4 + logical] = reachable[logical] ? mass[targets[logical]] : 0.0;
                output[sample * 4 + 2 + logical] = reachable[logical] ? cost[targets[logical]] : std::numeric_limits<double>::infinity();
            }
        }
    } catch (const std::bad_alloc&) {
        return 3;
    }
    return 0;
}
