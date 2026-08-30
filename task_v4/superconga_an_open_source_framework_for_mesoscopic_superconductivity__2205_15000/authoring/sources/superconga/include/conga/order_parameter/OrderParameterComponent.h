//===-- OrderParameterComponent.h - Component of order parameter group. ---===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Storage for a single order parameter component, added to the total order
/// parameter.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_ORDER_PARAMETER_COMPONENT_H_
#define CONGA_ORDER_PARAMETER_COMPONENT_H_

#include "../Type.h"
#include "../arg.h"
#include "../defines.h"
#include "../fermi_surface/FermiSurface.h"
#include "../grid.h"
#include "OrderParameterBasis.h"
#include "OrderParameterInitial.h"

#include <cmath>
#include <iostream>
#include <memory>
#include <string>

namespace conga {
/// @brief Struct describing a single normal inclusion.
/// @tparam T Float or double.
template <typename T> struct NormalInclusion {
public:
  /// @brief Normal inclusion constructor.
  /// @param inRadius The normal inclusion radius (coherence lengths).
  /// @param inStrength The normal inclusion strength (0 to 1).
  NormalInclusion(const T inRadius, const T inStrength)
      : m_radius(inRadius), m_strength(inStrength) {}

  // The radius.
  CONGA_ARG(T, radius);

  // The suppression strength.
  CONGA_ARG(T, strength);

  // The normal inclusion center.
  CONGA_ARG(vector2d<T>, center) = {static_cast<T>(0), static_cast<T>(0)};
};

/// @brief Struct describing an order-parameter component.
/// @tparam T Float or double.
template <typename T> struct ComponentOptions {
  /// @brief Component options constructor.
  /// @param inSymmetry The basis-function symmetry.
  ComponentOptions(const Symmetry inSymmetry) : m_symmetry(inSymmetry) {}

  // The basis-function symmetry, e.g. s-wave.
  CONGA_ARG(Symmetry, symmetry);

  // The initial value.
  CONGA_ARG(thrust::complex<T>,
            initialValue) = thrust::complex<T>(static_cast<T>(1),
                                               static_cast<T>(0));

  // The critical temperature (0,1].
  CONGA_ARG(T, criticalTemperature) = static_cast<T>(1);

  // The standard deviation of the initial noise.
  CONGA_ARG(T, initialNoiseStdDev) = static_cast<T>(0);

  // A vector of initial vortices.
  CONGA_ARG(std::vector<Vortex<T>>, vortices) = {};

  // A vector of normal inclusions.
  CONGA_ARG(std::vector<NormalInclusion<T>>, normalInclusions) = {};
};

template <typename T> class OrderParameterComponent {
public:
  // Constructors and destructor.
  OrderParameterComponent(const ComponentOptions<T> &inOptions,
                          const int inGridResolution);
  OrderParameterComponent(const OrderParameterComponent<T> &other);

  ~OrderParameterComponent();

  OrderParameterComponent<T> *clone() const;

  // Functions
  void initialize(const FermiSurface<T> *const inFermiSurface);

  GridGPU<T> *getGrid() const { return _deltaComp; }
  T getRelativeTc() const { return m_criticalTemperature; }

  void computeMomentumDependence(GridGPU<T> *target, const T pX, const T pY,
                                 const T inCrystalAxesRotation,
                                 bool conjugateBasisFunction = false) const;

  void initCouplingConstant(const T inTemperature, const int inNumEnergies,
                            const T *const inEnergies,
                            const T *const inResidues,
                            const int inGridResolution);

  void applyCouplingConstant();

  std::string getType() const { return m_basisFunction.getSymmetryStr(); };

private:
  template <typename S>
  friend void swap(OrderParameterComponent<S> &A,
                   OrderParameterComponent<S> &B);

  void applyNormalInclusions(GridGPU<T> &inOutGrid) const;

  // Relative critical temperature.
  T m_criticalTemperature;

  // Coupling constant.
  // CAUTION!!! Upon changing Tc/energies/similar, need to re-calculate.
  T m_couplingConstant;
  std::unique_ptr<GridGPU<T>> m_couplingConstantGrid;

  // The basis function of this order-parameter component.
  BasisFunction<T> m_basisFunction;

  // Order parameter component
  GridGPU<T> *_deltaComp;

  // Normal inclusions.
  std::vector<T> m_normalInclusionCentersX;
  std::vector<T> m_normalInclusionCentersY;
  std::vector<T> m_normalInclusionRadii;
  std::vector<T> m_normalInclusionStrengths;
};

namespace internal {
/// \brief Kernel for adding normal inclusions: suppress coupling constant.
///
/// \tparam T Floating point precision (single or double).
/// \param inNumX Number of x lattice-points in geometry.
/// \param inNumY Number of y lattice-points in geometry.
/// \param inNumNormalInclusions Number of normal inclusions.
/// \param inCentersX Center x-coordinate for each normal inclusion: [-1,1].
/// \param inCentersY Center y-coordinate for each normal inclusion: [-1,1].
/// \param inRadii Radius of each normal inclusion (coherence lengths).
/// \param inStrengths Suppression strengths of normal inclusion.
/// \param inOutReal Pointer to real part of the grid.
/// \param inOutImag Pointer to imaginary part of the grid.
template <typename T>
__global__ void applyNormalInclusionsKernel(
    const int inNumX, const int inNumY, const int inNumNormalInclusions,
    const T *const inCentersX, const T *const inCentersY,
    const T *const inRadii, const T *const inStrengths, T *const inOutReal,
    T *const inOutImag) {
  // Discrete coordinates in discretized order parameter lattice.
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  const int j = blockIdx.y * blockDim.y + threadIdx.y;

  // Check that coordinates lie within geometry.
  if (i < inNumX && j < inNumY) {
    // Normalize coordinates to [-MAXIMUM_COORDINATE, MAXIMUM_COORDINATE].
    const T scale = static_cast<T>(2 * constants::MAXIMUM_COORDINATE);
    const T x = scale * (static_cast<T>(i) / static_cast<T>(inNumX - 1) -
                         static_cast<T>(0.5));
    const T y = scale * (static_cast<T>(j) / static_cast<T>(inNumY - 1) -
                         static_cast<T>(0.5));

    // Compute unique coordinate index.
    const int idx = j * inNumX + i;

    // Loop over normal inclusions: set coupling constant suppressions.
    for (int normalInclusionIdx = 0; normalInclusionIdx < inNumNormalInclusions;
         ++normalInclusionIdx) {
      // Compute distance between thread coordinate and normal inclusion
      // coordinate.
      const T dx = x - inCentersX[normalInclusionIdx];
      const T dy = y - inCentersY[normalInclusionIdx];
      const T distance = hypot(dx, dy);

      // Suppress amplitude if within normal inclusion radius.
      const T ratio = distance / inRadii[normalInclusionIdx];
      if (ratio < static_cast<T>(1)) {
        const T strength = inStrengths[normalInclusionIdx];
        // Zero derivative at the boundary and the center, and continuous.
        const T suppression =
            strength * ratio * ratio *
                (static_cast<T>(3) - static_cast<T>(2) * ratio) +
            (static_cast<T>(1) - strength);
        inOutReal[idx] *= suppression;
        inOutImag[idx] *= suppression;
      }
    }
  }
}

} // namespace internal

template <typename T>
OrderParameterComponent<T>::OrderParameterComponent(
    const ComponentOptions<T> &inOptions, const int inGridResolution)
    : _deltaComp(0), m_criticalTemperature(inOptions.criticalTemperature()),
      m_couplingConstant(static_cast<T>(0.0)), m_couplingConstantGrid(nullptr),
      m_basisFunction(inOptions.symmetry()), m_normalInclusionCentersX(0),
      m_normalInclusionCentersY(0), m_normalInclusionRadii(0),
      m_normalInclusionStrengths(0) {
  GridGPU<T>::initializeGrid(_deltaComp, inGridResolution, inGridResolution, 1,
                             Type::complex);
  perturbedPhaseWindings(inOptions.initialValue(),
                         inOptions.initialNoiseStdDev(), inOptions.vortices(),
                         *_deltaComp);

  std::vector<T> normalInclusionCentersX;
  std::vector<T> normalInclusionCentersY;
  std::vector<T> normalInclusionRadii;
  std::vector<T> normalInclusionStrengths;

  for (const auto &normalInclusion : inOptions.normalInclusions()) {
    normalInclusionRadii.push_back(normalInclusion.radius());
    normalInclusionStrengths.push_back(normalInclusion.strength());
    normalInclusionCentersX.push_back(normalInclusion.center()[0]);
    normalInclusionCentersY.push_back(normalInclusion.center()[1]);
  }

  m_normalInclusionCentersX = normalInclusionCentersX;
  m_normalInclusionCentersY = normalInclusionCentersY;
  m_normalInclusionRadii = normalInclusionRadii;
  m_normalInclusionStrengths = normalInclusionStrengths;

  // Set normal inclusions on the initial guess right away.
  applyNormalInclusions(*_deltaComp);
}

template <typename T>
OrderParameterComponent<T>::OrderParameterComponent(
    const OrderParameterComponent<T> &other)
    : m_criticalTemperature(other.m_criticalTemperature),
      m_couplingConstant(other.m_couplingConstant),
      m_basisFunction(other.m_basisFunction),
      m_normalInclusionCentersX(other.m_normalInclusionCentersX),
      m_normalInclusionCentersY(other.m_normalInclusionCentersY),
      m_normalInclusionRadii(other.m_normalInclusionRadii),
      m_normalInclusionStrengths(other.m_normalInclusionStrengths) {
  if (other._deltaComp) {
    _deltaComp = new GridGPU<T>(*other._deltaComp);
  }
  if (other.m_couplingConstantGrid) {
    // This is a bit ugly perhaps. We are using a unique_ptr
    m_couplingConstantGrid =
        std::make_unique<GridGPU<T>>(*other.m_couplingConstantGrid);
  }
}

template <typename T> OrderParameterComponent<T>::~OrderParameterComponent() {
  if (_deltaComp) {
    delete _deltaComp;
  }
}

template <typename T>
void swap(OrderParameterComponent<T> &A, OrderParameterComponent<T> &B) {
  std::swap(A.m_criticalTemperature, B.m_criticalTemperature);
  std::swap(A._deltaComp, B._deltaComp);
  std::swap(A.m_couplingConstant, B.m_couplingConstant);
  std::swap(A.m_couplingConstantGrid, B.m_couplingConstantGrid);
  std::swap(A.m_basisFunction, B.m_basisFunction);
  std::swap(A.m_normalInclusionCentersX, B.m_normalInclusionCentersX);
  std::swap(A.m_normalInclusionCentersY, B.m_normalInclusionCentersY);
  std::swap(A.m_normalInclusionRadii, B.m_normalInclusionRadii);
  std::swap(A.m_normalInclusionStrengths, B.m_normalInclusionStrengths);
}

template <typename T>
OrderParameterComponent<T> *OrderParameterComponent<T>::clone() const {
  return new OrderParameterComponent<T>(*this);
}

template <typename T>
void OrderParameterComponent<T>::initialize(
    const FermiSurface<T> *const inFermiSurface) {

  if (inFermiSurface) {
    m_basisFunction.normalize(inFermiSurface);
  }
}

template <typename T>
void OrderParameterComponent<T>::initCouplingConstant(
    const T inTemperature, const int inNumEnergies, const T *const inEnergies,
    const T *const inResidues, const int inGridResolution) {
  // Compute (inverted) energy sum.
  T energySum = static_cast<T>(0.0);
  for (int i = 0; i < inNumEnergies; ++i) {
    energySum += inResidues[i] / inEnergies[i];
  }
  energySum *= inTemperature;

  // Note, that here we implicitly assume that the basis functions are
  // normalized. I.e. <|eta|^2> = 1. Otherwise the energySum would be scaled by
  // <|eta|^2>.
  m_couplingConstant =
      inTemperature /
      (std::log(inTemperature / m_criticalTemperature) + energySum);

  if (m_normalInclusionCentersX.size() > 0) {
    // Initialize coupling constant grid. It is a grid to allow heterogeneous
    // systems, with different normal/superconducting regions.
    // Todo(Patric): Make real instead? Must then probably update the
    // arithmetics in applyCouplingConstant.
    m_couplingConstantGrid = std::make_unique<GridGPU<T>>(
        inGridResolution, inGridResolution, 1, Type::complex);
    // TODO(patric): set to zero outside domain?
    m_couplingConstantGrid->setValue(m_couplingConstant, Type::real);
    m_couplingConstantGrid->setValue(static_cast<T>(0.0), Type::imag);

    // Apply normal region to coupling constant.
    applyNormalInclusions(*m_couplingConstantGrid);
  }

#ifndef NDEBUG
  // Print the value.
  std::cout << "m_couplingConstant: " << m_couplingConstant << "\n";
  std::cout << "inTemperature: " << inTemperature << "\n";
  std::cout << "m_criticalTemperature: " << m_criticalTemperature << "\n";
  std::cout << "energySum: " << energySum << "\n";
#endif
}

template <typename T> void OrderParameterComponent<T>::applyCouplingConstant() {
  // Save some time by only using a grid coupling constant when it is actually
  // needed.
  if (m_couplingConstantGrid) {
    *_deltaComp *= (*m_couplingConstantGrid);
  } else {
    *_deltaComp *= m_couplingConstant;
  }
}

template <typename T>
void OrderParameterComponent<T>::applyNormalInclusions(
    GridGPU<T> &inOutGrid) const {
  // Number of normal inclusions.
  const int numNormalInclusions = m_normalInclusionCentersX.size();

  // Add normal inclusions.
  if (numNormalInclusions > 0) {

    // Sanity checks.
    // TODO(Patric): Allow for applying normal inclusions even if real?
    assert(inOutGrid.numFields() == 1);
    assert(inOutGrid.representation() == Type::complex);

    // Copy normal inclusions to the GPU.
    const thrust::device_vector<T> centersXGPU(m_normalInclusionCentersX);
    const thrust::device_vector<T> centersYGPU(m_normalInclusionCentersY);
    const thrust::device_vector<T> radiiGPU(m_normalInclusionRadii);
    const thrust::device_vector<T> strengthsGPU(m_normalInclusionStrengths);

    // Calculate GPU thread blocks.
    const auto [blocksPerGrid, threadsPerBlock] =
        inOutGrid.getKernelDimensions();

    // Apply normal inclusions via GPU kernel.
    internal::applyNormalInclusionsKernel<<<blocksPerGrid, threadsPerBlock>>>(
        inOutGrid.dimX(), inOutGrid.dimY(), numNormalInclusions,
        thrust::raw_pointer_cast(centersXGPU.data()),
        thrust::raw_pointer_cast(centersYGPU.data()),
        thrust::raw_pointer_cast(radiiGPU.data()),
        thrust::raw_pointer_cast(strengthsGPU.data()),
        inOutGrid.getDataPointer(0, Type::real),
        inOutGrid.getDataPointer(0, Type::imag));
  }
}

template <typename T>
void OrderParameterComponent<T>::computeMomentumDependence(
    GridGPU<T> *target, const T pX, const T pY, const T inCrystalAxesRotation,
    bool conjugateBasisFunction) const {
  T pXRotated;
  T pYRotated;
  utils::rotate(inCrystalAxesRotation, pX, pY, pXRotated, pYRotated);
  const thrust::complex<T> basisFunction =
      m_basisFunction.evaluate(pXRotated, pYRotated);
  (*target) *=
      (conjugateBasisFunction ? thrust::conj(basisFunction) : basisFunction);
}
} // namespace conga

#endif // CONGA_ORDER_PARAMETER_COMPONENT_H_
