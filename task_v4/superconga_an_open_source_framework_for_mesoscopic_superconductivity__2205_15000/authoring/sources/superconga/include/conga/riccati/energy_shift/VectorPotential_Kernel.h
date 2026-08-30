//===- VectorPotential_Kernel.h - GPU kernel for computing energy shift. -===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// GPU kernel for computing the energy shift caused by vector potentials (both
/// external vector potentials, and vector potentials induced by currents).
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_VECTOR_POTENTIAL_KERNEL_H_
#define CONGA_VECTOR_POTENTIAL_KERNEL_H_

#include "../../configure.h"

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

#include <math.h>

namespace conga {
template <typename T, template <typename> class POTENTIAL>
__global__ void computeEnergyShiftOnlyExternalKernel(
    const int inDimX, const int inDimY, const T inFermiVelocityX,
    const T inFermiVelocityY, const T inSystemAngle, const T inFluxDensity,
    const int inChargeSign, const T inArea, const T inGridElementSize,
    T *const outEnergyShift) {
  // XY-coordinate indices.
  const int xIdx = blockDim.x * blockIdx.x + threadIdx.x;
  const int yIdx = blockDim.y * blockIdx.y + threadIdx.y;

  if (xIdx < inDimX && yIdx < inDimY) {
    // Center system coordinates at origin.
    const T offsetX = -static_cast<T>(0.5) * static_cast<T>(inDimX - 1);
    const T offsetY = -static_cast<T>(0.5) * static_cast<T>(inDimY - 1);

    // Go to local, physical coordinates.
    T x = (static_cast<T>(xIdx) + offsetX) * inGridElementSize;
    T y = (static_cast<T>(yIdx) + offsetY) * inGridElementSize;

    // Rotate local coordinates to global frame.
    utils::rotate(inSystemAngle, x, y);

    T vectorPotentialX;
    T vectorPotentialY;
    POTENTIAL<T>::compute(inFluxDensity, inArea, x, y, vectorPotentialX,
                          vectorPotentialY);

    // Linear index.
    const int idx = yIdx * inDimX + xIdx;

    // Compute energy shift.
    outEnergyShift[idx] =
        static_cast<T>(inChargeSign) * (inFermiVelocityX * vectorPotentialX +
                                        inFermiVelocityY * vectorPotentialY);
  }
}

template <typename T, template <typename> class POTENTIAL>
__global__ void computeEnergyShiftKernel(
    const int inDimX, const int inDimY, const T inFermiVelocityX,
    const T inFermiVelocityY, const T inSystemAngle, const T inFluxDensity,
    const int inChargeSign, const T inArea, const T inGridElementSize,
    const T *const inVectorPotentialX, const T *const inVectorPotentialY,
    T *const outEnergyShift) {
  // XY-coordinate indices.
  const int xIdx = blockDim.x * blockIdx.x + threadIdx.x;
  const int yIdx = blockDim.y * blockIdx.y + threadIdx.y;

  if (xIdx < inDimX && yIdx < inDimY) {
    // Center system coordinates at origin.
    const T offsetX = -static_cast<T>(0.5) * static_cast<T>(inDimX - 1);
    const T offsetY = -static_cast<T>(0.5) * static_cast<T>(inDimY - 1);

    // Go to local, physical coordinates.
    T x = (static_cast<T>(xIdx) + offsetX) * inGridElementSize;
    T y = (static_cast<T>(yIdx) + offsetY) * inGridElementSize;

    // Rotate local coordinates to global frame.
    utils::rotate(inSystemAngle, x, y);

    // External vector potential.
    T extVectorPotentialX;
    T extVectorPotentialY;
    POTENTIAL<T>::compute(inFluxDensity, inArea, x, y, extVectorPotentialX,
                          extVectorPotentialY);

    // Linear index.
    const int idx = yIdx * inDimX + xIdx;

    // The total vector potential.
    const T vectorPotentialX = inVectorPotentialX[idx] + extVectorPotentialX;
    const T vectorPotentialY = inVectorPotentialY[idx] + extVectorPotentialY;

    // Compute energy shift.
    outEnergyShift[idx] =
        static_cast<T>(inChargeSign) * (inFermiVelocityX * vectorPotentialX +
                                        inFermiVelocityY * vectorPotentialY);
  }
}
} // namespace conga

#endif // CONGA_VECTOR_POTENTIAL_KERNEL_H_
