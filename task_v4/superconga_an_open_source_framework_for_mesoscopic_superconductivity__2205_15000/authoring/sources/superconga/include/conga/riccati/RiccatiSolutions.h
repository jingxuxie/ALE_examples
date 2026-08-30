//===- RiccatiSolutions.h - Coherence func. solutions to the Riccati eq. -===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// This contains the analytic solutions to the Riccati equation (with respect
/// to the coherence functions), namely the homogeneous (bulk) solution, and the
/// stepping solution using the mid-point method.
///
//===----------------------------------------------------------------------===//

#ifndef CONGA_RICCATI_SOLUTIONS_H
#define CONGA_RICCATI_SOLUTIONS_H

#include "../configure.h"

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

#include <thrust/complex.h>
#include <thrust/pair.h>

// TODO(patric): change to other define macros, since other compilers (clang or
// whatever) might enable host/device, but not CUDACC/HIPCC. See:
// https://docs.amd.com/bundle/HIP-Programming-Guide-v5.2/page/Transitioning_from_CUDA_to_HIP.html#d4439e822
#if defined(__CUDACC__) or defined(__HIPCC__)
#ifndef _HD_
#define _HD_ __host__ __device__
#endif
#endif

namespace conga {
namespace riccati {
/// \brief Riccati equation homogeneous: gamma and gammaTilde.
///
/// \param inEnergy Energy.
/// \param inOrderParameter Order parameter.
/// \param inOrderParameterTilde Tilde order parameter.
///
/// \return The homogeneous solutions {gamma, gammaTilde}.
template <typename T>
_HD_ thrust::pair<thrust::complex<T>, thrust::complex<T>>
computeHomogeneous(const thrust::complex<T> &inEnergy,
                   const thrust::complex<T> &inOrderParameter,
                   const thrust::complex<T> &inOrderParameterTilde) {
  // Form Omega and i*Omega.
  const thrust::complex<T> Omega = thrust::sqrt(
      inOrderParameter * inOrderParameterTilde - inEnergy * inEnergy);
  const thrust::complex<T> iOmega(-Omega.imag(), Omega.real());

  // Inverse denominator.
  const thrust::complex<T> invDenom =
      thrust::complex<T>(static_cast<T>(1), static_cast<T>(0)) /
      (inEnergy + iOmega);

  // The homogenous solutions.
  const thrust::complex<T> gamma = -inOrderParameter * invDenom;
  const thrust::complex<T> gammaTilde = inOrderParameterTilde * invDenom;

  return {gamma, gammaTilde};
}

/// \brief Mid-point stepping solution: gamma. Input the negative conjugate of
/// the order parameter in order to compute gammaTilde.
///
/// \param inEnergy The energy at the middle of the step.
/// \param inOrderParameter The order parameter at the middle of the step.
/// \param inOrderParameterTilde The tilde order parameter at the middle of the
/// step.
/// \param inInitial Value at the start of the step. \param inStep Step
/// size.
///
/// \return Value at the end of the step.
template <typename T>
_HD_ thrust::complex<T>
computeStep(const thrust::complex<T> &inEnergy,
            const thrust::complex<T> &inOrderParameter,
            const thrust::complex<T> &inOrderParameterTilde,
            const thrust::complex<T> &inInitial, const T inStep) {
  // For convenience.
  const thrust::complex<T> step(static_cast<T>(0), inStep);

  // These coefficients come from the mid-point method:
  //
  // y_n = y_{n-1} + h f((s_n + s_{n-1}) / 2 , (y_n + y_{n-1}) / 2)
  //
  // It yields a quadratic equation to solve:
  //
  // 0 = a * y^2_n + b * y_n + c
  //
  // with the following coefficients.
  const thrust::complex<T> a =
      static_cast<T>(0.25) * step * inOrderParameterTilde;
  const thrust::complex<T> b =
      static_cast<T>(2) * a * inInitial + step * inEnergy - static_cast<T>(1);
  const thrust::complex<T> c =
      (a * inInitial + step * inEnergy + static_cast<T>(1)) * inInitial +
      inOrderParameter * step;

  // Solution.
  const thrust::complex<T> discriminant =
      thrust::sqrt(b * b - static_cast<T>(4) * a * c);
  return static_cast<T>(2) * c / (-b + discriminant);
}
} // namespace riccati
} // namespace conga

#endif // CONGA_RICCATI_SOLUTIONS_H
