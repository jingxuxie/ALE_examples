#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN

#include "conga/BulkSolver.h"
#include "conga/Context.h"
#include "conga/Parameters.h"
#include "conga/Type.h"
#include "conga/accelerators/BarzilaiBorwein.h"
#include "conga/boundary/BoundaryConditionSpecular.h"
#include "conga/compute/ComputeCurrent.h"
#include "conga/compute/ComputeFreeEnergy.h"
#include "conga/compute/ComputeImpuritySelfEnergy.h"
#include "conga/compute/ComputeOrderParameter.h"
#include "conga/defines.h"
#include "conga/geometry/DiscGeometry.h"
#include "conga/geometry/GeometryGroup.h"
#include "conga/grid.h"
#include "conga/integration/IntegrationIteratorOzaki.h"
#include "conga/order_parameter/OrderParameter.h"
#include "conga/riccati/RiccatiSolverConfined.h"
#include "conga/utils.h"
#include "conga/wrappers/doctest.h"

#include <cmath>

namespace helper {
/// \brief Test that the order paramater has the expected momentum dependence
/// and magnitude.
///
/// \return Void.
template <typename T> void testOrderParameter() {
  // =================== ARRANGE ====================
  // Test the order parameter for a chiral d-wave at a particular momentum.
  const std::vector<conga::Symmetry> symmetries = {
      conga::Symmetry::DWAVE_XY, conga::Symmetry::DWAVE_X2_Y2};
  const T angle = static_cast<T>(0.666 * M_PI);
  const T momentumX = std::cos(angle);
  const T momentumY = std::sin(angle);
  const T tolerance = static_cast<T>(1e-7);

  // General parameters.
  const T grainWidth = static_cast<T>(10);
  const T pointsPerCoherenceLength = static_cast<T>(1.0);
  const int numMomenta = 16;
  const T convergenceCriterion = static_cast<T>(1e-5);
  const T temperature = static_cast<T>(0.9);
  const T energyCutoff = static_cast<T>(16);

  // Create context.
  conga::Context<T> context;

  // Set parameters.
  conga::Parameters<T> *parameters = new conga::Parameters<T>(&context);
  parameters->setGrainWidth(grainWidth);
  parameters->setPointsPerCoherenceLength(pointsPerCoherenceLength);
  parameters->setAngularResolution(numMomenta);
  parameters->setConvergenceCriterion(convergenceCriterion);
  parameters->setTemperature(temperature);
  parameters->setEnergyCutoff(energyCutoff);

  // Create disc geometry.
  conga::GeometryGroup<T> *geometry = new conga::GeometryGroup<T>(&context);
  const T grainFraction = parameters->getGrainFraction();
  geometry->add(new conga::DiscGeometry<T>(grainFraction), conga::Type::add);

  // Integrator.
  new conga::IntegrationIteratorOzaki<T>(&context);

  // Create solver.
  conga::RiccatiSolver<T> *riccatiSolver =
      new conga::RiccatiSolverConfined<T, conga::gauge::Symmetric>(&context);
  riccatiSolver->add(new conga::BoundaryConditionSpecular<T>);

  // Solve the bulk problem.

  conga::BulkSolver<T> bulkSolver(parameters->getTemperature(),
                                  parameters->getEnergyCutoff(),
                                  parameters->getAngularResolution());
  for (int i = 0; i < 2; ++i) {
    const T criticalTemperature = static_cast<T>(1);
    const T phaseShift = static_cast<T>(i) * static_cast<T>(0.5 * M_PI);
    bulkSolver.addOrderParameterComponent(symmetries[i], criticalTemperature,
                                          phaseShift);
  }
  const bool bulkConverged =
      bulkSolver.compute(parameters->getConvergenceCriterion());
  REQUIRE(bulkConverged);

  // Create s-wave order parameter with phase winding.
  conga::OrderParameter<T> *orderParameter =
      new conga::OrderParameter<T>(&context);
  for (const auto symmetry : symmetries) {
    conga::ComponentOptions<T> options(symmetry);
    options.initialValue(bulkSolver.orderParameterComponent(symmetry));
    orderParameter->addComponent(options);
  }

  context.initialize();

  // =================== ACT ==================== //
  const int numGrainLatticeSites = geometry->getNumGrainLatticeSites();
  const T invNumGrainLatticeSites =
      static_cast<T>(1) / static_cast<T>(numGrainLatticeSites);

  // The average magnitude.
  const T testAverageMagnitude =
      orderParameter->sumMagnitude() * invNumGrainLatticeSites;

  // The average value for a particular Fermi momentum.
  T real;
  T imag;
  orderParameter->getMomentumDependentGrid(momentumX, momentumY)
      .sumField(real, imag);
  const thrust::complex<T> testAverageMomentumDependence(
      real * invNumGrainLatticeSites, imag * invNumGrainLatticeSites);

  // =================== ASSERT ==================== //
  const T expectedAverageOrderParameter = bulkSolver.orderParameterMagnitude();
  CHECK(testAverageMagnitude ==
        doctest::Approx(expectedAverageOrderParameter).epsilon(tolerance));

  // Compute expected momentum dependence.
  const conga::FermiSurface<T> *const fermiSurface = context.getFermiSurface();
  thrust::complex<T> expectedAverageMomentumDependence(static_cast<T>(0));
  for (const auto symmetry : symmetries) {
    const conga::BasisFunction<T> basisFunction(symmetry, fermiSurface);
    expectedAverageMomentumDependence +=
        bulkSolver.orderParameterComponent(symmetry) *
        basisFunction.evaluate(momentumX, momentumY);
  }

  CHECK(testAverageMomentumDependence.real() ==
        doctest::Approx(expectedAverageMomentumDependence.real())
            .epsilon(tolerance));
  CHECK(testAverageMomentumDependence.imag() ==
        doctest::Approx(expectedAverageMomentumDependence.imag())
            .epsilon(tolerance));
}
} // namespace helper

TEST_CASE("Test order parameter - <float>") {
  helper::testOrderParameter<float>();
}

TEST_CASE("Test order parameter - <double>") {
  helper::testOrderParameter<double>();
}
