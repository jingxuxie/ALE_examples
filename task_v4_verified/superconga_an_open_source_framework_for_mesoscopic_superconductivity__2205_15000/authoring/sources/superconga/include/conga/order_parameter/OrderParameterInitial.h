//===-------------- OrderParameterInitial.h - Polygon class. --------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Collection of functions to set the initial condition of the order parameter.
/// All member functions are static so this struct should not be instantiated.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_ORDER_PARAMETER_INITIAL_H_
#define CONGA_ORDER_PARAMETER_INITIAL_H_

#include "../arg.h"
#include "../configure.h"
#include "../defines.h"
#include "../grid.h"
#include "../utils.h"

#if CONGA_HIP
#include <hip/hip_runtime.h>
#include <hiprand.h>
#include <hiprand_kernel.h>
#elif CONGA_CUDA
#include <cuda.h>
#include <curand.h>
#include <curand_kernel.h>
#endif

#include <thrust/complex.h>
#include <thrust/device_vector.h>

#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
#include <vector>

namespace conga {
/// @brief Struct describing a single vortex.
/// @tparam T Float or double.
template <typename T> struct Vortex {
public:
  /// @brief Vortex constructor.
  /// @param inWindingNumber The winding number of the (centered) vortex.
  Vortex(const T inWindingNumber) : m_windingNumber(inWindingNumber) {}

  // The winding number.
  CONGA_ARG(T, windingNumber);

  // The vortex center.
  CONGA_ARG(vector2d<T>, center) = {static_cast<T>(0), static_cast<T>(0)};
};

namespace internal {
/// @brief Kernel for perturbedPhaseWinding.
/// @tparam T Floating point precision (single or double).
/// @param inNumX Number of x lattice-points in geometry.
/// @param inNumY Number of y lattice-points in geometry.
/// @param inMagnitude Overall amplitude.
/// @param inPhase Overall phase.
/// @param inNoiseStdDev Standard deviation of the additive Gaussian noise.
/// @param inNumVortices Number of vortices.
/// @param inNumWindings List with the phase winding around each vortex.
/// @param inCentersX Center x-coordinate for each vortex: [-0.5, 0.5].
/// @param inCentersY Center y-coordinate for each vortex: [-0.5, 0.5].
/// @param outReal Real part of order parameter.
/// @param outImag Imag part of order parameter.
template <typename T>
__global__ void perturbedPhaseWindingKernel(
    const int inNumX, const int inNumY, const T inMagnitude, const T inPhase,
    const T inNoiseStdDev, const int inNumVortices,
    const T *const inNumWindings, const T *const inCentersX,
    const T *const inCentersY, T *const outReal, T *const outImag) {
  // Discrete coordinates in discretized order parameter lattice.
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  const int j = blockIdx.y * blockDim.y + threadIdx.y;

  // Check that coordinates lie within geometry.
  if (i < inNumX && j < inNumY) {
    // Normalize coordinates to [-MAXIMUM_COORDINATE, MAXIMUM_COORDINATE].
    const T scale = static_cast<T>(2 * constants::MAXIMUM_COORDINATE);
    const T x = scale * (static_cast<T>(i) / static_cast<T>(inNumX - 1) -
                         static_cast<T>(0.5));
    const T y = scale * (static_cast<T>(j) / static_cast<T>(inNumY - 1) -
                         static_cast<T>(0.5));

    // The phase without vortices.
    T phase = inPhase;

    // Loop over vortices and add the phase.
    for (int vortexIdx = 0; vortexIdx < inNumVortices; ++vortexIdx) {
      const T offsetX = x - inCentersX[vortexIdx];
      const T offsetY = y - inCentersY[vortexIdx];
      const T radius = hypot(offsetX, offsetY);

      // Avoid x=y=0.
      const T angle = radius > static_cast<T>(0) ? atan2(offsetY, offsetX)
                                                 : static_cast<T>(0.0);

      // Compute the total phase.
      phase += angle * inNumWindings[vortexIdx];
    }

    // Compute unique coordinate index (for storage and seed).
    const int idx = j * inNumX + i;

    // Generate state and seed for random number:
    // CUDA: https://docs.nvidia.com/cuda/curand/device-api-overview.html
    // HIP/ROCm: https://rocrand.readthedocs.io/en/latest/
    const unsigned int seed = static_cast<unsigned int>(clock());
    const int seedSubSequence = idx;
    const int seedOffsetPerCall = 0;
#if CONGA_HIP
    hiprandState state;
    hiprand_init(seed, seedSubSequence, seedOffsetPerCall, &state);

    // Noise.
    const T realNoise =
        inNoiseStdDev * static_cast<T>(hiprand_normal_double(&state));
    const T imagNoise =
        inNoiseStdDev * static_cast<T>(hiprand_normal_double(&state));
#elif CONGA_CUDA
    curandState state;
    curand_init(seed, seedSubSequence, seedOffsetPerCall, &state);

    // Noise.
    const T realNoise =
        inNoiseStdDev * static_cast<T>(curand_normal_double(&state));
    const T imagNoise =
        inNoiseStdDev * static_cast<T>(curand_normal_double(&state));
#endif

    // Store result.
    outReal[idx] = inMagnitude * cos(phase) + realNoise;
    outImag[idx] = inMagnitude * sin(phase) + imagNoise;
  }
}
} // namespace internal

template <typename T>
void perturbedPhaseWindings(const thrust::complex<T> &inValue,
                            const T inNoiseStdDev,
                            const std::vector<Vortex<T>> &inVortices,
                            GridGPU<T> &inOutGrid) {
  // Sanity checks.
  assert(inOutGrid.numFields() == 1);
  assert(inOutGrid.representation() == Type::complex);

  // The order parameter bulk value (perhaps).
  const T magnitude = thrust::abs(inValue);
  const T phase = thrust::arg(inValue);

  // Number of lattice points in order parameter lattice.
  const int dimX = inOutGrid.dimX();
  const int dimY = inOutGrid.dimY();

  // Calculate GPU thread blocks.
  const auto [blocksPerGrid, threadsPerBlock] = inOutGrid.getKernelDimensions();

  // Copy vortices to CPU vectors.
  thrust::host_vector<T> vortexWindingNumbers;
  thrust::host_vector<T> vortexCentersX;
  thrust::host_vector<T> vortexCentersY;
  for (const auto &vortex : inVortices) {
    vortexWindingNumbers.push_back(vortex.windingNumber());
    vortexCentersX.push_back(vortex.center()[0]);
    vortexCentersY.push_back(vortex.center()[1]);
  }

  // Copy to the GPU.
  const thrust::device_vector<T> numWindingsGPU(vortexWindingNumbers);
  const thrust::device_vector<T> centersXGPU(vortexCentersX);
  const thrust::device_vector<T> centersYGPU(vortexCentersY);

  // Number of vortices.
  const int numVortices = static_cast<int>(inVortices.size());

  // Call GPU kernel.
  internal::perturbedPhaseWindingKernel<<<blocksPerGrid, threadsPerBlock>>>(
      dimX, dimY, magnitude, phase, inNoiseStdDev, numVortices,
      thrust::raw_pointer_cast(numWindingsGPU.data()),
      thrust::raw_pointer_cast(centersXGPU.data()),
      thrust::raw_pointer_cast(centersYGPU.data()),
      inOutGrid.getDataPointer(0, Type::real),
      inOutGrid.getDataPointer(0, Type::imag));
}
} // namespace conga

#endif // CONGA_ORDER_PARAMETER_INITIAL_H_
