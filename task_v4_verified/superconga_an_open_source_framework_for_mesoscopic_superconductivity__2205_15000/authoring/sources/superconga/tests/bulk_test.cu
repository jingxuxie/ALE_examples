#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN

#include "conga/BulkSolver.h"
#include "conga/defines.h"
#include "conga/order_parameter/OrderParameterBasis.h"
#include "conga/utils.h"
#include "conga/wrappers/doctest.h"

// Helper for s-wave tests.
#include "conga/swave_bulk.h"

#include <cmath>
#include <limits>
#include <vector>

namespace helper {
// A helper function to test that compares the results for Matsubara and Ozaki
// energies.
template <typename T>
void testCompareOzakiMatsubara(const T inTolerance,
                               const T inConvergenceCriteria) {
  // =================== ARRANGE ==================== //
  const T temperature = static_cast<T>(0.5);
  const T energyCutoff = static_cast<T>(32);
  const int numFermiMomenta = 1;
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;

  // =================== ACT ==================== //
  std::vector<thrust::complex<T>> orderParameters;
  std::vector<bool> converged;
  for (const bool useOzaki : {true, false}) {
    conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta,
                                useOzaki);
    solver.addOrderParameterComponent(symmetry);
    const bool success = solver.compute(inConvergenceCriteria);
    converged.push_back(success);

    const thrust::complex<T> orderParameter =
        solver.orderParameterComponent(symmetry);
    orderParameters.push_back(orderParameter);
  }

  // =================== ASSERT ==================== //
  CHECK(orderParameters[0].real() ==
        doctest::Approx(orderParameters[1].real()).epsilon(inTolerance));
  CHECK(orderParameters[0].imag() ==
        doctest::Approx(orderParameters[1].imag()).epsilon(inTolerance));
  CHECK(converged[0]);
  CHECK(converged[1]);
}

// A helper function to test that the bulk order parameter solver gives
// the expected, analytical, result at (almost) zero temperature.
template <typename T>
void testOrderParameterZeroTemperature(const T inTolerance,
                                       const T inConvergenceCriteria,
                                       const conga::Symmetry inSymmetry) {
  // =================== ARRANGE ==================== //
  const T temperature = static_cast<T>(0.01);
  const T energyCutoff = static_cast<T>(64);
  const int numFermiMomenta = (inSymmetry == conga::Symmetry::SWAVE) ? 1 : 101;

  // =================== ACT ==================== //
  conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta);
  solver.addOrderParameterComponent(inSymmetry);
  const bool success = solver.compute(inConvergenceCriteria);
  const T orderParameter = solver.orderParameterMagnitude();

  // =================== ASSERT ==================== //
  const T orderParameterExpected =
      (inSymmetry == conga::Symmetry::SWAVE)
          ? static_cast<T>(conga::constants::S_WAVE_BULK)
          : static_cast<T>(conga::constants::D_WAVE_BULK);
  CHECK(orderParameter ==
        doctest::Approx(orderParameterExpected).epsilon(inTolerance));
  CHECK(success);
}

template <typename T>
void testChiralDWaveZeroTemperature(const T inTolerance,
                                    const T inConvergenceCriteria) {
  // =================== ARRANGE ==================== //
  const T temperature = static_cast<T>(0.01);
  const T energyCutoff = static_cast<T>(64);
  const int numFermiMomenta = 101;
  const T criticalTemperature = static_cast<T>(1);
  const T phaseShift = static_cast<T>(2.0 * M_PI * 0.25);

  // =================== ACT ==================== //
  conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta);
  solver.addOrderParameterComponent(conga::Symmetry::DWAVE_XY);
  solver.addOrderParameterComponent(conga::Symmetry::DWAVE_X2_Y2,
                                    criticalTemperature, phaseShift);
  const bool success = solver.compute(inConvergenceCriteria);
  const T orderParameter = solver.orderParameterMagnitude();

  // =================== ASSERT ==================== //
  // The total magnitude of the order parameter is the same as for s-wave.
  const T orderParameterExpected =
      static_cast<T>(conga::constants::S_WAVE_BULK);
  CHECK(orderParameter ==
        doctest::Approx(orderParameterExpected).epsilon(inTolerance));
  CHECK(success);
}

