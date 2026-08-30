//===------ BulkSolver.h - Class for solving everything in bulk. ----------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Class for computing the multi-component order parameter and impurity
/// self-energies in bulk.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_BULK_H_
#define CONGA_BULK_H_

#include "compute/ComputeResidual.h"
#include "configure.h"
#include "defines.h"
#include "fermi_surface/FermiSurfaceCircle.h"
#include "green/LocalGreens.h"
#include "impurities/local_impurities.h"
#include "matsubara.h"
#include "order_parameter/OrderParameterBasis.h"
#include "ozaki.h"
#include "riccati/RiccatiSolutions.h"

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

#include <thrust/complex.h>

#include <algorithm>
#include <cassert>
#include <cmath>
#include <memory>
#include <numeric>
#include <tuple>
#include <vector>

namespace conga {
template <typename T> class BulkSolver {
public:
  /// @brief Solver for the bulk order-parameter.
  /// @param inTemperature The temperature (in units of Tc).
  /// @param inEnergyCutoff The energy cutoff (in units of 2*pi*kB*Tc).
  /// @param inNumFermiMomenta The number of momenta in the (circular) Fermi
  /// surface average.
  /// @param inUseOzaki Whether to use Ozaki or Matsubara energies.
  BulkSolver(const T inTemperature, const T inEnergyCutoff,
             const int inNumFermiMomenta, const bool inUseOzaki = true);

  /// @brief Set the impurity scattering energy.
  /// @param The new value.
  void scatteringEnergy(const T inScatteringEnergy);

  /// @brief Set the impurity scattering energy.
  /// @param The new value.
  void scatteringPhaseShift(const T inScatteringPhaseShift);

  /// @brief Add an order-parameter component.
  /// @param inSymmetry The symmetry of the component (e.g. s-wave).
  /// @param inCriticalTemperature The critical temperature.
  /// @param inPhaseShift Initial phase shift.
  void
  addOrderParameterComponent(const Symmetry inSymmetry,
                             const T inCriticalTemperature = static_cast<T>(1),
                             const T inPhaseShift = static_cast<T>(0));

  /// @brief Compute the order parameter.
  /// @param inConvergenceCriterion Terminate when the residual is smaller than
  /// this.
  /// @return Whether it converged or not.
  bool compute(const T inConvergenceCriterion);

  /// @brief Get the total order-parameter magnitude.
  /// @return The value (a real number).
  T orderParameterMagnitude() const;

  /// @brief Get the value of a certain order-parameter component.
  /// @param inSymmetry The symmetry (e.g. s-wave) of the requested component.
  /// @return The value (a complex number).
  thrust::complex<T> orderParameterComponent(const Symmetry inSymmetry) const;

  /// @brief Get the impurity self-energies.
  /// @return The tuple {Sigma, Delta, DeltaTilde}.
  std::tuple<std::vector<thrust::complex<T>>, std::vector<thrust::complex<T>>,
             std::vector<thrust::complex<T>>>
  impuritySelfEnergy() const;

private:
  // The impurity scattering energy.
  double m_scatteringEnergy;
  double m_scatteringPhaseShift;

  std::vector<BasisFunction<double>> m_opBasis;
  std::vector<double> m_couplingConstants;
  std::vector<thrust::complex<double>> m_opComponents;

  std::vector<thrust::complex<double>> m_impSigma;
  std::vector<thrust::complex<double>> m_impDelta;
  std::vector<thrust::complex<double>> m_impDeltaTilde;

  std::vector<double> m_energies;
  std::vector<double> m_residues;

  const double m_temperature;
  const FermiSurfaceCircle<double> m_fermiSurface;

  /// @brief Compute the energies and residues.
  /// @param inEnergyCutoff The energy cutoff (in units of 2*pi*kB*Tc).
  /// @param inUseOzaki Whether to use Ozaki or Matsubara energies.
  void computeEnergiesAndResidues(const double inEnergyCutoff,
                                  const bool inUseOzaki);

  thrust::complex<double>
  orderParameterWithMomentum(const vector2d<double> &inFermiMomentum) const;

  std::tuple<std::vector<thrust::complex<double>>,
             std::vector<thrust::complex<double>>,
             std::vector<thrust::complex<double>>>
  computeGreen(const thrust::complex<double> &inOrderParameter) const;

  double computeResidualInternal(
      const std::vector<thrust::complex<double>> &inOld,
      const std::vector<thrust::complex<double>> &inNew) const;
};

template <typename T>
BulkSolver<T>::BulkSolver(const T inTemperature, const T inEnergyCutoff,
                          const int inNumFermiMomenta, const bool inUseOzaki)
    : m_temperature(static_cast<double>(inTemperature)),
      m_scatteringEnergy(0.0), m_scatteringPhaseShift(0.0),
      m_fermiSurface(inNumFermiMomenta) {
  if (inUseOzaki) {
    std::tie(m_energies, m_residues) = ozaki::computeEnergiesAndResidues(
        m_temperature, static_cast<double>(inEnergyCutoff));
  } else {
    std::tie(m_energies, m_residues) = matsubara::computeEnergiesAndResidues(
        m_temperature, static_cast<double>(inEnergyCutoff));
  }

  // Sanity check.
  assert(m_energies.size() == m_residues.size());
}

template <typename T>
void BulkSolver<T>::scatteringEnergy(const T inScatteringEnergy) {
  m_scatteringEnergy = static_cast<double>(inScatteringEnergy);
}

template <typename T>
void BulkSolver<T>::scatteringPhaseShift(const T inScatteringPhaseShift) {
  m_scatteringPhaseShift = static_cast<double>(inScatteringPhaseShift);
}

template <typename T>
void BulkSolver<T>::addOrderParameterComponent(const Symmetry inSymmetry,
                                               const T inCriticalTemperature,
                                               const T inPhaseShift) {
  m_opBasis.push_back(BasisFunction<double>(inSymmetry, &m_fermiSurface));

  double sum = 0.0;
  for (std::size_t i = 0; i < m_energies.size(); ++i) {
    sum += m_residues[i] / m_energies[i];
  }
  sum *= m_temperature;

  // Note, that here we implicitly assume that the basis functions are
  // normalized. I.e. <|eta|^2> = 1. Otherwise the sum would be scaled by
  // <|eta|^2>.
  const double couplingConstant =
      m_temperature /
      (std::log(m_temperature / static_cast<double>(inCriticalTemperature)) +
       sum);
  m_couplingConstants.push_back(couplingConstant);

  const double scale =
      std::sqrt(1.0 - m_temperature * m_temperature * m_temperature);
  const double zeroTemperatureValue = (inSymmetry == Symmetry::SWAVE)
                                          ? constants::S_WAVE_BULK
                                          : constants::D_WAVE_BULK;
  const double magnitude = scale * zeroTemperatureValue;
  const thrust::complex<double> orderParameter =
      magnitude *
      thrust::complex<double>(std::cos(inPhaseShift), std::sin(inPhaseShift));
  m_opComponents.push_back(orderParameter);
}

template <typename T>
thrust::complex<double> BulkSolver<T>::orderParameterWithMomentum(
    const vector2d<double> &inFermiMomentum) const {
  thrust::complex<double> orderParameter(static_cast<T>(0));
  const std::size_t numComponents = m_opComponents.size();
  for (std::size_t i = 0; i < numComponents; ++i) {
    orderParameter +=
        m_opComponents[i] * m_opBasis[i].evaluate(inFermiMomentum);
  }
  return orderParameter;
}

template <typename T>
std::tuple<std::vector<thrust::complex<double>>,
           std::vector<thrust::complex<double>>,
           std::vector<thrust::complex<double>>>
BulkSolver<T>::computeGreen(
    const thrust::complex<double> &inOrderParameter) const {
  const std::size_t numEnergies = m_energies.size();
  std::vector<thrust::complex<double>> gGreen(numEnergies);
  std::vector<thrust::complex<double>> fGreen(numEnergies);
  std::vector<thrust::complex<double>> fTildeGreen(numEnergies);

  for (std::size_t energyIdx = 0; energyIdx < numEnergies; ++energyIdx) {
    const thrust::complex<double> energy =
        thrust::complex<double>(0.0, m_energies[energyIdx]) -
        m_scatteringEnergy * m_impSigma[energyIdx];
    const thrust::complex<double> orderParameter =
        inOrderParameter + m_scatteringEnergy * m_impDelta[energyIdx];
    const thrust::complex<double> orderParameterTilde =
        thrust::conj(inOrderParameter) +
        m_scatteringEnergy * m_impDeltaTilde[energyIdx];

    const auto [gamma, gammaTilde] = riccati::computeHomogeneous(
        energy, orderParameter, orderParameterTilde);

    gGreen[energyIdx] = Greens<double>::compute(gamma, gammaTilde);
    fGreen[energyIdx] = GreensAnomalous<double>::compute(gamma, gammaTilde);
    fTildeGreen[energyIdx] =
        GreensAnomalousTilde<double>::compute(gamma, gammaTilde);
  }
  return {gGreen, fGreen, fTildeGreen};
}

template <typename T>
double BulkSolver<T>::computeResidualInternal(
    const std::vector<thrust::complex<double>> &inOld,
    const std::vector<thrust::complex<double>> &inNew) const {
  assert(inOld.size() == inNew.size());

  double numer = 0.0;
  double denom = 0.0;
  for (std::size_t i = 0; i < inOld.size(); ++i) {
    const thrust::complex<double> old = inOld[i];
    const thrust::complex<double> diff = inNew[i] - old;
    numer =
        std::max(std::max(std::abs(diff.real()), std::abs(diff.imag())), numer);
    denom =
        std::max(std::max(std::abs(old.real()), std::abs(old.imag())), denom);
  }

  return computeResidual(numer, denom, constants::RESIDUAL_EPSILON);
}

template <typename T>
bool BulkSolver<T>::compute(const T inConvergenceCriterion) {
  assert(m_opBasis.size() == m_couplingConstants.size());
  assert(m_opBasis.size() == m_opComponents.size());
  const std::size_t numComponents = m_opComponents.size();

  const int numAngles = m_fermiSurface.getNumAngles();
  const std::size_t numEnergies = m_energies.size();
  const double convergenceCriterion =
      static_cast<double>(inConvergenceCriterion);

  m_impSigma = std::vector<thrust::complex<double>>(numEnergies);
  m_impDelta = std::vector<thrust::complex<double>>(numEnergies);
  m_impDeltaTilde = std::vector<thrust::complex<double>>(numEnergies);

  // Expose this? Or use while?
  const int numIterations = 42000;

  // Used for Polyak acceleration.
  // TODO(Niclas): Use some other acceleration. Perhaps use the old method when
  // there is only one component!?
  std::vector<thrust::complex<double>> opComponentsOld(numComponents);
  const double stepSize = 2.0;
  const double drag = 0.5;

  bool isConverged = false;
  for (int iterationIdx = 0; iterationIdx < numIterations; ++iterationIdx) {
    std::vector<thrust::complex<double>> opComponentsNew(numComponents);
    std::vector<thrust::complex<double>> impSigmaNew(numEnergies);
    std::vector<thrust::complex<double>> impDeltaNew(numEnergies);
    std::vector<thrust::complex<double>> impDeltaTildeNew(numEnergies);

    for (int angleIdx = 0; angleIdx < numAngles; ++angleIdx) {
      const auto fermiMomentum = m_fermiSurface.getFermiMomentum(angleIdx);
      const double integrandFactor =
          m_fermiSurface.getIntegrandFactor(angleIdx);

      const thrust::complex<double> op =
          orderParameterWithMomentum(fermiMomentum);

      const auto [gGreen, fGreen, fTildeGreen] = computeGreen(op);

      const thrust::complex<double> fSum = std::transform_reduce(
          fGreen.begin(), fGreen.end(), m_residues.begin(),
          thrust::complex<double>(0.0));
      const thrust::complex<double> fTildeSum = std::transform_reduce(
          fTildeGreen.begin(), fTildeGreen.end(), m_residues.begin(),
          thrust::complex<double>(0.0));
      for (std::size_t i = 0; i < numComponents; ++i) {
        opComponentsNew[i] +=
            0.5 * integrandFactor * (fSum + thrust::conj(fTildeSum)) *
            thrust::conj(m_opBasis[i].evaluate(fermiMomentum));
      }

      if (m_scatteringEnergy > 0.0) {
        for (std::size_t energyIdx = 0; energyIdx < numEnergies; ++energyIdx) {
          impSigmaNew[energyIdx] += integrandFactor * gGreen[energyIdx];
          impDeltaNew[energyIdx] += integrandFactor * fGreen[energyIdx];
          impDeltaTildeNew[energyIdx] +=
              integrandFactor * fTildeGreen[energyIdx];
        }
      }
    } // End angle loop.

    // Apply coupling constants.
    for (std::size_t i = 0; i < numComponents; ++i) {
      opComponentsNew[i] *= m_couplingConstants[i];
    }

    // Finalize the impurity the self-energies.
    if (m_scatteringEnergy > 0.0 && std::abs(m_scatteringPhaseShift) > 0.0) {
      const double c = std::cos(m_scatteringPhaseShift);
      const double s = std::sin(m_scatteringPhaseShift);
      for (std::size_t energyIdx = 0; energyIdx < numEnergies; ++energyIdx) {
        const thrust::complex<double> gAvg = impSigmaNew[energyIdx];
        const thrust::complex<double> fAvg = impDeltaNew[energyIdx];
        const thrust::complex<double> fTildeAvg = impDeltaNew[energyIdx];

        thrust::tie(impSigmaNew[energyIdx], impDeltaNew[energyIdx],
                    impDeltaTildeNew[energyIdx]) =
            impurities::computeSelfEnergy(gAvg, fAvg, fTildeAvg, c, s);
      }
    }

    const double opResidual =
        computeResidualInternal(m_opComponents, opComponentsNew);
    const double impSigmaResidual =
        computeResidualInternal(m_impSigma, impSigmaNew);
    const double impDeltaResidual =
        computeResidualInternal(m_impDelta, impDeltaNew);
    const double impDeltaTildeResidual =
        computeResidualInternal(m_impDeltaTilde, impDeltaTildeNew);
    const double residual = std::max({opResidual, impSigmaResidual,
                                      impDeltaResidual, impDeltaTildeResidual});

    if (std::isnan(residual)) {
      std::printf("-- FAILURE! NaN in bulk solver at iteration = %d\n.",
                  iterationIdx);
      break;
    }

    isConverged = residual < convergenceCriterion;
    if (isConverged) {
#ifndef NDEBUG
      std::printf("-- SUCCESS! Bulk solver converged at iteration = %d.\n",
                  iterationIdx);
#endif
      break;
    }

    // Update order parameter.
    if (iterationIdx > 0) {
      // Take Polyak step.
      const double weightNew = stepSize;
      const double weightCurrent = 2.0 - stepSize - drag;
      const double weightOld = drag - 1.0;

      for (std::size_t i = 0; i < numComponents; ++i) {
        opComponentsNew[i] = opComponentsNew[i] * weightNew +
                             m_opComponents[i] * weightCurrent +
                             opComponentsOld[i] * weightOld;
      }
    }
    opComponentsOld = m_opComponents;
    m_opComponents = opComponentsNew;

    m_impSigma = impSigmaNew;
    m_impDelta = impDeltaNew;
    m_impDeltaTilde = impDeltaTildeNew;
  } // End main loop.

#ifndef NDEBUG
  if (!isConverged) {
    std::printf("-- FAILURE! Bulk solver did not converge.\n");
  }
#endif

  return isConverged;
}

template <typename T> T BulkSolver<T>::orderParameterMagnitude() const {
  double result = 0.0;
  for (const auto &component : m_opComponents) {
    result += thrust::norm(component);
  }
  result = std::sqrt(result);
  return static_cast<T>(result);
}

template <typename T>
thrust::complex<T>
BulkSolver<T>::orderParameterComponent(const Symmetry inSymmetry) const {
  thrust::complex<T> result(static_cast<T>(0));
  const std::size_t numComponents = m_opComponents.size();
  for (std::size_t i = 0; i < numComponents; ++i) {
    if (m_opBasis[i].getSymmetry() == inSymmetry) {
      const auto val = m_opComponents[i];
      result = thrust::complex<T>(static_cast<T>(val.real()),
                                  static_cast<T>(val.imag()));
      break;
    }
  }
  return result;
}

template <typename T>
std::tuple<std::vector<thrust::complex<T>>, std::vector<thrust::complex<T>>,
           std::vector<thrust::complex<T>>>
BulkSolver<T>::impuritySelfEnergy() const {
  const std::size_t numEnergies = m_impSigma.size();

  std::vector<thrust::complex<T>> impSigma(numEnergies);
  std::vector<thrust::complex<T>> impDelta(numEnergies);
  std::vector<thrust::complex<T>> impDeltaTilde(numEnergies);

  for (std::size_t i = 0; i < numEnergies; ++i) {
    impSigma[i] = thrust::complex<T>(static_cast<T>(m_impSigma[i].real()),
                                     static_cast<T>(m_impSigma[i].imag()));
    impDelta[i] = thrust::complex<T>(static_cast<T>(m_impDelta[i].real()),
                                     static_cast<T>(m_impDelta[i].imag()));
    impDeltaTilde[i] =
        thrust::complex<T>(static_cast<T>(m_impDeltaTilde[i].real()),
                           static_cast<T>(m_impDeltaTilde[i].imag()));
  }

  return {std::move(impSigma), std::move(impDelta), std::move(impDeltaTilde)};
}
} // namespace conga

#endif // CONGA_BULK_H_
