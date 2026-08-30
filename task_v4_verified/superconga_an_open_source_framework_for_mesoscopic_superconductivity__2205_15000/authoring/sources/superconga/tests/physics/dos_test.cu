//===--------- dost_test.cu - Unit tests of the density of states  --------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Different tests of the density of states (DOS), e.g. checking that given an
/// order parameter with a constant bulk value yields the expected DOS.
///
//===----------------------------------------------------------------------===//
#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN

// TODO(niclas): These should not have to be included! They are needed because
// "Context" only has forward declarations.
#include "conga/compute/ComputeCurrent.h"
#include "conga/compute/ComputeFreeEnergy.h"
#include "conga/compute/ComputeImpuritySelfEnergy.h"
#include "conga/compute/ComputeOrderParameter.h"

#include "conga/BulkSolver.h"
#include "conga/Context.h"
#include "conga/Parameters.h"
#include "conga/boundary/BoundaryConditionSpecular.h"
#include "conga/compute/ComputeLDOS.h"
#include "conga/defines.h"
#include "conga/fermi_surface/FermiSurfaceCircle.h"
#include "conga/geometry/DiscGeometry.h"
#include "conga/geometry/GeometryGroup.h"
#include "conga/geometry/PolygonGeometry.h"
#include "conga/green/LocalGreens.h"
#include "conga/grid.h"
#include "conga/impurities/local_impurities.h"
#include "conga/integration/IntegrationIteratorKeldysh.h"
#include "conga/order_parameter/OrderParameter.h"
#include "conga/riccati/RiccatiSolutions.h"
#include "conga/riccati/RiccatiSolverConfined.h"
#include "conga/run_simulation.h"
#include "conga/wrappers/doctest.h"

#include <thrust/complex.h>

#include <complex>
#include <iostream>
#include <stdlib.h>
#include <tuple>

