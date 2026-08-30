//= RiccatiSolverConfined.h - Solve Riccati equations in confined geometry. =//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Riccati solver implementation for confined geometries, i.e. finite system
/// confined by well-defined boundaries. Derives from the virtual class
/// RiccatiSolver.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_RICCATI_SOLVER_CONFINED_H_
#define CONGA_RICCATI_SOLVER_CONFINED_H_

#include "../grid.h"
#include "../impurities/ImpuritySelfEnergy.h"
#include "RiccatiSolver.h"
#include "riccati_gpu_kernels.h"

#include <thrust/complex.h>

#include <cmath>
#include <memory>
#include <string>

namespace conga {
template <typename T, template <typename> class POTENTIAL>
class RiccatiSolverConfined : public RiccatiSolver<T> {
public:
  // Constructors and Destructors
  RiccatiSolverConfined();
  ~RiccatiSolverConfined();

  RiccatiSolverConfined(Context<T> *ctx);

  int initialize() override;

  // Functions
  void computeCoherenceFunctionsInitial(
      const ParameterIterator<int> &inEnergyIterator,
      const GridGPU<T> &inEnergies, const GridGPU<T> &inOrderParameter,
      const int inAngleIdx) override;

  void computeCoherenceFunctionsBurnIn(
      const ParameterIterator<int> &inEnergyIterator,
      const GridGPU<T> &inEnergies, const GridGPU<T> &inOrderParameter,
      const int inAngleIdx) override;

  void computeCoherenceFunctions(const ParameterIterator<int> &inEnergyIterator,
                                 const GridGPU<T> &inEnergies,
                                 const GridGPU<T> &inOrderParameter,
                                 const int inAngleIdx) override;

  // Get a string describing the vector potential type, e.g. solenoid.
  std::string getVectorPotentialType() const { return POTENTIAL<T>::type(); }

private:
  // Enum for what to actually compute when called.
  enum class ComputeType { INITIAL, BURNIN, GENERAL };

  // Grid for storing a computed coherence function (rotated).
  GridGPU<T> m_coherenceRotated;

  // Grid for storing the rotated order parameter.
  GridGPU<T> m_orderParameterRotated;

  // Pointer to rotated impurity self-energy. Is nullptr if not used.
  std::unique_ptr<ImpuritySelfEnergy<T>> m_impuritySelfEnergyRotated;

  void computeCoherenceInternal(const ParameterIterator<int> &inEnergyIterator,
                                const GridGPU<T> &inEnergies,
                                const GridGPU<T> &inOrderParameter,
                                const int inAngleIdx,
                                const ComputeType inComputeType);

  template <bool IS_GAMMA>
  void computeCoherenceInitial(
      const riccati::KernelParameters<T> &inKernelParameters,
      const GridGPU<T> &inEnergies, const GridGPU<T> &inEnergyShift,
      const ImpuritySelfEnergy<T> *const inImpuritySelfEnergy,
      const GridGPU<T> &inOrderParameter, const GridGPU<char> &inDomainLabels,
      const GridGPU<int> &inSparseIdxExit,
      GridGPU<T> &outBoundaryCoherenceExit);

  template <bool IS_GAMMA>
  void computeCoherenceBurnIn(
      const riccati::KernelParameters<T> &inKernelParameters,
      const GridGPU<T> &inEnergies, const GridGPU<T> &inEnergyShift,
      const ImpuritySelfEnergy<T> *const inImpuritySelfEnergy,
      const GridGPU<T> &inOrderParameter, const GridGPU<char> &inDomainLabels,
      const GridGPU<T> &inBoundaryDistances,
      const GridGPU<int> &inSparseIdxEnter, const GridGPU<int> &inSparseIdxExit,
      const GridGPU<T> &inBoundaryCoherenceEnter,
      GridGPU<T> &outBoundaryCoherenceExit);

