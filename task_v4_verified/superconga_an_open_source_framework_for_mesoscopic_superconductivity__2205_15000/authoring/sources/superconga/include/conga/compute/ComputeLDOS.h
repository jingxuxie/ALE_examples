//===-- ComputeLDOS.h - Class for local density of states compute object. -===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Compute object class for local density of states.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_COMPUTE_LDOS_H_
#define CONGA_COMPUTE_LDOS_H_

#include "../Type.h"
#include "../grid.h"
#include "ComputeProperty.h"
#include "ComputeResidual.h"

namespace conga {
template <typename T> class ComputeLDOS : public ComputeProperty<T> {
public:
  // Constructors and Destructors
  ComputeLDOS();
  ~ComputeLDOS();

  ComputeLDOS(Context<T> *ctx);

  GridGPU<T> *getResult() override { return m_ldosAll; }
  GridGPU<T> *getResultInterval() { return m_ldosInterval; }

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
  // Computed LDOS will be stored here at end of IntegrationIterator::compute()
  // function.
  GridGPU<T> *m_ldosInterval;

  // The result when every energy level has converged.
  GridGPU<T> *m_ldosAll;
};

template <typename T>
ComputeLDOS<T>::ComputeLDOS()
    : ComputeProperty<T>(), m_ldosInterval(0), m_ldosAll(0) {}

template <typename T>
ComputeLDOS<T>::ComputeLDOS(Context<T> *ctx)
    : ComputeProperty<T>(ctx), m_ldosInterval(0), m_ldosAll(0) {
  ctx->add(this);
}

template <typename T> ComputeLDOS<T>::~ComputeLDOS() {
  if (m_ldosInterval) {
    delete m_ldosInterval;
  }
  if (m_ldosAll) {
    delete m_ldosAll;
  }
}

template <typename T> int ComputeLDOS<T>::initialize() {
  typedef ContextModule<T> C;

  const int N0 = C::getParameters()->getGridResolutionBase();

  const int numEnergies = C::getParameters()->getNumEnergies();
  const int numEnergiesInterval =
      C::getIntegrationIterator()->getEnergyIterator()->getNumInterval();

  GridGPU<T>::initializeGrid(m_ldosInterval, N0, N0, numEnergiesInterval,
                             Type::real);
  GridGPU<T>::initializeGrid(m_ldosAll, N0, N0, numEnergies, Type::real);

#ifndef NDEBUG
  const int memoryLDOS =
      (m_ldosAll->numElements() + m_ldosInterval->numElements()) *
      static_cast<int>(sizeof(T));
  std::cout << "LDOS memory: " << memoryLDOS << "\n";
#endif

  ComputeProperty<T>::initGreensAngle(N0, numEnergiesInterval);
  return 0;
}

template <typename T> void ComputeLDOS<T>::initializeIteration(int numFields) {
  // Unused.
  (void)numFields;

  if (ComputeProperty<T>::doCompute()) {
    m_ldosInterval->setZero();
  }
}

template <typename T> void ComputeLDOS<T>::initializeGreensAngle() {
  if (ComputeProperty<T>::doCompute())
    ComputeProperty<T>::initializeGreensAngle(); // Sets to zero
}

template <typename T>
void ComputeLDOS<T>::computeGreensAngle(
    const GridGPU<T> *const inGamma, const GridGPU<T> *const inGammaTilde,
    const GridGPU<T> *const inOrderParameter) {
  if (ComputeProperty<T>::doCompute()) {
    const IntegrationIterator<T> *ii =
        ContextModule<T>::getIntegrationIterator();
    const int energyIdxOffset = ii->getEnergyIdxOffset_boundaryStorage();
    const int numEnergiesCurrentBlock = ii->getNumEnergiesInterval();
    GreensFunctionStatic<T, Greens>::computeGreens(
        inGamma, inGammaTilde, energyIdxOffset, numEnergiesCurrentBlock,
        ComputeProperty<T>::getGreensCurrentAngle());
  }
}

namespace ldos_internal {
template <typename T>
__global__ void
integrateGreensAngle(const int inDimX, const int inDimY, const int inNumFields,
                     const T inIntegrandFactor, const T *const inGreenImag,
                     T *const inOutLDOSInterval) {
  // Indices of spatial coordinates.
  const int x = blockIdx.x * blockDim.x + threadIdx.x;
  const int y = blockIdx.y * blockDim.y + threadIdx.y;

  // Energy index.
  const int z = blockIdx.z * blockDim.z + threadIdx.z;

  if (x < inDimX && y < inDimY && z < inNumFields) {
    const int idxLDOS = inDimX * (z * inDimY + y) + x;
    // The factor of two is due to the data being complex.
    // TODO(niclas): Get rid of all these error prone, manually set, indices.
    const int idxGreen = inDimX * (z * inDimY * 2 + y) + x;
    inOutLDOSInterval[idxLDOS] += inGreenImag[idxGreen] * inIntegrandFactor;
  }
}
} // namespace ldos_internal

template <typename T>
void ComputeLDOS<T>::integrateGreensAngle(
    const FermiSurface<T> *const inFermiSurface, const int angleIdx) {
  if (ComputeProperty<T>::doCompute()) {
    GridGPU<T> *greens = ComputeProperty<T>::getGreensCurrentAngle();

    const T integrandFactor = inFermiSurface->getIntegrandFactor(angleIdx);

    // Kernel parameters.
    const auto [numBlocks, numThreadsPerBlock] =
        m_ldosInterval->getKernelDimensionsFields();

    // Dimensions.
    const int dimX = m_ldosInterval->dimX();
    const int dimY = m_ldosInterval->dimY();
    const int numFields = m_ldosInterval->numFields();

    // Call GPU kernel.
    ldos_internal::integrateGreensAngle<<<numBlocks, numThreadsPerBlock>>>(
        dimX, dimY, numFields, integrandFactor,
        greens->getDataPointer(0, Type::imag),
        m_ldosInterval->getDataPointer());
  }
}

template <typename T> void ComputeLDOS<T>::computePropertyFromGreens() {
  if (ComputeProperty<T>::doCompute()) {
    typedef ContextModule<T> C;

    // Get some info
    const ParameterIterator<int> *iter =
        C::getIntegrationIterator()->getEnergyIterator();

    const int numEnergiesCurrentBlock = iter->getNumInterval();
    const int energyIdx_offset = iter->getCurrentValue();

    // Compute LDOS
    *m_ldosInterval *= -1.0;

    C::getGeometry()->zeroValuesOutsideDomainRef(m_ldosInterval);

    const int dimX = m_ldosInterval->dimX();
    const int dimY = m_ldosInterval->dimY();
    const int numFields = m_ldosInterval->numFields();
    const Type::type representation = m_ldosInterval->representation();
    GridGPU<T> ldosIntervalOld(dimX, dimY, numFields, representation);

    // Copy temp LDOS to full grid.
    for (int i = 0; i < numEnergiesCurrentBlock; ++i) {
      m_ldosAll->copyFieldTo(&ldosIntervalOld, i + energyIdx_offset, i);
      m_ldosInterval->copyFieldTo(m_ldosAll, i, i + energyIdx_offset);
    }

    // Compute residual.
    const ResidualNorm normType = C::getParameters()->getResidualNormType();
    const T residual =
        computeResidual(ldosIntervalOld, *m_ldosInterval, normType);
    ComputeProperty<T>::setResidual(residual);

    // Check convergence.
    const bool isPartiallyConverged =
        residual < C::getParameters()->getConvergenceCriterion();
    ComputeProperty<T>::setPartiallyConverged(isPartiallyConverged);
  } else {
    ComputeProperty<T>::setConverged(false);
  }
}
} // namespace conga

#endif // CONGA_COMPUTE_LDOS_H_
