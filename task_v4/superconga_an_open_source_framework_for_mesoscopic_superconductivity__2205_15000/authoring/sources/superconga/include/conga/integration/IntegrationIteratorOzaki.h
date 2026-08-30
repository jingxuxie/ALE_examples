//===-- IntegrationiteratorOzaki.h - Ozaki integration summation. ---------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Ozaki implementation of the integration iterator, i.e. the class that
/// handles summation over Ozaki poles.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_INTEGRATION_ITERATOR_OZAKI_H_
#define CONGA_INTEGRATION_ITERATOR_OZAKI_H_

#include "../Context.h"
#include "../ParameterIterator.h"
#include "../compute/ComputeProperty.h"
#include "../fermi_surface/FermiSurface.h"
#include "../geometry/GeometryGroup.h"
#include "../order_parameter/OrderParameter.h"
#include "../ozaki.h"
#include "../riccati/RiccatiSolver.h"
#include "../utils.h"

#include <thrust/device_vector.h>

#include <vector>

namespace conga {
template <typename T>
class IntegrationIteratorOzaki : public IntegrationIterator<T> {
public:
  IntegrationIteratorOzaki(const int inNumEnergiesPerBlock = -1);
  IntegrationIteratorOzaki(Context<T> *const inOutContext,
                           const int inNumEnergiesPerBlock = -1);
  ~IntegrationIteratorOzaki();

  int initialize() override;

  // Configures energy iterators
  void initIterators(const int inNumEnergiesPerBlock);
  void initEnergies() override;

  int getNumEnergiesInterval() const override;
  int getEnergyIdxOffset_boundaryStorage() const override;
  int getNumEnergiesStorage() const override;

  // Call this once before starting self consistent iteration, or when changing
  // initial condition.
  void setBoundaryInitialCondition() override;

