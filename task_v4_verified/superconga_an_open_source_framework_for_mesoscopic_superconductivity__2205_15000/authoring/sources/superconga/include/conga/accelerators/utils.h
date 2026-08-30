//===-------------- utils.h - Accelerator utility functions. --------------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Accelerator utility functions.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_ACCELERATOR_UTILS_H_
#define CONGA_ACCELERATOR_UTILS_H_

#include "../check_gpu_error.h"
#include "../configure.h"
#include "../grid.h"
#include "../impurities/ImpuritySelfEnergy.h"
#include "../order_parameter/OrderParameter.h"

#include <cassert>

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

namespace conga {
namespace accelerators {
/// \brief Sum all elements of a grid.
///
/// \param inGrid The grid to sum.
///
/// \return The sum.
template <typename T> T sumGrid(const GridGPU<T> &inGrid) {
  double sum = 0.0;
  for (int i = 0; i < inGrid.numFields(); ++i) {
    sum += static_cast<double>(inGrid.sumField(i));
  }
  return static_cast<T>(sum);
}

namespace internal {
/// \brief Copy all elements from inSrc to inOutDst, writing to memory offset
/// inOffset.
///
/// \param inSrc The grid to copy from.
/// \param inOffset The memory offset to start writing to in inOutDst.
/// \param inOutDst The grid to write to.
///
/// \return The total number of elements copied.
template <typename T>
std::size_t concatenate(const GridGPU<T> &inSrc, const std::size_t inOffset,
                        GridGPU<T> &inOutDst) {
  const std::size_t numElements = inSrc.numElements();
#if CONGA_HIP
  CHECK_GPU_ERROR(hipMemcpy(inOutDst.getDataPointer() + inOffset,
                            inSrc.getDataPointer(), numElements * sizeof(T),
                            hipMemcpyDeviceToDevice));
#elif CONGA_CUDA
  CHECK_GPU_ERROR(cudaMemcpy(inOutDst.getDataPointer() + inOffset,
                             inSrc.getDataPointer(), numElements * sizeof(T),
                             cudaMemcpyDeviceToDevice));
#endif
  return numElements;
}

/// \brief Concatenate the order-parameter components.
///
/// The real and imaginary parts are treated as separate fields.
///
/// \param inOrderParameter The order parameter.
/// \param inOffset The memory offset to start writing to in inOutDst.
/// \param inOutDst The concatenated result.
///
/// \return The total number of elements copied.
template <typename T>
std::size_t concatenate(const OrderParameter<T> &inOrderParameter,
                        const std::size_t inOffset, GridGPU<T> &inOutDst) {
  std::size_t numElements = 0;
  const int numComponents = inOrderParameter.getNumComponents();
  for (int i = 0; i < numComponents; ++i) {
    const GridGPU<T> &component = *(inOrderParameter.getComponentGrid(i));
    numElements += concatenate(component, inOffset + numElements, inOutDst);
  }
  return numElements;
}

/// \brief Copy elements from inSrc to inOutDst, reading from memory offset
/// inOffset.
///
/// \param inSrc The grid to copy from.
/// \param inOffset The memory offset to start from in inSrc.
/// \param inOutDst The grid to write to.
///
/// \return The total number of elements copied.
template <typename T>
std::size_t split(const GridGPU<T> &inSrc, const std::size_t inOffset,
                  GridGPU<T> &inOutDst) {
  const std::size_t numElements = inOutDst.numElements();
#if CONGA_HIP
  CHECK_GPU_ERROR(hipMemcpy(inOutDst.getDataPointer(),
                            inSrc.getDataPointer() + inOffset,
                            numElements * sizeof(T), hipMemcpyDeviceToDevice));
#elif CONGA_CUDA
  CHECK_GPU_ERROR(
      cudaMemcpy(inOutDst.getDataPointer(), inSrc.getDataPointer() + inOffset,
                 numElements * sizeof(T), cudaMemcpyDeviceToDevice));
#endif
  return numElements;
}

/// \brief Split the concatenated order-parameter components.
///
/// \param inSrc The order-parameter components concatenated.
/// \param inOffset The memory offset to start from in inSrc.
/// \param inOutOrderParameter The order parameter.
///
/// \return The total number of elements copied.
template <typename T>
std::size_t split(const GridGPU<T> &inSrc, const std::size_t inOffset,
                  OrderParameter<T> &inOutOrderParameter) {
  std::size_t numElements = 0;
  const int numComponents = inOutOrderParameter.getNumComponents();
  for (int i = 0; i < numComponents; ++i) {
    GridGPU<T> &component = *(inOutOrderParameter.getComponentGrid(i));
    numElements += split(inSrc, inOffset + numElements, component);
  }
  return numElements;
}
} // namespace internal

/// \brief Concatenate the order-parameter components.
///
/// The real and imaginary parts are treated as separate (real) fields.
///
/// \param inOrderParameter The order parameter.
///
/// \return The concatenated result.
template <typename T>
GridGPU<T> concatenate(const OrderParameter<T> &inOrderParameter) {
  const int dimX = inOrderParameter.getComponentGrid(0)->dimX();
  const int dimY = inOrderParameter.getComponentGrid(0)->dimY();
  const T numComponents = inOrderParameter.getNumComponents();
  const int complexFactor = 2;
  const int numFields = complexFactor * numComponents;
  const Type::type representation = Type::real;
  GridGPU<T> result(dimX, dimY, numFields, representation);

  const std::size_t offset = 0;
  const std::size_t numElements =
      internal::concatenate(inOrderParameter, offset, result);

  assert(numElements == dimX * dimY * numFields);

  return result;
}

/// \brief Concatenate the order-parameter components and the vector potential.
///
/// The real and imaginary parts are treated as separate fields.
///
/// \param inOrderParameter The order parameter.
/// \param inVectorPotential The vector potential.
///
/// \return The concatenated result.
template <typename T>
GridGPU<T> concatenate(const OrderParameter<T> &inOrderParameter,
                       const GridGPU<T> &inVectorPotential) {
  const int dimX = inOrderParameter.getComponentGrid(0)->dimX();
  const int dimY = inOrderParameter.getComponentGrid(0)->dimY();
  const T numComponents = inOrderParameter.getNumComponents();
  const int complexFactor = 2;
  const int numFields =
      complexFactor * numComponents + inVectorPotential.numFields();
  const Type::type representation = Type::real;
  GridGPU<T> result(dimX, dimY, numFields, representation);

  std::size_t numElements = 0;
  numElements += internal::concatenate(inOrderParameter, numElements, result);
  numElements += internal::concatenate(inVectorPotential, numElements, result);

  assert(numElements == dimX * dimY * numFields);

  return result;
}

/// \brief Split the concatenated order-parameter components.
///
/// \param inSrc The order-parameter components concatenated.
/// \param inOutVectorPotential The order parameter.
///
/// \return Void.
template <typename T>
void split(const GridGPU<T> &inSrc, OrderParameter<T> &inOutOrderParameter) {
  std::size_t numElements = 0;
  numElements += internal::split(inSrc, numElements, inOutOrderParameter);
  assert(numElements == inSrc.numElements());
}

/// \brief Split the concatenated order-parameter components and the vector
/// potential.
///
/// \param inSrc The order-parameter components and vector potential
/// concatenated.
/// \param inOutOrderParameter The order parameter.
/// \param inOutVectorPotential The vector potential.
///
/// \return Void.
template <typename T>
void split(const GridGPU<T> &inSrc, OrderParameter<T> &inOutOrderParameter,
           GridGPU<T> &inOutVectorPotential) {
  std::size_t numElements = 0;
  numElements += internal::split(inSrc, numElements, inOutOrderParameter);
  numElements += internal::split(inSrc, numElements, inOutVectorPotential);
  assert(numElements == inSrc.numElements());
}
} // namespace accelerators
} // namespace conga

#endif // CONGA_ACCELERATOR_UTILS_H_
