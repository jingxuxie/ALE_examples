#include <algorithm>
#include <cmath>
#include <vector>
#include <numeric>

extern "C" void project(const double* values, double* result, int size, int mode, double penalty_one, double penalty_two) {
    std::fill(result, result + size, 0.0);
    if (mode == 5 || mode == 6) {
        std::vector<int> indices(size);
        std::iota(indices.begin(),indices.end(),0);
        auto compare = [&](int first,int second){return values[first]>values[second];};
        int occupied_count = penalty_two > 0 ? int(penalty_two) : 768;
        if (mode == 5) {
            std::nth_element(indices.begin(),indices.begin()+occupied_count,indices.end(),compare);
            for (int rank = 0; rank < occupied_count; ++rank) result[indices[rank]] = std::max(0.0,values[indices[rank]]);
        } else {
            std::sort(indices.begin(),indices.end(),compare);
            int count = 0;
            for (int index : indices) {
                if (result[(index+size-1)%size] || result[(index+1)%size]) continue;
                result[index] = std::max(0.0,values[index]);
                if (++count == occupied_count) break;
            }
        }
        if (penalty_one > 0) {
            for (int index = 0; index < size; ++index) if (result[index]) result[index] += penalty_one * (std::clamp(std::round(result[index]),1.0,2.0)-result[index]);
        }
        return;
    }
    if (mode == 4) {
        std::vector<double> sorted(values, values + size), candidate(size);
        std::nth_element(sorted.begin(), sorted.begin()+285, sorted.end(), std::greater<double>());
        double threshold_two = sorted[285];
        std::nth_element(sorted.begin()+285, sorted.begin()+950, sorted.end(), std::greater<double>());
        double occupied_penalty = 2*sorted[950]-1;
        double extra_penalty = 2*threshold_two-3;
        double best_error = 1e20;
        for (int iteration = 0; iteration < 18; ++iteration) {
            project(values, candidate.data(), size, 3, occupied_penalty, occupied_penalty+extra_penalty);
            int occupied = 0, twos = 0;
            for (double value : candidate) { occupied += value > 0; twos += value == 2; }
            double error = std::abs(occupied-768) + std::abs(twos-256);
            if (error < best_error) { best_error = error; std::copy(candidate.begin(), candidate.end(), result); }
            if (error == 0) return;
            double rate = iteration < 8 ? 1.0 : 0.5;
            occupied_penalty += rate * 0.0018 * (occupied-768);
            extra_penalty += rate * (0.0035 * (twos-256) - 0.001 * (occupied-768));
        }
        std::vector<int> indices(size);
        std::iota(indices.begin(), indices.end(), 0);
        std::sort(indices.begin(), indices.end(), [&](int first,int second){return values[first]>values[second];});
        int occupied = 0;
        for (int index = 0; index < size; ++index) occupied += result[index] > 0;
        if (occupied > 768) for (int rank = size-1; rank >= 0 && occupied > 768; --rank) {
            int index = indices[rank];
            if (result[index]) {result[index]=0; --occupied;}
        }
        if (occupied < 768) for (int index : indices) {
            if (!result[index] && !result[(index+size-1)%size] && !result[(index+1)%size]) {result[index]=1; ++occupied;}
            if (occupied == 768) break;
        }
        int count = 0;
        for (int index : indices) if (result[index]) result[index] = ++count <= 256 ? 2 : 1;
        return;
    }
    if (mode < 2) {
        std::vector<int> indices(size);
        std::iota(indices.begin(), indices.end(), 0);
        auto compare = [&](int first, int second) { return values[first] > values[second]; };
        if (mode == 0) {
            std::nth_element(indices.begin(), indices.begin() + 256, indices.end(), compare);
            std::nth_element(indices.begin() + 256, indices.begin() + 768, indices.end(), compare);
            for (int rank = 0; rank < 768; ++rank) result[indices[rank]] = rank < 256 ? 2 : 1;
        } else {
            std::sort(indices.begin(), indices.end(), compare);
            int count = 0;
            for (int index : indices) {
                if (result[(index + size - 1) % size] || result[(index + 1) % size]) continue;
                result[index] = count < 256 ? 2 : 1;
                if (++count == 768) break;
            }
        }
        return;
    }
    if (mode == 2) {
        for (int index = 0; index < size; ++index) result[index] = std::clamp(std::round(values[index]), 0.0, 2.0);
        return;
    }
    std::vector<double> weights(size), best(size + 2), alternate(size);
    std::vector<int> labels(size);
    for (int index = 0; index < size; ++index) {
        double score_one = 2 * values[index] - 1 - penalty_one;
        double score_two = 4 * values[index] - 4 - penalty_two;
        labels[index] = score_two > score_one ? 2 : 1;
        weights[index] = std::max(score_one, score_two);
    }
    auto run = [&](int start, int end, double* output) {
        best[start] = 0;
        best[start + 1] = 0;
        for (int index = start; index < end; ++index) best[index + 2] = std::max(best[index + 1], best[index] + weights[index]);
        int index = end - 1;
        while (index >= start) {
            if (best[index + 2] > best[index + 1]) {
                output[index] = labels[index];
                index -= 2;
            } else --index;
        }
        return best[end + 1];
    };
    double first_score = run(1, size, result);
    double second_score = weights[0] + run(2, size - 1, alternate.data());
    if (second_score > first_score) {
        std::copy(alternate.begin(), alternate.end(), result);
        result[0] = labels[0];
    }
}
