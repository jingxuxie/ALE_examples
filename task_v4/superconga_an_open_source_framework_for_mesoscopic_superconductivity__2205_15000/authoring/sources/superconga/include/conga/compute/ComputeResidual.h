//===----- ComputeResidual.h - Functionality for computing residual. ------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Functionality for computing the residual between different self-consistent
/// iterations.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_COMPUTE_RESIDUAL_H_
#define CONGA_COMPUTE_RESIDUAL_H_

#include "../defines.h"
#include "../grid/GridData.h"

#include <cassert>
#include <cmath>
#include <limits>

namespace conga {
/// \brief Compute the residual as numer / max(denom, epsilon).
///
/// \param inNumer The numerator.
/// \param inDenom The denominator.
/// \param inEpsilon When to stop using relative error and move towards absolut
/// error. This is needed for quantities converging to zero.
///
/// \return The residual.
template <typename T>
inline T computeResidual(const T inNumer, const T inDenom, const T inEpsilon) {
  return inNumer / std::max(inDenom, inEpsilon);
}

/// \brief Enum class for residual norm.
enum class ResidualNorm { L1, L2, LInf };

/// \brief Compute the residual given old and new values.
///
/// \param inOld The old value.
/// \param inNew The new value.
///
/// \return The residual.
template <typename T> inline T computeResidual(const T inOld, const T inNew) {
  const T numer = std::abs(inOld - inNew);
  const T denom = std::abs(inOld);
  const T epsilon = static_cast<T>(constants::RESIDUAL_EPSILON);
  return computeResidual(numer, denom, epsilon);
}

/// \brief Compute the residual given old and new values.
///
/// \param inOld The old values.
/// \param inNew The new values.
/// \param inNormType Which norm to use.
///
/// \return The residual.
template <typename T, typename Device>
inline T computeResidual(const GridData<T, Device> &inOld,
                         const GridData<T, Device> &inNew,
                         const ResidualNorm inNormType) {
  // Sanity check.
  assert(inOld.numElements() == inNew.numElements());
  assert(inOld.isComplex() == inNew.isComplex());

  // Compute.
  T numer = static_cast<T>(0);
  T denom = static_cast<T>(0);
  T epsilon = static_cast<T>(constants::RESIDUAL_EPSILON);
  switch (inNormType) {
  case ResidualNorm::L1: {
    numer = (inOld - inNew).L1Norm();
    denom = inOld.L1Norm();
    // TODO(Niclas): This should probably be:
    // numGrainLatticeSites * numFields *(1 + static_cast<int>(isComplex)).
    const int numElements = inOld.numElements();
    epsilon *= static_cast<T>(numElements);
    break;
  }
  case ResidualNorm::L2: {
    numer = (inOld - inNew).L2Norm();
    denom = inOld.L2Norm();
    // TODO(Niclas): This should probably be:
    // numGrainLatticeSites * numFields *(1 + static_cast<int>(isComplex)).
    const int numElements = inOld.numElements();
    epsilon *= static_cast<T>(numElements);
    break;
  }
  case ResidualNorm::LInf: {
    numer = (inOld - inNew).LInfNorm();
    denom = inOld.LInfNorm();
    break;
  }
  }
  return computeResidual(numer, denom, epsilon);
}
} // namespace conga

#endif // CONGA_COMPUTE_RESIDUAL_H_