namespace helper {
// Helper function for computing the Fermi-surface averages of the Greens
// functions g, f, and tilde(f), needed in order to compute the expected DOS.
template <typename T>
std::tuple<thrust::complex<T>, thrust::complex<T>, thrust::complex<T>>
computeAvgGreens(const thrust::complex<T> &inEnergy, const T inOrderParameter,
                 const conga::BasisFunction<T> &inBasisFunction,
                 const thrust::complex<T> &inImpSigma,
                 const thrust::complex<T> &inImpDelta,
                 const thrust::complex<T> &inImpDeltaTilde,
                 const conga::FermiSurface<T> *const inFermiSurface) {
  const int numMomenta = inFermiSurface->getNumAngles();

  thrust::complex<T> gAvg(static_cast<T>(0));
  thrust::complex<T> fAvg(static_cast<T>(0));
  thrust::complex<T> fTildeAvg(static_cast<T>(0));

  for (int angleIdx = 0; angleIdx < numMomenta; ++angleIdx) {
    const auto fermiMomentum = inFermiSurface->getFermiMomentum(angleIdx);

    const thrust::complex<T> eta = inBasisFunction.evaluate(fermiMomentum);
    const thrust::complex<T> orderParameter = eta * inOrderParameter;

    const auto [gamma, gammaTilde] = conga::riccati::computeHomogeneous(
        inEnergy - inImpSigma, orderParameter + inImpDelta,
        thrust::conj(orderParameter) + inImpDeltaTilde);

    const thrust::complex<T> gTerm =
        conga::Greens<T>::compute(gamma, gammaTilde);
    const thrust::complex<T> fTerm =
        conga::GreensAnomalous<T>::compute(gamma, gammaTilde);
    const thrust::complex<T> fTildeTerm =
        conga::GreensAnomalousTilde<T>::compute(gamma, gammaTilde);

    const T integrandFactor = inFermiSurface->getIntegrandFactor(angleIdx);
    gAvg += gTerm * integrandFactor;
    fAvg += fTerm * integrandFactor;
    fTildeAvg += fTildeTerm * integrandFactor;
  }

  return {gAvg, fAvg, fTildeAvg};
}

template <typename T>
T computeResidual(const thrust::complex<T> &inOld,
                  const thrust::complex<T> &inNew) {
  return conga::computeResidual(
      thrust::abs(inOld - inNew), thrust::abs(inOld),
      static_cast<T>(conga::constants::RESIDUAL_EPSILON));
}

// Test that a grain, set to constant bulk value, gives the expected density of
// states.
template <typename T>
void testDensityOfStates(const bool inUseSwave,
                         const T inConvergenceCriterion) {
  // =================== ARRANGE ==================== //
  const T temperature = static_cast<T>(0.5);
  const T grainWidth = static_cast<T>(10);
  const T pointsPerCoherenceLength = static_cast<T>(1);
  const int numMomenta = 64;
  const int numEnergies = 24;
  const int numEnergiesPerBlock = 16;
  const T energyMin = static_cast<T>(0);
  const T energyMax = static_cast<T>(0.5);
  const T energyBroadening = static_cast<T>(1e-3);
  const T scatteringEnergy = static_cast<T>(0.01);
  const T scatteringPhaseShift = static_cast<T>(0.1 * M_PI);
  const conga::ResidualNorm residualNormType = conga::ResidualNorm::L2;
  const int numIterationsBurnIn = 0;
  const int numIterationsMin = 0;
  const int numIterationsMax = 1000;

  // Create Context
  const bool isRetarded = true;
  conga::Context<T> context(isRetarded);

  // Storage for system simulation parameters (e.g. temperature, lattice size).
  conga::Parameters<T> *parameters = new conga::Parameters<T>(&context);
  parameters->setGrainWidth(grainWidth);
  parameters->setPointsPerCoherenceLength(pointsPerCoherenceLength);
  parameters->setAngularResolution(numMomenta);
  parameters->setConvergenceCriterion(inConvergenceCriterion);
  parameters->setTemperature(temperature);
  parameters->setEnergyRange(energyMin, energyMax, numEnergies,
                             energyBroadening);
  parameters->setScatteringEnergy(scatteringEnergy);
  parameters->setScatteringPhaseShift(scatteringPhaseShift);
  parameters->setResidualNormType(residualNormType);

  // Create geometry group: add/remove geometry objects (e.g. discs, polygons)
  // from the geometry group
  conga::GeometryGroup<T> *geometry = new conga::GeometryGroup<T>(&context);
  const T grainFraction = parameters->getGrainFraction();
  if (inUseSwave) {
    // Add a disc to the simulation geometry.
    // Note, corners introduce artifacts. For an s-wave we can have a disc
    // instead, and lower the tolerance.
    geometry->add(new conga::DiscGeometry<T>(grainFraction), conga::Type::add);
  } else {
    // Add a square to the simulation geometry.
    const int numVertices = 4;
    geometry->add(new conga::PolygonGeometry<T>(grainFraction, numVertices),
                  conga::Type::add);
  }

  // Iterator.
  new conga::IntegrationIteratorKeldysh<T>(&context, numEnergiesPerBlock);

  // Choose a Riccati solver for a confined geometry, without magnetic fields
  conga::RiccatiSolver<T> *riccatiSolver =
      new conga::RiccatiSolverConfined<T, conga::gauge::Symmetric>(&context);
  // Add specular BC
  riccatiSolver->add(new conga::BoundaryConditionSpecular<T>);

  // Use s-wave or d-wave.
  const conga::Symmetry symmetry =
      inUseSwave ? conga::Symmetry::SWAVE : conga::Symmetry::DWAVE_X2_Y2;

  // Solve bulk.
  const T energyCutoff = static_cast<T>(32);
  conga::BulkSolver<T> bulkSolver(parameters->getTemperature(), energyCutoff,
                                  parameters->getAngularResolution());
  bulkSolver.scatteringEnergy(parameters->getScatteringEnergy());
  bulkSolver.scatteringPhaseShift(parameters->getScatteringPhaseShift());
  bulkSolver.addOrderParameterComponent(symmetry);
  const bool bulkConverged = bulkSolver.compute(inConvergenceCriterion);
  REQUIRE(bulkConverged);

  // Set up order parameter
  conga::OrderParameter<T> *orderParameter =
      new conga::OrderParameter<T>(&context);
  conga::ComponentOptions<T> options(symmetry);
  options.initialValue(bulkSolver.orderParameterComponent(symmetry));
  orderParameter->addComponent(options);

  // Add LDOS and impurity compute objects.
  new conga::ComputeLDOS<T>(&context);
  new conga::ComputeImpuritySelfEnergy<T>(&context);

  // Initialize everything.
  context.initialize();

  // =================== ACT ==================== //
  const bool verbose = true;
  conga::runPostprocess(numIterationsBurnIn, numIterationsMin, numIterationsMax,
                        verbose, context);
  const bool isConverged = context.isConverged();

  // Get results.
  const conga::GridGPU<T> &LDOS = *(context.getComputeLDOS()->getResult());
  const conga::ImpuritySelfEnergy<T> &impuritySelfEnergy =
      *(context.getImpuritySelfEnergy());

  // =================== ASSERT ==================== //

  // In order to compute the expected DOS we need the basis function, the Fermi
  // surface, and the bulk results.
  const conga::FermiSurface<T> *const fermiSurface = context.getFermiSurface();
  const conga::BasisFunction<T> basisFunction(symmetry, fermiSurface);
  const T orderParameterBulk = bulkSolver.orderParameterMagnitude();

  // Get energies.
  const conga::GridCPU<T> energies =
      *(context.getIntegrationIterator()->getEnergies());
  const T *const energiesPtr = energies.getDataPointer(0);

  const int numGrainLatticeSites =
      context.getGeometry()->getNumGrainLatticeSites();

  // For convenience.
  const T c = std::cos(scatteringPhaseShift);
  const T s = std::sin(scatteringPhaseShift);

  // Loop over energies and check the DOS for each.
  for (int energyIdx = 0; energyIdx < numEnergies; ++energyIdx) {
    const thrust::complex<T> energy(energiesPtr[energyIdx], energyBroadening);

    // The Fermi-surface averages of the Greens functions g, f, and tilde(f).
    thrust::complex<T> gAvg(static_cast<T>(0));
    thrust::complex<T> fAvg(static_cast<T>(0));
    thrust::complex<T> fTildeAvg(static_cast<T>(0));

    bool success = false;
    for (int iterationIdx = 0; iterationIdx < numIterationsMax;
         ++iterationIdx) {
      // Compute the impurity self-energy.
      // TODO(Niclas): I don't understand why structured bindings don't work
      // here.
      thrust::complex<T> impSigma, impDelta, impDeltaTilde;
      thrust::tie(impSigma, impDelta, impDeltaTilde) =
          conga::impurities::computeSelfEnergy(gAvg, fAvg, fTildeAvg, c, s,
                                               scatteringEnergy);

      const auto [gAvgNew, fAvgNew, fTildeAvgNew] =
          computeAvgGreens(energy, orderParameterBulk, basisFunction, impSigma,
                           impDelta, impDeltaTilde, fermiSurface);

      const T gResidual = computeResidual(gAvg, gAvgNew);
      const T fResidual = computeResidual(fAvg, fAvgNew);
      const T fTildeResidual = computeResidual(fTildeAvg, fTildeAvgNew);
      const T residual = std::max({gResidual, fResidual, fTildeResidual});

      // Update.
      gAvg = gAvgNew;
      fAvg = fAvgNew;
      fTildeAvg = fTildeAvgNew;

      success = residual < inConvergenceCriterion;
      if (success) {
        break;
      }
    }
    CHECK(success);

    const T expectedDOS = -gAvg.imag();

    const T testDOS =
        LDOS.sumField(energyIdx) / static_cast<T>(numGrainLatticeSites);
    CHECK(testDOS ==
          doctest::Approx(expectedDOS).epsilon(inConvergenceCriterion));
  }
  CHECK(isConverged);
}

// Compare with approximate value taken from Fig 6 in
// https://arxiv.org/abs/cond-mat/9502110.
template <typename T>
void compareWithKipAndSauls(const T inScatteringPhaseshift,
                            const T inExpectedDOS) {
  const conga::Symmetry symmetry = conga::Symmetry::DWAVE_X2_Y2;
  const T temperature = static_cast<T>(0.01);
  const T energyCutoff = static_cast<T>(64);
  const int numFermiMomenta = 1000;
  const T convergenceCriterion = static_cast<T>(1e-3);
  const T energyBroadening = static_cast<T>(1e-6);
  const int numIterationsMax = 1000;
  const T relativeEnergy = static_cast<T>(0.25);
  const T relativeScatteringEnergy = static_cast<T>(0.1);

  conga::BulkSolver<T> bulkSolver(temperature, energyCutoff, numFermiMomenta);
  bulkSolver.addOrderParameterComponent(symmetry);

  // Solve clean system.
  const bool bulkConvergedClean = bulkSolver.compute(convergenceCriterion);
  REQUIRE(bulkConvergedClean);

  // For convenience.
  const T cosPhaseShift = std::cos(inScatteringPhaseshift);
  const T sinPhaseShift = std::sin(inScatteringPhaseshift);

  // Kip and Sauls set Gamma_u = 0.1*\Delta_0, but we set
  // Gamma=Gamma_u*sin^2(delta_0)
  const T orderParameterBulkClean = bulkSolver.orderParameterMagnitude();
  const T scatteringEnergy = relativeScatteringEnergy *
                             orderParameterBulkClean * sinPhaseShift *
                             sinPhaseShift;

  // Solve impure system.
  bulkSolver.scatteringEnergy(scatteringEnergy);
  bulkSolver.scatteringPhaseShift(inScatteringPhaseshift);
  const bool bulkConverged = bulkSolver.compute(convergenceCriterion);
  REQUIRE(bulkConverged);

  const conga::FermiSurfaceCircle<T> fermiSurface(numFermiMomenta);
  const conga::BasisFunction<T> basisFunction(symmetry, &fermiSurface);
  const T orderParameterBulk = bulkSolver.orderParameterMagnitude();

  // The Fermi-surface averages of the Greens functions g, f, and tilde(f).
  thrust::complex<T> gAvg(static_cast<T>(0));
  thrust::complex<T> fAvg(static_cast<T>(0));
  thrust::complex<T> fTildeAvg(static_cast<T>(0));

  const thrust::complex<T> energy(relativeEnergy * orderParameterBulkClean,
                                  energyBroadening);

  bool success = false;
  for (int i = 0; i < numIterationsMax; ++i) {
    // Compute the impurity self-energy.
    // TODO(Niclas): I don't understand why structured bindings don't work
    // here.
    thrust::complex<T> impSigma, impDelta, impDeltaTilde;
    thrust::tie(impSigma, impDelta, impDeltaTilde) =
        conga::impurities::computeSelfEnergy(gAvg, fAvg, fTildeAvg,
                                             cosPhaseShift, sinPhaseShift,
                                             scatteringEnergy);

    const auto [gAvgNew, fAvgNew, fTildeAvgNew] =
        computeAvgGreens(energy, orderParameterBulk, basisFunction, impSigma,
                         impDelta, impDeltaTilde, &fermiSurface);

    const T gResidual = computeResidual(gAvg, gAvgNew);
    const T fResidual = computeResidual(fAvg, fAvgNew);
    const T fTildeResidual = computeResidual(fTildeAvg, fTildeAvgNew);
    const T residual = std::max({gResidual, fResidual, fTildeResidual});

    // Update.
    gAvg = gAvgNew;
    fAvg = fAvgNew;
    fTildeAvg = fTildeAvgNew;

    success = residual < convergenceCriterion;
    if (success) {
      break;
    }
  }
  CHECK(success);

  const T testDOS = -gAvg.imag();

  const T tolerance = static_cast<T>(0.1);
  const T scale = static_cast<T>(0);
  CHECK(testDOS ==
        doctest::Approx(inExpectedDOS).epsilon(tolerance).scale(scale));
}
} // namespace helper

