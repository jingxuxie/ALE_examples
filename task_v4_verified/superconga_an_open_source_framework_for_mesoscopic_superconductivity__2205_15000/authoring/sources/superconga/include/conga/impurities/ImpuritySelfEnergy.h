//===------ ImpuritySelfEnergy.h - Impurity self-energy container. --------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Impurity self-energy container, for storing Sigma and Delta.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_IMPURITY_SELF_ENERGY_H_
#define CONGA_IMPURITY_SELF_ENERGY_H_

#include "../grid.h"

#include <thrust/complex.h>

#include <cassert>
#include <vector>

namespace conga {
/// @brief Container for the impurity self-energy.
template <typename T> class ImpuritySelfEnergy {
public:
  /// @brief Constuctor.
  /// @param inDimX The number of lattice sites along the x-axis.
  /// @param inDimY The number of lattice sites along the y-axis.
  /// @param inNumEnergies The number of energies.
  ImpuritySelfEnergy(const int inDimX, const int inDimY, const T inNumEnergies)
      : sigma(inDimX, inDimY, inNumEnergies, Type::complex),
        delta(inDimX, inDimY, inNumEnergies, Type::complex),
        deltaTilde(inDimX, inDimY, inNumEnergies, Type::complex) {}

  /// @brief Set spatially homogenous values from bulk solution.
  /// @param inSigma The self-energy Sigma.
  /// @param inSigma The self-energy Delta.
  /// @param inSigma The self-energy DeltaTilde.
  void set(const std::vector<thrust::complex<T>> &inSigma,
           const std::vector<thrust::complex<T>> &inDelta,
           const std::vector<thrust::complex<T>> &inDeltaTilde) {
    // Sanity check.
    assert(inSigma.size() == inDelta.size());
    assert(inSigma.size() == inDeltaTilde.size());

    // TODO(Niclas): Enforce that they are equal?
    const int numFields =
        std::min(sigma.numFields(), static_cast<int>(inSigma.size()));

    // Loop over fields and set values.
    for (int i = 0; i < numFields; ++i) {
      sigma.setValue(inSigma[i].real(), Type::real, i);
      sigma.setValue(inSigma[i].imag(), Type::imag, i);
      delta.setValue(inDelta[i].real(), Type::real, i);
      delta.setValue(inDelta[i].imag(), Type::imag, i);
      deltaTilde.setValue(inDeltaTilde[i].real(), Type::real, i);
      deltaTilde.setValue(inDeltaTilde[i].imag(), Type::imag, i);
    }
  }

  // The self-energy Sigma.
  GridGPU<T> sigma;

  // The self-energy Delta.
  GridGPU<T> delta;

  // The self-energy tilde(Delta).
  GridGPU<T> deltaTilde;
};
} // namespace conga

#endif // CONGA_IMPURITY_SELF_ENERGY_H_
