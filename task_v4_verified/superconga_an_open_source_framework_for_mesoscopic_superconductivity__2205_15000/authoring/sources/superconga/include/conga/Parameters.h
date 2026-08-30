//===--------------- Parameters.h - Parameter storage class. --------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Storage class for parameters, with convenience functions.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_PARAMETERS_H_
#define CONGA_PARAMETERS_H_

#include "ContextModule.h"
#include "compute/ComputeResidual.h"
#include "defines.h"
#include "ozaki.h"
#include "utils.h"

#include <cmath>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace conga {
template <typename T> class Parameters : public ContextModule<T> {
public:
  Parameters() {}
  ~Parameters() {}

  Parameters(Context<T> *inOutContext);

  Parameters &operator=(const Parameters &inOther);

  template <typename T2>
  Parameters<T> &operator=(const Parameters<T2> &inOther);

  template <typename T2>
  Parameters<T> &operatorEq(const Parameters<T2> &inOther);

  template <typename T2> operator Parameters<T2>() const;

  virtual int initialize() { return 0; }

  // Getters
  int getGridResolutionBase() const { return m_gridResolution; }
  int getGridResolutionCoherence() const { return m_gridResolutionRotated; }
  int getGridResolutionDeltaRotated() const { return m_gridResolutionRotated; }

  T getGrainWidth() const { return m_grainWidth; }
  T getGridElementSize() const {
    return static_cast<T>(1) / m_pointsPerCoherenceLength;
  }
  T getGrainFraction() const { return m_grainFraction; }
  int getAngularResolution() const { return m_numAngles; }
  T getAngleIncrement() const;

  int getNumOzakiEnergies() const;
  T getTemperature() const { return m_temperature; }
  T getNumFluxQuanta() const { return m_numFluxQuanta; }
  int getChargeSign() const { return m_chargeSign; }

  T getScatteringEnergy() const { return m_scatteringEnergy; }
  T getScatteringPhaseShift() const { return m_scatteringPhaseShift; }

  ResidualNorm getResidualNormType() const { return m_residualNormType; }

  T getConvergenceCriterion() const { return m_convergenceCriterion; }

  T getEnergyCutoff() const { return m_energyCutoff; }

  T getEnergyMin() const { return m_energyMin; }
  T getEnergyMax() const { return m_energyMax; }
  int getNumEnergies() const { return m_numEnergies; }
  T getEnergyBroadening() const { return m_energyBroadening; }

  T getPenetrationDepth() const { return m_penetrationDepth; }

  // Setters
  // TODO: (Patric) Change name from grid to grain when referring to the
  // superconducting grain.
  void setGrainWidth(const T inGrainWidth);
  void setPointsPerCoherenceLength(const T inPointsPerCoherenceLength);
  void setAngularResolution(const int inNumAngles) {
    m_numAngles = inNumAngles;
  }

  void setEnergyCutoff(const T inEnergyCutoff) {
    m_energyCutoff = inEnergyCutoff;
    m_numOzakiEnergies =
        ozaki::computeNumEnergies(m_temperature, m_energyCutoff);
  };

  void setTemperature(const T inTemperature) {
    m_temperature = inTemperature;
    m_numOzakiEnergies =
        ozaki::computeNumEnergies(m_temperature, m_energyCutoff);
  }
  void setNumFluxQuanta(const T inNumFluxQuanta) {
    m_numFluxQuanta = inNumFluxQuanta;
  }

  void setChargeSign(const int inChargeSign) {
    m_chargeSign = utils::sign(inChargeSign);
  }

  void setScatteringEnergy(const T inScatteringEnergy) {
    m_scatteringEnergy = inScatteringEnergy;
  }

  void setScatteringPhaseShift(const T inScatteringPhaseShift) {
    m_scatteringPhaseShift = inScatteringPhaseShift;
  }

  void setResidualNormType(const ResidualNorm inNormType) {
    m_residualNormType = inNormType;
  }

  void setEnergyRange(const T inEnergyMin, const T inEnergyMax,
                      const int inNumEnergies,
                      const T inEnergyBroadening = static_cast<T>(0.01));
  void setNumEnergies(const int inNumEnergies) {
    m_numEnergies = inNumEnergies;
  }

  void setConvergenceCriterion(const T inConvergenceCriterion) {
    m_convergenceCriterion = inConvergenceCriterion;
  }

  void setPenetrationDepth(const T inPenetrationDepth) {
    m_penetrationDepth = inPenetrationDepth;
  }

  // Helpers
  void print() const;

private:
  // The grid resolution, i.e. N in the size of the (square) domain grid NxN.
  int m_gridResolution;

  // The grid resolution for rotated grids.
  int m_gridResolutionRotated;

  // Side length of superconducting grain in units hbar*<vF>/(2*pi*kB*Tc).
  T m_grainWidth;

  // The number of lattice points per coherence length.
  T m_pointsPerCoherenceLength;

  // The fraction of the simulation lattice maximally used for the grain.
  T m_grainFraction;

  // Number of angles to solve for.
  int m_numAngles;

  // Number of spectral energies.
  int m_numEnergies;

  // Energy cutoff.
  T m_energyCutoff;

  // Temperature in units of Tc.
  T m_temperature;

  // The number of external flux-quanta.
  T m_numFluxQuanta;

  // The penetration depth used when solving for the vector potential.
  T m_penetrationDepth;

  // The sign of the carrier charge.
  int m_chargeSign;

  // The scattering energy used for impurity self-energy.
  T m_scatteringEnergy;

  // The scattering phase-shift used for impurity self-energy.
  T m_scatteringPhaseShift;

  // The norm to use when computing residuals.
  ResidualNorm m_residualNormType;

  // The number of Ozaki energies.
  T m_numOzakiEnergies;

  // Lowest energy to compute LDOS for.
  T m_energyMin;

  // Highest energy to compute LDOS for.
  T m_energyMax;

  // Energy broadening (for e.g. retarded properties).
  T m_energyBroadening;

  // Numerical properties.
  T m_convergenceCriterion;

  // Set the lattice resolution.
  void setLatticeResolution(const T inGrainWidth,
                            const T inPointsPerCoherenceLength);
  int computeGridResolutionRotated(const int numGridBase) const;
};

