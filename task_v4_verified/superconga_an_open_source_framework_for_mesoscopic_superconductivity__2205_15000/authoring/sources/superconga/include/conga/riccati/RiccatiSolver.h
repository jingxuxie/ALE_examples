//===----- RiccatiSolver.h - Base class for riccati equation solver. ------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Base class for the Riccati equation solver.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_RICCATI_SOLVER_H_
#define CONGA_RICCATI_SOLVER_H_

#include "../ParameterIterator.h"
#include "../Parameters.h"
#include "../boundary/BoundaryCondition.h"
#include "../boundary/BoundaryStorage.h"
#include "../geometry/GeometryGroup.h"
#include "../geometry/domain_ops.h"
#include "../grid.h"
#include "../integration/IntegrationIterator.h"
#include "../utils.h"
#include "RiccatiSolutions.h"
#include "energy_shift/Gauges.h"
#include "energy_shift/VectorPotential_Kernel.h"

#include <cmath>
#include <limits>
#include <memory>
#include <utility>

/////////////////////////////////////////////////////////
// MAYBE PUT POINTER TO ENERGIES AND ENERGYITERATOR HERE
/////////////////////////////////////////////////////////

namespace conga {
template <typename T> class BoundaryStorage;

template <typename T> class RiccatiSolver : public ContextModule<T> {
public:
  // Constructors and Destructors

  RiccatiSolver();
  virtual ~RiccatiSolver();

  RiccatiSolver(Context<T> *ctx);

  // Allocate memory
  virtual int initialize();

  // Get pointers to storage of Riccati solutions (gamma/coherence functions).
  // These grids have dimensions (x,y,energy)
  GridGPU<T> *getGamma() const { return m_gamma.get(); }
  GridGPU<T> *getGammaTilde() const { return m_gammaTilde.get(); }

  // Functions related to Boundary condition:

  // Get pointer to sparse array where boundary values (for coherence functions)
  // are stored.
  BoundaryStorage<T> *getBoundaryStorage() const { return m_storage.get(); }

  // Add boundary condition.
  void add(BoundaryCondition<T> *bc) { _bc_list.push_back(bc); }

  int getNumBoundaryConditions() const { return _bc_list.size(); }
  BoundaryCondition<T> *getBoundaryCondition(const int idx) {
    return _bc_list[idx];
  }

  T getResidual() const { return m_residual; }

  // Vector potential
  GridGPU<T> *getEnergyShift() const { return m_energyShift.get(); }

  void computeBoundaryConditions();

  virtual void computeCoherenceFunctionsInitial(
      const ParameterIterator<int> &inEnergyIterator,
      const GridGPU<T> &inEnergies, const GridGPU<T> &inOrderParameter,
      const int inAngleIdx) = 0;

  virtual void computeCoherenceFunctionsBurnIn(
      const ParameterIterator<int> &inEnergyIterator,
      const GridGPU<T> &inEnergies, const GridGPU<T> &inOrderParameter,
      const int inAngleIdx) = 0;

  virtual void
  computeCoherenceFunctions(const ParameterIterator<int> &inEnergyIterator,
                            const GridGPU<T> &inEnergies,
                            const GridGPU<T> &inOrderParameter,
                            const int inAngleIdx) = 0;

  // Helper functions
  std::pair<dim3, dim3> getKernelDimensionsOptim(const int inNumEnergies,
                                                 const int inAngleIdx);

  virtual std::string getVectorPotentialType() const = 0;

private:
  // Storage for riccati trajectories
  std::unique_ptr<GridGPU<T>> m_gamma;
  std::unique_ptr<GridGPU<T>> m_gammaTilde;

  // Holds (and reflects) gammas on boundary between interations
  std::unique_ptr<BoundaryStorage<T>> m_storage;

  // Boundary conditions
  std::vector<BoundaryCondition<T> *> _bc_list;

  // Functor object for energy shift by the vector potential e -> e + vF.pS
  // (inclusion of magnetic field)
  // POTENTIAL<T>	_vpFunctor;

  // Precomputed field for energy shift
  std::unique_ptr<GridGPU<T>> m_energyShift;

  // Residual at boundary.
  T m_residual;
};

// This function could not be put into RiccatiSolver class, because of template
// parameter issues
template <typename T, template <typename> class VP>
void computeEnergyShift(const Parameters<T> &inParameters,
                        const T inSystemAngle, const T inFermiVelocityX,
                        const T inFermiVelocityY, const T inArea,
                        const GridGPU<T> &inVectorPotential,
                        GridGPU<T> &outEnergyShift) {
  // Add contribution from external magnetic field
  const int chargeSign = inParameters.getChargeSign();
  const T numFluxQuanta = inParameters.getNumFluxQuanta();
  const T h = inParameters.getGridElementSize();
  const T penetrationDepth = inParameters.getPenetrationDepth();
  const T fluxDensity = static_cast<T>(M_PI) * numFluxQuanta / inArea;

  const auto [blocksPerGrid, threadsPerBlock] =
      outEnergyShift.getKernelDimensions();

  const int dimX = outEnergyShift.dimX();
  const int dimY = outEnergyShift.dimY();

  if (penetrationDepth > static_cast<T>(0)) {
    GridGPU<T> vectorPotentialRotated(dimX, dimY, 2, Type::real);
    geometry::rotate(-inSystemAngle, inVectorPotential, vectorPotentialRotated);

    // The induced vector potential is scaled by the squared penetration depth
    // in order to simplify Ampere's law and the accelerators. The scaling needs
    // to be undone here.
    const T vectorPotentialScale =
        static_cast<T>(1) / (penetrationDepth * penetrationDepth);
    vectorPotentialRotated *= vectorPotentialScale;

    computeEnergyShiftKernel<T, VP><<<blocksPerGrid, threadsPerBlock>>>(
        dimX, dimY, inFermiVelocityX, inFermiVelocityY, inSystemAngle,
        fluxDensity, chargeSign, inArea, h,
        vectorPotentialRotated.getDataPointer(0),
        vectorPotentialRotated.getDataPointer(1),
        outEnergyShift.getDataPointer());
  } else if (std::abs(fluxDensity) > static_cast<T>(0)) {
    computeEnergyShiftOnlyExternalKernel<T, VP>
        <<<blocksPerGrid, threadsPerBlock>>>(dimX, dimY, inFermiVelocityX,
                                             inFermiVelocityY, inSystemAngle,
                                             fluxDensity, chargeSign, inArea, h,
                                             outEnergyShift.getDataPointer());
  } else {
    outEnergyShift.setZero();
  }
}

template <typename T>
RiccatiSolver<T>::RiccatiSolver()
    : ContextModule<T>(), m_gamma(nullptr), m_gammaTilde(nullptr),
      m_storage(nullptr), m_energyShift(nullptr),
      m_residual(std::numeric_limits<T>::max()) {}

template <typename T>
RiccatiSolver<T>::RiccatiSolver(Context<T> *ctx)
    : ContextModule<T>(ctx), m_gamma(nullptr), m_gammaTilde(nullptr),
      m_storage(nullptr), m_energyShift(nullptr),
      m_residual(std::numeric_limits<T>::max()) {}

template <typename T> RiccatiSolver<T>::~RiccatiSolver() {
#ifndef NDEBUG
  std::cout << "~RiccatiSolver()\n";
#endif
  for (int i = 0; i < getNumBoundaryConditions(); ++i) {
    delete _bc_list[i];
  }
}

template <typename T> int RiccatiSolver<T>::initialize() {
#ifndef NDEBUG
  std::cout << "RiccatiSolver<T>::initialize()\n";
#endif

  const int numEnergiesBlock =
      ContextModule<T>::getIntegrationIterator()->getNumEnergiesInterval();
  const int numEnergiesStorage =
      ContextModule<T>::getIntegrationIterator()->getNumEnergiesStorage();

  const int gridResolution =
      ContextModule<T>::getParameters()->getGridResolutionBase();
  m_gamma = std::make_unique<GridGPU<T>>(gridResolution, gridResolution,
                                         numEnergiesBlock, Type::complex);
  m_gammaTilde = std::make_unique<GridGPU<T>>(gridResolution, gridResolution,
                                              numEnergiesBlock, Type::complex);

  m_gamma->setZero();
  m_gammaTilde->setZero();

  const int gridResolutionRotated =
      ContextModule<T>::getParameters()->getGridResolutionCoherence();
  m_energyShift = std::make_unique<GridGPU<T>>(
      gridResolutionRotated, gridResolutionRotated, 1, Type::real);

  m_storage = std::make_unique<BoundaryStorage<T>>(
      ContextModule<T>::getGeometry(), ContextModule<T>::getFermiSurface());

  const int numAngles =
      ContextModule<T>::getParameters()->getAngularResolution();
  m_storage->initialize(gridResolutionRotated, numEnergiesStorage, numAngles);

  return 0;
}

template <typename T> void RiccatiSolver<T>::computeBoundaryConditions() {
  typedef RiccatiSolver<T> R;

  // Apply boundary condition(s)
  const int Nbc = getNumBoundaryConditions();

  T maxResidual = std::numeric_limits<T>::min();

  if (Nbc > 0) {
    for (int i = 0; i < Nbc; ++i) {
      const T residual = getBoundaryCondition(i)->computeBoundaryCondition(
          ContextModule<T>::getContext());
      maxResidual = std::max(maxResidual, residual);
    }
  } else {
#ifndef NDEBUG
    std::cout << "-- WARNING: No boundary conditions specified!\n";
#endif
  }

  m_residual = maxResidual;
}

template <typename T>
std::pair<dim3, dim3>
RiccatiSolver<T>::getKernelDimensionsOptim(const int inNumEnergies,
                                           const int inAngleIdx) {
  const int numTrajectories =
      m_storage->getNumIntersectingTrajectoriesAngle(inAngleIdx);
  return GridGPU<T>::getKernelDimensions(numTrajectories, inNumEnergies);
}
} // namespace conga

#endif // CONGA_RICCATI_SOLVER_H_
