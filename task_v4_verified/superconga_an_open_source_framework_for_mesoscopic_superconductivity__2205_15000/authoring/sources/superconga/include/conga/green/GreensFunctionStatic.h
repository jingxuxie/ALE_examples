//===-- GreensFunctionStatic.h - Green function computation wrapper. ------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Kernels and wrappers to compute Green functions (quasiparticle propagator
/// and anomalous pair propagator).
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_GREENS_FUNCTION_STATIC_H_
#define CONGA_GREENS_FUNCTION_STATIC_H_

#include "../ParameterIterator.h"
#include "../Parameters.h"
#include "../grid.h"
#include "LocalGreens.h"

#include <thrust/complex.h>

#include <cassert>

namespace conga {
template <typename T, template <typename> class GREENS>
struct GreensFunctionStatic {
  /// \brief Compute Green function for all energies.
  ///
  /// \param inGamma The coherence function "gamma".
  /// \param inGammaTilde The coherence function "gammaTilde".
  /// \param outResult The result.
  ///
  /// \return Void.
  static void computeGreens(const GridGPU<T> *const inGamma,
                            const GridGPU<T> *const inGammaTilde,
                            const int inEnergyIdxOffset,
                            const int inNumEnergiesCurrentBlock,
                            GridGPU<T> *outResult);