template <typename T>
Parameters<T>::Parameters(Context<T> *const inOutContext)
    : m_grainWidth(static_cast<T>(20)),
      m_pointsPerCoherenceLength(static_cast<T>(5)), m_numAngles(64),
      m_energyCutoff(static_cast<T>(10)), m_temperature(static_cast<T>(0.5)),
      m_numFluxQuanta(static_cast<T>(0)), m_chargeSign(-1),
      m_scatteringEnergy(static_cast<T>(0)),
      m_scatteringPhaseShift(static_cast<T>(0)),
      m_convergenceCriterion(static_cast<T>(1e-6)), m_numEnergies(128),
      m_energyMin(static_cast<T>(0)), m_energyMax(static_cast<T>(3)),
      m_energyBroadening(static_cast<T>(0.05)), m_numOzakiEnergies(1),
      m_penetrationDepth(-static_cast<T>(1)),
      m_residualNormType(ResidualNorm::L2) {
  ContextModule<T>::setContext(inOutContext);
  inOutContext->set(this);
  setLatticeResolution(m_grainWidth, m_pointsPerCoherenceLength);
}

template <typename T>
Parameters<T> &Parameters<T>::operator=(const Parameters<T> &inOther) {
  operatorEq(inOther);
  return *this;
}

template <typename T>
template <typename T2>
Parameters<T> &Parameters<T>::operator=(const Parameters<T2> &inOther) {
  operatorEq(inOther);
  return *this;
}

template <typename T>
template <typename T2>
Parameters<T>::operator Parameters<T2>() const {
  Parameters<T2> other;
  other = *this;
  return other;
}

// Is this necessary?
template <typename T>
template <typename T2>
Parameters<T> &Parameters<T>::operatorEq(const Parameters<T2> &inOther) {
  m_grainWidth = inOther.getGrainWidth();
  m_numAngles = inOther.getAngularResolution();
  m_energyCutoff = inOther.getEnergyCutoff();
  m_temperature = inOther.getTemperature();
  m_numFluxQuanta = inOther.getNumFluxQuanta();
  m_convergenceCriterion = inOther.getConvergenceCriterion();
  m_numEnergies = inOther.getNumEnergies();
  m_energyMin = inOther.getEnergyMin();
  m_energyMax = inOther.getEnergyMax();
  m_energyBroadening = inOther.getEnergyBroadening();

  m_numOzakiEnergies = inOther.m_numOzakiEnergies;
  m_penetrationDepth = inOther.m_penetrationDepth;

  m_grainFraction = inOther.m_grainFraction;
  m_grainWidth = inOther.m_grainWidth;
  m_pointsPerCoherenceLength = inOther.m_pointsPerCoherenceLength;

  m_gridResolution = inOther.m_gridResolution;
  m_gridResolutionRotated = inOther.m_gridResolutionRotated;

  return *this;
}

template <typename T> int Parameters<T>::getNumOzakiEnergies() const {
  return m_numOzakiEnergies;
}