template <typename T>
void testSWaveWithImpurites(const T inTolerance,
                            const T inConvergenceCriteria) {
  // =================== ARRANGE ==================== //
  const T temperature = static_cast<T>(0.5);
  const T energyCutoff = static_cast<T>(64);
  const int numFermiMomenta = 1;
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;

  // Scattering energies.
  const std::vector<T> scatteringEnergies = {static_cast<T>(0),
                                             static_cast<T>(1)};

  // =================== ACT ==================== //
  std::vector<T> orderParameters;
  std::vector<bool> converged;
  for (const T scatteringEnergy : scatteringEnergies) {
    conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta);
    solver.scatteringEnergy(scatteringEnergy);
    solver.addOrderParameterComponent(symmetry);
    const bool success = solver.compute(inConvergenceCriteria);
    converged.push_back(success);
    const T orderParameter = solver.orderParameterMagnitude();
    orderParameters.push_back(orderParameter);
  }

  // =================== ASSERT ==================== //
  // An s-wave order parameter should not be suppressed by the impurity
  // scattering.
  CHECK(orderParameters[0] ==
        doctest::Approx(orderParameters[1]).epsilon(inTolerance));
  CHECK(converged[0]);
  CHECK(converged[1]);
}

template <typename T> void testDWaveWithImpuritesKillingOP() {
  // =================== ARRANGE ==================== //
  const T temperature = static_cast<T>(0.05);
  const T energyCutoff = static_cast<T>(16);
  const int numFermiMomenta = 32;
  const T convergenceCriterion = static_cast<T>(1e-5);
  const conga::Symmetry symmetry = conga::Symmetry::DWAVE_X2_Y2;

  // Scattering energies.
  // The scattering energy, at low temperature, where the grain stops being
  // superconducting is roughly Gamma = 0.14*2*pi*kB*Tc according to Sauls.
  // See inset of Fig. 5 in https://arxiv.org/abs/cond-mat/9502110
  const T limit = static_cast<T>(0.14);
  const std::vector<T> scatteringEnergies = {static_cast<T>(0.9) * limit,
                                             static_cast<T>(1.1) * limit};

  for (const T scatteringEnergy : scatteringEnergies) {
    // =================== ACT ==================== //
    conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta);
    solver.scatteringEnergy(scatteringEnergy);
    solver.addOrderParameterComponent(symmetry);
    const bool success = solver.compute(convergenceCriterion);
    const T orderParameter = solver.orderParameterMagnitude();

    // =================== ASSERT ==================== //
    // Compare results.
    if (scatteringEnergy > limit) {
      CHECK(orderParameter < convergenceCriterion);
    } else {
      // Just some "large" number. The order parameter should be finite.
      CHECK(orderParameter > static_cast<T>(0.05));
    }
    CHECK(success);
  }
}

template <typename T> void testDWaveWithImpuritesBornVsUnitary() {
  // =================== ARRANGE ==================== //
  const T temperature = static_cast<T>(0.01);
  const T energyCutoff = static_cast<T>(16);
  const int numFermiMomenta = 32;
  const T convergenceCriterion = static_cast<T>(1e-5);
  const T scatteringEnergy = static_cast<T>(0.1);
  const conga::Symmetry symmetry = conga::Symmetry::DWAVE_X2_Y2;

  // Scattering phase shifts.
  const std::vector<T> scatteringPhaseShifts = {static_cast<T>(0),
                                                static_cast<T>(0.5 * M_PI)};

  // =================== ACT ==================== //
  std::vector<T> orderParameters;
  std::vector<bool> converged;
  for (const T scatteringPhaseShift : scatteringPhaseShifts) {
    conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta);
    solver.scatteringEnergy(scatteringEnergy);
    solver.scatteringPhaseShift(scatteringPhaseShift);
    solver.addOrderParameterComponent(symmetry);
    const bool success = solver.compute(convergenceCriterion);
    converged.push_back(success);
    const T orderParameter = solver.orderParameterMagnitude();
    orderParameters.push_back(orderParameter);
  }

  // =================== ASSERT ==================== //
  // In the unitary limit the order parameter is more suppressed than in the
  // Born limit. See Fig. 5 in https://arxiv.org/abs/cond-mat/9502110
  const T ratioExpected = static_cast<T>(1.17 / 0.89);
  const T ratio = orderParameters[0] / orderParameters[1];
  const T tolerance = static_cast<T>(1e-4);
  CHECK(ratio == doctest::Approx(ratioExpected).epsilon(tolerance));
  CHECK(converged[0]);
  CHECK(converged[1]);
}

