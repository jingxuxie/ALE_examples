//===---- ComputeCurrent.h - Class for current density compute object. ----===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Compute object class for current density.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_COMPUTE_CURRENT_H_
#define CONGA_COMPUTE_CURRENT_H_

#include "../defines.h"
#include "../grid.h"
#include "../utils.h"
#include "ComputeProperty.h"
#include "ComputeResidual.h"

#include <memory>

namespace conga {
template <typename T> class ComputeCurrent : public ComputeProperty<T> {
public:
  // Constructors.
  ComputeCurrent();
  ComputeCurrent(Context<T> *ctx);

  GridGPU<T> *getResult() override { return m_result.get(); }

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
                            const int inAngleIdx) override;

  // Compute physical property from greens function.
  void computePropertyFromGreens() override;

private:
  // The result, i.e. the charge-current density.
  std::unique_ptr<GridGPU<T>> m_result;

  // The previous result in order to compute residuals.
  std::unique_ptr<GridGPU<T>> m_resultPrevious;

  // Whether this is the first iteration or not. If it is the first then the
  // residual is not computed.
  bool m_isFirstIteration;
};

template <typename T>
ComputeCurrent<T>::ComputeCurrent()
    : ComputeProperty<T>(), m_result(nullptr), m_resultPrevious(nullptr),
      m_isFirstIteration(true) {}

template <typename T>
ComputeCurrent<T>::ComputeCurrent(Context<T> *ctx)
    : ComputeProperty<T>(ctx), m_result(nullptr), m_resultPrevious(nullptr),
      m_isFirstIteration(true) {
  ctx->add(this);
}

template <typename T> int ComputeCurrent<T>::initialize() {
#ifndef NDEBUG
  std::cout << "ComputeCurrent<T>::initialize()\n";
#endif
  const int gridResolution =
      ContextModule<T>::getParameters()->getGridResolutionBase();

  m_result = std::make_unique<GridGPU<T>>(gridResolution, gridResolution, 2,
                                          Type::real);
  m_resultPrevious = std::make_unique<GridGPU<T>>(
      gridResolution, gridResolution, 2, Type::real);

  ComputeProperty<T>::initGreensAngle(gridResolution);

  return 0;
}

template <typename T>
void ComputeCurrent<T>::initializeIteration(int numFields) {
  // Unused.
  (void)numFields;

  if (ComputeProperty<T>::doCompute()) {
    m_result->setZero();
  }
}

template <typename T> void ComputeCurrent<T>::initializeGreensAngle() {
  if (ComputeProperty<T>::doCompute()) {
    // Set to zero.
    ComputeProperty<T>::initializeGreensAngle();
  }
}

template <typename T>
void ComputeCurrent<T>::computeGreensAngle(
    const GridGPU<T> *const inGamma, const GridGPU<T> *const inGammaTilde,
    const GridGPU<T> *const inOrderParameter) {
  if (ComputeProperty<T>::doCompute()) {
    const IntegrationIterator<T> *ii =
        ContextModule<T>::getIntegrationIterator();
    const GridGPU<T> *residues = ii->getResidues();
    const int energyIdxOffset = ii->getEnergyIdxOffset_boundaryStorage();
    const int numEnergiesCurrentBlock = ii->getNumEnergiesInterval();

    GreensFunctionStatic<T, Greens>::computeGreensSumEnergy(
        inGamma, inGammaTilde, residues, energyIdxOffset,
        numEnergiesCurrentBlock, ComputeProperty<T>::getGreensCurrentAngle());
  }
}

namespace current_density_internal {
template <typename T>
__global__ void
integrateGreensAngle(const int inDimX, const int inDimY,
                     const T inFermiVelocityX, const T inFermiVelocityY,
                     const T inIntegrandFactor, const T *const inGreenReal,
                     T *const inOutCurrentDensityX,
                     T *const inOutCurrentDensityY) {
  // Indices of spatial coordinates.
  const int x = blockIdx.x * blockDim.x + threadIdx.x;
  const int y = blockIdx.y * blockDim.y + threadIdx.y;

  if (x < inDimX && y < inDimY) {
    const int idx = inDimX * y + x;
    const T green = inGreenReal[idx] * inIntegrandFactor;
    inOutCurrentDensityX[idx] += green * inFermiVelocityX;
    inOutCurrentDensityY[idx] += green * inFermiVelocityY;
  }
}
} // namespace current_density_internal

template <typename T>
void ComputeCurrent<T>::integrateGreensAngle(
    const FermiSurface<T> *const inFermiSurface, const int inAngleIdx) {
  if (ComputeProperty<T>::doCompute()) {
    const GridGPU<T> *const greens =
        ComputeProperty<T>::getGreensCurrentAngle();

    const auto [fermiVelocityX, fermiVelocityY] =
        inFermiSurface->getFermiVelocity(inAngleIdx);
    const T integrandFactor = inFermiSurface->getIntegrandFactor(inAngleIdx);

    // Kernel parameters.
    const auto [numBlocks, numThreadsPerBlock] =
        m_result->getKernelDimensions();

    const int dimX = m_result->dimX();
    const int dimY = m_result->dimY();

    // Call GPU kernel.
    current_density_internal::
        integrateGreensAngle<<<numBlocks, numThreadsPerBlock>>>(
            dimX, dimY, fermiVelocityX, fermiVelocityY, integrandFactor,
            greens->getDataPointer(0, Type::real), m_result->getDataPointer(0),
            m_result->getDataPointer(1));
  }
}

template <typename T> void ComputeCurrent<T>::computePropertyFromGreens() {
  if (ComputeProperty<T>::doCompute()) {
    const T T_Tc = ContextModule<T>::getParameters()->getTemperature();
    const int chargeSign = ContextModule<T>::getParameters()->getChargeSign();
    // The factor of 2 comes from defining j_d = 2*pi*kB*Tc*|e|*vF*NF.
    const T factor = static_cast<T>(2 * chargeSign) * T_Tc;
    *m_result *= factor;

    // Set zero outside of the domain so that the residual is computed
    // correctly.
    ContextModule<T>::getGeometry()->zeroValuesOutsideDomainRef(m_result.get());

    // Compute residual.
    const ResidualNorm normType =
        ContextModule<T>::getParameters()->getResidualNormType();
    const T actualResidual =
        computeResidual(*m_resultPrevious, *m_result, normType);

    // Fetch convergence criterion.
    const T convergenceCriterion =
        ContextModule<T>::getParameters()->getConvergenceCriterion();

    // Fake residual to use the first iteration. This is done because the
    // initial current density has nothing to do with the initial order
    // parameter and vector potential. So the residual from the first iteration
    // is nonsense, and prevents the program from saying that convergence has
    // been reached when starting from a previously converged solution.
    // TODO(Niclas): Read the current from file?
    const T fakeResidual = convergenceCriterion * static_cast<T>(0.1);

    // Set residual.
    const T residual = m_isFirstIteration ? fakeResidual : actualResidual;
    ComputeProperty<T>::setResidual(residual);

    // Check convergence.
    const bool isConverged = residual < convergenceCriterion;
    ComputeProperty<T>::setConverged(isConverged);

    // Copy to previous.
    *m_resultPrevious = *m_result;

    // First iteration is done.
    m_isFirstIteration = false;
  } else {
    ComputeProperty<T>::setConverged(false);
  }
}
} // namespace conga

#endif // CONGA_COMPUTE_CURRENT_H_