  template <bool IS_GAMMA>
  void computeCoherenceGeneral(
      const riccati::KernelParameters<T> &inKernelParameters,
      const GridGPU<T> &inEnergies, const GridGPU<T> &inEnergyShift,
      const ImpuritySelfEnergy<T> *const inImpuritySelfEnergy,
      const GridGPU<T> &inOrderParameter, const GridGPU<char> &inDomainLabels,
      const GridGPU<T> &inBoundaryDistances,
      const GridGPU<int> &inSparseIdxEnter, const GridGPU<int> &inSparseIdxExit,
      const GridGPU<T> &inBoundaryCoherenceEnter,
      GridGPU<T> &outBoundaryCoherenceExit, GridGPU<T> &outCoherence);
};

template <typename T, template <typename> class POTENTIAL>
RiccatiSolverConfined<T, POTENTIAL>::RiccatiSolverConfined()
    : RiccatiSolver<T>(), m_impuritySelfEnergyRotated(nullptr) {}

template <typename T, template <typename> class POTENTIAL>
RiccatiSolverConfined<T, POTENTIAL>::RiccatiSolverConfined(Context<T> *ctx)
    : RiccatiSolver<T>(ctx), m_impuritySelfEnergyRotated(nullptr) {
#ifndef NDEBUG
  std::cout << "RiccatiSolverConfined::RiccatiSolverConfined( Context<T>* )\n";
#endif
  ctx->set(this);
}

template <typename T, template <typename> class POTENTIAL>
RiccatiSolverConfined<T, POTENTIAL>::~RiccatiSolverConfined() {}

template <typename T, template <typename> class POTENTIAL>
int RiccatiSolverConfined<T, POTENTIAL>::initialize() {
  RiccatiSolver<T>::initialize();

  // Note that this is the CURRENT block. For Ozaki initialize is only called
  // once, so this is the maximum block size. For Retarded this will be called
  // multiple times. Thus the last block might be smaller.
  const int numEnergiesBlock =
      ContextModule<T>::getIntegrationIterator()->getNumEnergiesInterval();

  const int gridResolutionRotated =
      ContextModule<T>::getParameters()->getGridResolutionCoherence();

  m_coherenceRotated = GridGPU<T>(gridResolutionRotated, gridResolutionRotated,
                                  numEnergiesBlock, Type::complex);
  m_orderParameterRotated = GridGPU<T>(gridResolutionRotated,
                                       gridResolutionRotated, 1, Type::complex);

  return 0;
}

template <typename T, template <typename> class POTENTIAL>
void RiccatiSolverConfined<T, POTENTIAL>::computeCoherenceFunctionsInitial(
    const ParameterIterator<int> &inEnergyIterator,
    const GridGPU<T> &inEnergies, const GridGPU<T> &inOrderParameter,
    const int inAngleIdx) {
  computeCoherenceInternal(inEnergyIterator, inEnergies, inOrderParameter,
                           inAngleIdx, ComputeType::INITIAL);
}

template <typename T, template <typename> class POTENTIAL>
void RiccatiSolverConfined<T, POTENTIAL>::computeCoherenceFunctionsBurnIn(
    const ParameterIterator<int> &inEnergyIterator,
    const GridGPU<T> &inEnergies, const GridGPU<T> &inOrderParameter,
    const int inAngleIdx) {
  computeCoherenceInternal(inEnergyIterator, inEnergies, inOrderParameter,
                           inAngleIdx, ComputeType::BURNIN);
}

template <typename T, template <typename> class POTENTIAL>
void RiccatiSolverConfined<T, POTENTIAL>::computeCoherenceFunctions(
    const ParameterIterator<int> &inEnergyIterator,
    const GridGPU<T> &inEnergies, const GridGPU<T> &inOrderParameter,
    const int inAngleIdx) {
  computeCoherenceInternal(inEnergyIterator, inEnergies, inOrderParameter,
                           inAngleIdx, ComputeType::GENERAL);
}

template <typename T, template <typename> class POTENTIAL>
void RiccatiSolverConfined<T, POTENTIAL>::computeCoherenceInternal(
    const ParameterIterator<int> &inEnergyIterator,
    const GridGPU<T> &inEnergies, const GridGPU<T> &inOrderParameter,
    const int inAngleIdx, const ComputeType inComputeType) {
  // ================ The relevant objects ================ //

  const Parameters<T> *const parameters = ContextModule<T>::getParameters();
  const FermiSurface<T> *const fermiSurface =
      ContextModule<T>::getFermiSurface();
  const GeometryGroup<T> *const geometry = RiccatiSolver<T>::getGeometry();
  BoundaryStorage<T> *const storage = RiccatiSolver<T>::getBoundaryStorage();

  // ================ Set kernel parameters ================ //

  riccati::KernelParameters<T> kernelParameters;
  const T h = parameters->getGridElementSize();
  const T fermiSpeed = fermiSurface->getFermiSpeed(inAngleIdx);
  kernelParameters.stepSize = h / fermiSpeed;
  kernelParameters.scatteringEnergy = parameters->getScatteringEnergy();
  kernelParameters.gridResolution = parameters->getGridResolutionCoherence();
  kernelParameters.numEnergiesBlock = inEnergyIterator.getNumInterval();
  kernelParameters.energyIdxOffset = inEnergyIterator.getCurrentValue();
  kernelParameters.angleIdx = inAngleIdx;
  kernelParameters.numEnergiesStorage =
      ContextModule<T>::getIntegrationIterator()->getNumEnergiesStorage();
  kernelParameters.energyIdxOffsetStorage =
      ContextModule<T>::getIntegrationIterator()
          ->getEnergyIdxOffset_boundaryStorage();
  kernelParameters.xIdxMin =
      (storage->getTrajectoryRangeX()->getDataPointer(0))[inAngleIdx];
  kernelParameters.xIdxMax =
      (storage->getTrajectoryRangeX()->getDataPointer(1))[inAngleIdx];
  kernelParameters.yIdxMin =
      (storage->getTrajectoryRangeY()->getDataPointer(0))[inAngleIdx];
  kernelParameters.yIdxMax =
      (storage->getTrajectoryRangeY()->getDataPointer(1))[inAngleIdx];

  // ================ The relevant geometry grids ================ //

  const GridGPU<char> &domainLabelsRotated = *(geometry->getDomainLabelsGrid());
  const GridGPU<char> &domainLabelsRef = *(geometry->getDomainGrid());
  const GridGPU<T> &boundaryDistancesRotated =
      *(geometry->getBoundaryDistanceGrid());

  // ================ Rotate what needs to be rotated ================ //

  const T systemAngle = fermiSurface->getSystemAngle(inAngleIdx);

  geometry::rotate(-systemAngle, domainLabelsRef, domainLabelsRotated,
                   inOrderParameter, m_orderParameterRotated);

  const ImpuritySelfEnergy<T> *const impuritySelfEnergy =
      ContextModule<T>::getImpuritySelfEnergy();
  if (impuritySelfEnergy) {
    if (!m_impuritySelfEnergyRotated) {
      const int dimX = m_orderParameterRotated.dimX();
      const int dimY = m_orderParameterRotated.dimY();
      const int numFields = kernelParameters.numEnergiesBlock;
      m_impuritySelfEnergyRotated =
          std::make_unique<ImpuritySelfEnergy<T>>(dimX, dimY, numFields);
    }
    geometry::rotate(-systemAngle, domainLabelsRef, domainLabelsRotated,
                     kernelParameters.energyIdxOffsetStorage,
                     impuritySelfEnergy->sigma,
                     m_impuritySelfEnergyRotated->sigma);
    geometry::rotate(-systemAngle, domainLabelsRef, domainLabelsRotated,
                     kernelParameters.energyIdxOffsetStorage,
                     impuritySelfEnergy->delta,
                     m_impuritySelfEnergyRotated->delta);
    geometry::rotate(-systemAngle, domainLabelsRef, domainLabelsRotated,
                     kernelParameters.energyIdxOffsetStorage,
                     impuritySelfEnergy->deltaTilde,
                     m_impuritySelfEnergyRotated->deltaTilde);
  }

  // Compute energy shift from magnetic field (via rotated vector potential).
  const auto [fermiVelocityX, fermiVelocityY] =
      fermiSurface->getFermiVelocity(inAngleIdx);
  const T area = geometry->area();
  const GridGPU<T> &inducedVectorPotential =
      *(ContextModule<T>::getContext()->getInducedVectorPotential());
  GridGPU<T> &energyShift = *(RiccatiSolver<T>::getEnergyShift());
  computeEnergyShift<T, POTENTIAL>(*parameters, systemAngle, fermiVelocityX,
                                   fermiVelocityY, area, inducedVectorPotential,
                                   energyShift);

  // ================ The relevant storage grids ================ //

  const GridGPU<int> &gammaSparseIdxEnter =
      *(storage->getIndexSparseIn_gamma());
  const GridGPU<int> &gammaSparseIdxExit =
      *(storage->getIndexSparseOut_gamma());
  const GridGPU<int> &gammaTildeSparseIdxEnter =
      *(storage->getIndexSparseIn_gammabar());
  const GridGPU<int> &gammaTildeSparseIdxExit =
      *(storage->getIndexSparseOut_gammabar());
  const GridGPU<T> &gammaBoundaryEnter = *(storage->getBoundaryIn_gamma());
  const GridGPU<T> &gammaTildeBoundaryEnter =
      *(storage->getBoundaryIn_gammabar());
  GridGPU<T> &gammaBoundaryExit = *(storage->getBoundaryOut_gamma());
  GridGPU<T> &gammaTildeBoundaryExit = *(storage->getBoundaryOut_gammabar());

  switch (inComputeType) {
  case ComputeType::INITIAL: {
    // Gamma: Set boundary to bulk values.
    computeCoherenceInitial<true>(kernelParameters, inEnergies, energyShift,
                                  m_impuritySelfEnergyRotated.get(),
                                  m_orderParameterRotated, domainLabelsRotated,
                                  gammaSparseIdxExit, gammaBoundaryExit);

    // GammaTilde: Set boundary to bulk values.
    computeCoherenceInitial<false>(
        kernelParameters, inEnergies, energyShift,
        m_impuritySelfEnergyRotated.get(), m_orderParameterRotated,
        domainLabelsRotated, gammaTildeSparseIdxExit, gammaTildeBoundaryExit);

    break;
  } // End initial.
  case ComputeType::BURNIN: {
    // Gamma: Compute boundary without storing the values in the domain.
    computeCoherenceBurnIn<true>(
        kernelParameters, inEnergies, energyShift,
        m_impuritySelfEnergyRotated.get(), m_orderParameterRotated,
        domainLabelsRotated, boundaryDistancesRotated, gammaSparseIdxEnter,
        gammaSparseIdxExit, gammaBoundaryEnter, gammaBoundaryExit);

    // GammaTilde: Compute boundary without storing the values in the domain.
    computeCoherenceBurnIn<false>(
        kernelParameters, inEnergies, energyShift,
        m_impuritySelfEnergyRotated.get(), m_orderParameterRotated,
        domainLabelsRotated, boundaryDistancesRotated, gammaTildeSparseIdxEnter,
        gammaTildeSparseIdxExit, gammaTildeBoundaryEnter,
        gammaTildeBoundaryExit);

    break;
  } // End Burnin.
  case ComputeType::GENERAL: {
    // Gamma: Compute boundary and the domain.
    computeCoherenceGeneral<true>(kernelParameters, inEnergies, energyShift,
                                  m_impuritySelfEnergyRotated.get(),
                                  m_orderParameterRotated, domainLabelsRotated,
                                  boundaryDistancesRotated, gammaSparseIdxEnter,
                                  gammaSparseIdxExit, gammaBoundaryEnter,
                                  gammaBoundaryExit, m_coherenceRotated);
    GridGPU<T> &gamma = *(RiccatiSolver<T>::getGamma());
    geometry::rotate(systemAngle, domainLabelsRotated, domainLabelsRef,
                     m_coherenceRotated, gamma);

    // GammaTilde: Compute boundary and the domain.
    computeCoherenceGeneral<false>(
        kernelParameters, inEnergies, energyShift,
        m_impuritySelfEnergyRotated.get(), m_orderParameterRotated,
        domainLabelsRotated, boundaryDistancesRotated, gammaTildeSparseIdxEnter,
        gammaTildeSparseIdxExit, gammaTildeBoundaryEnter,
        gammaTildeBoundaryExit, m_coherenceRotated);
    GridGPU<T> &gammaTilde = *(RiccatiSolver<T>::getGammaTilde());
    geometry::rotate(systemAngle, domainLabelsRotated, domainLabelsRef,
                     m_coherenceRotated, gammaTilde);

    break;
  } // End General.
  } // End switch.
}

template <typename T, template <typename> class POTENTIAL>
template <bool IS_GAMMA>
void RiccatiSolverConfined<T, POTENTIAL>::computeCoherenceInitial(
    const riccati::KernelParameters<T> &inKernelParameters,
    const GridGPU<T> &inEnergies, const GridGPU<T> &inEnergyShift,
    const ImpuritySelfEnergy<T> *const inImpuritySelfEnergy,
    const GridGPU<T> &inOrderParameter, const GridGPU<char> &inDomainLabels,
    const GridGPU<int> &inSparseIdxExit, GridGPU<T> &outBoundaryCoherenceExit) {

  const auto [blocksPerGrid, threadsPerBlock] =
      RiccatiSolver<T>::getKernelDimensionsOptim(
          inKernelParameters.numEnergiesBlock, inKernelParameters.angleIdx);

  if (inImpuritySelfEnergy) {
    riccati::computeCoherenceInitial<T, IS_GAMMA>
        <<<blocksPerGrid, threadsPerBlock>>>(
            inKernelParameters, inEnergies.getDataPointer(0, Type::real),
            inEnergies.getDataPointer(0, Type::imag),
            inEnergyShift.getDataPointer(),
            inImpuritySelfEnergy->sigma.getDataPointer(0, Type::real),
            inImpuritySelfEnergy->sigma.getDataPointer(0, Type::imag),
            inImpuritySelfEnergy->delta.getDataPointer(0, Type::real),
            inImpuritySelfEnergy->delta.getDataPointer(0, Type::imag),
            inImpuritySelfEnergy->deltaTilde.getDataPointer(0, Type::real),
            inImpuritySelfEnergy->deltaTilde.getDataPointer(0, Type::imag),
            inOrderParameter.getDataPointer(0, Type::real),
            inOrderParameter.getDataPointer(0, Type::imag),
            inDomainLabels.getDataPointer(), inSparseIdxExit.getDataPointer(),
            outBoundaryCoherenceExit.getDataPointer(0, Type::real),
            outBoundaryCoherenceExit.getDataPointer(0, Type::imag));
  } else {
    riccati::computeCoherenceInitial<T, IS_GAMMA>
        <<<blocksPerGrid, threadsPerBlock>>>(
            inKernelParameters, inEnergies.getDataPointer(0, Type::real),
            inEnergies.getDataPointer(0, Type::imag),
            inEnergyShift.getDataPointer(),
            inOrderParameter.getDataPointer(0, Type::real),
            inOrderParameter.getDataPointer(0, Type::imag),
            inDomainLabels.getDataPointer(), inSparseIdxExit.getDataPointer(),
            outBoundaryCoherenceExit.getDataPointer(0, Type::real),
            outBoundaryCoherenceExit.getDataPointer(0, Type::imag));
  }
}

template <typename T, template <typename> class POTENTIAL>
template <bool IS_GAMMA>
void RiccatiSolverConfined<T, POTENTIAL>::computeCoherenceBurnIn(
    const riccati::KernelParameters<T> &inKernelParameters,
    const GridGPU<T> &inEnergies, const GridGPU<T> &inEnergyShift,
    const ImpuritySelfEnergy<T> *const inImpuritySelfEnergy,
    const GridGPU<T> &inOrderParameter, const GridGPU<char> &inDomainLabels,
    const GridGPU<T> &inBoundaryDistances, const GridGPU<int> &inSparseIdxEnter,
    const GridGPU<int> &inSparseIdxExit,
    const GridGPU<T> &inBoundaryCoherenceEnter,
    GridGPU<T> &outBoundaryCoherenceExit) {

  const auto [blocksPerGrid, threadsPerBlock] =
      RiccatiSolver<T>::getKernelDimensionsOptim(
          inKernelParameters.numEnergiesBlock, inKernelParameters.angleIdx);

  if (inImpuritySelfEnergy) {
    riccati::computeCoherenceBurnIn<T, IS_GAMMA>
        <<<blocksPerGrid, threadsPerBlock>>>(
            inKernelParameters, inEnergies.getDataPointer(0, Type::real),
            inEnergies.getDataPointer(0, Type::imag),
            inEnergyShift.getDataPointer(),
            inImpuritySelfEnergy->sigma.getDataPointer(0, Type::real),
            inImpuritySelfEnergy->sigma.getDataPointer(0, Type::imag),
            inImpuritySelfEnergy->delta.getDataPointer(0, Type::real),
            inImpuritySelfEnergy->delta.getDataPointer(0, Type::imag),
            inImpuritySelfEnergy->deltaTilde.getDataPointer(0, Type::real),
            inImpuritySelfEnergy->deltaTilde.getDataPointer(0, Type::imag),
            inOrderParameter.getDataPointer(0, Type::real),
            inOrderParameter.getDataPointer(0, Type::imag),
            inDomainLabels.getDataPointer(),
            inBoundaryDistances.getDataPointer(),
            inSparseIdxEnter.getDataPointer(), inSparseIdxExit.getDataPointer(),
            inBoundaryCoherenceEnter.getDataPointer(0, Type::real),
            inBoundaryCoherenceEnter.getDataPointer(0, Type::imag),
            outBoundaryCoherenceExit.getDataPointer(0, Type::real),
            outBoundaryCoherenceExit.getDataPointer(0, Type::imag));
  } else {
    riccati::computeCoherenceBurnIn<T, IS_GAMMA>
        <<<blocksPerGrid, threadsPerBlock>>>(
            inKernelParameters, inEnergies.getDataPointer(0, Type::real),
            inEnergies.getDataPointer(0, Type::imag),
            inEnergyShift.getDataPointer(),
            inOrderParameter.getDataPointer(0, Type::real),
            inOrderParameter.getDataPointer(0, Type::imag),
            inDomainLabels.getDataPointer(),
            inBoundaryDistances.getDataPointer(),
            inSparseIdxEnter.getDataPointer(), inSparseIdxExit.getDataPointer(),
            inBoundaryCoherenceEnter.getDataPointer(0, Type::real),
            inBoundaryCoherenceEnter.getDataPointer(0, Type::imag),
            outBoundaryCoherenceExit.getDataPointer(0, Type::real),
            outBoundaryCoherenceExit.getDataPointer(0, Type::imag));
  }
}

template <typename T, template <typename> class POTENTIAL>
template <bool IS_GAMMA>
void RiccatiSolverConfined<T, POTENTIAL>::computeCoherenceGeneral(
    const riccati::KernelParameters<T> &inKernelParameters,
    const GridGPU<T> &inEnergies, const GridGPU<T> &inEnergyShift,
    const ImpuritySelfEnergy<T> *const inImpuritySelfEnergy,
    const GridGPU<T> &inOrderParameter, const GridGPU<char> &inDomainLabels,
    const GridGPU<T> &inBoundaryDistances, const GridGPU<int> &inSparseIdxEnter,
    const GridGPU<int> &inSparseIdxExit,
    const GridGPU<T> &inBoundaryCoherenceEnter,
    GridGPU<T> &outBoundaryCoherenceExit, GridGPU<T> &outCoherence) {

  const auto [blocksPerGrid, threadsPerBlock] =
      RiccatiSolver<T>::getKernelDimensionsOptim(
          inKernelParameters.numEnergiesBlock, inKernelParameters.angleIdx);

  if (inImpuritySelfEnergy) {
    riccati::computeCoherence<T, IS_GAMMA><<<blocksPerGrid, threadsPerBlock>>>(
        inKernelParameters, inEnergies.getDataPointer(0, Type::real),
        inEnergies.getDataPointer(0, Type::imag),
        inEnergyShift.getDataPointer(),
        inImpuritySelfEnergy->sigma.getDataPointer(0, Type::real),
        inImpuritySelfEnergy->sigma.getDataPointer(0, Type::imag),
        inImpuritySelfEnergy->delta.getDataPointer(0, Type::real),
        inImpuritySelfEnergy->delta.getDataPointer(0, Type::imag),
        inImpuritySelfEnergy->deltaTilde.getDataPointer(0, Type::real),
        inImpuritySelfEnergy->deltaTilde.getDataPointer(0, Type::imag),
        inOrderParameter.getDataPointer(0, Type::real),
        inOrderParameter.getDataPointer(0, Type::imag),
        inDomainLabels.getDataPointer(), inBoundaryDistances.getDataPointer(),
        inSparseIdxEnter.getDataPointer(), inSparseIdxExit.getDataPointer(),
        inBoundaryCoherenceEnter.getDataPointer(0, Type::real),
        inBoundaryCoherenceEnter.getDataPointer(0, Type::imag),
        outBoundaryCoherenceExit.getDataPointer(0, Type::real),
        outBoundaryCoherenceExit.getDataPointer(0, Type::imag),
        outCoherence.getDataPointer(0, Type::real),
        outCoherence.getDataPointer(0, Type::imag));
  } else {
    riccati::computeCoherence<T, IS_GAMMA><<<blocksPerGrid, threadsPerBlock>>>(
        inKernelParameters, inEnergies.getDataPointer(0, Type::real),
        inEnergies.getDataPointer(0, Type::imag),
        inEnergyShift.getDataPointer(),
        inOrderParameter.getDataPointer(0, Type::real),
        inOrderParameter.getDataPointer(0, Type::imag),
        inDomainLabels.getDataPointer(), inBoundaryDistances.getDataPointer(),
        inSparseIdxEnter.getDataPointer(), inSparseIdxExit.getDataPointer(),
        inBoundaryCoherenceEnter.getDataPointer(0, Type::real),
        inBoundaryCoherenceEnter.getDataPointer(0, Type::imag),
        outBoundaryCoherenceExit.getDataPointer(0, Type::real),
        outBoundaryCoherenceExit.getDataPointer(0, Type::imag),
        outCoherence.getDataPointer(0, Type::real),
        outCoherence.getDataPointer(0, Type::imag));
  }
}
} // namespace conga

#endif // CONGA_RICCATI_SOLVER_CONFINED_H_