template <typename T>
void Parameters<T>::setEnergyRange(const T inEnergyMin, const T inEnergyMax,
                                   const int inNumEnergies,
                                   const T inEnergyBroadening) {
  m_energyMin = inEnergyMin;
  m_energyMax = inEnergyMax;
  m_energyBroadening = inEnergyBroadening;

  // Do the limits make sense?
  // TODO(niclas): Shouldn't we check that min < max? And why set the number of
  // energies to 1 if max = 0?
  if (inEnergyMax == static_cast<T>(0.0) || inEnergyMax == inEnergyMin) {
    m_numEnergies = 1;
  } else {
    m_numEnergies = inNumEnergies;
  }
}

template <typename T> void Parameters<T>::setGrainWidth(const T inGrainWidth) {
  // Grain width in coherence lengths: hbar*<vF>/(kB*Tc).
  m_grainWidth = inGrainWidth;

  // Update the lattice resolution.
  setLatticeResolution(m_grainWidth, m_pointsPerCoherenceLength);
}

template <typename T>
void Parameters<T>::setPointsPerCoherenceLength(
    const T inPointsPerCoherenceLength) {
  // Points per coherence length: hbar*<vF>/(kB*Tc).
  m_pointsPerCoherenceLength = inPointsPerCoherenceLength;

  // Update the lattice resolution.
  setLatticeResolution(m_grainWidth, m_pointsPerCoherenceLength);
}

template <typename T>
void Parameters<T>::setLatticeResolution(const T inGrainWidth,
                                         const T inPointsPerCoherenceLength) {
  // The fractional number of lattice points required for the grain itself,
  // excluding safety margin.
  const T fracPointsGrain = inGrainWidth * inPointsPerCoherenceLength;

  // The total number of required points, including safety margin.
  const int numPointsTotal = static_cast<int>(std::ceil(fracPointsGrain)) +
                             2 * constants::GRAIN_SIZE_MARGIN;

  // The fraction of points for the grain.
  m_grainFraction = fracPointsGrain / static_cast<T>(numPointsTotal);

  // Set the number of points per side in the simulation.
  m_gridResolution = numPointsTotal;

  // Set the number of points per side with rotational margin.
  m_gridResolutionRotated = computeGridResolutionRotated(numPointsTotal);
}

template <typename T> T Parameters<T>::getAngleIncrement() const {
  return static_cast<T>(2.0 * M_PI) / static_cast<T>(m_numAngles);
}

template <typename T>
int Parameters<T>::computeGridResolutionRotated(const int inNumGridBase) const {
  // The rotated size is given by:
  // N + 2x >= sqrt(2)N
  // ==>
  // x >= 0.5 * (sqrt(2) - 1) * N
  const double marginFractional =
      0.5 * (std::sqrt(2.0) - 1.0) * static_cast<double>(inNumGridBase);
  const int margin = static_cast<int>(std::ceil(marginFractional));
  const int numGridRotated = inNumGridBase + 2 * margin;
  return numGridRotated;
}

template <typename T> void Parameters<T>::print() const {
  std::cout << "Grain resolution base: " << m_gridResolution << std::endl;
  std::cout << "Grain resolution rotated: " << m_gridResolutionRotated
            << std::endl;
  std::cout << "Grain Width: " << m_grainWidth << std::endl;
  std::cout << "Grain fraction: " << m_grainFraction << std::endl;
  std::cout << "Points per coherence length: " << m_pointsPerCoherenceLength
            << std::endl;
  std::cout << "Angular resolution: " << m_numAngles << std::endl;
  std::cout << "Temperature: " << m_temperature << std::endl;
  std::cout << "Flux quanta: " << m_numFluxQuanta << std::endl;
  std::cout << "Number of Ozaki energies: " << m_numOzakiEnergies << std::endl;
  std::cout << "Spectral energy range: (" << m_energyMin << ", " << m_energyMax
            << ")" << std::endl;
  std::cout << "Number of spectral energy levels: " << m_numEnergies
            << std::endl;
  std::cout << "Spectral energy broadening: " << m_energyBroadening
            << std::endl;
  std::cout << "Convergence criterion: " << m_convergenceCriterion << std::endl;
  std::cout << "Cutoff parameter: " << m_energyCutoff << std::endl;
  std::cout << "Penetration depth: " << m_penetrationDepth << std::endl;
  std::cout << "Charge sign: " << m_chargeSign << std::endl;
  std::cout << "Scattering energy: " << m_scatteringEnergy << std::endl;
  std::cout << "Scattering phase shift: " << m_scatteringPhaseShift
            << std::endl;
  // std::cout << "Residual norm type: " << m_residualNormType << std::endl;
}
} // namespace conga

#endif // CONGA_PARAMETERS_H_