  // Computes all properties added with addComputeProperty(). Iterate this self
  // consistently.
  void compute(const bool inIsBurnIn) override;

private:
  bool m_boundaryInitialized;
};

template <typename T>
IntegrationIteratorOzaki<T>::IntegrationIteratorOzaki(
    const int inNumEnergiesPerBlock)
    : IntegrationIterator<T>(inNumEnergiesPerBlock),
      m_boundaryInitialized(false) {}

template <typename T>
IntegrationIteratorOzaki<T>::IntegrationIteratorOzaki(
    Context<T> *const inOutContext, int inNumEnergiesPerBlock)
    : IntegrationIterator<T>(inOutContext, inNumEnergiesPerBlock),
      m_boundaryInitialized(false) {
#ifndef NDEBUG
  std::cout << "IntegrationIteratorOzaki<T>()\n";
#endif
  inOutContext->set(this);
}

template <typename T> IntegrationIteratorOzaki<T>::~IntegrationIteratorOzaki() {
#ifndef NDEBUG
  std::cout << "~IntegrationIteratorOzaki()\n";
#endif
}

template <typename T> int IntegrationIteratorOzaki<T>::initialize() {
#ifndef NDEBUG
  std::cout << "IntegrationIteratorOzaki::initialize()\n";
#endif
  IntegrationIterator<T>::initialize();
  const int numEnergiesPerBlock =
      IntegrationIterator<T>::getNumEnergiesPerBlock();
  initIterators(numEnergiesPerBlock);

  return 0;
}

template <typename T> void IntegrationIteratorOzaki<T>::initEnergies() {
  const Parameters<T> *param = ContextModule<T>::getParameters();

  const T temperature = param->getTemperature();
  const int numEnergies = param->getNumOzakiEnergies();

  const auto [energiesCPU, residuesCPU] =
      ozaki::computeEnergiesAndResidues(temperature, numEnergies);

  GridGPU<T> *energies = new GridGPU<T>(numEnergies, 1, 1, Type::complex);
  thrust::device_vector<T> &data = energies->getVector();
  thrust::copy(energiesCPU.begin(), energiesCPU.end(),
               data.begin() + energiesCPU.size());

  GridGPU<T> *residues = new GridGPU<T>(numEnergies, 1, 1, Type::real);
  residues->setVector(residuesCPU);

  IntegrationIterator<T>::setEnergies(energies);
  IntegrationIterator<T>::setResidues(residues);
}

template <typename T>
void IntegrationIteratorOzaki<T>::initIterators(
    const int inNumEnergiesPerBlock) {
  typedef IntegrationIterator<T> I;

  initEnergies();

  const int numEnergies = I::getEnergies()->dimX();

  ParameterIterator<int> *iter = new ParameterIterator<int>(0, numEnergies);
  I::setEnergyIterator(iter);

  const int numEnergiesPerBlock =
      inNumEnergiesPerBlock < 1 ? numEnergies
                                : std::min(inNumEnergiesPerBlock, numEnergies);
  iter->setIncrement(numEnergiesPerBlock);

#ifndef NDEBUG
  std::cout << "Initializing ozaki iterator with Ne = " << numEnergies
            << ", NeBlock = " << numEnergiesPerBlock << "\n";

  for (iter->begin(); !iter->isDone(); iter->next()) {
    std::cout << "min = " << iter->getMin() << "\n";
    std::cout << "max = " << iter->getMax() << "\n";
    std::cout << "inc = " << iter->getIncrement() << "\n";
    std::cout << "num = " << iter->getNumInterval() << "\n\n";
  }
#endif

  iter->begin();
}

template <typename T>
int IntegrationIteratorOzaki<T>::getNumEnergiesInterval() const {
  return IntegrationIterator<T>::getEnergyIterator()->getNumInterval();
}

template <typename T>
int IntegrationIteratorOzaki<T>::getEnergyIdxOffset_boundaryStorage() const {
  // The storage knows about all energies. So there is an offset.
  return IntegrationIterator<T>::getEnergyIterator()->getCurrentValue();
}

template <typename T>
int IntegrationIteratorOzaki<T>::getNumEnergiesStorage() const {
  // The storage needs to have the same size as the total number of energies.
  return IntegrationIterator<T>::getEnergies()->dimX();
}

template <typename T>
void IntegrationIteratorOzaki<T>::setBoundaryInitialCondition() {
#ifndef NDEBUG
  std::cout << "IntegrationIteratorOzaki<T>::setBoundaryInitialCondition(): "
               "Begin...\n";
#endif

  typedef IntegrationIterator<T> I;

  Context<T> *context = ContextModule<T>::getContext();

  // Get some parameters and variables
  const int numAngles = context->getParameters()->getAngularResolution();

  ParameterIterator<int> *energyIterator = I::getEnergyIterator();
  const GridGPU<T> &energies = *(I::getEnergies());

  RiccatiSolver<T> *riccatiSolver = context->getRiccatiSolver();
  GeometryGroup<T> *geometryGroup = context->getGeometry();
  const OrderParameter<T> *const orderParameter = context->getOrderParameter();
  const FermiSurface<T> *const fermiSurface = context->getFermiSurface();

  // Do angle loop (integrate over momentum angles)
  for (int angleIdx = 0; angleIdx < numAngles; ++angleIdx) {
    // The Fermi momentum.
    const auto [fermiMomentumX, fermiMomentumY] =
        fermiSurface->getFermiMomentum(angleIdx);

    // Rotate order parameter field to current angle
    const GridGPU<T> orderParameterWithMomentum =
        orderParameter->getMomentumDependentGrid(fermiMomentumX,
                                                 fermiMomentumY);

    // Angle (in radians) of system in local frame.
    const T systemAngle = fermiSurface->getSystemAngle(angleIdx);

    // Create discrete geometry data for current angle
    geometryGroup->create(-systemAngle);

    // Compute coherence functions and store on boundary as initial condition
    for (energyIterator->begin(); !energyIterator->isDone();
         energyIterator->next()) {
      riccatiSolver->computeCoherenceFunctionsInitial(
          *energyIterator, energies, orderParameterWithMomentum, angleIdx);
    }
  }

  // Apply boundary condition(s).
  riccatiSolver->computeBoundaryConditions();

  // The boundary is initialized.
  m_boundaryInitialized = true;

#ifndef NDEBUG
  std::cout
      << "IntegrationIteratorOzaki<T>::setBoundaryInitialCondition(): Done!\n";
#endif

  // Print GPU error, if any.
  ContextModule<T>::checkGpuError(
      "IntegrationIteratorOzaki<T>::setBoundaryInitialCondition()");
}

template <typename T>
void IntegrationIteratorOzaki<T>::compute(const bool inIsBurnIn) {
  typedef IntegrationIterator<T> I;

  Context<T> *context = ContextModule<T>::getContext();

  // Get some parameters and variables
  const int numAngles = context->getParameters()->getAngularResolution();
  const FermiSurface<T> *const fermiSurface = context->getFermiSurface();

  ParameterIterator<int> *energyIterator = I::getEnergyIterator();
  const GridGPU<T> &energies = *(I::getEnergies());

  RiccatiSolver<T> *riccatiSolver = context->getRiccatiSolver();
  GeometryGroup<T> *geometryGroup = context->getGeometry();
  const OrderParameter<T> *const orderParameter = context->getOrderParameter();

  const int numComputeObjects = context->getNumComputeObjects();

  // Set initial condition on boundary.
  if (!m_boundaryInitialized) {
    setBoundaryInitialCondition();
  }

  if (!inIsBurnIn) {
    for (int i = 0; i < numComputeObjects; ++i) {
      context->getComputeObject(i)->initializeIteration(
          energyIterator->getNumInterval());
    }
  }

  // Do angle loop (=momentum integral, and sum over energies).
  for (int angleIdx = 0; angleIdx < numAngles; ++angleIdx) {
    // The Fermi momentum.
    const auto [fermiMomentumX, fermiMomentumY] =
        fermiSurface->getFermiMomentum(angleIdx);

    // Rotate order parameter field to current angle
    const GridGPU<T> orderParameterWithMomentum =
        orderParameter->getMomentumDependentGrid(fermiMomentumX,
                                                 fermiMomentumY);

    // Angle (in radians) of system in local frame.
    const T systemAngle = fermiSurface->getSystemAngle(angleIdx);

    // Create discrete geometry data for current angle
    geometryGroup->create(-systemAngle);

    if (!inIsBurnIn) {
      // Solve Riccati equations for current angle and compute propagators.
      for (int i = 0; i < numComputeObjects; ++i) {
        context->getComputeObject(i)->initializeGreensAngle();
      }
    }

    // Iterate over (possibly) several blocks of energies.
    for (energyIterator->begin(); !energyIterator->isDone();
         energyIterator->next()) {

      if (inIsBurnIn) {
        riccatiSolver->computeCoherenceFunctionsBurnIn(
            *energyIterator, energies, orderParameterWithMomentum, angleIdx);
      } else {
        riccatiSolver->computeCoherenceFunctions(
            *energyIterator, energies, orderParameterWithMomentum, angleIdx);

        for (int i = 0; i < numComputeObjects; ++i) {
          context->getComputeObject(i)->computeGreensAngle(
              riccatiSolver->getGamma(), riccatiSolver->getGammaTilde(),
              &orderParameterWithMomentum);
        }
      }
    }

    if (!inIsBurnIn) {
      // Add integration contribution of greens function from current angle.
      for (int i = 0; i < numComputeObjects; ++i) {
        context->getComputeObject(i)->integrateGreensAngle(fermiSurface,
                                                           angleIdx);
      }
    }
  }

  if (!inIsBurnIn) {
    // Compute updated order parameter (components).
    // Add coupling constant and angle integration normalization factor here.
    for (int i = 0; i < numComputeObjects; ++i) {
      context->getComputeObject(i)->computePropertyFromGreens();
    }
  }

  // Apply boundary condition(s).
  riccatiSolver->computeBoundaryConditions();

  // Print GPU error, if any.
  ContextModule<T>::checkGpuError("IntegrationIteratorOzaki<T>::compute()");

  I::increaseIterationCount();
}
} // namespace conga

#endif // CONGA_INTEGRATION_ITERATOR_OZAKI_H_
