//===-------------- GridFunctions_CPU.h - CPU grid functions. -------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// CPU-specific implementation of functions to operate on Grid functions, i.e.
/// thrust host vectors.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_GRID_FUNCTIONS_CPU_H_
#define CONGA_GRID_FUNCTIONS_CPU_H_

#include "../Type.h"
#include "../defines.h"
#include "../utils.h"

#include <thrust/device_vector.h>
#include <thrust/extrema.h>
#include <thrust/host_vector.h>

#include <cassert>
#include <cmath>

namespace conga {
///////////////////////////////////////////
// Code path for CPU (host) specific code
///////////////////////////////////////////
/*
// Declaring the fully templated version, so we can specialize below.
template <typename T, typename DEV>
struct GridFunctions
{};
*/
// Forward declaration.
template <typename, typename> class GridData;

template <typename T> struct GridFunctions<T, thrust::host_vector<T>> {
  GridData<T, thrust::host_vector<T>> *grid;

  GridFunctions(GridData<T, thrust::host_vector<T>> *ptr) : grid(ptr) {}

  template <typename T2>
  void typeConvert(GridData<T2, thrust::device_vector<T2>> &other) const;

  // Compute the complex magnitude squared, of specified field.
  void complexMagnitudeSq(GridData<T, thrust::host_vector<T>> *result) const;

  // Compute complex phase of this (complex) grid.
  void complexPhase(GridData<T, thrust::host_vector<T>> *result) const;

  // Compute gradient of complex phase of this grid.
  void complexPhaseGradient(GridData<T, thrust::host_vector<T>> *result,
                            const T h) const;

  /// \brief Compute the moment: 0.5 * sum(cross(r, grid)). Note that the only
  /// the z-component is returned.
  ///
  /// \param h The side length of a lattice site.
  ///
  /// \return The result.
  T moment(const T h) const;

  // Compute the magnitude of the real part of this vector field.
  void fieldMagnitude(GridData<T, thrust::host_vector<T>> *result) const;

  // Sum all fields.
  void sumFieldComponents(GridData<T, thrust::host_vector<T>> *result) const;

  // Change resolution of grid, with linear interpolation of existing data.
  void resample(const int inDimX, const int inDimY);

  // Find min and max value of range
  void minmax(const GridData<T, thrust::host_vector<T>> &grid, T &minv, T &maxv,
              int field, Type::type part) const;
};

namespace internal {
// Iterators
//
template <typename T, typename DEV, template <typename> class F>
void iterOne(const GridData<T, DEV> &dst, F<T> functor, int field = -1,
             Type::type part = Type::complex) {
  const int Nx = dst.dimX();
  const int Ny = dst.dimY();

  const int doReal = int(part == Type::real || part == Type::complex);
  const int doImag =
      int((part == Type::imag || part == Type::complex) && dst.isComplex());

  const Type::type parts[2] = {Type::real, Type::imag};

  const int c_begin = field == -1 ? 0 : field;
  const int c_end = field == -1 ? dst.numFields() : field + 1;

  int i, j, p, c, idx;
  T *data_dst;

  for (c = c_begin; c < c_end; ++c) {
    for (p = 1 - doReal; p < 1 + doImag; ++p) {
      data_dst = dst.getDataPointer(c, parts[p]);

      for (j = 0; j < Ny; ++j) {
        for (i = 0; i < Nx; ++i) {
          idx = j * Nx + i;
          data_dst[idx] = functor(data_dst[idx]);
        }
      }
    }
  }
}

template <typename T, typename DEV, template <typename> class F>
void iterTwo(const GridData<T, DEV> &src, GridData<T, DEV> &dst, F<T> functor,
             Type::type part = Type::complex, int fieldSrc = -1,
             int fieldDst = -1) {
  const int Nx = dst.dimX();
  const int Ny = dst.dimY();

  const int numFieldsSrc = src.numFields();
  const int numFieldsDst = dst.numFields();

  const Type::type parts[2] = {Type::real, Type::imag};

  const int doReal = int(part == Type::real || part == Type::complex);
  const int doImag =
      int((part == Type::imag || part == Type::complex) && src.isComplex());

  int c_end = 1, doAllFields = 0;

  if (fieldSrc == -1) {
    c_end = numFieldsSrc;
    doAllFields = 1;
  }

  int i, j, p, c, idx;
  T *data_src, *data_dst;

  for (c = 0; c < c_end; ++c) {
    fieldSrc = doAllFields ? c : fieldSrc;
    fieldDst = doAllFields ? c : fieldDst;

    fieldDst = fieldDst >= numFieldsDst ? numFieldsDst - 1 : fieldDst;

    for (p = 1 - doReal; p < 1 + doImag; ++p) {
      data_src = src.getDataPointer(fieldSrc, parts[p]);
      data_dst = dst.getDataPointer(fieldDst, parts[p]);

      for (j = 0; j < Ny; ++j) {
        for (i = 0; i < Nx; ++i) {
          idx = j * Nx + i;
          data_dst[idx] = functor(data_src[idx], data_dst[idx]);
        }
      }
    }
  }
}

template <typename T, typename DEV, template <typename> class F>
void iterTwoComplexToReal(const GridData<T, DEV> &src, GridData<T, DEV> &dst,
                          F<T> functor) {
  const int Nx = dst.dimX();
  const int Ny = dst.dimY();

  int i, j, c, idx;
  T *data_src_re, *data_src_im, *data_dst;

  for (c = 0; c < dst.numFields(); ++c) {
    data_src_re = src.getDataPointer(c, Type::real);
    data_src_im = src.getDataPointer(c, Type::imag);

    data_dst = dst.getDataPointer(c, Type::real);

    for (j = 0; j < Ny; ++j) {
      for (i = 0; i < Nx; ++i) {
        idx = j * Nx + i;
        data_dst[idx] = functor(data_src_re[idx], data_src_im[idx]);
      }
    }
  }
}

// Functors
//
template <typename T> struct EqFuncScalar {
  const T a;
  EqFuncScalar(T _a) : a(_a) {}
  T operator()(const T &dst) { return a; }
};

template <typename T> struct EqFuncGrid {
  EqFuncGrid() {}
  T operator()(const T &src, const T &dst) { return src; }
};

template <typename T> struct MultFuncOne {
  const T a;
  MultFuncOne(T _a) : a(_a) {}
  T operator()(const T &dst) { return a * dst; }
};

template <typename T> struct MultFuncTwo {
  MultFuncTwo() {}
  T operator()(const T &src, const T &dst) { return src * dst; }
};

template <typename T> struct AddFuncOne {
  const T a;
  AddFuncOne(T _a) : a(_a) {}
  T operator()(const T &dst) { return a + dst; }
};

template <typename T> struct AddFuncTwo {
  AddFuncTwo() {}
  T operator()(const T &src, const T &dst) { return src + dst; }
};

template <typename T> struct SubFuncTwo {
  SubFuncTwo() {}
  T operator()(const T &src, const T &dst) { return dst - src; }
};

template <typename T> struct ComplexMagnitudeSqFunc {
  ComplexMagnitudeSqFunc() {}
  T operator()(const T inReal, const T inImag) {
    return inReal * inReal + inImag * inImag;
  }
};

template <typename T> struct ComplexPhaseFunc {
  ComplexPhaseFunc() {}
  T operator()(const T inReal, const T inImag) { return atan2(inImag, inReal); }
};

template <typename T> struct FieldMagnitudeFunc {
  FieldMagnitudeFunc() {}
  T operator()(const T &src, const T &dst) { return dst + src * src; }
};

template <typename T> struct SqrtFunc {
  SqrtFunc() {}
  T operator()(const T &dst) { return std::sqrt(dst); }
};

template <typename T> struct LogFunc {
  const T a;
  LogFunc(T _a) : a(_a) {}
  T operator()(const T &dst) { return std::log(dst + a); }
};
} // namespace internal

template <typename T>
template <typename T2>
void GridFunctions<T, thrust::host_vector<T>>::typeConvert(
    GridData<T2, thrust::device_vector<T2>> &other) const {
  other.getVector() = grid->getVector();
}

template <typename T>
void GridFunctions<T, thrust::host_vector<T>>::complexMagnitudeSq(
    GridData<T, thrust::host_vector<T>> *result) const {
  iterTwoComplexToReal(*grid, *result, internal::ComplexMagnitudeSqFunc<T>());
}

template <typename T>
void GridFunctions<T, thrust::host_vector<T>>::complexPhase(
    GridData<T, thrust::host_vector<T>> *result) const {
  iterTwoComplexToReal(*grid, *result, internal::ComplexPhaseFunc<T>());
}

template <typename T>
T GridFunctions<T, thrust::host_vector<T>>::moment(const T h) const {
  // Sanity check.
  assert(grid->numFields() == 2);
  assert(grid->representation() == Type::real);

  // Get pointers.
  const T *const srcX = grid->getDataPointer(0, Type::real);
  const T *const srcY = grid->getDataPointer(1, Type::real);

  // Dimensions.
  const int dimX = grid->dimX();
  const int dimY = grid->dimY();

  // Coordinate of the center.
  const T centerX = static_cast<T>(0.5) * static_cast<T>(dimX - 1);
  const T centerY = static_cast<T>(0.5) * static_cast<T>(dimY - 1);

  // Do cross product and sum.
  T sum = static_cast<T>(0);
  for (int yIdx = 0; yIdx < dimY; ++yIdx) {
    for (int xIdx = 0; xIdx < dimX; ++xIdx) {
      const int idx = yIdx * dimY + xIdx;
      const T x = static_cast<T>(xIdx) - centerX;
      const T y = static_cast<T>(yIdx) - centerY;
      sum += x * srcY[idx] - y * srcX[idx];
    }
  }

  // Two factors of h comes from the integral, the other from the position
  // vector.
  const T factor = static_cast<T>(0.5) * h * h * h;
  const T result = factor * sum;

  return result;
}

template <typename T>
void GridFunctions<T, thrust::host_vector<T>>::fieldMagnitude(
    GridData<T, thrust::host_vector<T>> *result) const {
  result->setZero();
  iterTwo(*grid, *result, internal::FieldMagnitudeFunc<T>(), Type::real);
  result->sqrt();
}

template <typename T>
void GridFunctions<T, thrust::host_vector<T>>::sumFieldComponents(
    GridData<T, thrust::host_vector<T>> *result) const {
  result->setZero();
  iterTwo(*grid, *result, internal::AddFuncTwo<T>(), grid->representation());
}

template <typename T>
void GridFunctions<T, thrust::host_vector<T>>::complexPhaseGradient(
    GridData<T, thrust::host_vector<T>> *result, const T h) const {
  const int Nx = grid->_dimX;
  const int Ny = grid->_dimY;

  T *data_src_re = grid->getDataPointer(0, Type::real);
  T *data_src_im = grid->getDataPointer(0, Type::imag);
  T *data_dst_x = result->getDataPointer(0, Type::real);
  T *data_dst_y = result->getDataPointer(1, Type::real);

  T f0, f1, f2, g0, g1, g2, denom, dPhase_dx, dPhase_dy;

  // Grid index
  int idx, idx_x0, idx_x2, idx_y0, idx_y2;

  // Set gradient to zero at borders for now. Implement other gradient methods
  // later!
  dPhase_dx = (T)0.0;
  dPhase_dy = (T)0.0;

  for (int ty = 0; ty < Ny; ++ty) {
    for (int tx = 0; tx < Nx; ++tx) {
      dPhase_dx = (T)0.0;
      dPhase_dy = (T)0.0;

      idx = ty * Nx + tx;

      if (tx > 0 && tx < Nx - 1 && ty > 0 && ty < Ny - 1) {
        idx_x0 = ty * Nx + (tx - 1);
        idx_x2 = ty * Nx + (tx + 1);

        idx_y0 = (ty - 1) * Nx + tx;
        idx_y2 = (ty + 1) * Nx + tx;

        // Read elements at current grid point
        f1 = data_src_im[idx];
        g1 = data_src_re[idx];

        // Some precomputed quantities
        denom = (T)2.0 * h * (f1 * f1 + g1 * g1);

        if (denom > (T)0.00001) {
          denom = (T)1.0 / denom;

          // Gradient in x
          f0 = data_src_im[idx_x0];
          g0 = data_src_re[idx_x0];

          f2 = data_src_im[idx_x2];
          g2 = data_src_re[idx_x2];

          dPhase_dx = ((f2 - f0) * g1 - f1 * (g2 - g0)) * denom;

          // Gradient in y
          f0 = data_src_im[idx_y0];
          f2 = data_src_im[idx_y2];

          g0 = data_src_re[idx_y0];
          g2 = data_src_re[idx_y2];

          dPhase_dy = ((f2 - f0) * g1 - f1 * (g2 - g0)) * denom;
        }
      }

      data_dst_x[idx] = dPhase_dx;
      data_dst_y[idx] = dPhase_dy;
    }
  }
}

template <typename T>
void GridFunctions<T, thrust::host_vector<T>>::resample(const int inDimX,
                                                        const int inDimY) {
  const int isComplex = int(grid->isComplex());
  const int dimZ = grid->numFields() * (1 + isComplex);
  const int numElements = inDimX * inDimY * dimZ;

  // Allocate vector for new grid.
  thrust::host_vector<T> dst(numElements);

  // Get the old spatial dimensions.
  const int oldDimX = grid->dimX();
  const int oldDimY = grid->dimY();

  // Get the old data.
  const thrust::host_vector<T> &src = grid->getVector();

  // We have a number of safety pixels along each edge of the simulation space.
  // These pixels should not be a part of the interpolation.
  // TODO(Niclas): If we change the margin size then we need to read the margin
  // from file. And have two inputs to this function: marginOld and marginNew.
  const int margin = constants::GRAIN_SIZE_MARGIN;
  const int twoMargin = 2 * margin;

  for (int z = 0; z < dimZ; ++z) {
    for (int y = 0; y < inDimY; ++y) {
      for (int x = 0; x < inDimX; ++x) {
        // Scaling factor between grids.
        // The safety margin should not be included in the scales.
        const T xScale = static_cast<T>(oldDimX - 1 - twoMargin) /
                         static_cast<T>(inDimX - 1 - twoMargin);
        const T yScale = static_cast<T>(oldDimY - 1 - twoMargin) /
                         static_cast<T>(inDimY - 1 - twoMargin);

        // Coordinates in old grid.
        const T xOld = xScale * static_cast<T>(x - margin) + margin;
        const T yOld = yScale * static_cast<T>(y - margin) + margin;

        // Floor coordinates.
        const int xFloor = static_cast<int>(xOld);
        const int yFloor = static_cast<int>(yOld);

        // Fractions.
        const T xFrac = xOld - static_cast<T>(xFloor);
        const T yFrac = yOld - static_cast<T>(yFloor);

        // What to add to the index to get the next pixel. If there is no next
        // pixel the value is zero.
        const int xNext = x < inDimX - 1 ? 1 : 0;
        const int yNext = y < inDimY - 1 ? oldDimX : 0;

        // Indices to interpolate with.
        const int idx00 = (z * oldDimY + yFloor) * oldDimX + xFloor;
        const int idx01 = idx00 + xNext;
        const int idx10 = idx00 + yNext;
        const int idx11 = idx10 + xNext;

        const T x1_interp =
            (static_cast<T>(1) - xFrac) * src[idx00] + xFrac * src[idx01];

        const T x2_interp =
            (static_cast<T>(1) - xFrac) * src[idx10] + xFrac * src[idx11];

        const int idx = (z * inDimY + y) * inDimX + x;
        dst[idx] = (static_cast<T>(1) - yFrac) * x1_interp + yFrac * x2_interp;
      }
    }
  }

  // Change affected class member variables.
  grid->_dimX = inDimX;
  grid->_dimY = inDimY;
  grid->m_vector = dst;
}

template <typename T>
void GridFunctions<T, thrust::host_vector<T>>::minmax(
    const GridData<T, thrust::host_vector<T>> &grid, T &minv, T &maxv,
    int field, Type::type part) const {
  const thrust::host_vector<T> &vec = grid.getVector();

  const size_t start = grid.getFieldComponentOffset(field, part);
  const size_t end = start + grid.dimX() * grid.dimY();

  const auto result =
      thrust::minmax_element(vec.begin() + start, vec.begin() + end);

  minv = *result.first;
  maxv = *result.second;
}
} // namespace conga

#endif // CONGA_GRID_FUNCTIONS_CPU_H_
