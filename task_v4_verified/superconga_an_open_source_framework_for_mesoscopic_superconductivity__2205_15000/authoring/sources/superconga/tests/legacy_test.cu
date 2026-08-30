#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN

#include "conga/compute/ComputeResidual.h"
#include "conga/compute/ComputeVectorPotential.h"
#include "conga/grid.h"
#include "conga/utils.h"
#include "conga/wrappers/doctest.h"

#include <thrust/host_vector.h>

#include <cmath>
#include <limits>

namespace helper {
namespace legacy {
namespace internal {
// Compute vector potential by integrating greens function kernel
template <typename T>
__global__ void computeVectorPotential2d_kernel(
    T *const inOutVectorPotentialX, T *const inOutVectorPotentialY,
    const T *const inCurrentDensityX, const T *const inCurrentDensityY,
    const int px, const int py, const T inLatticeSpacing, const int Nx) {
  // Coordinates to grid
  const int x = blockIdx.x * blockDim.x + threadIdx.x;
  const int y = blockIdx.y * blockDim.y + threadIdx.y;

  if (x < Nx && y < Nx) {
    // For convenience.
    const T latticeArea = inLatticeSpacing * inLatticeSpacing;

    T factor;
    if (x == px && y == py) {
      factor = static_cast<T>(0.25) * latticeArea *
               (static_cast<T>(M_PI - 6.0) +
                static_cast<T>(2.0) * log(latticeArea * static_cast<T>(0.5)));
    } else {
      const T dx = static_cast<T>(px - x);
      const T dy = static_cast<T>(py - y);
      factor = latticeArea * log(inLatticeSpacing * sqrt(dx * dx + dy * dy));
    }

    // Vector-potential index.
    const int idx = y * Nx + x;

    // Current-density index.
    const int idxp = py * Nx + px;

    inOutVectorPotentialX[idx] += factor * inCurrentDensityX[idxp];
    inOutVectorPotentialY[idx] += factor * inCurrentDensityY[idxp];
  }
}
} // namespace internal

template <typename T>
void computeVectorPotential(conga::GridGPU<T> &inOutVectorPotential,
                            const conga::GridGPU<T> &inCurrentDensity,
                            const conga::GridGPU<char> &inDomainLabels,
                            const T inLatticeSpacing) {
  // Set to zero because we'll add stuff to it.
  inOutVectorPotential.setZero();

  // Get the required kernel dimensions.
  const auto [bpg, tpb] = inOutVectorPotential.getKernelDimensions();

  const int N = inOutVectorPotential.dimX();

  // Get the thrust-vector from the domain labels, and copy to the CPU.
  const thrust::host_vector<char> &domainLabelsCPU = inDomainLabels.getVector();
  const char *const domainLabelsPtr =
      thrust::raw_pointer_cast(domainLabelsCPU.data());

  for (int y = 0; y < N; ++y) {
    for (int x = 0; x < N; ++x) {
      if (domainLabelsPtr[y * N + x] > 0) {
        internal::computeVectorPotential2d_kernel<<<bpg, tpb>>>(
            inOutVectorPotential.getDataPointer(0),
            inOutVectorPotential.getDataPointer(1),
            inCurrentDensity.getDataPointer(0),
            inCurrentDensity.getDataPointer(1), x, y, inLatticeSpacing, N);
      }
    }
  }

  // Factor from the equation itself.
  const T equationFactor = -static_cast<T>(1.0);

  // Factor from the Green function.
  const T greenFactor = static_cast<T>(1) / static_cast<T>(2.0 * M_PI);

  // Scale the result appropriately.
  inOutVectorPotential *= equationFactor * greenFactor;
}
} // namespace legacy

// A helper function to test legacy::computeVectorPotential.
template <typename T> void testComputeVectorPotential(const T inTolerance) {
  // =================== ARRANGE ==================== //
  // The number of lattice sites per side.
  const int N = 32;

  // Physical side length of a lattice cell.
  const T latticeSpacing = static_cast<T>(0.1);

  // The number of "fields" for the domain labels and the current density.
  const int domainDimension = 1;
  const int currentDimension = 2;

  // Set the domain labels to "1" everywhere.
  conga::GridGPU<char> domainLabels(N, N, domainDimension, conga::Type::real);
  domainLabels.setValue('1', conga::Type::real);

  // Construct the current density.
  conga::GridGPU<T> currenDensity(N, N, currentDimension, conga::Type::real);
  currenDensity.setValue(static_cast<T>(1), conga::Type::real);

  // =================== ACT ==================== //
  // Construct a vector-potential grid on the GPU.
  conga::GridGPU<T> vectorPotential(N, N, currentDimension, conga::Type::real);

  legacy::computeVectorPotential(vectorPotential, currenDensity, domainLabels,
                                 latticeSpacing);

  // =================== ASSERT ==================== //
  // The maximum error, in terms of relative Frobenius norm, of the
  // eigen-decomposition approximation.
  const T maxError = static_cast<T>(1e-6);

  // Whether to use the analytical expression for the matrix elements of the
  // Green function. This must be false, because we didn't have an analytical
  // implementation before.
  const T analytical = false;

  // Do not enforce current conservation.
  const bool enforceCurrentConservation = false;
  const int numGrainLatticeSites = N * N;

  // Compute the induced vector potential.
  conga::ComputeVectorPotential<T> computeVectorPotential(
      maxError, analytical, enforceCurrentConservation);
  computeVectorPotential.initialize(N, latticeSpacing, numGrainLatticeSites);
  computeVectorPotential.solve(currenDensity);

  conga::GridGPU<T> expVectorPotential = *(computeVectorPotential.getResult());

  const conga::ResidualNorm normType = conga::ResidualNorm::LInf;
  const T residual =
      conga::computeResidual(vectorPotential, expVectorPotential, normType);

  // Compare results.
  CHECK(residual < inTolerance);
}
} // namespace helper

// ================== Test computeVectorPotential ================== //

TEST_CASE("Test legacy::testComputeVectorPotential<float>") {
  const float tolerance = 1e-5F;
  helper::testComputeVectorPotential(tolerance);
}

TEST_CASE("Test legacy::testComputeVectorPotential<double>") {
  const double tolerance = 1e-8;
  helper::testComputeVectorPotential(tolerance);
}
