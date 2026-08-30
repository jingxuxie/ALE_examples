//===---- ComputeFreeEnergy.h - Class for free energy compute object. -----===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Compute object class for free energy.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_COMPUTE_FREE_ENERGY_H_
#define CONGA_COMPUTE_FREE_ENERGY_H_

#include "../green/LocalGreens.h"
#include "../grid.h"
#include "../order_parameter/OrderParameter.h"
#include "ComputeProperty.h"
#include "ComputeResidual.h"

#include <thrust/complex.h>

#include <cmath>
#include <cstdio>
#include <limits>

namespace conga {
template <typename T> class ComputeFreeEnergy : public ComputeProperty<T> {
public:
  // Constructors.
  ComputeFreeEnergy();
  ComputeFreeEnergy(Context<T> *const inOutContext);

  GridGPU<T> *getResult() override { return nullptr; }
  T getFreeEnergy() const { return m_freeEnergy; }
  T getFreeEnergyPerUnitArea() const { return m_freeEnergyPerUnitArea; }
  T getMagneticFreeEnergy() const { return m_magneticFreeEnergy; }
  T getMagneticFreeEnergyPerUnitArea() const {
    return m_magneticFreeEnergyPerUnitArea;
  }

  int initialize() override;

  // This should be called once for every iteration, before any integration
  // takes place.
  void initializeIteration(const int inNumFields = 1) override;

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
  // Total free energy.
  T m_freeEnergy;
  T m_freeEnergyPerUnitArea;

  // Magnetic part of the free energy.
  T m_magneticFreeEnergy;
  T m_magneticFreeEnergyPerUnitArea;

  // The value of the Fermi-surface integrand of the free-energy kernel I
  // (summed over energies and positions).
  T m_integrandI;

  // The total value of the Fermi-surface integral of the free-energy kernel I
  // (summed over energies and positions).
  T m_integralI;

  // Whether this is the first iteration or not. If it is the first then the
  // residual is not computed.
  bool m_isFirstIteration;
};

/// \brief Compute the free-energy kernel I
///
/// GPU function to compute the kernel I which enters the Eilenberger free
/// energy. This is the only object in the free energy which actually depends on
/// angle. See page 25 of P. Holmvall PhD Thesis.
///
/// \param inOrderParameter Order parameter value
/// \param inGamma Riccati coherence function
/// \param inGammaTilde Tilde Riccati coherence function
/// \param outFreeEnergy The free energy
template <typename T>
__device__ T computeFreeEnergyKernelI(
    const thrust::complex<T> &inOrderParameter,
    const thrust::complex<T> &inGamma, const thrust::complex<T> &inGammaTilde) {
  const thrust::complex<T> tmp = thrust::conj(inOrderParameter) * inGamma -
                                 inOrderParameter * inGammaTilde;
  // Multiply with I and return real part
  return -tmp.imag();
}

// Parallelize calculation of free-energy kernel I over spatial coordinates
template <typename T>
__global__ void computeFreeEnergy_Kernel(
    const int inNumLatticePoints, const int inEnergyIdxOffset,
    const int inNumEnergiesCurrentBlock, const T *const inGammaReal,
    const T *const inGammaImag, const T *const inGammaTildeReal,
    const T *const inGammaTildeImag, const T *const inOrderParameterReal,
    const T *const inOrderParameterImag, const T *const inOzakiResidues,
    T *outFreeEnergy) {
  const int x = blockDim.x * blockIdx.x + threadIdx.x; // x index
  const int y = blockDim.y * blockIdx.y + threadIdx.y; // y index

  // Check that thread has work to do
  if ((x < inNumLatticePoints) && (y < inNumLatticePoints)) {
    // Calculate unique index for the grain coordinate
    const int grainCoordinateIdx = y * inNumLatticePoints + x;

    // Initialize the sum (over Ozaki poles) to zero
    T sum = static_cast<T>(0);

    // Order parameter at this coordinate
    const thrust::complex<T> orderParameter(
        inOrderParameterReal[grainCoordinateIdx],
        inOrderParameterImag[grainCoordinateIdx]);

    // Loop over Ozaki poles: the energy sum in the free-energy kernel I
    for (int energyIdx = 0; energyIdx < inNumEnergiesCurrentBlock;
         ++energyIdx) {
      // TODO(patric): This is dangerous! We should not manually calculate
      // index like this! Imagine that you want to calculate more coherence
      // functions (like gamma plus/minus instead), then you have to change
      // all these places manually?
      const int coherenceFunctionIdx =
          energyIdx * 2 * inNumLatticePoints * inNumLatticePoints +
          grainCoordinateIdx;

      // Coherence functions in the current coordinate, angle and energy
      const thrust::complex<T> gamma(inGammaReal[coherenceFunctionIdx],
                                     inGammaImag[coherenceFunctionIdx]);
      const thrust::complex<T> gammaTilde(
          inGammaTildeReal[coherenceFunctionIdx],
          inGammaTildeImag[coherenceFunctionIdx]);

      // Calculate I(x, y, energy, angle)
      const T term =
          computeFreeEnergyKernelI(orderParameter, gamma, gammaTilde);

      // Multiply by Ozaki residue and sum the contribution.
      sum += inOzakiResidues[energyIdx + inEnergyIdxOffset] * term;
    }

    // Add contribution to the free energy in this coordinate.
    outFreeEnergy[grainCoordinateIdx] = sum;
  }
}

template <typename T>
ComputeFreeEnergy<T>::ComputeFreeEnergy()
    : ComputeProperty<T>(), m_freeEnergy(static_cast<T>(0)),
      m_freeEnergyPerUnitArea(static_cast<T>(0)),
      m_magneticFreeEnergy(static_cast<T>(0)),
      m_magneticFreeEnergyPerUnitArea(static_cast<T>(0)),
      m_integrandI(static_cast<T>(0)), m_integralI(static_cast<T>(0)),
      m_isFirstIteration(true) {}

template <typename T>
ComputeFreeEnergy<T>::ComputeFreeEnergy(Context<T> *const inOutContext)
    : ComputeProperty<T>(inOutContext), m_freeEnergy(static_cast<T>(0)),
      m_freeEnergyPerUnitArea(static_cast<T>(0)),
      m_magneticFreeEnergy(static_cast<T>(0)),
      m_magneticFreeEnergyPerUnitArea(static_cast<T>(0)),
      m_integrandI(static_cast<T>(0)), m_integralI(static_cast<T>(0)),
      m_isFirstIteration(true) {
  inOutContext->add(this);
}

template <typename T> int ComputeFreeEnergy<T>::initialize() {
#ifndef NDEBUG
  std::cout << "ComputeFreeEnergy<T>::initialize()\n";
#endif

  return 0;
}

template <typename T>
void ComputeFreeEnergy<T>::initializeIteration(const int inNumFields) {
  // Unused.
  (void)inNumFields;

  if (ComputeProperty<T>::doCompute()) {
    m_integralI = static_cast<T>(0);
  }
}

template <typename T> void ComputeFreeEnergy<T>::initializeGreensAngle() {
  if (ComputeProperty<T>::doCompute()) {
    m_integrandI = static_cast<T>(0);
  }
}

// Computes the free-energy kernel 'I' for current angle, for every spatial grid
// point (summed over energies).
template <typename T>
void ComputeFreeEnergy<T>::computeGreensAngle(
    const GridGPU<T> *const inGamma, const GridGPU<T> *const inGammaTilde,
    const GridGPU<T> *const inOrderParameter) {
  if (ComputeProperty<T>::doCompute()) {

    const int dimX = inGamma->dimX();
    const int dimY = inGamma->dimY();

    GridGPU<T> freeEnergyKernelIntegrand(dimX, dimY, 1, Type::real);

    const IntegrationIterator<T> *ii =
        ContextModule<T>::getIntegrationIterator();
    const GridGPU<T> *residues = ii->getResidues();
    const int energyIdxOffset = ii->getEnergyIdxOffset_boundaryStorage();
    const int numEnergiesCurrentBlock = ii->getNumEnergiesInterval();

    const auto [blocksPerGrid, threadsPerBlock] =
        freeEnergyKernelIntegrand.getKernelDimensions();

    computeFreeEnergy_Kernel<<<blocksPerGrid, threadsPerBlock>>>(
        dimX, energyIdxOffset, numEnergiesCurrentBlock,
        inGamma->getDataPointer(0, Type::real),
        inGamma->getDataPointer(0, Type::imag),
        inGammaTilde->getDataPointer(0, Type::real),
        inGammaTilde->getDataPointer(0, Type::imag),
        inOrderParameter->getDataPointer(0, Type::real),
        inOrderParameter->getDataPointer(0, Type::imag),
        residues->getDataPointer(0, Type::real),
        freeEnergyKernelIntegrand.getDataPointer(0));

    m_integrandI += freeEnergyKernelIntegrand.sumField();
  }
}

// Sums the free-energy kernel 'I' over spatial grid points, and adds result to
// total angle integration.
template <typename T>
void ComputeFreeEnergy<T>::integrateGreensAngle(
    const FermiSurface<T> *const inFermiSurface, const int angleIdx) {
  if (ComputeProperty<T>::doCompute()) {
    // The integrand factor for this angle/momentum.
    const T integrandFactor = inFermiSurface->getIntegrandFactor(angleIdx);

    // Accumulate.
    m_integralI += m_integrandI * integrandFactor;
  }
}

template <typename T> void ComputeFreeEnergy<T>::computePropertyFromGreens() {
  if (ComputeProperty<T>::doCompute()) {
    // This variables will contain the (unnormalized) magnetic, and
    // non-magnetic, parts of the free energy.
    T magneticSum = static_cast<T>(0);
    T nonMagneticSum = static_cast<T>(0);

    // Get properties.
    const T latticeElementSize =
        ContextModule<T>::getParameters()->getGridElementSize();
    const T temperature = ContextModule<T>::getParameters()->getTemperature();
    const int numGrainLatticeSites =
        ContextModule<T>::getGeometry()->getNumGrainLatticeSites();

    // Compute second term of free energy not involving angle integration.
    GridCPU<T> ozakiEnergies =
        *(ContextModule<T>::getIntegrationIterator()->getEnergies());
    GridCPU<T> ozakiResidues =
        *(ContextModule<T>::getIntegrationIterator()->getResidues());

    const T *ozakiEnergies_im = ozakiEnergies.getDataPointer(0, Type::imag);
    const T *ozakiResidues_re = ozakiResidues.getDataPointer(0, Type::real);

    const int numEnergies = ozakiEnergies.dimX();
    T sumInverseEnergy = static_cast<T>(0);
    for (int ozakiIdx = 0; ozakiIdx < numEnergies; ++ozakiIdx) {
      sumInverseEnergy +=
          ozakiResidues_re[ozakiIdx] / ozakiEnergies_im[ozakiIdx];
    }
    sumInverseEnergy *= temperature;

    // Update the non-magnetic sum.
    nonMagneticSum += temperature * m_integralI;

    // Add contribution from the order parameter.
    const OrderParameter<T> *const orderParameter =
        ContextModule<T>::getOrderParameter();
    const int numOrderParameterComponents = orderParameter->getNumComponents();

    for (int i = 0; i < numOrderParameterComponents; ++i) {
      // Fetch a component.
      const OrderParameterComponent<T> *const component =
          orderParameter->getComponent(i);

      // Compute the temperature dependent factor.
      const T relativeTc = component->getRelativeTc();
      const T factor = std::log(temperature / relativeTc) + sumInverseEnergy;

      // Compute the squared absolute value.
      GridGPU<T> componentSquared = component->getGrid()->complexMagnitudeSq();

      // Set to zero outside of the grain.
      ContextModule<T>::getGeometry()->zeroValuesOutsideDomainRef(
          &componentSquared);

      // Add contribution from this order-parameter component.
      nonMagneticSum += componentSquared.sumField() * factor;
    }

    // The Ginzburg-Landau parameter.
    const T penetrationDepth =
        ContextModule<T>::getParameters()->getPenetrationDepth();

    // Add contribution from the induced magnetic field.
    if (penetrationDepth > static_cast<T>(0)) {
      // Fetch the vector potential.
      const GridGPU<T> *const inducedVectorPotential =
          ContextModule<T>::getContext()->getInducedVectorPotential();

      // Compute the magnetic field.
      const GridGPU<T> magneticField =
          inducedVectorPotential->curl(latticeElementSize);

      // Note that the prefactor depends on our choice of unit definitions.
      // The division with the squared penetration depth comes from the induced
      // vector potential being scaled by the squared penetration depth in order
      // to simplify Ampere's law and the accelerators. The scaling is undone
      // here.
      const T magneticFactor =
          static_cast<T>(0.5) / (penetrationDepth * penetrationDepth);

      // Update the magnetic sum.
      magneticSum += magneticFactor * magneticField.sumSquare();
    }

    // For convenience.
    const T latticeElementArea = latticeElementSize * latticeElementSize;

    // Free energy (area integrated).
    const T magneticFreeEnergy = magneticSum * latticeElementArea;
    const T totalFreeEnergy =
        (nonMagneticSum + magneticSum) * latticeElementArea;

    // Free energy (normalized).
    const T magneticFreeEnergyPerUnitArea =
        magneticSum / static_cast<T>(numGrainLatticeSites);
    const T totalFreeEnergyPerUnitArea =
        (nonMagneticSum + magneticSum) / static_cast<T>(numGrainLatticeSites);

    // Compute residual.
    const T actualResidual =
        computeResidual(m_freeEnergyPerUnitArea, totalFreeEnergyPerUnitArea);

    // Fetch convergence criterion.
    const T convergenceCriterion =
        ContextModule<T>::getParameters()->getConvergenceCriterion();

    // Fake residual to use the first iteration. This is done because the
    // initial free energy has nothing to do with the initial order parameter
    // and vector potential. So the residual from the first iteration
    // is nonsense, and prevents the program from saying that convergence has
    // been reached when starting from a previously converged solution.
    // TODO(Niclas): Read the free energy from file?
    const T fakeResidual = convergenceCriterion * static_cast<T>(0.1);

    // Set residual.
    const T residual = m_isFirstIteration ? fakeResidual : actualResidual;
    ComputeProperty<T>::setResidual(residual);

    // Check convergence.
    const bool isConverged = residual < convergenceCriterion;
    ComputeProperty<T>::setConverged(isConverged);

    // Update member variables.
    m_freeEnergy = totalFreeEnergy;
    m_freeEnergyPerUnitArea = totalFreeEnergyPerUnitArea;
    m_magneticFreeEnergy = magneticFreeEnergy;
    m_magneticFreeEnergyPerUnitArea = magneticFreeEnergyPerUnitArea;
    m_isFirstIteration = false;
  } else {
    ComputeProperty<T>::setConverged(false);
  }
}
} // namespace conga

#endif // CONGA_COMPUTE_FREE_ENERGY_H_
