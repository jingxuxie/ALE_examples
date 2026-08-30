//===---- check_gpu_error.h - Wrapper function for handling GPU errors ----===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Following recommended practices for catching and displaying GPU errors from
/// CUDA/HIP.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_CHECK_GPU_ERROR_H_
#define CONGA_CHECK_GPU_ERROR_H_

#if CONGA_HIP
#include <hip/hip_runtime.h>

// Handle errors from HIP.
#define CHECK_GPU_ERROR(val)                                                   \
  checkGpuErrorWrapper((val), #val, __FILE__, __LINE__)
template <typename T>
void checkGpuErrorWrapper(T inError, const char *const inFunction,
                          const char *const inFile, const int inLine) {
  if (inError != hipSuccess) {
    std::cerr << "HIP Runtime Error at: " << inFile << ":" << inLine
              << std::endl;
    std::cerr << hipGetErrorString(inError) << " " << inFunction << std::endl;
  }
}

#elif CONGA_CUDA
#include <cuda.h>

// Handle errors from CUDA.
#define CHECK_GPU_ERROR(val)                                                   \
  checkGpuErrorWrapper((val), #val, __FILE__, __LINE__)
template <typename T>
void checkGpuErrorWrapper(T inError, const char *const inFunction,
                          const char *const inFile, const int inLine) {
  if (inError != cudaSuccess) {
    std::cerr << "CUDA Runtime Error at: " << inFile << ":" << inLine
              << std::endl;
    std::cerr << cudaGetErrorString(inError) << " " << inFunction << std::endl;
  }
}
#endif

#endif // CONGA_CHECK_GPU_ERROR_H_