#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN

#include "conga/green/LocalGreens.h"
#include "conga/riccati/RiccatiSolutions.h"
#include "conga/wrappers/doctest.h"

#include <thrust/complex.h>

#include <limits>

namespace helper {
// Factor of machine precision for the tolerance of tests.
const double TOLERANCE_FACTOR = 10.0;
const double SCALE = 0.01;

/// \brief Test Green function element 'g'.
///
/// \return Void.
template <typename T> void testGreen() {
  // =================== ARRANGE ==================== //
  const thrust::complex<T> energy(static_cast<T>(1), static_cast<T>(3));
  const thrust::complex<T> orderParameter(static_cast<T>(4),
                                          static_cast<T>(-1));

  const auto [gamma, gammaTilde] = conga::riccati::computeHomogeneous(
      energy, orderParameter, thrust::conj(orderParameter));

  // =================== ACT ==================== //
  // Compute the Green function element 'g'.
  const thrust::complex<T> result =
      conga::Greens<T>::compute(gamma, gammaTilde);

  // =================== ASSERT ==================== //
  // The expected value with bulk coherence functions.
  const thrust::complex<T> expected =
      -energy / thrust::sqrt(thrust::norm(orderParameter) - energy * energy);

  // Check.
  const T tolerance = static_cast<float>(TOLERANCE_FACTOR) *
                      std::numeric_limits<float>::epsilon();
  const T scale = static_cast<T>(SCALE);
  CHECK(result.real() ==
        doctest::Approx(expected.real()).epsilon(tolerance).scale(scale));
  CHECK(result.imag() ==
        doctest::Approx(expected.imag()).epsilon(tolerance).scale(scale));
}

/// \brief Test Green function elements (f + tilde(f)^*)/2.
///
/// \return Void.
template <typename T> void testGreenAnomalousMean() {
  // =================== ARRANGE ==================== //
  const thrust::complex<T> energy(static_cast<T>(1), static_cast<T>(3));
  const thrust::complex<T> orderParameter(static_cast<T>(4),
                                          static_cast<T>(-1));

  const auto [gamma, gammaTilde] = conga::riccati::computeHomogeneous(
      energy, orderParameter, thrust::conj(orderParameter));

  // =================== ACT ==================== //
  // Compute the mean of Green function elements 'f' and '\tilde{f}^*'.
  const thrust::complex<T> result =
      conga::GreensAnomalousMean<T>::compute(gamma, gammaTilde);

  // =================== ASSERT ==================== //
  // The expected value with bulk coherence functions.
  const thrust::complex<T> Omega =
      thrust::sqrt(thrust::norm(orderParameter) - energy * energy);
  const thrust::complex<T> expected =
      static_cast<T>(0.5) * orderParameter *
      (static_cast<T>(1) / Omega + static_cast<T>(1) / thrust::conj(Omega));

  // Check.
  const T tolerance = static_cast<float>(TOLERANCE_FACTOR) *
                      std::numeric_limits<float>::epsilon();
  const T scale = static_cast<T>(SCALE);
  CHECK(result.real() ==
        doctest::Approx(expected.real()).epsilon(tolerance).scale(scale));
  CHECK(result.imag() ==
        doctest::Approx(expected.imag()).epsilon(tolerance).scale(scale));
}

/// \brief Test Green function elements f.
///
/// \return Void.
template <typename T> void testGreenAnomalous() {
  // =================== ARRANGE ==================== //
  const thrust::complex<T> energy(static_cast<T>(1), static_cast<T>(3));
  const thrust::complex<T> orderParameter(static_cast<T>(4),
                                          static_cast<T>(-1));

  const auto [gamma, gammaTilde] = conga::riccati::computeHomogeneous(
      energy, orderParameter, thrust::conj(orderParameter));

  // =================== ACT ==================== //
  // Compute the mean of Green function elements 'f'.
  const thrust::complex<T> result =
      conga::GreensAnomalous<T>::compute(gamma, gammaTilde);

  // =================== ASSERT ==================== //
  // The expected value with bulk coherence functions.
  const thrust::complex<T> Omega =
      thrust::sqrt(thrust::norm(orderParameter) - energy * energy);
  const thrust::complex<T> expected = orderParameter / Omega;

  // Check.
  const T tolerance = static_cast<float>(TOLERANCE_FACTOR) *
                      std::numeric_limits<float>::epsilon();
  const T scale = static_cast<T>(SCALE);
  CHECK(result.real() ==
        doctest::Approx(expected.real()).epsilon(tolerance).scale(scale));
  CHECK(result.imag() ==
        doctest::Approx(expected.imag()).epsilon(tolerance).scale(scale));
}

/// \brief Test Green function elements tilde(f).
///
/// \return Void.
template <typename T> void testGreenAnomalousTilde() {
  // =================== ARRANGE ==================== //
  const thrust::complex<T> energy(static_cast<T>(1), static_cast<T>(3));
  const thrust::complex<T> orderParameter(static_cast<T>(4),
                                          static_cast<T>(-1));

  const auto [gamma, gammaTilde] = conga::riccati::computeHomogeneous(
      energy, orderParameter, thrust::conj(orderParameter));

  // =================== ACT ==================== //
  // Compute the mean of Green function elements 'tilde(f)'.
  const thrust::complex<T> result =
      conga::GreensAnomalousTilde<T>::compute(gamma, gammaTilde);

  // =================== ASSERT ==================== //
  // The expected value with bulk coherence functions.
  const thrust::complex<T> Omega =
      thrust::sqrt(thrust::norm(orderParameter) - energy * energy);
  const thrust::complex<T> expected = thrust::conj(orderParameter) / Omega;

  // Check.
  const T tolerance = static_cast<float>(TOLERANCE_FACTOR) *
                      std::numeric_limits<float>::epsilon();
  const T scale = static_cast<T>(SCALE);
  CHECK(result.real() ==
        doctest::Approx(expected.real()).epsilon(tolerance).scale(scale));
  CHECK(result.imag() ==
        doctest::Approx(expected.imag()).epsilon(tolerance).scale(scale));
}
} // namespace helper

// =============== Test Green function element g =============== //

TEST_CASE("Test Green function element g - <double>") {
  helper::testGreen<double>();
}

TEST_CASE("Test Green function element g - <float>") {
  helper::testGreen<float>();
}

// ======== Test Green function element (f + tilde(f)^*)/2 ======== //

TEST_CASE("Test Green function element (f + tilde(f)^*)/2 - <double>") {
  helper::testGreenAnomalousMean<double>();
}

TEST_CASE("Test Green function element (f + tilde(f)^*)/2 - <float>") {
  helper::testGreenAnomalousMean<float>();
}

// ======== Test Green function element f ======== //

TEST_CASE("Test Green function element f - <double>") {
  helper::testGreenAnomalous<double>();
}

TEST_CASE("Test Green function element f - <float>") {
  helper::testGreenAnomalous<float>();
}

// ======== Test Green function element tilde(f) ======== //

TEST_CASE("Test Green function element tilde(f) - <double>") {
  helper::testGreenAnomalousTilde<double>();
}

TEST_CASE("Test Green function element tilde(f) - <float>") {
  helper::testGreenAnomalousTilde<float>();
}
