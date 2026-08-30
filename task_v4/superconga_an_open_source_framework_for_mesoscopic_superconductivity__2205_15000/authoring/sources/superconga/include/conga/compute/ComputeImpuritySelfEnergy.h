//===--------------------- ComputeImpuritySelfEnergy.h  -------------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Compute object class for impurity self-energy.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_COMPUTE_IMPURITY_SELF_ENERGY_H_
#define CONGA_COMPUTE_IMPURITY_SELF_ENERGY_H_

#include "../Type.h"
#include "../defines.h"
#include "../grid.h"
#include "../impurities/ImpuritySelfEnergy.h"
#include "../impurities/local_impurities.h"
#include "../utils.h"
#include "ComputeProperty.h"
#include "ComputeResidual.h"

#include <memory>
#include <thrust/complex.h>

namespace conga {
template <typename T>
class ComputeImpuritySelfEnergy : public ComputeProperty<T> {
public:
  // Constructors
  ComputeImpuritySelfEnergy(const bool inEnforceTildeSymmetry = false);
  ComputeImpuritySelfEnergy(Context<T> *ctx,
                            const bool inEnforceTildeSymmetry = false);

  GridGPU<T> *getResult() override { return nullptr; }

  ImpuritySelfEnergy<T> *getImpuritySelfEnergy() { return m_result.get(); }
  const ImpuritySelfEnergy<T> *getImpuritySelfEnergy() const {
    return m_result.get();
  }

  int initialize() override;

  // This should be called once for every iteration, before any integration
  // takes place.
  void initializeIteration(int numFields = 1) override;

  // This should be called once for every angle, before any integration takes
  // place.
  void initializeGreensAngle() override;

  // Computes greens function for current angle. This may be called multiple
  // times as we integrate over many energies. Result is in local frame and will
  // be stored in _greensCurrentAngle.
  void computeGreensAngle(const GridGPU<T> *const inGamma,
                          const GridGPU<T> *const inGammaTilde,
                          const GridGPU<T> *const inOrderParameter) override;

  // Add the result from computeGreensAngle() to total. Rotates
  // _greensCurrentAngle to global frame and adds momentum dependence.
  void integrateGreensAngle(const FermiSurface<T> *const inFermiSurface,
                            const int angleIdx) override;

  // Compute physical property from greens function.
  void computePropertyFromGreens() override;

private:
  std::unique_ptr<ImpuritySelfEnergy<T>> m_result;
  std::unique_ptr<ImpuritySelfEnergy<T>> m_tmp;