// A helper function to test that the s-wave bulk order parameter solver gives
// the expected, analytical, result at the critical temperature.
template <typename T>
void testComputeOrderParameterBulkSWaveCriticalTemperature(
    const T inTolerance, const T inConvergenceCriteria) {
  // =================== ARRANGE ==================== //
  const T temperature = static_cast<T>(1.0);
  const T energyCutoff = static_cast<T>(64);
  const int numFermiMomenta = 1;
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;

  // =================== ACT ==================== //
  conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta);
  solver.addOrderParameterComponent(symmetry);
  const bool success = solver.compute(inConvergenceCriteria);
  const T orderParameter = solver.orderParameterMagnitude();

  // =================== ASSERT ==================== //
  const T orderParameterExpected = static_cast<T>(0.0);
  CHECK(orderParameter ==
        doctest::Approx(orderParameterExpected).epsilon(inTolerance));
  CHECK(success);
}

// A helper function to test that the s-wave bulk order parameter solver gives
// approximately the right answer close to the critical temperature.
template <typename T>
void testComputeOrderParameterBulkSWaveIntermediateTemperature(
    const T inTolerance, const T inConvergenceCriteria,
    const T inMinTemperature = static_cast<T>(0.99),
    const T inMaxTemperature = static_cast<T>(0.999999),
    const int inNumTemperatures = 10) {
  // =================== ARRANGE ==================== //
  const std::vector<T> temperatures = conga::utils::linspace(
      inMinTemperature, inMaxTemperature, inNumTemperatures);
  const T energyCutoff = static_cast<T>(64);
  const int numFermiMomenta = 1;
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;

  // See page 180 of P. Holmvall lic thesis.
  // Note that we are using 2*pi*kB*Tc as our energy scale.
  // The value of the Riemann zeto function evaluated at 3, i.e. Apery's
  // constant = zeta(3).
  // https://en.wikipedia.org/wiki/Ap%C3%A9ry's_constant
  const T apery = static_cast<T>(std::riemann_zeta(3));
  const T preFactor =
      std::sqrt(static_cast<T>(2) / (static_cast<T>(7) * apery));

  for (const T &temperature : temperatures) {
    // =================== ACT ==================== //
    conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta);
    solver.addOrderParameterComponent(symmetry);
    const bool success = solver.compute(inConvergenceCriteria);
    const T orderParameter = solver.orderParameterMagnitude();

    // =================== ASSERT ==================== //
    // See page 180 of P. Holmvall lic thesis.
    // Note that this apprixmation is only valid very close to the critical
    // temperature.
    const T orderParameterExpected =
        preFactor * std::sqrt(static_cast<T>(1.0) - temperature);
    CHECK(orderParameter ==
          doctest::Approx(orderParameterExpected).epsilon(inTolerance));
    CHECK(success);
  }
}

// A helper function to test that the s-wave bulk free energy gives
// the expected value.
template <typename T>
void testComputeFreeEnergyBulkSWave(const T inTolerance, const T inTemperature,
                                    const T inFreeEnergyExpected) {
  // =================== ARRANGE ==================== //
  const T energyCutoff = static_cast<T>(64);
  const int numFermiMomenta = 1;
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;
  const T convergenceCriteria = static_cast<T>(1e-6);

  conga::BulkSolver<T> solver(inTemperature, energyCutoff, numFermiMomenta);
  solver.addOrderParameterComponent(symmetry);
  const bool success = solver.compute(convergenceCriteria);
  const T orderParameter = solver.orderParameterMagnitude();

  // =================== ACT ==================== //
  const T freeEnergy =
      conga::computeFreeEnergyBulkSWave(inTemperature, orderParameter);

  // =================== ASSERT ==================== //
  CHECK(freeEnergy ==
        doctest::Approx(inFreeEnergyExpected).epsilon(inTolerance));
  CHECK(success);
}

