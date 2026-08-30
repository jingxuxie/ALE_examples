#include <cmath>
#include <algorithm>
#include <cstring>
#include <omp.h>

constexpr int size = 24;
constexpr int cells = size * size;
const int groups[12] = {0,0,1,0,1,1,0,1,0,1,1,0};

void rotate(double* matrix, int first, int second, double cosine, double sine) {
    for (int column = 0; column < size; ++column) {
        double lower = matrix[first*size+column];
        double upper = matrix[second*size+column];
        matrix[first*size+column] = cosine*lower+sine*upper;
        matrix[second*size+column] = -sine*lower+cosine*upper;
    }
    for (int row = 0; row < size; ++row) {
        double lower = matrix[row*size+first];
        double upper = matrix[row*size+second];
        matrix[row*size+first] = cosine*lower+sine*upper;
        matrix[row*size+second] = -sine*lower+cosine*upper;
    }
}

double inverse(double* matrix, double* output) {
    std::fill(output, output+cells, 0.0);
    for (int index = 0; index < size; ++index) output[index*size+index] = 1.0;
    double determinant = 1.0;
    for (int column = 0; column < size; ++column) {
        int pivot = column;
        for (int row = column+1; row < size; ++row)
            if (std::abs(matrix[row*size+column]) > std::abs(matrix[pivot*size+column])) pivot = row;
        if (pivot != column) {
            for (int index = 0; index < size; ++index) {
                std::swap(matrix[column*size+index], matrix[pivot*size+index]);
                std::swap(output[column*size+index], output[pivot*size+index]);
            }
            determinant = -determinant;
        }
        double scale = matrix[column*size+column];
        determinant *= scale;
        if (std::abs(scale) < 1e-24) return 0.0;
        for (int index = 0; index < size; ++index) {
            matrix[column*size+index] /= scale;
            output[column*size+index] /= scale;
        }
        for (int row = 0; row < size; ++row) {
            if (row == column) continue;
            double factor = matrix[row*size+column];
            for (int index = 0; index < size; ++index) {
                matrix[row*size+index] -= factor*matrix[column*size+index];
                output[row*size+index] -= factor*output[column*size+index];
            }
        }
    }
    return determinant;
}

void single(const double* angles, const double* errors, double* fidelity, double* gradient) {
    double state[cells] = {};
    double history[24][cells];
    double bond_cosine[12], bond_sine[12];
    double kick_cosine[24][2], kick_sine[24][2];
    int partner[size];
    double sign[size];
    for (int site = 0; site < 12; ++site) {
        state[(2*site)*size+2*site+1] = 1.0;
        state[(2*site+1)*size+2*site] = -1.0;
        int first = 2*site+1, second = (2*site+2)%size;
        partner[first] = second;
        partner[second] = first;
        sign[first] = site == 11 ? -1.0 : 1.0;
        sign[second] = -sign[first];
        double angle = -M_PI/2*(1.0+errors[2]+errors[3+site])*(site == 11 ? -1.0 : 1.0);
        bond_cosine[site] = std::cos(angle);
        bond_sine[site] = std::sin(angle);
    }
    for (int layer = 0; layer < 24; ++layer) {
        for (int edge = layer%2; edge < 12; edge += 2)
            rotate(state, 2*edge+1, (2*edge+2)%size, bond_cosine[edge], bond_sine[edge]);
        for (int group = 0; group < 2; ++group) {
            double angle = angles[2*layer+group]*(1.0+errors[group]);
            kick_cosine[layer][group] = std::cos(angle);
            kick_sine[layer][group] = std::sin(angle);
        }
        for (int site = 0; site < 12; ++site)
            rotate(state, 2*site, 2*site+1, kick_cosine[layer][groups[site]], kick_sine[layer][groups[site]]);
        std::memcpy(history[layer], state, sizeof(state));
    }
    double matrix[cells], inverted[cells], adjoint[cells];
    for (int row = 0; row < size; ++row)
        for (int column = 0; column < size; ++column)
            matrix[row*size+column] = (row == column ? 1.0 : 0.0)-sign[row]*state[partner[row]*size+column];
    double determinant = inverse(matrix, inverted);
    *fidelity = std::sqrt(std::abs(determinant))/4096.0;
    for (int row = 0; row < size; ++row)
        for (int column = 0; column < size; ++column)
            adjoint[row*size+column] = -0.5*(*fidelity)*inverted[column*size+partner[row]]*sign[partner[row]];
    std::fill(gradient, gradient+48, 0.0);
    for (int layer = 23; layer >= 0; --layer) {
        const double* current = history[layer];
        for (int site = 0; site < 12; ++site) {
            int first = 2*site, second = first+1;
            double derivative = 0.0;
            for (int index = 0; index < size; ++index) {
                derivative += adjoint[first*size+index]*current[second*size+index]
                    - adjoint[second*size+index]*current[first*size+index]
                    + adjoint[index*size+first]*current[index*size+second]
                    - adjoint[index*size+second]*current[index*size+first];
            }
            gradient[2*layer+groups[site]] += derivative*(1.0+errors[groups[site]]);
        }
        for (int site = 0; site < 12; ++site)
            rotate(adjoint, 2*site, 2*site+1, kick_cosine[layer][groups[site]], -kick_sine[layer][groups[site]]);
        for (int edge = layer%2; edge < 12; edge += 2)
            rotate(adjoint, 2*edge+1, (2*edge+2)%size, bond_cosine[edge], -bond_sine[edge]);
    }
}

extern "C" void evaluate(const double* angles, const double* errors, int count, double* fidelities, double* gradients) {
    #pragma omp parallel for num_threads(4) schedule(static)
    for (int scenario = 0; scenario < count; ++scenario)
        single(angles, errors+15*scenario, fidelities+scenario, gradients+48*scenario);
}
