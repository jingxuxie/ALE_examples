#include <array>
#include <cmath>
#include <complex>

using Real = double;
using Complex = std::complex<Real>;
using Vector = std::array<Real, 4>;

template <int Rows, int Columns>
struct Matrix {
    Complex values[Rows][Columns]{};
    Matrix& operator+=(const Matrix& other) {
        for (int row = 0; row < Rows; ++row)
            for (int column = 0; column < Columns; ++column)
                values[row][column] += other.values[row][column];
        return *this;
    }
};

template <int Rows, int Inner, int Columns>
Matrix<Rows, Columns> operator*(const Matrix<Rows, Inner>& left,
                               const Matrix<Inner, Columns>& right) {
    Matrix<Rows, Columns> result;
    for (int row = 0; row < Rows; ++row)
        for (int inner = 0; inner < Inner; ++inner)
            for (int column = 0; column < Columns; ++column)
                result.values[row][column] += left.values[row][inner] * right.values[inner][column];
    return result;
}

Vector operator+(const Vector& left, const Vector& right) {
    Vector result;
    for (int axis = 0; axis < 4; ++axis) result[axis] = left[axis] + right[axis];
    return result;
}

Vector operator-(const Vector& left, const Vector& right) {
    Vector result;
    for (int axis = 0; axis < 4; ++axis) result[axis] = left[axis] - right[axis];
    return result;
}

Vector operator*(Real scale, const Vector& vector) {
    Vector result;
    for (int axis = 0; axis < 4; ++axis) result[axis] = scale * vector[axis];
    return result;
}

Real dot(const Vector& left, const Vector& right) {
    return left[0] * right[0] - left[1] * right[1] - left[2] * right[2] - left[3] * right[3];
}

Matrix<4, 4> slash(const Vector& vector) {
    Matrix<4, 4> result;
    const Complex upper(vector[1], -vector[2]);
    const Complex lower(vector[1], vector[2]);
    result.values[0][0] = vector[0];
    result.values[1][1] = vector[0];
    result.values[2][2] = -vector[0];
    result.values[3][3] = -vector[0];
    result.values[0][2] = -vector[3];
    result.values[0][3] = -upper;
    result.values[1][2] = -lower;
    result.values[1][3] = vector[3];
    result.values[2][0] = vector[3];
    result.values[2][1] = upper;
    result.values[3][0] = lower;
    result.values[3][1] = -vector[3];
    return result;
}

Vector cubic(const Vector& left, const Vector& right,
             const Vector& left_p, const Vector& right_p) {
    return dot(left, right) * (left_p - right_p)
        + dot(left_p + 2.0 * right_p, left) * right
        - dot(2.0 * left_p + right_p, right) * left;
}

Vector cross(const Vector& left, const Vector& right) {
    return {0, left[2] * right[3] - left[3] * right[2],
            left[3] * right[1] - left[1] * right[3],
            left[1] * right[2] - left[2] * right[1]};
}

std::array<Vector, 2> polarizations(const Vector& momentum) {
    Vector direction = (1.0 / momentum[0]) * momentum;
    direction[0] = 0;
    int smallest = 1;
    for (int axis = 2; axis < 4; ++axis)
        if (std::abs(direction[axis]) < std::abs(direction[smallest])) smallest = axis;
    Vector basis{};
    basis[smallest] = 1;
    Vector first = cross(direction, basis);
    first = (1.0 / std::sqrt(-dot(first, first))) * first;
    return {first, cross(direction, first)};
}

