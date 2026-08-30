//===------- GridFunctions.h - GridFunctions wrapper for CPU or GPU. ------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Wrapper for GridFunctions file, choosing either CPU or GPU implementation.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_GRID_FUNCTIONS_H_
#define CONGA_GRID_FUNCTIONS_H_

// Declaring the fully templated version, so we can specialize below.
namespace conga {
template <typename T, typename DEV> struct GridFunctions {};
} // namespace conga

// TODO(patric): change to other define macros, since other compilers (clang or
// whatever) might enable host/device, but not CUDACC/HIPCC. See:
// https://docs.amd.com/bundle/HIP-Programming-Guide-v5.2/page/Transitioning_from_CUDA_to_HIP.html#d4439e822
#include "GridFunctions_CPU.h"
#if defined(__CUDACC__) or defined(__HIPCC__)
#include "GridFunctions_GPU.h"
#endif

#endif // CONGA_GRID_FUNCTIONS_H_
