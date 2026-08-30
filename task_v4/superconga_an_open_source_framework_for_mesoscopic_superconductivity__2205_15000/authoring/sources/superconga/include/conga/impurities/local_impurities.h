//=======- local_impurities.h - Functions for impurity self-energies. -=======//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// This contains the expression for isotropic non-magnetic impurity
/// self-energies.
///
//===----------------------------------------------------------------------===//

#ifndef CONGA_LOCAL_IMPURITIES_H
#define CONGA_LOCAL_IMPURITIES_H

#include "../configure.h"

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

#include <thrust/complex.h>
#include <thrust/tuple.h>

// TODO(patric): change to other define macros, since other compilers (clang or
// whatever) might enable host/device, but not CUDACC/HIPCC. See:
// https://docs.amd.com/bundle/HIP-Programming-Guide-v5.2/page/Transitioning_from_CUDA_to_HIP.html#d4439e822
#if defined(__CUDACC__) or defined(__HIPCC__)
#ifndef _HD_
#define _HD_ __host__ __device__
#endif
#endif

namespace conga {
namespace impurities {
/// \brief Compute the non-magnetic impurity self-energies.
///
/// \param inAvgG The Fermi-surface averaged matrix element g.
/// \param inAvgF The Fermi-surface averaged matrix element f.
/// \param inAvgFTilde The Fermi-surface averaged matrix element tilde(f).
/// \param inCosPhase Cosine of the scattering phase shift.
/// \param inSinPhase Sine of the scattering phase shift, delta_0.
/// \param inScatteringEnergy The scattering energy, Gamma = Gamma_u * sin^2(delta_0).
///
/// \return The self-energies {Sigma, Delta, DeltaTilde}.
template <typename T>
_HD_ thrust::tuple<thrust::complex<T>, thrust::complex<T>, thrust::complex<T>>
computeSelfEnergy(const thrust::complex<T> &inAvgG,
                  const thrust::complex<T> &inAvgF,
                  const thrust::complex<T> &inAvgFTilde, const T inCosPhase,
                  const T inSinPhase, const T inScatteringEnergy) {
  // See Eq. (4) in: https://arxiv.org/pdf/1110.5050v1.pdf

  // The inverse (cos^2(delta_0) - sin^2(delta_0)*hat(g)^2).
  // Note that g, f, and tilde(f) here are defined without the pi.
  const thrust::complex<T> factor =
      inScatteringEnergy /
      (inCosPhase * inCosPhase +
       inSinPhase * inSinPhase * (inAvgF * inAvgFTilde - inAvgG * inAvgG));

  const thrust::complex<T> Sigma = inAvgG * factor;
  const thrust::complex<T> Delta = inAvgF * factor;
  const thrust::complex<T> DeltaTilde = inAvgFTilde * factor;

  return {Sigma, Delta, DeltaTilde};
}

/// \brief Compute the non-magnetic impurity self-energies.
///
/// \param inAvgG The Fermi-surface averaged matrix element g.
/// \param inAvgF The Fermi-surface averaged matrix element f.
/// \param inAvgFTilde The Fermi-surface averaged matrix element tilde(f).
/// \param inCosPhase Cosine of the scattering phase shift.
/// \param inSinPhase Sine of the scattering phase shift.
///
/// \return The self-energies {Sigma, Delta, DeltaTilde}.
template <typename T>
_HD_ thrust::tuple<thrust::complex<T>, thrust::complex<T>, thrust::complex<T>>
computeSelfEnergy(const thrust::complex<T> &inAvgG,
                  const thrust::complex<T> &inAvgF,
                  const thrust::complex<T> &inAvgFTilde, const T inCosPhase,
                  const T inSinPhase) {
  const T dummy = static_cast<T>(1);
  return computeSelfEnergy(inAvgG, inAvgF, inAvgFTilde, inCosPhase, inSinPhase,
                           dummy);
}
} // namespace impurities
} // namespace conga

#endif // CONGA_LOCAL_IMPURITIES_H
