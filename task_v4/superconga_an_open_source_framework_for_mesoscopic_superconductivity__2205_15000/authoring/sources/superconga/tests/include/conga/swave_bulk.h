//===---------- swave_bulk.h - Common functions for s-wave tests. ---------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Functions for computing the free energy and the Yoshida function for s-wave
/// bulk order parameters.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_SWAVE_BULK_H_
#define CONGA_SWAVE_BULK_H_

#include "conga/matsubara.h"

#include <cmath>
#include <limits>
#include <tuple>
#include <vector>

namespace conga {
template <typename T>
T computeFreeEnergyBulkSWave(const T inTemperature, const T inOrderParameter,
                             const T inEnergyCutoff = static_cast<T>(1e2)) {
  std::vector<T> energies;
  std::tie(energies, std::ignore) =
      matsubara::computeEnergiesAndResidues(inTemperature, inEnergyCutoff);
  const int numEnergies = static_cast<int>(energies.size());

  T energySum = static_cast<T>(0.0);
  for (int n = numEnergies - 1; n >= 0; --n) {
    const T energy = energies[n];
    const T Omega = std::hypot(inOrderParameter, energy);
    // The second term is equal to i (delta^* gamma - delta gammaTilde).
    energySum +=
        (static_cast<T>(1) / energy - static_cast<T>(2) / (energy + Omega));
  }
  const T freeEnergy = inOrderParameter * inOrderParameter *
                       (std::log(inTemperature) + inTemperature * energySum);
  return freeEnergy;
}

/// \brief Compute the Yoshida function Y_{3/2} at a given temperature.
///
/// \param inTemperature The temperature [Tc].
/// \param inOrderParameter The bulk order-parameter [2*pi*kB*Tc].
/// \param inEnergyCutoff The energy cutoff [2*pi*kB*Tc].
///
/// \return Y_{3/2}(T).
template <typename T>
T computeYoshidaBulkSWave(const T inTemperature, const T inOrderParameter,
                          const T inEnergyCutoff) {
  if (inTemperature < std::numeric_limits<T>::epsilon()) {
    // If the temperature is approximately zero then return the known
    // zero-temperature value.
    return static_cast<T>(1);
  }

  std::vector<T> energies;
  std::tie(energies, std::ignore) =
      matsubara::computeEnergiesAndResidues(inTemperature, inEnergyCutoff);
  const int numEnergies = static_cast<int>(energies.size());

  T energySum = static_cast<T>(0);
  for (int n = numEnergies - 1; n >= 0; --n) {
    const T energy = energies[n];
    const T Omega = std::hypot(inOrderParameter, energy);
    energySum += static_cast<T>(1) / static_cast<T>(std::pow(Omega, 3));
  }

  return inTemperature * inOrderParameter * inOrderParameter * energySum;
}
} // namespace conga

#endif // CONGA_SWAVE_BULK_H_
