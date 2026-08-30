//===---- ContextModule.h - . ----===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_CONTEXT_MODULE_H_
#define CONGA_CONTEXT_MODULE_H_

#include "configure.h"

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

#include <iostream>
#include <string>

namespace conga {
template <typename> class ComputeProperty;
template <typename> class Context;
template <typename> class FermiSurface;
template <typename> class GeometryGroup;
template <typename> class ImpuritySelfEnergy;
template <typename> class IntegrationIterator;
template <typename> class OrderParameter;
template <typename> class Parameters;
template <typename> class RiccatiSolver;

template <typename T> class ContextModule {
public:
  ContextModule() : _context(0) {}
  virtual ~ContextModule() {}

  // Copy constructor
  ContextModule(const ContextModule<T> &other) : _context(other._context) {}

  // Context constructor
  // Makes sure that Context knows about this ContextModule, and vice versa.
  ContextModule(Context<T> *ctx) { _context = ctx; }

  void setContext(Context<T> *ctx) { _context = ctx; }
  Context<T> *getContext() const { return _context; }

  FermiSurface<T> *getFermiSurface() const {
    return _context->getFermiSurface();
  }

  GeometryGroup<T> *getGeometry() const { return _context->getGeometry(); }

  ImpuritySelfEnergy<T> *getImpuritySelfEnergy() const {
    return _context->getImpuritySelfEnergy();
  }

  IntegrationIterator<T> *getIntegrationIterator() const {
    return _context->getIntegrationIterator();
  }

  OrderParameter<T> *getOrderParameter() const {
    return _context->getOrderParameter();
  }

  Parameters<T> *getParameters() const { return _context->getParameters(); }

  RiccatiSolver<T> *getRiccatiSolver() const {
    return _context->getRiccatiSolver();
  }

  int getNumComputeObjects() const { return _context->getNumComputeObjects(); }
  ComputeProperty<T> *getComputeObject(int idx) const {
    return _context->getComputeObject(idx);
  }

  // The function Context::initialize() calls ContextModule::initialize() for
  // all context modules. Call Context::initialize() after changing anything in
  // Parameters object.
  virtual int initialize() = 0;

  static void checkGpuError(std::string msg = "");

private:
  Context<T> *_context;
};

template <typename T> void ContextModule<T>::checkGpuError(std::string msg) {
#if CONGA_HIP
  hipError_t err = hipGetLastError();

  if (err != hipSuccess)
    std::cerr << "-- HIP ERROR! " << msg << ": " << hipGetErrorString(err)
              << std::endl;
#elif CONGA_CUDA
  cudaError_t err = cudaGetLastError();

  if (err != cudaSuccess)
    std::cerr << "-- CUDA ERROR! " << msg << ": " << cudaGetErrorString(err)
              << std::endl;
#endif
}
} // namespace conga

#endif // CONGA_CONTEXT_MODULE_H_
