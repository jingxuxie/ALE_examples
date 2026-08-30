#ifndef CONGA_MATSUBARA_H_
#define CONGA_MATSUBARA_H_

#include <algorithm>
#include <utility>
#include <vector>

namespace conga {
namespace matsubara {
/// @brief Compute the number of Matsubara energies needed.
/// @tparam T Float or double.
/// @param inTemperature The temperature (in units of Tc).
/// @param inEnergyCutoff The energy cutoff (in units of 2*pi*kB*Tc).
/// @return The number of energies.
template <typename T>
int computeNumEnergies(const T inTemperature, const T inEnergyCutoff) {
  // Comes from: cutoff = T * (n + 0.5).
  // But the n is the largest n we need to include, so the number of energies
  // is one more, hence the plus one.
  return 1 +
         static_cast<int>(inEnergyCutoff / inTemperature - static_cast<T>(0.5));
}

/// @brief Compute the Matsubara energies and residues.
/// @tparam T Float or double.
/// @param inTemperature The temperature (in units of Tc).
/// @param inNumEnergies The number of energies.
/// @return The pair {energies, residues}.
template <typename T>
std::pair<std::vector<T>, std::vector<T>>
computeEnergiesAndResidues(const T inTemperature, const int inNumEnergies) {
  std::vector<T> matsubaraEnergies;
  std::vector<T> matsubaraResidues;

  for (int n = 0; n < inNumEnergies; ++n) {
    const T matsubaraEnergy =
        inTemperature * (static_cast<T>(n) + static_cast<T>(0.5));
    matsubaraEnergies.push_back(matsubaraEnergy);
  }

  // Matsubara so fill with ones.
  matsubaraResidues.resize(inNumEnergies);
  const T matsubaraResidue = static_cast<T>(1);
  std::fill(matsubaraResidues.begin(), matsubaraResidues.end(),
            matsubaraResidue);

  return {matsubaraEnergies, matsubaraResidues};
}

/// @brief Compute the Matsubara energies and residues.
/// @tparam T Float or double.
/// @param inTemperature The temperature (in units of Tc).
/// @param inEnergyCutoff The energy cutoff (in units of 2*pi*kB*Tc).
/// @return The pair {energies, residues}.
template <typename T>
std::pair<std::vector<T>, std::vector<T>>
computeEnergiesAndResidues(const T inTemperature, const T inEnergyCutoff) {
  const int numEnergies = computeNumEnergies(inTemperature, inEnergyCutoff);
  return computeEnergiesAndResidues(inTemperature, numEnergies);
}
} // namespace matsubara
} // namespace conga

#endif // CONGA_MATSUBARA_H_
