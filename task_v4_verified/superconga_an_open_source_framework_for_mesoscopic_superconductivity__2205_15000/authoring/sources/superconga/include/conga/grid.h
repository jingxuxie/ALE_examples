//===------------- grid.h - GridData wrapper for CPU or GPU. -------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Wrapper for GridData class type, choosing either host or device for CPU or
/// GPU. Also has convenient shortened definitions for data structures.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_GRID_H_
#define CONGA_GRID_H_

#include "configure.h"

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

// TODO(patric): change to other define macros, since other compilers (clang or
// whatever) might enable host/device, but not CUDACC/HIPCC. See:
// https://docs.amd.com/bundle/HIP-Programming-Guide-v5.2/page/Transitioning_from_CUDA_to_HIP.html#d4439e822
#if defined(__CUDACC__) or defined(__HIPCC__)
#define _DEV_ __host__ __device__
#else
#define _DEV_
#endif

#include "grid/GridData.h"

#include <thrust/device_vector.h>
#include <thrust/host_vector.h>

namespace conga {
// TODO(patric): change to other define macros, since other compilers (clang or
// whatever) might enable host/device, but not CUDACC/HIPCC. See:
// https://docs.amd.com/bundle/HIP-Programming-Guide-v5.2/page/Transitioning_from_CUDA_to_HIP.html#d4439e822
#if defined(__CUDACC__) or defined(__HIPCC__)
template <typename T> using VectorGPU = thrust::device_vector<T>;
template <typename T> using GridGPU = GridData<T, thrust::device_vector<T>>;
#else
template <typename T> using VectorGPU = thrust::host_vector<T>;
template <typename T> using GridGPU = GridData<T, thrust::host_vector<T>>;
#endif

template <typename T> using VectorCPU = thrust::host_vector<T>;
template <typename T> using GridCPU = GridData<T, thrust::host_vector<T>>;
} // namespace conga

#endif // CONGA_GRID_H_