  const bool m_enforceTildeSymmetry;
};

template <typename T>
ComputeImpuritySelfEnergy<T>::ComputeImpuritySelfEnergy(
    const bool inEnforceTildeSymmetry)
    : ComputeProperty<T>(), m_enforceTildeSymmetry(inEnforceTildeSymmetry),
      m_result(nullptr), m_tmp(nullptr) {}

template <typename T>
ComputeImpuritySelfEnergy<T>::ComputeImpuritySelfEnergy(
    Context<T> *ctx, const bool inEnforceTildeSymmetry)
    : ComputeProperty<T>(ctx), m_enforceTildeSymmetry(inEnforceTildeSymmetry),
      m_result(nullptr), m_tmp(nullptr) {
  ctx->add(this);
}

template <typename T> int ComputeImpuritySelfEnergy<T>::initialize() {
#ifndef NDEBUG
  std::cout << "ComputeImpuritySelfEnergy<T>::initialize()\n";
#endif

  const int gridResolution =
      ContextModule<T>::getParameters()->getGridResolutionBase();

  // Note, for Ozaki this is all energies. But for Retarded this is the number
  // of energies in the current block.
  const int numEnergies =
      ContextModule<T>::getIntegrationIterator()->getNumEnergiesStorage();

  m_result = std::make_unique<ImpuritySelfEnergy<T>>(
      gridResolution, gridResolution, numEnergies);
  m_tmp = std::make_unique<ImpuritySelfEnergy<T>>(gridResolution,
                                                  gridResolution, numEnergies);

  return 0;
}

template <typename T>
void ComputeImpuritySelfEnergy<T>::initializeIteration(int numFields) {
  // Unused.
  (void)numFields;

  if (ComputeProperty<T>::doCompute()) {
    m_result->sigma.setZero();
    m_result->delta.setZero();

    const bool isRetarded = ContextModule<T>::getContext()->isRetarded();
    if (!m_enforceTildeSymmetry || isRetarded) {
      m_result->deltaTilde.setZero();
    }
  }
}

template <typename T>
void ComputeImpuritySelfEnergy<T>::initializeGreensAngle() {
  if (ComputeProperty<T>::doCompute()) {
    m_tmp->sigma.setZero();
    m_tmp->delta.setZero();

    const bool isRetarded = ContextModule<T>::getContext()->isRetarded();
    if (!m_enforceTildeSymmetry || isRetarded) {
      m_tmp->deltaTilde.setZero();
    }
  }
}

template <typename T>
void ComputeImpuritySelfEnergy<T>::computeGreensAngle(
    const GridGPU<T> *const inGamma, const GridGPU<T> *const inGammaTilde,
    const GridGPU<T> *const inOrderParameter) {

  if (ComputeProperty<T>::doCompute()) {
    const IntegrationIterator<T> *ii =
        ContextModule<T>::getIntegrationIterator();
    const int energyIdxOffset = ii->getEnergyIdxOffset_boundaryStorage();
    const int numEnergiesCurrentBlock = ii->getNumEnergiesInterval();

    GreensFunctionStatic<T, Greens>::computeGreens(
        inGamma, inGammaTilde, energyIdxOffset, numEnergiesCurrentBlock,
        &(m_tmp->sigma));

    const bool isRetarded = ContextModule<T>::getContext()->isRetarded();
    if (!m_enforceTildeSymmetry || isRetarded) {
      GreensFunctionStatic<T, GreensAnomalous>::computeGreens(
          inGamma, inGammaTilde, energyIdxOffset, numEnergiesCurrentBlock,
          &(m_tmp->delta));
      GreensFunctionStatic<T, GreensAnomalousTilde>::computeGreens(
          inGamma, inGammaTilde, energyIdxOffset, numEnergiesCurrentBlock,
          &(m_tmp->deltaTilde));
    } else {
      GreensFunctionStatic<T, GreensAnomalousMean>::computeGreens(
          inGamma, inGammaTilde, energyIdxOffset, numEnergiesCurrentBlock,
          &(m_tmp->delta));
      // DeltaTilde is inferred via symmetry.
    }
  }
}

template <typename T>
void ComputeImpuritySelfEnergy<T>::integrateGreensAngle(
    const FermiSurface<T> *const inFermiSurface, const int angleIdx) {
  if (ComputeProperty<T>::doCompute()) {
    const T integrandFactor = inFermiSurface->getIntegrandFactor(angleIdx);
    m_result->sigma += m_tmp->sigma * integrandFactor;
    m_result->delta += m_tmp->delta * integrandFactor;

    const bool isRetarded = ContextModule<T>::getContext()->isRetarded();
    if (!m_enforceTildeSymmetry || isRetarded) {
      m_result->deltaTilde += m_tmp->deltaTilde * integrandFactor;
    }
  }
}

namespace imp_internal {
/// @brief GPU kernel for computing the impurity self-energy.
/// @tparam T Float or double.
/// @param inDimX The number of lattice sites along the x-axis.
/// @param inDimY The number of lattice sites along the y-axis.
/// @param inNumEnergies The number of energies.
/// @param inCos Cosine of the scattering phase shift.
/// @param inSin Sine of the scattering phase shift.
/// @param inOutSigmaReal As input Real[<g>] that is overwritten by Real[Sigma].
/// @param inOutSigmaImag As input Imag[<g>] that is overwritten by Imag[Sigma].
/// @param inOutDeltaReal As input Real[<f>] that is overwritten by Real[Delta].
/// @param inOutDeltaImag As input Imag[<f>] that is overwritten by Imag[Delta].
/// @param inOutDeltaTildeReal As input Real[<fTilde>] that is overwritten by
/// Real[DeltaTilde].
/// @param inOutDeltaTildeImag As input Imag[<fTilde>] that is overwritten by
/// Imag[DeltaTilde].
template <typename T>
__global__ void
computeSelfEnergy(const int inDimX, const int inDimY, const int inNumEnergies,
                  const T inCos, const T inSin, T *const inOutSigmaReal,
                  T *const inOutSigmaImag, T *const inOutDeltaReal,
                  T *const inOutDeltaImag, T *const inOutDeltaTildeReal,
                  T *const inOutDeltaTildeImag) {
  const int x = blockIdx.x * blockDim.x + threadIdx.x;
  const int y = blockIdx.y * blockDim.y + threadIdx.y;
  const int z = blockIdx.z * blockDim.z + threadIdx.z;

  if (x < inDimX && y < inDimY && z < inNumEnergies) {
    const int idx = inDimX * (2 * z * inDimY + y) + x;

    // Read <g>, <f>, and <tilde(f)>.
    const thrust::complex<T> gAvg(inOutSigmaReal[idx], inOutSigmaImag[idx]);
    const thrust::complex<T> fAvg(inOutDeltaReal[idx], inOutDeltaImag[idx]);
    const thrust::complex<T> fTildeAvg(inOutDeltaTildeReal[idx],
                                       inOutDeltaTildeImag[idx]);

    // TODO(Niclas): I don't understand why structured bindings don't work here.
    thrust::complex<T> sigma, delta, deltaTilde;
    thrust::tie(sigma, delta, deltaTilde) =
        impurities::computeSelfEnergy(gAvg, fAvg, fTildeAvg, inCos, inSin);

    inOutSigmaReal[idx] = sigma.real();
    inOutSigmaImag[idx] = sigma.imag();

    inOutDeltaReal[idx] = delta.real();
    inOutDeltaImag[idx] = delta.imag();

    inOutDeltaTildeReal[idx] = deltaTilde.real();
    inOutDeltaTildeImag[idx] = deltaTilde.imag();
  }
}
} // namespace imp_internal

template <typename T>
void ComputeImpuritySelfEnergy<T>::computePropertyFromGreens() {
  typedef ComputeProperty<T> C;

  if (C::doCompute()) {
    const bool isRetarded = ContextModule<T>::getContext()->isRetarded();
    if (m_enforceTildeSymmetry && !isRetarded) {
      // Enforce tilde symmetry.
      m_result->deltaTilde = m_result->delta;
      m_result->deltaTilde.conjugate();
    }

    GridGPU<T> &sigma = m_result->sigma;
    GridGPU<T> &delta = m_result->delta;
    GridGPU<T> &deltaTilde = m_result->deltaTilde;

    // If not Born impurities then we need to call the GPU kernel and do the
    // general case.
    const T scatteringPhaseShift =
        C::getParameters()->getScatteringPhaseShift();
    if (std::abs(scatteringPhaseShift) > static_cast<T>(0)) {
      // Get the size and dimension.
      const int dimX = sigma.dimX();
      const int dimY = sigma.dimY();
      // For Ozaki this is the total number of energies.
      // For Retarded is the number of energies in the current block.
      const int numEnergies =
          ContextModule<T>::getIntegrationIterator()->getNumEnergiesStorage();

      // Kernel parameters.
      const auto [numBlocks, numThreadsPerBlock] =
          sigma.getKernelDimensionsFields();

      // Do trigonometry outside of the GPU kernel for performance.
      const T c = std::cos(scatteringPhaseShift);
      const T s = std::sin(scatteringPhaseShift);

      // Compute the self-energy.
      imp_internal::computeSelfEnergy<<<numBlocks, numThreadsPerBlock>>>(
          dimX, dimY, numEnergies, c, s, sigma.getDataPointer(0, Type::real),
          sigma.getDataPointer(0, Type::imag),
          delta.getDataPointer(0, Type::real),
          delta.getDataPointer(0, Type::imag),
          deltaTilde.getDataPointer(0, Type::real),
          deltaTilde.getDataPointer(0, Type::imag));
    }

    // Set values outside of the grain to zero so that the residual only is
    // computed in the actual grain.
    C::getGeometry()->zeroValuesOutsideDomainRef(&sigma);
    C::getGeometry()->zeroValuesOutsideDomainRef(&delta);
    C::getGeometry()->zeroValuesOutsideDomainRef(&deltaTilde);

    // Fetch the previous self-energies so we can compute the residual.
    const ImpuritySelfEnergy<T> *const selfEnergyOld =
        ContextModule<T>::getImpuritySelfEnergy();

    // Compute residual.
    const ResidualNorm normType = C::getParameters()->getResidualNormType();
    const T residualSigma =
        computeResidual(selfEnergyOld->sigma, sigma, normType);
    const T residualDelta =
        computeResidual(selfEnergyOld->delta, delta, normType);
    const T residualDeltaTilde =
        computeResidual(selfEnergyOld->deltaTilde, deltaTilde, normType);
    const T residual =
        std::max({residualSigma, residualDelta, residualDeltaTilde});
    ComputeProperty<T>::setResidual(residual);

    // Check convergence.
    const T convergenceCriterion =
        C::getParameters()->getConvergenceCriterion();
    const bool isConverged = residual < convergenceCriterion;
    ComputeProperty<T>::setConverged(isConverged);
  } else {
    C::setConverged(false);
  }
}
} // namespace conga

#endif // CONGA_COMPUTE_IMPURITY_SELF_ENERGY_H_
