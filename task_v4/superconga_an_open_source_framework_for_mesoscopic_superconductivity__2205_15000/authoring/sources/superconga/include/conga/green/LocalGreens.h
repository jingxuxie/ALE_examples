//===-- LocalGreens.h - Compute Green functions. --------------------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Compute Green functions (quasiparticle propagator and anomalous pair
/// propagator) from coherence functions.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_LOCAL_GREENS_H_
#define CONGA_LOCAL_GREENS_H_

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

// TODO(patric): change to other define macros, since other compilers (clang or
// whatever) might enable host/device, but not CUDACC/HIPCC. See:
// https://docs.amd.com/bundle/HIP-Programming-Guide-v5.2/page/Transitioning_from_CUDA_to_HIP.html#d4439e822
#if defined(__CUDACC__) or defined(__HIPCC__)
#ifndef _HD_
#define _HD_ __host__ __device__
#endif
#endif

#include <thrust/complex.h>

namespace conga {
/// \brief Compute the Green function "g".
///
/// g = -i (1 - \gamma \tilde{gamma}) / (1 + \gamma \tilde{gamma})
///
/// \param inGamma The coherence function "gamma".
/// \param inGammaTilde The coherence function "gammaTilde".
///
/// \return The Green function "g".
template <typename T> struct Greens {
  _HD_ static thrust::complex<T>
  compute(const thrust::complex<T> &inGamma,
          const thrust::complex<T> &inGammaTilde) {
    const thrust::complex<T> prod = inGamma * inGammaTilde;
    const thrust::complex<T> tmp =
        -((static_cast<T>(1.0) - prod) / (static_cast<T>(1.0) + prod));

    // Multiply by I.
    return thrust::complex<T>(-tmp.imag(), tmp.real());
  }
};

/// \brief Compute the mean of the Green functions "f" and "\tilde{f}^*".
///
/// f = -2i \gamma / (1 + \gamma \tilde{gamma})
/// \tilde{f} = 2i \tilde{gamma} / (1 + \gamma \tilde{gamma})
///
/// \param inGamma The coherence function "gamma".
/// \param inGammaTilde The coherence function "gammaTilde".
///
/// \return The mean "(f + \tilde{f}^*)/2".
template <typename T> struct GreensAnomalousMean {
  _HD_ static thrust::complex<T>
  compute(const thrust::complex<T> &inGamma,
          const thrust::complex<T> &inGammaTilde) {
    // Common factor of f and \tilde{f} (except I).
    const thrust::complex<T> tmp =
        static_cast<T>(1) / (static_cast<T>(1) + inGamma * inGammaTilde);

    // Multiply by I.
    const thrust::complex<T> factor(-tmp.imag(), tmp.real());

    const thrust::complex<T> f = -factor * inGamma;
    const thrust::complex<T> f_tilde_conj = thrust::conj(factor * inGammaTilde);

    return f + f_tilde_conj;
  }
};

/// \brief Compute the Green functions "f".
///
/// f = -2i \gamma / (1 + \gamma \tilde{gamma})
///
/// \param inGamma The coherence function "gamma".
/// \param inGammaTilde The coherence function "gammaTilde".
///
/// \return "f".
template <typename T> struct GreensAnomalous {
  _HD_ static thrust::complex<T>
  compute(const thrust::complex<T> &inGamma,
          const thrust::complex<T> &inGammaTilde) {
    // Common factor of f and \tilde{f} (except I).
    const thrust::complex<T> tmp =
        static_cast<T>(2) / (static_cast<T>(1) + inGamma * inGammaTilde);

    // Multiply by I.
    const thrust::complex<T> factor(-tmp.imag(), tmp.real());

    return -factor * inGamma;
  }
};

/// \brief Compute the Green functions "\tilde{f}".
///
/// \tilde{f} = 2i \tilde{gamma} / (1 + \gamma \tilde{gamma})
///
/// \param inGamma The coherence function "gamma".
/// \param inGammaTilde The coherence function "gammaTilde".
///
/// \return "\tilde{f}".
template <typename T> struct GreensAnomalousTilde {
  _HD_ static thrust::complex<T>
  compute(const thrust::complex<T> &inGamma,
          const thrust::complex<T> &inGammaTilde) {
    // Common factor of f and \tilde{f} (except I).
    const thrust::complex<T> tmp =
        static_cast<T>(2) / (static_cast<T>(1) + inGamma * inGammaTilde);

    // Multiply by I.
    const thrust::complex<T> factor(-tmp.imag(), tmp.real());

    return factor * inGammaTilde;
  }
};
} // namespace conga

#endif // CONGA_LOCAL_GREENS_H_