// ================= Compare with Kip and Sauls ================= //

TEST_CASE("Compare with Kip and Sauls - Unitary, phase = pi/2 (float)") {
  const float scatteringPhaseShift = static_cast<float>(M_PI / 2.0);
  // They mention 0.4 in the paper. But I measure 52/128 ~ 0.41 from the plot.
  const float expectedDOS = 0.4f;
  helper::compareWithKipAndSauls<float>(scatteringPhaseShift, expectedDOS);
}

TEST_CASE("Compare with Kip and Sauls - Intermediate, phase = pi/3 (float)") {
  const float scatteringPhaseShift = static_cast<float>(M_PI / 3.0);
  const float expectedDOS = 45.0f / 128.0f;
  helper::compareWithKipAndSauls<float>(scatteringPhaseShift, expectedDOS);
}

TEST_CASE("Compare with Kip and Sauls - Intermediate, phase = pi/4 (float)") {
  const float scatteringPhaseShift = static_cast<float>(M_PI / 4.0);
  const float expectedDOS = 34.0f / 128.0f;
  helper::compareWithKipAndSauls<float>(scatteringPhaseShift, expectedDOS);
}

TEST_CASE("Compare with Kip and Sauls - Intermediate, phase = pi/20 (float)") {
  const float scatteringPhaseShift = static_cast<float>(M_PI / 20.0);
  const float expectedDOS = 24.0f / 128.0f;
  helper::compareWithKipAndSauls<float>(scatteringPhaseShift, expectedDOS);
}

// ================= Test DOS s-wave ================= //

TEST_CASE("Test DOS - s-wave (float)") {
  const float convergenceCriterion = 1e-4f;
  const bool useSwave = true;
  helper::testDensityOfStates<float>(useSwave, convergenceCriterion);
}

TEST_CASE("Test DOS - s-wave (double)") {
  // TODO(Niclas): For some reason it does not converge with 1e-7.
  const double convergenceCriterion = 1e-6;
  const bool useSwave = true;
  helper::testDensityOfStates<double>(useSwave, convergenceCriterion);
}

// ================= Test DOS d-wave ================= //

TEST_CASE("Test DOS - d-wave (float)") {
  // TODO(Niclas): Why is d-wave float always worse?
  const float convergenceCriterion = 1e-3f;
  const bool useSwave = false;
  helper::testDensityOfStates<float>(useSwave, convergenceCriterion);
}

TEST_CASE("Test DOS - d-wave (double)") {
  const double convergenceCriterion = 1e-7;
  const bool useSwave = false;
  helper::testDensityOfStates<double>(useSwave, convergenceCriterion);
}
