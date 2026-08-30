#include <algorithm>
#include <array>
#include <fstream>
#include <iostream>
#include <numeric>
#include <queue>
#include <set>
#include <tuple>
#include <vector>

int rank_vectors(std::vector<int> vectors, int width) {
    std::array<int, 16> pivots{};
    int rank = 0;
    for (int vector : vectors) {
        while (vector) {
            int pivot = 31 - __builtin_clz(vector);
            if (pivots[pivot]) vector ^= pivots[pivot];
            else { pivots[pivot] = vector; ++rank; break; }
        }
    }
    return rank;
}

void transform(std::vector<int>& values) {
    for (int stride = 1; stride < static_cast<int>(values.size()); stride <<= 1)
        for (int block = 0; block < static_cast<int>(values.size()); block += stride * 2)
            for (int offset = 0; offset < stride; ++offset) values[block + stride + offset] ^= values[block + offset];
}

std::vector<int> score(const std::vector<int>& coefficients, int width, int count) {
    int full = (1 << width) - 1;
    std::vector<int> top;
    for (int bit = 0; bit < width; ++bit) top.push_back(coefficients[full ^ (1 << bit)]);
    std::vector<int> result{rank_vectors(top, count)};
    std::array<int, 16> histogram{};
    for (int combination = 1; combination < (1 << count); ++combination) {
        bool highest = false;
        for (int coefficient : top) if (__builtin_parity(coefficient & combination)) { highest = true; break; }
        if (highest) continue;
        std::vector<int> matrix(width);
        for (int first = 0; first < width; ++first)
            for (int second = first + 1; second < width; ++second)
                if (__builtin_parity(coefficients[full ^ (1 << first) ^ (1 << second)] & combination)) {
                    matrix[first] ^= 1 << second;
                    matrix[second] ^= 1 << first;
                }
        ++histogram[rank_vectors(matrix, width)];
    }
    for (int rank = 0; rank <= width; rank += 2) result.push_back(-histogram[rank]);
    return result;
}

int main(int argc, char** argv) {
    std::ifstream input(argv[1]);
    int width, count;
    input >> width >> count;
    std::vector<int> table(1 << width);
    for (auto& value : table) input >> value;
    std::vector<int> coefficients = table;
    transform(coefficients);
    auto initial = score(coefficients, width, count);
    std::cerr << "initial";
    for (int value : initial) std::cerr << ' ' << value;
    std::cerr << std::endl;
    std::set<int> directions;
    int full = (1 << width) - 1;
    for (int combination = 1; combination < (1 << count); ++combination) {
        int direction = 0;
        for (int bit = 0; bit < width; ++bit)
            if (__builtin_parity(coefficients[full ^ (1 << bit)] & combination)) direction ^= 1 << bit;
        if (direction) directions.insert(direction);
    }
    using Candidate = std::tuple<std::vector<int>, int, int, int>;
    std::priority_queue<Candidate> best;
    for (int direction : directions) {
        int pivot = __builtin_ctz(direction);
        std::vector<int> forms_basis;
        for (int bit = 0; bit < width; ++bit) if (bit != pivot) forms_basis.push_back((1 << bit) ^ (((direction >> bit) & 1) << pivot));
        std::vector<int> forms(1 << (width - 1));
        std::vector<std::vector<unsigned char>> parities(forms.size(), std::vector<unsigned char>(table.size()));
        for (int mask = 1; mask < static_cast<int>(forms.size()); ++mask) {
            int bit = __builtin_ctz(mask);
            forms[mask] = forms[mask ^ (1 << bit)] ^ forms_basis[bit];
            for (int address = 0; address <= full; ++address) parities[mask][address] = __builtin_parity(address & forms[mask]);
        }
        std::vector<int> difference(table.size());
        for (int address = 0; address <= full; ++address) difference[address] = table[address] ^ table[address ^ direction];
        int tested = 0;
        for (int first = 1; first < static_cast<int>(forms.size()); ++first) {
            int first_pivot = 31 - __builtin_clz(first);
            for (int second = 1 << (first_pivot + 1); second < static_cast<int>(forms.size()); ++second) {
                if (second >> first_pivot & 1) continue;
                for (int address = 0; address <= full; ++address) coefficients[address] = table[address] ^ ((parities[first][address] & parities[second][address]) ? difference[address] : 0);
                transform(coefficients);
                auto candidate_score = score(coefficients, width, count);
                Candidate candidate{candidate_score, direction, forms[first], forms[second]};
                if (best.size() < 100 || candidate < best.top()) {
                    best.push(candidate);
                    if (best.size() > 100) best.pop();
                }
                ++tested;
            }
        }
        std::cerr << "direction " << direction << " tested " << tested << std::endl;
    }
    std::vector<Candidate> sorted;
    while (!best.empty()) { sorted.push_back(best.top()); best.pop(); }
    std::reverse(sorted.begin(), sorted.end());
    for (int index = 0; index < static_cast<int>(sorted.size()); ++index) {
        const auto& [candidate_score, direction, left, right] = sorted[index];
        if (index < 15) {
            std::cerr << index << " gate " << direction << ' ' << left << ' ' << right << " score";
            for (int value : candidate_score) std::cerr << ' ' << value;
            std::cerr << std::endl;
        }
        std::ofstream output(std::string(argv[2]) + "_" + std::to_string(index) + ".txt");
        output << width << ' ' << count << '\n';
        for (int address = 0; address <= full; ++address) output << table[address ^ ((__builtin_parity(address & left) && __builtin_parity(address & right)) ? direction : 0)] << ' ';
        output << '\n' << direction << ' ' << left << ' ' << right << '\n';
    }
}
