//= riccati_gpu_kernels.h - GPU kernels for solving the Riccati equqations.
//=//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===-----------------------------------------------------------------------===//
///
/// \file
/// Riccati solver implementation for confined geometries, i.e. finite system
/// confined by well-defined boundaries. Derives from the virtual class
/// RiccatiSolver.
///
//===-----------------------------------------------------------------------===//
#ifndef CONGA_RICCATI_GPU_KERNELS_H_
#define CONGA_RICCATI_GPU_KERNELS_H_

// The domain labels for entering/exit at the boundary for gamma and gammaTilde.
#define GAMMA_ENTER 2
#define GAMMA_EXIT 3
#define GAMMATILDE_ENTER 3
#define GAMMATILDE_EXIT 2

#include "RiccatiSolutions.h"

#include <thrust/complex.h>

namespace conga {
namespace riccati {
// Helper struct for scalar parameters needed for the GPU kernels.
template <typename T> struct KernelParameters {
  int angleIdx;
  int energyIdxOffset;
  int energyIdxOffsetStorage;
  int gridResolution;
  int numEnergiesBlock;
  int numEnergiesStorage;
  int xIdxMin;
  int xIdxMax;
  int yIdxMin;
  int yIdxMax;
  T stepSize;
  T scatteringEnergy;
};

/// \brief Make order parameter from real/imag parts. The stepping formulas are
/// identical for gamma and gammaTilde except gammaTilde has replaced (Delta,
/// tilde(Delta)) --> (-tilde(Delta), -Delta). So by applying this
/// transformation during construction we only need to implement one general
/// stepping function.
///
/// \param inReal The real part of the order parameter.
/// \param inImag The imaginary part of the order parameter.
///
/// \return The pair {Delta, tilde(Delta)} if IS_GAMMA = true, otherwise
/// {-tilde(Delta), -Delta}.
template <typename T, bool IS_GAMMA>
inline __device__ thrust::pair<thrust::complex<T>, thrust::complex<T>>
makeOrderParameter(const T inReal, const T inImag) {
  const thrust::complex<T> orderParameter =
      IS_GAMMA ? thrust::complex<T>(inReal, inImag)
               : thrust::complex<T>(-inReal, inImag);
  return {orderParameter, thrust::conj(orderParameter)};
}

/// \brief Make order parameter from real/imag parts and impurity self-energies.
/// The stepping formulas are identical for gamma and gammaTilde except
/// gammaTilde has replaced (Delta, tilde(Delta)) --> (-tilde(Delta), -Delta).
/// So by applying this transformation during construction we only need to
/// implement one general stepping function.
///
/// \param inReal The real part of the order parameter.
/// \param inImag The imaginary part of the order parameter.
/// \param inImp The impurity self-energy Delta.
/// \param inImpTilde The impurity self-energy tilde(Delta).
///
/// \return The pair {Delta, tilde(Delta)} if IS_GAMMA = true, otherwise
/// {-tilde(Delta), -Delta}.
template <typename T, bool IS_GAMMA>
inline __device__ thrust::pair<thrust::complex<T>, thrust::complex<T>>
makeOrderParameter(const T inReal, const T inImag,
                   const thrust::complex<T> &inImp,
                   const thrust::complex<T> &inImpTilde) {
  const thrust::complex<T> orderParameter =
      IS_GAMMA ? thrust::complex<T>(inReal, inImag) + inImp
               : thrust::complex<T>(-inReal, inImag) - inImpTilde;
  const thrust::complex<T> orderParameterTilde =
      IS_GAMMA ? thrust::complex<T>(inReal, -inImag) + inImpTilde
               : thrust::complex<T>(-inReal, -inImag) - inImp;
  return {orderParameter, orderParameterTilde};
}

/// \brief Interpolate linearly taking a half unit step.
///
/// \param inVal0 The value at zero step.
/// \param inVal1 The value at unit step.
///
/// \return The interpolated value.
template <typename T>
inline __device__ thrust::complex<T>
interpolateLinear(const thrust::complex<T> &inVal0,
                  const thrust::complex<T> &inVal1) {
  return (inVal1 + inVal0) * static_cast<T>(0.5);
}

/// \brief Take a step along a trajectory and read/write boundary values if
/// encountered.
///
/// \param inStep The step length (h/vF).
/// \param inXIdx The x-index.
/// \param inYIdx The y-index.
/// \param inAngleIdx The angle index.
/// \param inEnergyIdx The energy index.
/// \param inEnergyIdxOffsetStorage The energy offset (needed for computing
/// sparse indices).
/// \param inNumEnergiesStorage The number of energies in storage.
/// \param inLatticeSideLength The number of lattice sites per side length
/// (assuming a square lattice).
/// \param inEnergy The energy at the current lattice site.
/// \param inEnergyPrevious The energy at the previous lattice site.
/// \param inOrderParameter The order parameter at the current lattice site.
/// \param inOrderParameterTilde The tilde order parameter at the current
/// lattice site. \param inOrderParameterPrevious The order parameter at the
/// previous lattice site.
/// \param inOrderParameterTildePrevious The tilde order
/// parameter at the previous lattice site. \
/// param inBoundaryDistances Array of
/// distances to the boundary.
/// \param inCoherenceIdxInward Some array of indices
/// needed for computing sparse indices (inward).
/// \param inCoherenceIdxOutward
/// Some array of indices needed for computing sparse indices (outward).
/// \param
/// inBoundaryCoherenceInwardReal The inward, real boundary coherence value.
/// \param inBoundaryCoherenceInwardImag The inward, imag boundary coherence
/// value.
/// \param inOutBoundaryCoherenceOutwardReal The outward, real boundary
/// coherence value.
/// \param inOutBoundaryCoherenceOutwardImag The outward, imag boundary
/// coherence value.
/// \param inOutBoundaryEntryCount The number of encountered entry sites.
/// \param inOutBoundaryExitCount The number of encountered exit sites.
/// \param inOutCoherence The previous coherence value, will be overwritten by
/// the current value.
template <typename T, int DOMAIN_ENTER, int DOMAIN_EXIT>
inline __device__ void
computeStep(const T inStep, const int inXIdx, const int inYIdx,
            const int inAngleIdx, const int inEnergyIdx,
            const int inEnergyIdxOffsetStorage, const int inNumEnergiesStorage,
            const int inLatticeSideLength, const thrust::complex<T> &inEnergy,
            const thrust::complex<T> &inEnergyPrevious,
            const thrust::complex<T> &inOrderParameter,
            const thrust::complex<T> &inOrderParameterTilde,
            const thrust::complex<T> &inOrderParameterPrevious,
            const thrust::complex<T> &inOrderParameterTildePrevious,
            const char inDomainLabel,
            const T *const __restrict__ inBoundaryDistances,
            const int *const __restrict__ inCoherenceIdxInward,
            const int *const __restrict__ inCoherenceIdxOutward,
            const T *const __restrict__ inBoundaryCoherenceInwardReal,
            const T *const __restrict__ inBoundaryCoherenceInwardImag,
            T *const __restrict__ inOutBoundaryCoherenceOutwardReal,
            T *const __restrict__ inOutBoundaryCoherenceOutwardImag,
            int &inOutBoundaryEntryCount, int &inOutBoundaryExitCount,
            thrust::complex<T> &inOutCoherence) {
  // Spatial index for boundary distance.
  const int spatialIdx = inYIdx * inLatticeSideLength + inXIdx;

  switch (inDomainLabel) {
  case 1: {
    // =========== Inside the domain =========== //
    const thrust::complex<T> energyMiddle =
        interpolateLinear(inEnergyPrevious, inEnergy);
    const thrust::complex<T> deltaMiddle =
        interpolateLinear(inOrderParameterPrevious, inOrderParameter);
    const thrust::complex<T> deltaTildeMiddle =
        interpolateLinear(inOrderParameterTildePrevious, inOrderParameterTilde);
    // Take a step to the center of the lattice site.
    inOutCoherence = riccati::computeStep(
        energyMiddle, deltaMiddle, deltaTildeMiddle, inOutCoherence, inStep);
    break;
  }
  case DOMAIN_ENTER: {
    // =========== Enter the domain =========== //

    // Read boundary coherence function value.
    const int sparseIdx = BoundaryStorage<T>::getSparseIndex(
        inAngleIdx, inEnergyIdx + inEnergyIdxOffsetStorage, inXIdx,
        inOutBoundaryEntryCount, inNumEnergiesStorage, inLatticeSideLength,
        inCoherenceIdxInward);
    const thrust::complex<T> boundaryCoherence(
        inBoundaryCoherenceInwardReal[sparseIdx],
        inBoundaryCoherenceInwardImag[sparseIdx]);

    // Distance to exact boundary location from the center of the lattice
    // site.
    const T distance = abs(inBoundaryDistances[spatialIdx]);
    const T boundaryToCenterStep = distance * inStep;

    // Take a step from the grain boundary to the center of the lattice
    // site.
    inOutCoherence =
        riccati::computeStep(inEnergy, inOrderParameter, inOrderParameterTilde,
                             boundaryCoherence, boundaryToCenterStep);

    // Increase entry counter.
    inOutBoundaryEntryCount++;
    break;
  }
  case DOMAIN_EXIT: {
    // =========== Exit the domain =========== //

    // Take a step to the center of the lattice site.
    const thrust::complex<T> energyMiddle =
        interpolateLinear(inEnergyPrevious, inEnergy);
    const thrust::complex<T> deltaMiddle =
        interpolateLinear(inOrderParameterPrevious, inOrderParameter);
    const thrust::complex<T> deltaTildeMiddle =
        interpolateLinear(inOrderParameterTildePrevious, inOrderParameterTilde);
    inOutCoherence = riccati::computeStep(
        energyMiddle, deltaMiddle, deltaTildeMiddle, inOutCoherence, inStep);

    // Distance to exact boundary location from the center of the lattice
    // site.
    const T distance = abs(inBoundaryDistances[spatialIdx]);
    const T centerToBoundaryStep = distance * inStep;

    // Take a step from the center of the lattice site to the grain
    // boundary.
    const thrust::complex<T> boundaryCoherence =
        riccati::computeStep(inEnergy, inOrderParameter, inOrderParameterTilde,
                             inOutCoherence, centerToBoundaryStep);

    // Store boundary gamma.
    const int sparseIdx = BoundaryStorage<T>::getSparseIndex(
        inAngleIdx, inEnergyIdx + inEnergyIdxOffsetStorage, inXIdx,
        inOutBoundaryExitCount, inNumEnergiesStorage, inLatticeSideLength,
        inCoherenceIdxOutward);
    inOutBoundaryCoherenceOutwardReal[sparseIdx] = boundaryCoherence.real();
    inOutBoundaryCoherenceOutwardImag[sparseIdx] = boundaryCoherence.imag();

    // Increase exit counter.
    inOutBoundaryExitCount++;
    break;
  }
  default: {
    // =========== Outside the domain =========== //
    inOutCoherence = thrust::complex<T>(static_cast<T>(0), static_cast<T>(0));
  }
  }
}

template <typename T, bool IS_GAMMA>
__global__ void
computeCoherence(const KernelParameters<T> inKernelParameters,
                 const T *const __restrict__ inEnergiesReal,
                 const T *const __restrict__ inEnergiesImag,
                 const T *const __restrict__ inEnergyShift,
                 const T *const __restrict__ inImpuritySelfEnergySigmaReal,
                 const T *const __restrict__ inImpuritySelfEnergySigmaImag,
                 const T *const __restrict__ inImpuritySelfEnergyDeltaReal,
                 const T *const __restrict__ inImpuritySelfEnergyDeltaImag,
                 const T *const __restrict__ inImpuritySelfEnergyDeltaTildeReal,
                 const T *const __restrict__ inImpuritySelfEnergyDeltaTildeImag,
                 const T *const __restrict__ inOrderParameterReal,
                 const T *const __restrict__ inOrderParameterImag,
                 const char *const __restrict__ inDomainLabels,
                 const T *const __restrict__ inBoundaryDistances,
                 const int *const __restrict__ idx_in_gamma,
                 const int *const __restrict__ idx_out_gamma,
                 const T *const __restrict__ bnd_in_gamma_real,
                 const T *const __restrict__ bnd_in_gamma_imag,
                 T *const __restrict__ bnd_out_gamma_real,
                 T *const __restrict__ bnd_out_gamma_imag,
                 T *const __restrict__ inCoherenceReal,
                 T *const __restrict__ inCoherenceImag) {
  // Unpack kernel parameters.
  const int gridResolution = inKernelParameters.gridResolution;
  const int numEnergiesStorage = inKernelParameters.numEnergiesStorage;
  const int numEnergiesBlock = inKernelParameters.numEnergiesBlock;
  const int energyIdxOffset = inKernelParameters.energyIdxOffset;
  const int energyIdxOffsetStorage = inKernelParameters.energyIdxOffsetStorage;
  const int xIdxMin = inKernelParameters.xIdxMin;
  const int xIdxMax = inKernelParameters.xIdxMax;
  const int yIdxMin = inKernelParameters.yIdxMin;
  const int yIdxMax = inKernelParameters.yIdxMax;
  const int angleIdx = inKernelParameters.angleIdx;
  const T stepSize = inKernelParameters.stepSize;
  const T scatteringEnergy = inKernelParameters.scatteringEnergy;

  const int x = blockDim.x * blockIdx.x + threadIdx.x + xIdxMin;
  // Note that this is the index within one energy block.
  const int energyIdx = blockDim.y * blockIdx.y + threadIdx.y;

  if (x <= xIdxMax && energyIdx < numEnergiesBlock) {
    // Read the energy.
    const thrust::complex<T> energyZeroPotential(
        inEnergiesReal[energyIdx + energyIdxOffset],
        inEnergiesImag[energyIdx + energyIdxOffset]);

    // In order to read/write values from/to the boundary coherence functions,
    // we need to keep track of how many boundaries we have encountered along
    // the trajectory.
    int boundary_entry_count = 0;
    int boundary_exit_count = 0;

    // Which y-coordinate to start from is determined by whether we are solving
    // for gamma or gammatilde.
    const int y_start = IS_GAMMA ? yIdxMin : yIdxMax;

    // The previous energy and order parameter. They are updated as we traverse
    // the trajectory.
    thrust::complex<T> energyPrev(static_cast<T>(0), static_cast<T>(0));
    thrust::complex<T> deltaPrev(static_cast<T>(0), static_cast<T>(0));
    thrust::complex<T> deltaTildePrev(static_cast<T>(0), static_cast<T>(0));

    // The value of the coherence function at the center of the current
    // lattice site. It is updated as we traverse the trajectory.
    thrust::complex<T> coherence(static_cast<T>(0), static_cast<T>(0));

    // Compute coherence function along trajectory.
    for (int i = 0; i <= (yIdxMax - yIdxMin); ++i) {
      const int y = y_start + (IS_GAMMA ? i : -i);

      // Index to 2d-grids.
      const int spatialIdx = y * gridResolution + x;

      // Index to coherence grid (for energies in the block).
      const int coherenceIdx =
          energyIdx * 2 * gridResolution * gridResolution + spatialIdx;

      // The energy.
      const thrust::complex<T> impSigma =
          scatteringEnergy *
          thrust::complex<T>(inImpuritySelfEnergySigmaReal[coherenceIdx],
                             inImpuritySelfEnergySigmaImag[coherenceIdx]);
      const thrust::complex<T> energy =
          energyZeroPotential - impSigma + inEnergyShift[spatialIdx];

      // The order parameter.
      const thrust::complex<T> impDelta =
          scatteringEnergy *
          thrust::complex<T>(inImpuritySelfEnergyDeltaReal[coherenceIdx],
                             inImpuritySelfEnergyDeltaImag[coherenceIdx]);
      const thrust::complex<T> impDeltaTilde =
          scatteringEnergy *
          thrust::complex<T>(inImpuritySelfEnergyDeltaTildeReal[coherenceIdx],
                             inImpuritySelfEnergyDeltaTildeImag[coherenceIdx]);
      const auto [delta, deltaTilde] = makeOrderParameter<T, IS_GAMMA>(
          inOrderParameterReal[spatialIdx], inOrderParameterImag[spatialIdx],
          impDelta, impDeltaTilde);

      // What type of site are we on?
      const char domainLabel = inDomainLabels[spatialIdx];

      // Take step and read/write boundary values.
      computeStep<T, (IS_GAMMA ? GAMMA_ENTER : GAMMATILDE_ENTER),
                  (IS_GAMMA ? GAMMA_EXIT : GAMMATILDE_EXIT)>(
          stepSize, x, y, angleIdx, energyIdx, energyIdxOffsetStorage,
          numEnergiesStorage, gridResolution, energy, energyPrev, delta,
          deltaTilde, deltaPrev, deltaTildePrev, domainLabel,
          inBoundaryDistances, idx_in_gamma, idx_out_gamma, bnd_in_gamma_real,
          bnd_in_gamma_imag, bnd_out_gamma_real, bnd_out_gamma_imag,
          boundary_entry_count, boundary_exit_count, coherence);

      // Store coherence function.
      inCoherenceReal[coherenceIdx] = coherence.real();
      inCoherenceImag[coherenceIdx] = coherence.imag();

      // Update previous energy and order parameter.
      energyPrev = energy;
      deltaPrev = delta;
      deltaTildePrev = deltaTilde;
    }
  }
}

template <typename T, bool IS_GAMMA>
__global__ void
computeCoherence(const KernelParameters<T> inKernelParameters,
                 const T *const __restrict__ inEnergiesReal,
                 const T *const __restrict__ inEnergiesImag,
                 const T *const __restrict__ inEnergyShift,
                 const T *const __restrict__ inOrderParameterReal,
                 const T *const __restrict__ inOrderParameterImag,
                 const char *const __restrict__ inDomainLabels,
                 const T *const __restrict__ inBoundaryDistances,
                 const int *const __restrict__ idx_in_gamma,
                 const int *const __restrict__ idx_out_gamma,
                 const T *const __restrict__ bnd_in_gamma_real,
                 const T *const __restrict__ bnd_in_gamma_imag,
                 T *const __restrict__ bnd_out_gamma_real,
                 T *const __restrict__ bnd_out_gamma_imag,
                 T *const __restrict__ inCoherenceReal,
                 T *const __restrict__ inCoherenceImag) {
  // Unpack kernel parameters.
  const int gridResolution = inKernelParameters.gridResolution;
  const int numEnergiesStorage = inKernelParameters.numEnergiesStorage;
  const int numEnergiesBlock = inKernelParameters.numEnergiesBlock;
  const int energyIdxOffset = inKernelParameters.energyIdxOffset;
  const int energyIdxOffsetStorage = inKernelParameters.energyIdxOffsetStorage;
  const int xIdxMin = inKernelParameters.xIdxMin;
  const int xIdxMax = inKernelParameters.xIdxMax;
  const int yIdxMin = inKernelParameters.yIdxMin;
  const int yIdxMax = inKernelParameters.yIdxMax;
  const int angleIdx = inKernelParameters.angleIdx;
  const T stepSize = inKernelParameters.stepSize;

  const int x = blockDim.x * blockIdx.x + threadIdx.x + xIdxMin;
  // Note that this is the index within one energy block.
  const int energyIdx = blockDim.y * blockIdx.y + threadIdx.y;

  if (x <= xIdxMax && energyIdx < numEnergiesBlock) {
    // Read the energy.
    const thrust::complex<T> energyZeroPotential(
        inEnergiesReal[energyIdx + energyIdxOffset],
        inEnergiesImag[energyIdx + energyIdxOffset]);

    // In order to read/write values from/to the boundary coherence functions,
    // we need to keep track of how many boundaries we have encountered along
    // the trajectory.
    int boundary_entry_count = 0;
    int boundary_exit_count = 0;

    // Which y-coordinate to start from is determined by whether we are solving
    // for gamma or gammatilde.
    const int y_start = IS_GAMMA ? yIdxMin : yIdxMax;

    // The previous energy and order parameter. They are updated as we traverse
    // the trajectory.
    thrust::complex<T> energyPrev(static_cast<T>(0), static_cast<T>(0));
    thrust::complex<T> deltaPrev(static_cast<T>(0), static_cast<T>(0));
    thrust::complex<T> deltaTildePrev(static_cast<T>(0), static_cast<T>(0));

    // The value of the coherence function at the center of the current
    // lattice site. It is updated as we traverse the trajectory.
    thrust::complex<T> coherence(static_cast<T>(0), static_cast<T>(0));

    // Compute coherence function along trajectory.
    for (int i = 0; i <= (yIdxMax - yIdxMin); ++i) {
      const int y = y_start + (IS_GAMMA ? i : -i);

      // Index to 2d-grids.
      const int spatialIdx = y * gridResolution + x;

      // Index to gamma grid (for all energies).
      const int coherenceIdx =
          energyIdx * 2 * gridResolution * gridResolution + spatialIdx;

      // The energy and order parameter.
      const thrust::complex<T> energy =
          energyZeroPotential + inEnergyShift[spatialIdx];
      const auto [delta, deltaTilde] = makeOrderParameter<T, IS_GAMMA>(
          inOrderParameterReal[spatialIdx], inOrderParameterImag[spatialIdx]);

      // What type of site are we on?
      const char domainLabel = inDomainLabels[spatialIdx];

      // Take step and read/write boundary values.
      computeStep<T, (IS_GAMMA ? GAMMA_ENTER : GAMMATILDE_ENTER),
                  (IS_GAMMA ? GAMMA_EXIT : GAMMATILDE_EXIT)>(
          stepSize, x, y, angleIdx, energyIdx, energyIdxOffsetStorage,
          numEnergiesStorage, gridResolution, energy, energyPrev, delta,
          deltaTilde, deltaPrev, deltaTildePrev, domainLabel,
          inBoundaryDistances, idx_in_gamma, idx_out_gamma, bnd_in_gamma_real,
          bnd_in_gamma_imag, bnd_out_gamma_real, bnd_out_gamma_imag,
          boundary_entry_count, boundary_exit_count, coherence);

      // Store coherence function.
      inCoherenceReal[coherenceIdx] = coherence.real();
      inCoherenceImag[coherenceIdx] = coherence.imag();

      // Update previous energy and order parameter.
      energyPrev = energy;
      deltaPrev = delta;
      deltaTildePrev = deltaTilde;
    }
  }
}

template <typename T, bool IS_GAMMA>
__global__ void computeCoherenceBurnIn(
    const KernelParameters<T> inKernelParameters,
    const T *const __restrict__ inEnergiesReal,
    const T *const __restrict__ inEnergiesImag,
    const T *const __restrict__ inEnergyShift,
    const T *const __restrict__ inImpuritySelfEnergySigmaReal,
    const T *const __restrict__ inImpuritySelfEnergySigmaImag,
    const T *const __restrict__ inImpuritySelfEnergyDeltaReal,
    const T *const __restrict__ inImpuritySelfEnergyDeltaImag,
    const T *const __restrict__ inImpuritySelfEnergyDeltaTildeReal,
    const T *const __restrict__ inImpuritySelfEnergyDeltaTildeImag,
    const T *const __restrict__ inOrderParameterReal,
    const T *const __restrict__ inOrderParameterImag,
    const char *const __restrict__ inDomainLabels,
    const T *const __restrict__ inBoundaryDistances,
    const int *const __restrict__ idx_in_gamma,
    const int *const __restrict__ idx_out_gamma,
    const T *const __restrict__ bnd_in_gamma_real,
    const T *const __restrict__ bnd_in_gamma_imag,
    T *const __restrict__ bnd_out_gamma_real,
    T *const __restrict__ bnd_out_gamma_imag) {
  // Unpack kernel parameters.
  const int gridResolution = inKernelParameters.gridResolution;
  const int numEnergiesStorage = inKernelParameters.numEnergiesStorage;
  const int numEnergiesBlock = inKernelParameters.numEnergiesBlock;
  const int energyIdxOffset = inKernelParameters.energyIdxOffset;
  const int energyIdxOffsetStorage = inKernelParameters.energyIdxOffsetStorage;
  const int xIdxMin = inKernelParameters.xIdxMin;
  const int xIdxMax = inKernelParameters.xIdxMax;
  const int yIdxMin = inKernelParameters.yIdxMin;
  const int yIdxMax = inKernelParameters.yIdxMax;
  const int angleIdx = inKernelParameters.angleIdx;
  const T stepSize = inKernelParameters.stepSize;
  const T scatteringEnergy = inKernelParameters.scatteringEnergy;

  const int x = blockDim.x * blockIdx.x + threadIdx.x + xIdxMin;
  // Note that this is the index within one energy block.
  const int energyIdx = blockDim.y * blockIdx.y + threadIdx.y;

  if (x <= xIdxMax && energyIdx < numEnergiesBlock) {
    // Read the energy.
    const thrust::complex<T> energyZeroPotential(
        inEnergiesReal[energyIdx + energyIdxOffset],
        inEnergiesImag[energyIdx + energyIdxOffset]);

    // In order to read/write values from/to the boundary coherence functions,
    // we need to keep track of how many boundaries we have encountered along
    // the trajectory.
    int boundary_entry_count = 0;
    int boundary_exit_count = 0;

    // Which y-coordinate to start from is determined by whether we are solving
    // for gamma or gammatilde.
    const int y_start = IS_GAMMA ? yIdxMin : yIdxMax;

    // The previous energy and order parameter. They are updated as we traverse
    // the trajectory.
    thrust::complex<T> energyPrev(static_cast<T>(0), static_cast<T>(0));
    thrust::complex<T> deltaPrev(static_cast<T>(0), static_cast<T>(0));
    thrust::complex<T> deltaTildePrev(static_cast<T>(0), static_cast<T>(0));

    // The value of the coherence function at the center of the current
    // lattice site. It is updated as we traverse the trajectory.
    thrust::complex<T> coherence(static_cast<T>(0), static_cast<T>(0));

    // Compute coherence function along trajectory.
    for (int i = 0; i <= (yIdxMax - yIdxMin); ++i) {
      const int y = y_start + (IS_GAMMA ? i : -i);

      // Index to 2d-grids.
      const int spatialIdx = y * gridResolution + x;

      // Index to gamma grid (for all energies).
      const int coherenceIdx = energyIdx * 2 * gridResolution * gridResolution +
                               y * gridResolution + x;

      // The energy.
      const thrust::complex<T> impSigma =
          scatteringEnergy *
          thrust::complex<T>(inImpuritySelfEnergySigmaReal[coherenceIdx],
                             inImpuritySelfEnergySigmaImag[coherenceIdx]);
      const thrust::complex<T> energy =
          energyZeroPotential - impSigma + inEnergyShift[spatialIdx];

      // The order parameter.
      const thrust::complex<T> impDelta =
          scatteringEnergy *
          thrust::complex<T>(inImpuritySelfEnergyDeltaReal[coherenceIdx],
                             inImpuritySelfEnergyDeltaImag[coherenceIdx]);
      const thrust::complex<T> impDeltaTilde =
          scatteringEnergy *
          thrust::complex<T>(inImpuritySelfEnergyDeltaTildeReal[coherenceIdx],
                             inImpuritySelfEnergyDeltaTildeImag[coherenceIdx]);
      const auto [delta, deltaTilde] = makeOrderParameter<T, IS_GAMMA>(
          inOrderParameterReal[spatialIdx], inOrderParameterImag[spatialIdx],
          impDelta, impDeltaTilde);

      // What type of node are we on?
      const char domainLabel = inDomainLabels[spatialIdx];

      // Take step and read/write boundary values.
      computeStep<T, (IS_GAMMA ? GAMMA_ENTER : GAMMATILDE_ENTER),
                  (IS_GAMMA ? GAMMA_EXIT : GAMMATILDE_EXIT)>(
          stepSize, x, y, angleIdx, energyIdx, energyIdxOffsetStorage,
          numEnergiesStorage, gridResolution, energy, energyPrev, delta,
          deltaTilde, deltaPrev, deltaTildePrev, domainLabel,
          inBoundaryDistances, idx_in_gamma, idx_out_gamma, bnd_in_gamma_real,
          bnd_in_gamma_imag, bnd_out_gamma_real, bnd_out_gamma_imag,
          boundary_entry_count, boundary_exit_count, coherence);

      // Update previous energy and order parameter.
      energyPrev = energy;
      deltaPrev = delta;
      deltaTildePrev = deltaTilde;
    }
  }
}

template <typename T, bool IS_GAMMA>
__global__ void
computeCoherenceBurnIn(const KernelParameters<T> inKernelParameters,
                       const T *const __restrict__ inEnergiesReal,
                       const T *const __restrict__ inEnergiesImag,
                       const T *const __restrict__ inEnergyShift,
                       const T *const __restrict__ inOrderParameterReal,
                       const T *const __restrict__ inOrderParameterImag,
                       const char *const __restrict__ inDomainLabels,
                       const T *const __restrict__ inBoundaryDistances,
                       const int *const __restrict__ idx_in_gamma,
                       const int *const __restrict__ idx_out_gamma,
                       const T *const __restrict__ bnd_in_gamma_real,
                       const T *const __restrict__ bnd_in_gamma_imag,
                       T *const __restrict__ bnd_out_gamma_real,
                       T *const __restrict__ bnd_out_gamma_imag) {
  // Unpack kernel parameters.
  const int gridResolution = inKernelParameters.gridResolution;
  const int numEnergiesStorage = inKernelParameters.numEnergiesStorage;
  const int numEnergiesBlock = inKernelParameters.numEnergiesBlock;
  const int energyIdxOffset = inKernelParameters.energyIdxOffset;
  const int energyIdxOffsetStorage = inKernelParameters.energyIdxOffsetStorage;
  const int xIdxMin = inKernelParameters.xIdxMin;
  const int xIdxMax = inKernelParameters.xIdxMax;
  const int yIdxMin = inKernelParameters.yIdxMin;
  const int yIdxMax = inKernelParameters.yIdxMax;
  const int angleIdx = inKernelParameters.angleIdx;
  const T stepSize = inKernelParameters.stepSize;

  const int x = blockDim.x * blockIdx.x + threadIdx.x + xIdxMin;
  // Note that this is the index within one energy block.
  const int energyIdx = blockDim.y * blockIdx.y + threadIdx.y;

  if (x <= xIdxMax && energyIdx < numEnergiesBlock) {
    // Read the energy.
    const thrust::complex<T> energyZeroPotential(
        inEnergiesReal[energyIdx + energyIdxOffset],
        inEnergiesImag[energyIdx + energyIdxOffset]);

    // In order to read/write values from/to the boundary coherence functions,
    // we need to keep track of how many boundaries we have encountered along
    // the trajectory.
    int boundary_entry_count = 0;
    int boundary_exit_count = 0;

    // Which y-coordinate to start from is determined by whether we are solving
    // for gamma or gammatilde.
    const int y_start = IS_GAMMA ? yIdxMin : yIdxMax;

    // The previous energy and order parameter. They are updated as we traverse
    // the trajectory.
    thrust::complex<T> energyPrev(static_cast<T>(0), static_cast<T>(0));
    thrust::complex<T> deltaPrev(static_cast<T>(0), static_cast<T>(0));
    thrust::complex<T> deltaTildePrev(static_cast<T>(0), static_cast<T>(0));

    // The value of the coherence function at the center of the current
    // lattice site. It is updated as we traverse the trajectory.
    thrust::complex<T> coherence(static_cast<T>(0), static_cast<T>(0));

    // Compute coherence function along trajectory.
    for (int i = 0; i <= (yIdxMax - yIdxMin); ++i) {
      const int y = y_start + (IS_GAMMA ? i : -i);

      // Index to 2d-grids.
      const int spatialIdx = y * gridResolution + x;

      // The energy and order parameter.
      const thrust::complex<T> energy =
          energyZeroPotential + inEnergyShift[spatialIdx];
      const auto [delta, deltaTilde] = makeOrderParameter<T, IS_GAMMA>(
          inOrderParameterReal[spatialIdx], inOrderParameterImag[spatialIdx]);

      // What type of node are we on?
      const char domainLabel = inDomainLabels[spatialIdx];

      // Take step and read/write boundary values.
      computeStep<T, (IS_GAMMA ? GAMMA_ENTER : GAMMATILDE_ENTER),
                  (IS_GAMMA ? GAMMA_EXIT : GAMMATILDE_EXIT)>(
          stepSize, x, y, angleIdx, energyIdx, energyIdxOffsetStorage,
          numEnergiesStorage, gridResolution, energy, energyPrev, delta,
          deltaTilde, deltaPrev, deltaTildePrev, domainLabel,
          inBoundaryDistances, idx_in_gamma, idx_out_gamma, bnd_in_gamma_real,
          bnd_in_gamma_imag, bnd_out_gamma_real, bnd_out_gamma_imag,
          boundary_entry_count, boundary_exit_count, coherence);

      // Update previous energy and order parameter.
      energyPrev = energy;
      deltaPrev = delta;
      deltaTildePrev = deltaTilde;
    }
  }
}

template <typename T, bool IS_GAMMA>
__global__ void computeCoherenceInitial(
    const KernelParameters<T> inKernelParameters,
    const T *const __restrict__ inEnergiesReal,
    const T *const __restrict__ inEnergiesImag,
    const T *const __restrict__ inEnergyShift,
    const T *const __restrict__ inImpuritySelfEnergySigmaReal,
    const T *const __restrict__ inImpuritySelfEnergySigmaImag,
    const T *const __restrict__ inImpuritySelfEnergyDeltaReal,
    const T *const __restrict__ inImpuritySelfEnergyDeltaImag,
    const T *const __restrict__ inImpuritySelfEnergyDeltaTildeReal,
    const T *const __restrict__ inImpuritySelfEnergyDeltaTildeImag,
    const T *const __restrict__ inOrderParameterReal,
    const T *const __restrict__ inOrderParameterImag,
    const char *const __restrict__ inDomainLabels,
    const int *const __restrict__ idx_out_gamma,
    T *const __restrict__ bnd_out_gamma_real,
    T *const __restrict__ bnd_out_gamma_imag) {
  // Unpack kernel parameters.
  const int gridResolution = inKernelParameters.gridResolution;
  const int numEnergiesStorage = inKernelParameters.numEnergiesStorage;
  const int numEnergiesBlock = inKernelParameters.numEnergiesBlock;
  const int energyIdxOffset = inKernelParameters.energyIdxOffset;
  const int energyIdxOffsetStorage = inKernelParameters.energyIdxOffsetStorage;
  const int xIdxMin = inKernelParameters.xIdxMin;
  const int xIdxMax = inKernelParameters.xIdxMax;
  const int yIdxMin = inKernelParameters.yIdxMin;
  const int yIdxMax = inKernelParameters.yIdxMax;
  const int angleIdx = inKernelParameters.angleIdx;
  const T scatteringEnergy = inKernelParameters.scatteringEnergy;

  const int x = blockDim.x * blockIdx.x + threadIdx.x + xIdxMin;
  // Note that this is the index within one energy block.
  const int energyIdx = blockDim.y * blockIdx.y + threadIdx.y;

  if (x <= xIdxMax && energyIdx < numEnergiesBlock) {
    // Read the energy.
    const thrust::complex<T> energyZeroPotential(
        inEnergiesReal[energyIdx + energyIdxOffset],
        inEnergiesImag[energyIdx + energyIdxOffset]);

    int boundary_exit_count = 0;

    // Which y-coordinate to start from is determined by whether we are solving
    // for gamma or gammatilde.
    const int y_start = IS_GAMMA ? yIdxMin : yIdxMax;

    // What domain label is an exit depends if we are computing gamma or
    // gammaTilde.
    const char domainExit = IS_GAMMA ? GAMMA_EXIT : GAMMATILDE_EXIT;

    // Compute coherence function along trajectory.
    for (int i = 0; i <= (yIdxMax - yIdxMin); ++i) {
      const int y = y_start + (IS_GAMMA ? i : -i);

      // Index to 2d-grids.
      const int spatialIdx = y * gridResolution + x;

      // What type of node are we on?
      const char domainLabel = inDomainLabels[spatialIdx];

      if (domainLabel == domainExit) {
        // Index to gamma grid (for all energies).
        const int coherenceIdx =
            energyIdx * 2 * gridResolution * gridResolution + spatialIdx;

        // The energy.
        const thrust::complex<T> impSigma =
            scatteringEnergy *
            thrust::complex<T>(inImpuritySelfEnergySigmaReal[coherenceIdx],
                               inImpuritySelfEnergySigmaImag[coherenceIdx]);
        const thrust::complex<T> energy =
            energyZeroPotential - impSigma + inEnergyShift[spatialIdx];

        // The order parameter.
        const thrust::complex<T> impDelta =
            scatteringEnergy *
            thrust::complex<T>(inImpuritySelfEnergyDeltaReal[coherenceIdx],
                               inImpuritySelfEnergyDeltaImag[coherenceIdx]);
        const thrust::complex<T> impDeltaTilde =
            scatteringEnergy *
            thrust::complex<T>(
                inImpuritySelfEnergyDeltaTildeReal[coherenceIdx],
                inImpuritySelfEnergyDeltaTildeImag[coherenceIdx]);
        const auto [delta, deltaTilde] = makeOrderParameter<T, IS_GAMMA>(
            inOrderParameterReal[spatialIdx], inOrderParameterImag[spatialIdx],
            impDelta, impDeltaTilde);

        // Compute gammas and store
        const int idx_sparse = BoundaryStorage<T>::getSparseIndex(
            angleIdx, energyIdx + energyIdxOffsetStorage, x,
            boundary_exit_count, numEnergiesStorage, gridResolution,
            idx_out_gamma);

        // Compute gamma at current grid point
        const auto [gamma, gammaTilde] =
            riccati::computeHomogeneous(energy, delta, deltaTilde);
        const thrust::complex<T> gBoundary = IS_GAMMA ? gamma : gammaTilde;

        bnd_out_gamma_real[idx_sparse] = gBoundary.real();
        bnd_out_gamma_imag[idx_sparse] = gBoundary.imag();

        boundary_exit_count++;
      }
    }
  }
}

template <typename T, bool IS_GAMMA>
__global__ void
computeCoherenceInitial(const KernelParameters<T> inKernelParameters,
                        const T *const __restrict__ inEnergiesReal,
                        const T *const __restrict__ inEnergiesImag,
                        const T *const __restrict__ inEnergyShift,
                        const T *const __restrict__ inOrderParameterReal,
                        const T *const __restrict__ inOrderParameterImag,
                        const char *const __restrict__ inDomainLabels,
                        const int *const __restrict__ idx_out_gamma,
                        T *const __restrict__ bnd_out_gamma_real,
                        T *const __restrict__ bnd_out_gamma_imag) {
  // Unpack kernel parameters.
  const int gridResolution = inKernelParameters.gridResolution;
  const int numEnergiesStorage = inKernelParameters.numEnergiesStorage;
  const int numEnergiesBlock = inKernelParameters.numEnergiesBlock;
  const int energyIdxOffset = inKernelParameters.energyIdxOffset;
  const int energyIdxOffsetStorage = inKernelParameters.energyIdxOffsetStorage;
  const int xIdxMin = inKernelParameters.xIdxMin;
  const int xIdxMax = inKernelParameters.xIdxMax;
  const int yIdxMin = inKernelParameters.yIdxMin;
  const int yIdxMax = inKernelParameters.yIdxMax;
  const int angleIdx = inKernelParameters.angleIdx;

  const int x = blockDim.x * blockIdx.x + threadIdx.x + xIdxMin;
  // Note that this is the index within one energy block.
  const int energyIdx = blockDim.y * blockIdx.y + threadIdx.y;

  if (x <= xIdxMax && energyIdx < numEnergiesBlock) {
    // Read the energy.
    const thrust::complex<T> energyZeroPotential(
        inEnergiesReal[energyIdx + energyIdxOffset],
        inEnergiesImag[energyIdx + energyIdxOffset]);

    int boundary_exit_count = 0;

    // Which y-coordinate to start from is determined by whether we are solving
    // for gamma or gammatilde.
    const int y_start = IS_GAMMA ? yIdxMin : yIdxMax;

    // What domain label is an exit depends if we are computing gamma or
    // gammaTilde.
    const char domainExit = IS_GAMMA ? GAMMA_EXIT : GAMMATILDE_EXIT;

    // Compute coherence function along trajectory.
    for (int i = 0; i <= (yIdxMax - yIdxMin); ++i) {
      const int y = y_start + (IS_GAMMA ? i : -i);

      // Index to 2d-grids.
      const int spatialIdx = y * gridResolution + x;

      // What type of node are we on?
      const char domainLabel = inDomainLabels[spatialIdx];

      if (domainLabel == domainExit) {
        // The energy and order parameter.
        const thrust::complex<T> energy =
            energyZeroPotential + inEnergyShift[spatialIdx];
        const thrust::complex<T> delta(inOrderParameterReal[spatialIdx],
                                       inOrderParameterImag[spatialIdx]);
        const thrust::complex<T> deltaTilde = thrust::conj(delta);

        // Compute gammas and store
        const int idx_sparse = BoundaryStorage<T>::getSparseIndex(
            angleIdx, energyIdx + energyIdxOffsetStorage, x,
            boundary_exit_count, numEnergiesStorage, gridResolution,
            idx_out_gamma);

        // Compute gamma at current grid point
        const auto [gamma, gammaTilde] =
            riccati::computeHomogeneous(energy, delta, deltaTilde);
        const thrust::complex<T> gBoundary = IS_GAMMA ? gamma : gammaTilde;

        bnd_out_gamma_real[idx_sparse] = gBoundary.real();
        bnd_out_gamma_imag[idx_sparse] = gBoundary.imag();

        boundary_exit_count++;
      }
    }
  }
}
} // namespace riccati
} // namespace conga

#endif // CONGA_RICCATI_GPU_KERNELS_H_
