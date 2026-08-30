#include <algorithm>
#include <cmath>
#include <cstdint>
#include <vector>
#include <map>

struct Basis {
    int sites, holes, spins;
    std::vector<int> masks, vacancies, lookup;
    Basis(int count, int empty, int up): sites(count), holes(empty), spins(up) {
        lookup.resize((empty ? count : 1) * (1 << count), -1);
        for (int hole = 0; hole < (empty ? count : 1); ++hole) {
            for (int mask = 0; mask < (1 << count); ++mask) {
                if (__builtin_popcount((unsigned)mask) != up || (empty && (mask & (1 << hole)))) continue;
                lookup[hole * (1 << count) + mask] = masks.size();
                masks.push_back(mask);
                vacancies.push_back(empty ? hole : -1);
            }
        }
    }
};

static std::map<int, Basis> bases;

static double smallest(const std::vector<double>& diagonal, const std::vector<double>& offdiag) {
    double lower = diagonal[0], upper = diagonal[0];
    int count = diagonal.size();
    for (int index = 0; index < count; ++index) {
        double radius = (index ? offdiag[index-1] : 0) + (index+1 < count ? offdiag[index] : 0);
        lower = std::min(lower, diagonal[index]-radius);
        upper = std::max(upper, diagonal[index]+radius);
    }
    for (int iteration = 0; iteration < 42; ++iteration) {
        double middle = (lower+upper)*0.5;
        double pivot = diagonal[0]-middle;
        int negative = pivot < 0;
        for (int index = 1; index < count; ++index) {
            if (std::abs(pivot) < 1e-24) pivot = -1e-24;
            pivot = diagonal[index]-middle-offdiag[index-1]*offdiag[index-1]/pivot;
            negative += pivot < 0;
        }
        if (negative) upper = middle; else lower = middle;
    }
    return (lower+upper)*0.5;
}

extern "C" double tj_energy(int sites, int holes, int up, const double* hopping,
                            const double* exchange, const double* onsite, int steps) {
    int key = sites*100+holes*20+up;
    if (!bases.count(key)) bases.emplace(key, Basis(sites,holes,up));
    const Basis& basis = bases.at(key);
    int dimension = basis.masks.size();
    std::vector<int> offsets(1,0), columns;
    std::vector<float> values, diagonal(dimension,0);
    columns.reserve(dimension*24);
    values.reserve(dimension*24);
    for (int row = 0; row < dimension; ++row) {
        int mask = basis.masks[row], hole = basis.vacancies[row];
        if (holes) diagonal[row] = onsite[hole];
        for (int first = 0; first < sites; ++first) {
            for (int second = first+1; second < sites; ++second) {
                double coupling = exchange[first*sites+second];
                if (first != hole && second != hole && coupling != 0 && (((mask>>first)^(mask>>second))&1)) {
                    diagonal[row] -= coupling*0.5;
                    int flipped = mask^(1<<first)^(1<<second);
                    int col = basis.lookup[(holes ? hole*(1<<sites):0)+flipped];
                    columns.push_back(col);
                    values.push_back(coupling*0.5);
                }
            }
        }
        if (holes) {
            for (int neighbor = 0; neighbor < sites; ++neighbor) {
                double strength = hopping[hole*sites+neighbor];
                if (strength == 0) continue;
                int flipped = (mask & (1<<neighbor)) ? mask^(1<<neighbor)^(1<<hole):mask;
                columns.push_back(basis.lookup[neighbor*(1<<sites)+flipped]);
                values.push_back((std::abs(hole-neighbor)%2 ? -1:1)*strength);
            }
        }
        offsets.push_back(columns.size());
    }
    std::vector<float> current(dimension), previous(dimension,0), result(dimension);
    uint64_t random = 317;
    double norm = 0;
    for (int row = 0; row < dimension; ++row) {
        random ^= random << 13;
        random ^= random >> 7;
        random ^= random << 17;
        current[row] = double(int(random&65535)-32768)/32768;
        norm += double(current[row])*current[row];
    }
    float scale = 1/std::sqrt(norm), beta = 0;
    for (float& value:current) value *= scale;
    std::vector<double> alphas, betas;
    double last = 1e100, estimate = 0;
    for (int iteration = 0; iteration < steps; ++iteration) {
        double alpha = 0;
        for (int row = 0; row < dimension; ++row) {
            float value = diagonal[row]*current[row]-beta*previous[row];
            for (int entry = offsets[row]; entry < offsets[row+1]; ++entry) value += values[entry]*current[columns[entry]];
            result[row] = value;
            alpha += double(value)*current[row];
        }
        norm = 0;
        for (int row = 0; row < dimension; ++row) {
            result[row] -= alpha*current[row];
            norm += double(result[row])*result[row];
        }
        beta = std::sqrt(norm);
        alphas.push_back(alpha);
        if (iteration >= 14 && (iteration%5 == 4 || iteration+1 == steps || beta < 1e-7)) {
            estimate = smallest(alphas,betas);
            if (last-estimate < 2e-7 || beta < 1e-7) break;
            last = estimate;
        }
        betas.push_back(beta);
        scale = 1/beta;
        for (int row = 0; row < dimension; ++row) {
            previous[row] = current[row];
            current[row] = result[row]*scale;
        }
    }
    return estimate;
}