// A helper function to test that the s-wave bulk order parameter and free
// energy are consistent with each other. For a certain temperature, compute the
// order parameter, then check that the free energy has a minimum at that order
// parameter and temperature.
template <typename T>
void testComputeFreeEnergyBulkSWaveMinima(
    const T inMinTemperature = static_cast<T>(0.1),
    const T inMaxTemperature = static_cast<T>(0.9),
    const int inNumTemperatures = 10) {
  // =================== ARRANGE ==================== //
  const std::vector<T> temperatures = conga::utils::linspace(
      inMinTemperature, inMaxTemperature, inNumTemperatures);

  const T energyCutoff = static_cast<T>(64);
  const int numFermiMomenta = 1;
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;
  const T convergenceCriteria = static_cast<T>(1e-6);

  // A small value to add to the order parameter.
  const T epsilon = static_cast<T>(1e-3);

  for (const T temperature : temperatures) {
    conga::BulkSolver<T> solver(temperature, energyCutoff, numFermiMomenta);
    solver.addOrderParameterComponent(symmetry);
    const bool success = solver.compute(convergenceCriteria);
    const T orderParameter = solver.orderParameterMagnitude();

    // =================== ACT ==================== //
    const T freeEnergy =
        conga::computeFreeEnergyBulkSWave(temperature, orderParameter);

    // =================== ASSERT ==================== //
    const T freeEnergyPlus = conga::computeFreeEnergyBulkSWave(
        temperature, orderParameter + epsilon);
    const T freeEnergyMinus = conga::computeFreeEnergyBulkSWave(
        temperature, orderParameter - epsilon);
    CHECK(freeEnergy < freeEnergyPlus);
    CHECK(freeEnergy < freeEnergyMinus);
    CHECK(success);
  }
}
} // namespace helper

// ============== Test Ozaki vs Matsubara ============== //

TEST_CASE("Test Ozaki vs Matsubara <float>") {
  const float tolerance = 1e-5F;
  const float convergenceCriteria = 1e-8f;
  helper::testCompareOzakiMatsubara(tolerance, convergenceCriteria);
}

TEST_CASE("Test Ozaki vs Matsubara <double>") {
  const double tolerance = 1e-5;
  const double convergenceCriteria = 1e-8;
  helper::testCompareOzakiMatsubara(tolerance, convergenceCriteria);
}

// ============== Test s-wave orderparameter @ T = 0 ============== //

TEST_CASE("Test s-wave orderparameter @ T = 0 <float>") {
  const float tolerance = 1e-5F;
  const float convergenceCriteria = 1e-8f;
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;
  helper::testOrderParameterZeroTemperature(tolerance, convergenceCriteria,
                                            symmetry);
}

TEST_CASE("Test s-wave orderparameter @ T = 0 <double>") {
  const double tolerance = 1e-6;
  const double convergenceCriteria = 1e-8;
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;
  helper::testOrderParameterZeroTemperature(tolerance, convergenceCriteria,
                                            symmetry);
}

// ============== Test d-wave orderparameter @ T = 0 ============== //

TEST_CASE("Test d-wave orderparameter @ T = 0 <float>") {
  const float tolerance = 1e-5F;
  const float convergenceCriteria = 1e-8f;
  const conga::Symmetry symmetry = conga::Symmetry::DWAVE_XY;
  helper::testOrderParameterZeroTemperature(tolerance, convergenceCriteria,
                                            symmetry);
}

TEST_CASE("Test d-wave orderparameter @ T = 0 <double>") {
  const double tolerance = 1e-6;
  const double convergenceCriteria = 1e-8;
  const conga::Symmetry symmetry = conga::Symmetry::DWAVE_XY;
  helper::testOrderParameterZeroTemperature(tolerance, convergenceCriteria,
                                            symmetry);
}

// ============== Test chiral d-wave orderparameter @ T = 0 ============== //

TEST_CASE("Test chiral d-wave orderparameter @ T = 0 <float>") {
  const float tolerance = 1e-5F;
  const float convergenceCriteria = 1e-8f;
  helper::testChiralDWaveZeroTemperature(tolerance, convergenceCriteria);
}

TEST_CASE("Test chiral d-wave orderparameter @ T = 0 <double>") {
  const double tolerance = 1e-6;
  const double convergenceCriteria = 1e-8;
  helper::testChiralDWaveZeroTemperature(tolerance, convergenceCriteria);
}

// ======== Test s-wave orderparameter with impurites @ T = 0.5 ======== //

TEST_CASE("Test s-wave orderparameter with impurites @ T = 0.5 <float>") {
  const float tolerance = 1e-5F;
  const float convergenceCriteria = 1e-8f;
  helper::testSWaveWithImpurites(tolerance, convergenceCriteria);
}

TEST_CASE("Test s-wave orderparameter with impurites @ T = 0.5 <double>") {
  const double tolerance = 1e-6;
  const double convergenceCriteria = 1e-8;
  helper::testSWaveWithImpurites(tolerance, convergenceCriteria);
}

