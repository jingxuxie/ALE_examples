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
#include "conga/geometry/GeometryGroup.h"
#include "conga/geometry/PolygonGeometry.h"
#include "conga/grid.h"
#include "conga/integration/IntegrationIteratorOzaki.h"
#include "conga/order_parameter/OrderParameter.h"
#include "conga/riccati/RiccatiSolverConfined.h"
#include "conga/run_iteration.h"
#include "conga/utils.h"
#include "conga/wrappers/doctest.h"

#include <vector>

namespace helper {
/// \brief Test that a d-wave grain without pair-breaking edges.
///
/// \return Void.
template <typename T> void testImpurities() {
  // =================== ARRANGE ==================== //
  // The accuracy of the test.
  const T tolerance = static_cast<T>(1e-3);
  const T scale = static_cast<T>(0);

  // Max number of iterations.
  const int maxIterations = 100;

  // General parameters.
  const T temperature = static_cast<T>(0.5);
  const T grainWidth = static_cast<T>(10);
  const T pointsPerCoherenceLength = static_cast<T>(2);
  const int numMomenta = 32;
  const T convergenceCriterion = static_cast<T>(1e-5);
  const T energyCutoff = static_cast<T>(16);
  const T scatteringEnergy = static_cast<T>(0.01);
  const T scatteringPhaseShift = static_cast<T>(0.1);
  const conga::ResidualNorm normType = conga::ResidualNorm::L2;
  const conga::Symmetry symmetry = conga::Symmetry::DWAVE_X2_Y2;

  // =================== ACT ==================== //
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
  parameters->setScatteringEnergy(scatteringEnergy);
  parameters->setScatteringPhaseShift(scatteringPhaseShift);
  parameters->setResidualNormType(normType);

  // Create square geometry.
  conga::GeometryGroup<T> *geometry = new conga::GeometryGroup<T>(&context);
  const T grainFraction = parameters->getGrainFraction();
  const int numVerticesSquare = 4;
  const T sideLength = static_cast<T>(1);
  geometry->add(new conga::PolygonGeometry<T>(grainFraction, numVerticesSquare,
                                              sideLength),
                conga::Type::add);

  // Integrator.
  new conga::IntegrationIteratorOzaki<T>(&context);

  // Create solver with radial gauge.
  conga::RiccatiSolver<T> *riccatiSolver =
      new conga::RiccatiSolverConfined<T, conga::gauge::Symmetric>(&context);
  riccatiSolver->add(new conga::BoundaryConditionSpecular<T>);

  // Solve the bulk problem.
  conga::BulkSolver<T> bulkSolver(parameters->getTemperature(),
                                  parameters->getEnergyCutoff(),
                                  parameters->getAngularResolution());
  bulkSolver.scatteringEnergy(parameters->getScatteringEnergy());
  bulkSolver.scatteringPhaseShift(parameters->getScatteringPhaseShift());
  bulkSolver.addOrderParameterComponent(symmetry);
  const bool bulkConverged =
      bulkSolver.compute(parameters->getConvergenceCriterion());
  REQUIRE(bulkConverged);

  // Create d-wave order parameter.
  conga::OrderParameter<T> *orderParameter =
      new conga::OrderParameter<T>(&context);
  conga::ComponentOptions<T> options(symmetry);
  options.initialValue(bulkSolver.orderParameterComponent(symmetry));
  orderParameter->addComponent(options);

  // Set the impurity self-energy.
  {
    const int gridResolution = parameters->getGridResolutionBase();
    const int numEnergies = parameters->getNumOzakiEnergies();
    auto impuritySelfEnergy = std::make_unique<conga::ImpuritySelfEnergy<T>>(
        gridResolution, gridResolution, numEnergies);
    const auto [impSigma, impDelta, impDeltaTilde] = bulkSolver.impuritySelfEnergy();
    impuritySelfEnergy->set(impSigma, impDelta, impDeltaTilde);
  }

  new conga::ComputeOrderParameter<T>(&context);
  new conga::ComputeImpuritySelfEnergy<T>(&context);

  // Set accelerator.
  context.set(std::make_unique<conga::accelerators::BarzilaiBorwein<T>>());

  // Run the simulation.
  context.initialize();
  const bool isConverged = conga::runCompute(0, maxIterations, true, context);

  // Save the result.
  const int numGrainLatticeSites =
      context.getGeometry()->getNumGrainLatticeSites();
  const T averageOrderParameter = context.getOrderParameter()->sumMagnitude() /
                                  static_cast<T>(numGrainLatticeSites);

  // =================== ASSERT ==================== //
  // Compare results.
  const T orderParameterBulk = bulkSolver.orderParameterMagnitude();
  CHECK(averageOrderParameter ==
        doctest::Approx(orderParameterBulk).epsilon(tolerance).scale(scale));

  // Check convergence.
  CHECK(isConverged);
}
} // namespace helper

TEST_CASE("Test impurities - <float>") { helper::testImpurities<float>(); }

TEST_CASE("Test impurities - <double>") { helper::testImpurities<double>(); }
