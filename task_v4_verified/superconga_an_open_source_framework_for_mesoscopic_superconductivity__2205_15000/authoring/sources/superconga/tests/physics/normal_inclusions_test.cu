#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN

#include "conga/BulkSolver.h"
#include "conga/Context.h"
#include "conga/Parameters.h"
#include "conga/accelerators/BarzilaiBorwein.h"
#include "conga/boundary/BoundaryConditionSpecular.h"
#include "conga/compute/ComputeCurrent.h"
#include "conga/compute/ComputeFreeEnergy.h"
#include "conga/compute/ComputeImpuritySelfEnergy.h"
#include "conga/compute/ComputeOrderParameter.h"
#include "conga/defines.h"
#include "conga/geometry/DiscGeometry.h"
#include "conga/geometry/GeometryGroup.h"
#include "conga/geometry/PolygonGeometry.h"
#include "conga/grid.h"
#include "conga/integration/IntegrationIteratorOzaki.h"
#include "conga/order_parameter/OrderParameter.h"
#include "conga/riccati/RiccatiSolverConfined.h"
#include "conga/run_iteration.h"
#include "conga/utils.h"
#include "conga/wrappers/doctest.h"

#include <iostream>
#include <limits>
#include <stdlib.h>
#include <vector>

namespace helper {
template <typename T> void testNormalInclusions() {
  // =================== ARRANGE ==================== //
  // Create Context
  conga::Context<T> context;

  // Winding number of vortex.
  const T windingNumber = static_cast<T>(-1);

  // Parameters for the normal inclusion. Note that the center is in the
  // internal coordinates [-0.5, 0.5].
  const T radius = static_cast<T>(0.05);
  const T strength = static_cast<T>(0.5);
  const conga::vector2d<T> center = {static_cast<T>(0.1), static_cast<T>(0)};

  // Set parameters.
  conga::Parameters<T> *parameters = new conga::Parameters<T>(&context);
  parameters->setGrainWidth(static_cast<T>(10));
  parameters->setPointsPerCoherenceLength(static_cast<T>(5));
  parameters->setAngularResolution(32);
  parameters->setConvergenceCriterion(static_cast<T>(1e-4));
  parameters->setTemperature(static_cast<T>(0.5));
  parameters->setEnergyCutoff(static_cast<T>(16));
  parameters->setNumFluxQuanta(static_cast<T>(1.5));
  parameters->setResidualNormType(conga::ResidualNorm::LInf);

  // Create geometry group: add/remove geometry objects (e.g. discs, polygons)
  // from the geometry group
  conga::GeometryGroup<T> *geometry = new conga::GeometryGroup<T>(&context);
  const T grainFraction = parameters->getGrainFraction();
  geometry->add(new conga::DiscGeometry<T>(grainFraction), conga::Type::add);

  // Integrator.
  new conga::IntegrationIteratorOzaki<T>(&context);

  // Choose a Riccati solver for a confined geometry.
  conga::RiccatiSolver<T> *riccatiSolver =
      new conga::RiccatiSolverConfined<T, conga::gauge::Symmetric>(&context);
  // Add specular BC
  riccatiSolver->add(new conga::BoundaryConditionSpecular<T>);

  // Solve the bulk problem.
  const conga::Symmetry symmetry = conga::Symmetry::SWAVE;
  conga::BulkSolver<T> bulkSolver(parameters->getTemperature(),
                                  parameters->getEnergyCutoff(),
                                  parameters->getAngularResolution());
  bulkSolver.addOrderParameterComponent(symmetry);
  const bool bulkConverged =
      bulkSolver.compute(parameters->getConvergenceCriterion());
  REQUIRE(bulkConverged);

  // Set up order parameter
  conga::OrderParameter<T> *orderParameter =
      new conga::OrderParameter<T>(&context);
  conga::ComponentOptions<T> options(symmetry);
  options.initialValue(bulkSolver.orderParameterComponent(symmetry));
  options.vortices({conga::Vortex<T>(windingNumber)});
  options.normalInclusions(
      {conga::NormalInclusion<T>(radius, strength).center(center)});
  orderParameter->addComponent(options);

  // Create compute objects
  // Order parameter compute object.
  new conga::ComputeOrderParameter<T>(&context);

  // Set accelerator.
  auto accelerator =
      std::make_unique<conga::accelerators::BarzilaiBorwein<T>>();
  context.set(std::move(accelerator));

  // =================== ACT ==================== //
  context.initialize();
  const bool isConverged = conga::runCompute(1, 666, true, context);

  // Get the domain and order-parameter magnitude so we can locate the minimum
  // within the grain.
  const conga::GridCPU<char> domain = *(geometry->getDomainGrid());
  const conga::GridCPU<T> magnitude =
      orderParameter->getComponentGrid(0)->abs();

  // For storing the position of the minimum.
  conga::vector2d<T> minPosition = {static_cast<T>(0), static_cast<T>(0)};
  T minVal = std::numeric_limits<T>::max();

  // Loop over the entire grid and find the position of the miniumum.
  const char *const domainPtr = domain.getDataPointer();
  const T *const magnitudePtr = magnitude.getDataPointer();
  const int dimX = domain.dimX();
  const int dimY = domain.dimY();
  for (int j = 0; j < dimY; ++j) {
    for (int i = 0; i < dimX; ++i) {
      const int idx = j * dimX + i;
      if (domainPtr[idx] > 0) {
        const T val = magnitudePtr[idx];
        if (val < minVal) {
          minVal = val;
          minPosition[0] = conga::utils::indexToInternal<T>(i, dimX);
          minPosition[1] = conga::utils::indexToInternal<T>(j, dimY);
        }
      }
    }
  }

  // =================== ASSERT ==================== //
  // Check that the minimum is lower than just the normal inclusion suppression.
  const T limit =
      bulkSolver.orderParameterMagnitude() * (static_cast<T>(1) - strength);
  CHECK(minVal < limit);
  // Check that the minimum lies within the normal inclusion.
  CHECK(std::hypot(minPosition[0] - center[0], minPosition[1] - center[1]) <
        radius);
  CHECK(isConverged);
}
} // namespace helper

// ================= Test normal inclusions ================= //

TEST_CASE("Test normal inclusion - (float)") {
  helper::testNormalInclusions<float>();
}

TEST_CASE("Test normal inclusion - (double)") {
  helper::testNormalInclusions<double>();
}