// ======== Test d-wave impurites killing OP @ T = 0 ======== //

TEST_CASE("Test d-wave impurites killing OP @ T = 0 <float>") {
  helper::testDWaveWithImpuritesKillingOP<float>();
}

TEST_CASE("Test d-wave impurites killing OP @ T = 0 <double>") {
  helper::testDWaveWithImpuritesKillingOP<double>();
}

// ======== Test d-wave impurites Born vs Unitary @ T = 0 ======== //

TEST_CASE("Test d-wave impurites Born vs Unitary @ T = 0 <float>") {
  helper::testDWaveWithImpuritesBornVsUnitary<float>();
}

TEST_CASE("Test d-wave impurites Born vs Unitary @ T = 0 <double>") {
  helper::testDWaveWithImpuritesBornVsUnitary<double>();
}

// ============== Test s-wave orderparameter @ T = 1 ============== //

TEST_CASE("Test s-wave orderparameter @ T = 1 <float>") {
  const float tolerance = 1e-6F;
  const float convergenceCriteria = 1e-8f;
  helper::testComputeOrderParameterBulkSWaveCriticalTemperature(
      tolerance, convergenceCriteria);
}

TEST_CASE("Test s-wave orderparameter @ T = 1 <double>") {
  const double tolerance = 1e-6;
  const double convergenceCriteria = 1e-8;
  helper::testComputeOrderParameterBulkSWaveCriticalTemperature(
      tolerance, convergenceCriteria);
}

// ============== Test computeOrderParameterBulkSWave - T < 1 ============== //

TEST_CASE("Test computeOrderParameterBulkSWave<float> - T < 1") {
  // Note, that we are testing temperatures quite far from Tc. Hence the large
  // tolerance.
  const float tolerance = 0.002F;
  const float convergenceCriteria = 1e-8f;
  helper::testComputeOrderParameterBulkSWaveIntermediateTemperature(
      tolerance, convergenceCriteria);
}

TEST_CASE("Test computeOrderParameterBulkSWave<double> - T < 1") {
  // Note, that we are testing temperatures quite far from Tc. Hence the large
  // tolerance.
  const double tolerance = 0.001;
  const double convergenceCriteria = 1e-8;
  helper::testComputeOrderParameterBulkSWaveIntermediateTemperature(
      tolerance, convergenceCriteria);
}

// ============== Test computeFreeEnergyBulkSWave - T = 0 ============== //

TEST_CASE("Test computeFreeEnergyBulkSWave<float> - T = 0") {
  const float tolerance = 1e-6F;
  const float temperature = 0.001F;
  const float freeEnergyExpected =
      -0.5F * static_cast<float>(conga::constants::S_WAVE_BULK *
                                 conga::constants::S_WAVE_BULK);
  helper::testComputeFreeEnergyBulkSWave(tolerance, temperature,
                                         freeEnergyExpected);
}

TEST_CASE("Test computeFreeEnergyBulkSWave<double> - T = 0") {
  const double tolerance = 1e-6;
  const double temperature = 0.001;
  const double freeEnergyExpected =
      -0.5 * conga::constants::S_WAVE_BULK * conga::constants::S_WAVE_BULK;
  helper::testComputeFreeEnergyBulkSWave(tolerance, temperature,
                                         freeEnergyExpected);
}

// ============== Test computeFreeEnergyBulkSWave - T = 1 ============== //

TEST_CASE("Test computeFreeEnergyBulkSWave<float> - T = 1") {
  const float tolerance = 1e-6F;
  const float temperature = 1.0F;
  const float freeEnergyExpected = 0.0F;
  helper::testComputeFreeEnergyBulkSWave(tolerance, temperature,
                                         freeEnergyExpected);
}

TEST_CASE("Test computeFreeEnergyBulkSWave<double> - T = 1") {
  const double tolerance = 1e-6;
  const double temperature = 1.0;
  const double freeEnergyExpected = 0.0;
  helper::testComputeFreeEnergyBulkSWave(tolerance, temperature,
                                         freeEnergyExpected);
}

// ============== Test computeFreeEnergyBulkSWave - Minima ============== //

TEST_CASE("Test computeFreeEnergyBulkSWave<float> - Minima") {
  helper::testComputeFreeEnergyBulkSWaveMinima<float>();
}

TEST_CASE("Test computeFreeEnergyBulkSWave<double> - Minima") {
  helper::testComputeFreeEnergyBulkSWaveMinima<double>();
}