  /// \brief Compute Green function for all energies and sum over energies.
  ///
  /// \param inGamma The coherence function "gamma".
  /// \param inGammaTilde The coherence function "gammaTilde".
  /// \param inResidues Residues to multiply the Green function (for each
  /// energy) before summing.
  /// \param outResult The result.
  ///
  /// \return Void.
  static void computeGreensSumEnergy(const GridGPU<T> *const inGamma,
                                     const GridGPU<T> *const inGammaTilde,
                                     const GridGPU<T> *const inResidues,
                                     const int inEnergyIdxOffset,
                                     const int inNumEnergiesCurrentBlock,
                                     GridGPU<T> *outResult);
};

namespace internal {
template <typename T, template <typename> class GREENS>
__global__ void computeGreens_kernel(
    const int inDimX, const int inDimY, const int inEnergyIdxOffset,
    const int inNumEnergiesCurrentBlock, const T *const inGammaReal,
    const T *const inGammaImag, const T *const inGammaTildeReal,
    const T *const inGammaTildeImag, T *outResultReal, T *outResultImag) {
  const int x = blockIdx.x * blockDim.x + threadIdx.x;
  const int y = blockIdx.y * blockDim.y + threadIdx.y;
  const int energyIdx = blockIdx.z * blockDim.z + threadIdx.z;

  if ((x < inDimX) && (y < inDimY) && (energyIdx < inNumEnergiesCurrentBlock)) {
    // TODO(niclas): Make this a macro.
    const int coherenceIdx = (2 * energyIdx * inDimY + y) * inDimX + x;

    const thrust::complex<T> gamma(inGammaReal[coherenceIdx],
                                   inGammaImag[coherenceIdx]);
    const thrust::complex<T> gammaTilde(inGammaTildeReal[coherenceIdx],
                                        inGammaTildeImag[coherenceIdx]);

    const thrust::complex<T> val = GREENS<T>::compute(gamma, gammaTilde);

    const int idx =
        (2 * (energyIdx + inEnergyIdxOffset) * inDimY + y) * inDimX + x;
    outResultReal[idx] = val.real();
    outResultImag[idx] = val.imag();
  }
}

template <typename T, template <typename> class GREENS>
__global__ void computeGreensSumEnergy_kernel(
    const int inDimX, const int inDimY, const int inEnergyIdxOffset,
    const int inNumEnergiesCurrentBlock, const T *const inGammaReal,
    const T *const inGammaImag, const T *const inGammaTildeReal,
    const T *const inGammaTildeImag, const T *const inResidues,
    T *const outResultReal, T *const outResultImag) {
  const int x = blockDim.x * blockIdx.x + threadIdx.x;
  const int y = blockDim.y * blockIdx.y + threadIdx.y;

  if ((x < inDimX) && (y < inDimY)) {
    // TODO(niclas): Make this a macro.
    const int spatialIdx = y * inDimX + x;

    thrust::complex<T> sum(static_cast<T>(0), static_cast<T>(0));

    for (int energyIdx = 0; energyIdx < inNumEnergiesCurrentBlock;
         ++energyIdx) {
      // TODO(niclas): Make this a macro.
      const int gamma_idx = energyIdx * 2 * inDimX * inDimY + spatialIdx;

      const thrust::complex<T> gamma(inGammaReal[gamma_idx],
                                     inGammaImag[gamma_idx]);
      const thrust::complex<T> gammaTilde(inGammaTildeReal[gamma_idx],
                                          inGammaTildeImag[gamma_idx]);

      const thrust::complex<T> val = GREENS<T>::compute(gamma, gammaTilde);
      sum += inResidues[energyIdx + inEnergyIdxOffset] * val;
    }

    outResultReal[spatialIdx] += sum.real();
    outResultImag[spatialIdx] += sum.imag();
  }
}
} // namespace internal

template <typename T, template <typename> class GREENS>
void GreensFunctionStatic<T, GREENS>::computeGreens(
    const GridGPU<T> *const inGamma, const GridGPU<T> *const inGammaTilde,
    const int inEnergyIdxOffset, const int inNumEnergiesCurrentBlock,
    GridGPU<T> *const outResult) {
  // Sanity checks.
  assert(inGamma->dimX() == inGammaTilde->dimX());
  assert(inGamma->dimY() == inGammaTilde->dimY());
  assert(inGamma->numFields() == inGammaTilde->numFields());
  assert(inGamma->dimX() == outResult->dimX());
  assert(inGamma->dimY() == outResult->dimY());

  assert(inEnergyIdxOffset >= 0);
  assert(inEnergyIdxOffset < outResult->numElements());
  assert(inNumEnergiesCurrentBlock >= 0);
  assert(inNumEnergiesCurrentBlock <= inGamma->numFields());
  assert((inEnergyIdxOffset + inNumEnergiesCurrentBlock) <=
         outResult->numElements());

  assert(inGamma->isComplex());
  assert(inGammaTilde->isComplex());
  assert(outResult->isComplex());

  // Kernel parameters.
  const auto [numBlocks, numThreadsPerBlock] =
      outResult->getKernelDimensionsFields();

  // Dimensions.
  const int dimX = inGamma->dimX();
  const int dimY = inGamma->dimY();
  const int numEnergies = inGamma->numFields();

  // Compute Greens function from gamma and gammaTilde
  internal::computeGreens_kernel<T, GREENS><<<numBlocks, numThreadsPerBlock>>>(
      dimX, dimY, inEnergyIdxOffset, inNumEnergiesCurrentBlock,
      inGamma->getDataPointer(0, Type::real),
      inGamma->getDataPointer(0, Type::imag),
      inGammaTilde->getDataPointer(0, Type::real),
      inGammaTilde->getDataPointer(0, Type::imag),
      outResult->getDataPointer(0, Type::real),
      outResult->getDataPointer(0, Type::imag));
}

template <typename T, template <typename> class GREENS>
void GreensFunctionStatic<T, GREENS>::computeGreensSumEnergy(
    const GridGPU<T> *const inGamma, const GridGPU<T> *const inGammaTilde,
    const GridGPU<T> *const inResidues, const int inEnergyIdxOffset,
    const int inNumEnergiesCurrentBlock, GridGPU<T> *const outResult) {
  // Sanity checks.
  assert(inGamma->dimX() == inGammaTilde->dimX());
  assert(inGamma->dimY() == inGammaTilde->dimY());
  assert(inGamma->numFields() == inGammaTilde->numFields());
  assert(inGamma->dimX() == outResult->dimX());
  assert(inGamma->dimY() == outResult->dimY());
  assert(inEnergyIdxOffset >= 0);
  assert(inEnergyIdxOffset < inResidues->numElements());
  assert(inNumEnergiesCurrentBlock >= 0);
  assert(inNumEnergiesCurrentBlock <= inGamma->numFields());
  assert((inEnergyIdxOffset + inNumEnergiesCurrentBlock) <=
         inResidues->numElements());
  assert(outResult->numFields() == 1);
  assert(inGamma->isComplex());
  assert(inGammaTilde->isComplex());
  assert(outResult->isComplex());

  // Kernel parameters.
  const auto [numBlocks, numThreadsPerBlock] = outResult->getKernelDimensions();

  // Dimensions.
  const int dimX = inGamma->dimX();
  const int dimY = inGamma->dimY();

  // Compute Greens function from gamma and gammaTilde.
  internal::computeGreensSumEnergy_kernel<T, GREENS>
      <<<numBlocks, numThreadsPerBlock>>>(
          dimX, dimY, inEnergyIdxOffset, inNumEnergiesCurrentBlock,
          inGamma->getDataPointer(0, Type::real),
          inGamma->getDataPointer(0, Type::imag),
          inGammaTilde->getDataPointer(0, Type::real),
          inGammaTilde->getDataPointer(0, Type::imag),
          inResidues->getDataPointer(0, Type::real),
          outResult->getDataPointer(0, Type::real),
          outResult->getDataPointer(0, Type::imag));
}
} // namespace conga

#endif // CONGA_GREENS_FUNCTION_STATIC_H_
