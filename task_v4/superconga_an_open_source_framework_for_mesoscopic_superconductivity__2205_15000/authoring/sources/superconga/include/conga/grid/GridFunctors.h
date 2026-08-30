//===---------- GridFunctors.h - Functors used by Grid data class. --------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Functors used by Grid data class, in the iterator-algorithm transformation
/// functions: these functors are used in operations between GridData objects
/// (and therefore thrust vectors).
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_GRID_FUNCTORS_H_
#define CONGA_GRID_FUNCTORS_H_

#include <cmath>

// TODO(patric): change to other define macros, since other compilers (clang or
// whatever) might enable host/device, but not CUDACC/HIPCC. See:
// https://docs.amd.com/bundle/HIP-Programming-Guide-v5.2/page/Transitioning_from_CUDA_to_HIP.html#d4439e822
#if defined(__CUDACC__) or defined(__HIPCC__)
#define __HD__ __host__ __device__
#else
#define __HD__
#endif

namespace conga {
namespace GridFunctors {

template <typename T> struct squareRoot {
  __HD__
  void operator()(T &val) { val = std::sqrt(val); }
};

template <typename T> struct absVal {
  __HD__
  void operator()(T &val) { val = std::abs(val); }
};
} // namespace GridFunctors
} // namespace conga

#endif // CONGA_GRID_FUNCTORS_H_