Real ordered(const std::array<Vector, 5>& momenta, const Real invariants[5][5],
             bool reverse) {
    const int quark_index = reverse ? 1 : 0;
    const int anti_index = reverse ? 0 : 1;
    const Vector& quark = momenta[quark_index];
    const Vector& anti = momenta[anti_index];
    Vector momentum[3][4]{};
    Real denominator[3][4]{};
    for (int start = 0; start < 3; ++start) {
        for (int stop = start + 1; stop <= 3; ++stop) {
            momentum[start][stop] = momentum[start][stop - 1] + momenta[stop + 1];
            for (int first = start; first < stop; ++first)
                for (int second = first + 1; second < stop; ++second)
                    denominator[start][stop] += invariants[first + 2][second + 2];
        }
    }
    Matrix<4, 4> left_propagator[4];
    Matrix<4, 4> right_propagator[4];
    for (int split = 1; split <= 3; ++split) {
        Real mass = denominator[0][split];
        for (int gluon = 0; gluon < split; ++gluon) mass += invariants[quark_index][gluon + 2];
        left_propagator[split] = slash((1.0 / mass) * (quark + momentum[0][split]));
    }
    for (int split = 0; split < 3; ++split) {
        Real mass = denominator[split][3];
        for (int gluon = split; gluon < 3; ++gluon) mass += invariants[anti_index][gluon + 2];
        right_propagator[split] = slash((-1.0 / mass) * (anti + momentum[split][3]));
    }
    Matrix<2, 4> quark_spinor;
    Matrix<4, 2> anti_spinor;
    const Real quark_scale = std::sqrt(quark[0]);
    const Real anti_scale = std::sqrt(anti[0]);
    quark_spinor.values[0][0] = quark_scale;
    quark_spinor.values[1][1] = quark_scale;
    quark_spinor.values[0][2] = -quark[3] / quark_scale;
    quark_spinor.values[0][3] = -Complex(quark[1], -quark[2]) / quark_scale;
    quark_spinor.values[1][2] = -Complex(quark[1], quark[2]) / quark_scale;
    quark_spinor.values[1][3] = quark[3] / quark_scale;
    anti_spinor.values[0][0] = anti[3] / anti_scale;
    anti_spinor.values[0][1] = Complex(anti[1], -anti[2]) / anti_scale;
    anti_spinor.values[1][0] = Complex(anti[1], anti[2]) / anti_scale;
    anti_spinor.values[1][1] = -anti[3] / anti_scale;
    anti_spinor.values[2][0] = anti_scale;
    anti_spinor.values[3][1] = anti_scale;
    std::array<Vector, 2> polarization[3];
    for (int gluon = 0; gluon < 3; ++gluon) polarization[gluon] = polarizations(momenta[gluon + 2]);
    Matrix<4, 4> photon[3];
    for (int axis = 0; axis < 3; ++axis) {
        Vector basis{};
        basis[axis + 1] = -1;
        photon[axis] = slash(basis);
    }
    Real result = 0;
    for (int helicity = 0; helicity < 8; ++helicity) {
        Vector current[3][4]{};
        Matrix<4, 4> vertex[3][4];
        for (int gluon = 0; gluon < 3; ++gluon)
            current[gluon][gluon + 1] = polarization[gluon][(helicity >> gluon) & 1];
        for (int size = 2; size <= 3; ++size) {
            for (int start = 0; start + size <= 3; ++start) {
                const int stop = start + size;
                Vector value{};
                for (int middle = start + 1; middle < stop; ++middle)
                    value = value - cubic(current[start][middle], current[middle][stop],
                                          momentum[start][middle], momentum[middle][stop]);
                if (size == 3) {
                    const Vector& first = current[0][1];
                    const Vector& second = current[1][2];
                    const Vector& third = current[2][3];
                    value = value + 2.0 * dot(first, third) * second
                        - dot(second, third) * first - dot(first, second) * third;
                }
                current[start][stop] = (1.0 / denominator[start][stop]) * value;
            }
        }
        for (int start = 0; start < 3; ++start)
            for (int stop = start + 1; stop <= 3; ++stop)
                vertex[start][stop] = slash(current[start][stop]);
        Matrix<2, 4> left[4];
        Matrix<4, 2> right[4];
        left[0] = quark_spinor;
        right[3] = anti_spinor;
        for (int stop = 1; stop <= 3; ++stop) {
            Matrix<2, 4> total;
            for (int start = 0; start < stop; ++start) total += left[start] * vertex[start][stop];
            left[stop] = total * left_propagator[stop];
        }
        for (int start = 2; start >= 0; --start) {
            Matrix<4, 2> total;
            for (int stop = start + 1; stop <= 3; ++stop) total += vertex[start][stop] * right[stop];
            right[start] = right_propagator[start] * total;
        }
        for (int axis = 0; axis < 3; ++axis) {
            Matrix<2, 2> amplitude;
            for (int split = 0; split <= 3; ++split) amplitude += (left[split] * photon[axis]) * right[split];
            for (int row = 0; row < 2; ++row)
                for (int column = 0; column < 2; ++column) result += std::norm(amplitude.values[row][column]);
        }
    }
    return result;
}

extern "C" void predict_kernel(const double* input_p, const double* input_s,
                               double* output, long count) {
    for (long event = 0; event < count; ++event) {
        std::array<Vector, 5> momenta;
        for (int particle = 0; particle < 5; ++particle) {
            const double* source = input_p + event * 20 + particle * 4;
            momenta[particle] = {source[3], source[0], source[1], source[2]};
        }
        Real invariants[5][5]{};
        int index = 0;
        for (int first = 0; first < 5; ++first)
            for (int second = first + 1; second < 5; ++second) {
                invariants[first][second] = invariants[second][first] = input_s[event * 10 + index];
                ++index;
            }
        const Real forward = ordered(momenta, invariants, false);
        const Real backward = ordered(momenta, invariants, true);
        output[event] = std::log((forward + backward) / 16.0);
    }
}
