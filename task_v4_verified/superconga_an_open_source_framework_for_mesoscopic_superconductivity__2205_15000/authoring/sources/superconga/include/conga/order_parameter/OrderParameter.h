//===----------- OrderParameter.h - Order parameter container. ------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Order parameter container, for storing different order parameter components.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_ORDER_PARAMETER_H_
#define CONGA_ORDER_PARAMETER_H_

#include "../Context.h"
#include "../ContextModule.h"
#include "../Parameters.h"
#include "../grid.h"
#include "../utils.h"
#include "OrderParameterComponent.h"

#include <string>

namespace conga {
template <typename T> class OrderParameter : public ContextModule<T> {
public:
  /// \brief Constructor.
  OrderParameter();

  /// \brief Constructor.
  ///
  /// \param inOther Another order parameter.
  OrderParameter(const OrderParameter<T> &inOther);

  /// \brief Constructor.
  ///
  /// \param inOutContext Context pointer.
  OrderParameter(Context<T> *inOutContext);

  /// \brief Destructor.
  ~OrderParameter();

  OrderParameter<T> &operator=(OrderParameter<T> inOther);

  /// \brief Set the rotation of the crystal ab-axes.
  ///
  /// \param inCrystalAxesRotation The rotation angle in radians.
  ///
  /// \return Void.
  void setCrystalAxesRotation(const T inCrystalAxesRotation) {
    m_crystalAxesRotation = inCrystalAxesRotation;
  }

  /// \brief Get the rotation of the crystal ab-axes.
  ///
  /// \return The rotation angle in radians.
  T getCrystalAxesRotation() const { return m_crystalAxesRotation; }

  /// \brief Initialize the order parameter.
  ///
  /// \return Whether the initialization was a success.
  // TODO(niclas): Return bool or status enum.
  int initialize() override;

  /// \brief Compute the sum of the magnitude.
  ///
  /// \return The sum.
  T sumMagnitude() const;

  /// @brief Add a component to the order parameter.
  /// @param inOptions The options specifying the component and its
  /// initialization.
  void addComponent(const ComponentOptions<T> &inOptions);

  /// \brief Get the number of components.
  ///
  /// \return The number of components.
  int getNumComponents() const;

  /// \brief Get a particular component.
  ///
  /// \param inIndex The index of the component.
  ///
  /// \return A pointer the the component.
  OrderParameterComponent<T> *getComponent(int inIndex) const;

  /// \brief Get a particular component's grid.
  ///
  /// \param inIndex The index of the component.
  ///
  /// \return A pointer the the grid.
  GridGPU<T> *getComponentGrid(int inIndex) const;

  /// \brief Get  sum of all components with momentum dependence for a
  /// particular momentum.
  ///
  /// \param inMomentumX The x-component of the Fermi momentum.
  /// \param inMomentumY The y-component of the Fermi momentum.
  ///
  /// \return The order parameter for this momentum.
  GridGPU<T> getMomentumDependentGrid(const T inMomentumX,
                                      const T inMomentumY) const;

  /// \brief Get the types of all components.
  ///
  /// \return The types, e.g. {"s", "dxy"}.
  std::vector<std::string> getTypes() const;

private:
  /// \brief Swap to order parameters.
  ///
  /// \param inA The first order parameter.
  /// \param inB The second order parameter.
  ///
  /// \return Void.
  template <typename S>
  friend void swap(OrderParameter<S> &inA, OrderParameter<S> &inB);

  // The rotation of the crystal ab-axes.
  T m_crystalAxesRotation;

  // A list of all components.
  std::vector<OrderParameterComponent<T> *> m_components;
};

template <typename T>
OrderParameter<T>::OrderParameter()
    : ContextModule<T>(), m_crystalAxesRotation(static_cast<T>(0)) {}

template <typename T>
OrderParameter<T>::OrderParameter(const OrderParameter<T> &inOther)
    : ContextModule<T>(inOther) {
  m_crystalAxesRotation = inOther.getCrystalAxesRotation();

  const int numComponents = inOther.getNumComponents();

  for (int i = 0; i < numComponents; ++i) {
    m_components.push_back(inOther.m_components[i]->clone());
  }
}

template <typename T>
OrderParameter<T>::OrderParameter(Context<T> *inOutContext)
    : ContextModule<T>(inOutContext), m_crystalAxesRotation(static_cast<T>(0)) {
  inOutContext->set(this);
}

template <typename T> OrderParameter<T>::~OrderParameter() {
  for (int i = 0; i < getNumComponents(); ++i) {
    delete m_components[i];
  }
}

template <typename T>
OrderParameter<T> &OrderParameter<T>::operator=(OrderParameter<T> inOther) {
  swap(*this, inOther);
  return *this;
}

template <typename T>
void swap(OrderParameter<T> &inA, OrderParameter<T> &inB) {
  std::swap(inA.m_components, inB.m_components);
}

template <typename T> int OrderParameter<T>::initialize() {
  const FermiSurface<T> *const fermiSurface =
      ContextModule<T>::getFermiSurface();

  for (int i = 0; i < getNumComponents(); ++i) {
    // Initialize the component.
    m_components[i]->initialize(fermiSurface);

    // Zero the values outside of the grain, so that we only compute residuals
    // of values that actually matter.
    GridGPU<T> *const component = getComponentGrid(i);
    ContextModule<T>::getGeometry()->zeroValuesOutsideDomainRef(component);
  }
  return 0;
}

template <typename T> T OrderParameter<T>::sumMagnitude() const {
  // Grid containing the elementwise sum of squared magnitudes of
  // order-parameter components.
  const int dimX = getComponentGrid(0)->dimX();
  const int dimY = getComponentGrid(0)->dimY();
  GridGPU<T> magnitudeSquare(dimX, dimY, 1, Type::real);

  const int numComponents = getNumComponents();
  for (int i = 0; i < numComponents; ++i) {
    magnitudeSquare += getComponentGrid(i)->complexMagnitudeSq();
  }

  return magnitudeSquare.sqrt().sumField();
}

template <typename T>
void OrderParameter<T>::addComponent(const ComponentOptions<T> &inOptions) {
  const int gridResolution =
      ContextModule<T>::getParameters()->getGridResolutionBase();
  conga::OrderParameterComponent<T> *component =
      new conga::OrderParameterComponent<T>(inOptions, gridResolution);
  m_components.push_back(component);
}

template <typename T> int OrderParameter<T>::getNumComponents() const {
  return m_components.size();
}

template <typename T>
OrderParameterComponent<T> *OrderParameter<T>::getComponent(int inIndex) const {
  const int numComponents = getNumComponents();

  // TODO(niclas): Is this behaviour really what a user expects? Shouldn't we
  // throw an exception?
  if (inIndex >= numComponents) {
    inIndex = numComponents - 1;
  }

  return m_components[inIndex];
}

template <typename T>
GridGPU<T> *OrderParameter<T>::getComponentGrid(int inIndex) const {
  return getComponent(inIndex)->getGrid();
}

template <typename T>
GridGPU<T>
OrderParameter<T>::getMomentumDependentGrid(const T inMomentumX,
                                            const T inMomentumY) const {
  // We need to sum all components with their basis function function
  // multiplied.
  const int dimX = m_components[0]->getGrid()->dimX();
  const int dimY = m_components[0]->getGrid()->dimY();
  const Type::type representation =
      m_components[0]->getGrid()->representation();
  GridGPU<T> result(dimX, dimY, 1, representation);

  for (int i = 0; i < getNumComponents(); ++i) {
    OrderParameterComponent<T> *component = getComponent(i);
    GridGPU<T> grid = *(component->getGrid());
    component->computeMomentumDependence(&grid, inMomentumX, inMomentumY,
                                         m_crystalAxesRotation);
    result += grid;
  }

  return result;
}

template <typename T>
std::vector<std::string> OrderParameter<T>::getTypes() const {
  const int numOrderParameterComponents = getNumComponents();
  std::vector<std::string> types;
  types.reserve(numOrderParameterComponents);

  for (int i = 0; i < numOrderParameterComponents; ++i) {
    const std::string componentType = getComponent(i)->getType();
    types.emplace_back(componentType);
  }
  return types;
}
} // namespace conga

#endif // CONGA_ORDER_PARAMETER_H_
