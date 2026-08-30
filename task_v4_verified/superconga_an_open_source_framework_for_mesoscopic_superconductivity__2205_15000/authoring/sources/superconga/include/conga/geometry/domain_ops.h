#ifndef CONGA_DOMAIN_OPS_H_
#define CONGA_DOMAIN_OPS_H_

#include "../configure.h"
#include "../grid.h"

#if CONGA_HIP
#include <hip/hip_runtime.h>
#elif CONGA_CUDA
#include <cuda.h>
#endif

namespace conga {
namespace geometry {
namespace internal {
/// @brief GPU kernel for extending a grid around the grain boundary.
/// @tparam T Commonly float or double.
/// @param inDimX The number of grid cells along the x-axis.
/// @param inDimY The number of grid cells along the y-axis.
/// @param inDimZ The number of grid cells along the z-axis.
/// @param inNumExtend The number of grid cells to extend around the boundary.
/// @param inDomainLabels Pointer to the domain labels describing the geometry.
/// @param inOutTarget Pointer to the grid to be extended.
template <typename T>
__global__ void extendValuesAtBoundary(const int inDimX, const int inDimY,
                                       const int inDimZ, const int inNumExtend,
                                       const char *const inDomainLabels,
                                       T *const inOutTarget) {
  const int x = blockIdx.x * blockDim.x + threadIdx.x + inNumExtend;
  const int y = blockIdx.y * blockDim.y + threadIdx.y + inNumExtend;
  const int z = blockIdx.z * blockDim.z + threadIdx.z;

  if (x < inDimX && y < inDimY && z < inDimZ) {
    const int idxDomain = y * inDimX + x;
    const char domainLabelCenter = inDomainLabels[idxDomain];

    if (domainLabelCenter == 0) {
      // Extent of the window along the x-axis.
      const int xMin = x - inNumExtend;
      const int xMax = x + inNumExtend;

      // Extent of the window along the y-axis.
      const int yMin = y - inNumExtend;
      const int yMax = y + inNumExtend;

      T val = static_cast<T>(0);
      int numPoints = 0;
      int minSquaredDistance = inDimX * inDimX + inDimY * inDimY;

      for (int ky = yMin; ky <= yMax; ++ky) {
        for (int kx = xMin; kx <= xMax; ++kx) {
          const int idxDomain = ky * inDimX + kx;
          const char domainLabel = inDomainLabels[idxDomain];

          if (domainLabel > 0) {
            // The squared distance to the pixel from the window center.
            const int dx = x - kx;
            const int dy = y - ky;
            const int squaredDistance = dx * dx + dy * dy;

            // The index of this point.
            const int idxNeighbour = (z * inDimY + ky) * inDimX + kx;

            // Update if better or equal.
            if (squaredDistance < minSquaredDistance) {
              val = inOutTarget[idxNeighbour];
              numPoints = 1;
              minSquaredDistance = squaredDistance;
            } else if (squaredDistance == minSquaredDistance) {
              val += inOutTarget[idxNeighbour];
              numPoints++;
            }
          }
        }
      }

      if (numPoints > 0) {
        const int idx = (z * inDimY + y) * inDimX + x;
        inOutTarget[idx] = val / static_cast<T>(numPoints);
      }
    }
  }
}

/// @brief GPU kernel for rotating a grid.
/// @tparam T Commonly float or double.
/// @param inSrcDimX The number of grid cells along the x-axis of the source
/// grid.
/// @param inSrcDimY The number of grid cells along the y-axis of the source
/// grid.
/// @param inDimZ The number of grid cells along the z-axis (same for source
/// and destination).
/// @param inDstDimX The number of grid cells along the x-axis of the
/// destination grid.
/// @param inDstDimY The number of grid cells along the y-axis of the
/// destination grid.
/// @param inCosAngle Cosine of the angle to rotate the grid.
/// @param inSinAngle Sine of the angle to rotate the grid.
/// @param inSrc Pointer to the grid to rotate.
/// @param outDst Pointer to the rotated grid.
template <typename T>
__global__ void rotate(const int inSrcDimX, const int inSrcDimY,
                       const int inDimZ, const int inDstDimX,
                       const int inDstDimY, const T inCosAngle,
                       const T inSinAngle, const T *const __restrict__ inSrc,
                       T *const __restrict__ outDst) {
  // The half differences in the number grid points along the spatial axes.
  const T halfDiffX =
      static_cast<T>(inSrcDimX - inDstDimX) * static_cast<T>(0.5);
  const T halfDiffY =
      static_cast<T>(inSrcDimY - inDstDimY) * static_cast<T>(0.5);

  // Shifts needed to move the origin from the corner to the center (and back).
  const T originShiftX = static_cast<T>(inSrcDimX - 1) * static_cast<T>(0.5);
  const T originShiftY = static_cast<T>(inSrcDimY - 1) * static_cast<T>(0.5);

  // Spatial coordinates of the destination grid.
  const int dstX = blockIdx.x * blockDim.x + threadIdx.x;
  const int dstY = blockIdx.y * blockDim.y + threadIdx.y;

  // Z-axis coordinate (same for both source and destination grids).
  const int z = blockIdx.z * blockDim.z + threadIdx.z;

  if (dstX < inDstDimX && dstY < inDstDimY && z < inDimZ) {
    // Array index to destination grid.
    const int idxDst = inDstDimX * (inDstDimY * z + dstY) + dstX;

    // Centered and unrotated spatial coordinates of the source grid.
    const T X = static_cast<T>(dstX) + halfDiffX - originShiftX;
    const T Y = static_cast<T>(dstY) + halfDiffY - originShiftY;

    // Rotated and uncentered spatial coordinates of the source grid.
    const T srcX_fp = X * inCosAngle + Y * inSinAngle + originShiftX;
    const T srcY_fp = -X * inSinAngle + Y * inCosAngle + originShiftY;

    // Integral spatial coordinates of the source grid.
    const int srcX = static_cast<int>(srcX_fp);
    const int srcY = static_cast<int>(srcY_fp);

    if ((srcX >= 0) && (srcX + 1 < inSrcDimX) && (srcY >= 0) &&
        (srcY + 1 < inSrcDimY)) {
      // The fractional part of the spatial coordinates of the source grid.
      const T fracX = srcX_fp - static_cast<T>(srcX);
      const T fracY = srcY_fp - static_cast<T>(srcY);

      // Source indices of the four points to be interpolated.
      const int idx00 = inSrcDimX * (inSrcDimY * z + srcY) + srcX;
      const int idx01 = idx00 + 1;
      const int idx10 = idx00 + inSrcDimX;
      const int idx11 = idx10 + 1;

      // Interpolation weights.
      const T weightX0 = static_cast<T>(1) - fracX;
      const T weightX1 = fracX;
      const T weightY0 = static_cast<T>(1) - fracY;
      const T weightY1 = fracY;

      // Interpolate along the x-axis and then the y-axis.
      const T interpX0 = weightX0 * inSrc[idx00] + weightX1 * inSrc[idx01];
      const T interpX1 = weightX0 * inSrc[idx10] + weightX1 * inSrc[idx11];
      outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
    } else {
      // If outside of the source grid.
      outDst[idxDst] = static_cast<T>(0);
    }
  }
}

/// @brief GPU kernel for rotating a grid, but only interpolate between values
/// within the domain, and only write to values within the domain.
/// @tparam T Commonly float or double.
/// @param inSrcDimX The number of grid cells along the x-axis of the source
/// grid.
/// @param inSrcDimY The number of grid cells along the y-axis of the source
/// grid.
/// @param inSrcDimZ The number of grid cells along the z-axis of the source
/// grid.
/// @param inDstDimX The number of grid cells along the x-axis of the
/// destination grid.
/// @param inDstDimY The number of grid cells along the y-axis of the
/// destination grid.
/// @param inDstDimZ The number of grid cells along the z-axis of the
/// destination grid.
/// @param inOffsetZ The offset along the source z-axis.
/// @param inCosAngle Cosine of the angle to rotate the grid.
/// @param inSinAngle Sine of the angle to rotate the grid.
/// @param inDomainLabelsSrc Pointer to the unrotated domain labels describing
/// the geometry.
/// @param inDomainLabelsDst Pointer to the rotated domain labels describing the
/// geometry.
/// @param inSrc Pointer to the grid to rotate.
/// @param outDst Pointer to the rotated grid.
template <typename T>
__global__ void
rotate(const int inSrcDimX, const int inSrcDimY, const int inSrcDimZ,
       const int inDstDimX, const int inDstDimY, const int inDstDimZ,
       const int inOffsetZ, const T inCosAngle, const T inSinAngle,
       const char *const __restrict__ inDomainLabelsSrc,
       const char *const __restrict__ inDomainLabelsDst,
       const T *const __restrict__ inSrc, T *const __restrict__ outDst) {
  // The half differences in the number grid points along the spatial axes.
  const T halfDiffX =
      static_cast<T>(inSrcDimX - inDstDimX) * static_cast<T>(0.5);
  const T halfDiffY =
      static_cast<T>(inSrcDimY - inDstDimY) * static_cast<T>(0.5);

  // Shifts needed to move the origin from the corner to the center, and back.
  const T originShiftX = static_cast<T>(inSrcDimX - 1) * static_cast<T>(0.5);
  const T originShiftY = static_cast<T>(inSrcDimY - 1) * static_cast<T>(0.5);

  // Spatial coordinates of the destination grid.
  const int dstX = blockIdx.x * blockDim.x + threadIdx.x;
  const int dstY = blockIdx.y * blockDim.y + threadIdx.y;

  // Z-axis coordinates.
  const int dstZ = blockIdx.z * blockDim.z + threadIdx.z;
  const int srcZ = dstZ + inOffsetZ;

  if (dstX < inDstDimX && dstY < inDstDimY && dstZ < inDstDimZ &&
      srcZ < inSrcDimZ) {
    // Array index to destination grid.
    const int idxDst = inDstDimX * (inDstDimY * dstZ + dstY) + dstX;

    // Is the destination index within the domain?
    const int idxDomain = inDstDimX * dstY + dstX;
    const bool inside = inDomainLabelsDst[idxDomain] > 0;

    // Centered and unrotated spatial coordinates of the source grid.
    const T X = static_cast<T>(dstX) + halfDiffX - originShiftX;
    const T Y = static_cast<T>(dstY) + halfDiffY - originShiftY;

    // Rotated and uncentered spatial coordinates of the source grid.
    const T srcX_fp = X * inCosAngle + Y * inSinAngle + originShiftX;
    const T srcY_fp = -X * inSinAngle + Y * inCosAngle + originShiftY;

    // Integral spatial coordinates of the source grid.
    const int srcX = static_cast<int>(srcX_fp);
    const int srcY = static_cast<int>(srcY_fp);

    if (inside && (srcX >= 0) && (srcX + 1 < inSrcDimX) && (srcY >= 0) &&
        (srcY + 1 < inSrcDimY)) {
      // The fractional part of the spatial coordinates of the source grid.
      const T fracX = srcX_fp - static_cast<T>(srcX);
      const T fracY = srcY_fp - static_cast<T>(srcY);

      // Source domain-label indices of the four points to be interpolated.
      const int idxDomain00 = inSrcDimX * srcY + srcX;
      const int idxDomain01 = idxDomain00 + 1;
      const int idxDomain10 = idxDomain00 + inSrcDimX;
      const int idxDomain11 = idxDomain10 + 1;

      // Check whether the points are within the source domain.
      const bool inside00 = inDomainLabelsSrc[idxDomain00] > 0;
      const bool inside01 = inDomainLabelsSrc[idxDomain01] > 0;
      const bool inside10 = inDomainLabelsSrc[idxDomain10] > 0;
      const bool inside11 = inDomainLabelsSrc[idxDomain11] > 0;

      // Source indices of the four points to be interpolated.
      const int idxSrc00 = inSrcDimX * (inSrcDimY * srcZ + srcY) + srcX;
      const int idxSrc01 = idxSrc00 + 1;
      const int idxSrc10 = idxSrc00 + inSrcDimX;
      const int idxSrc11 = idxSrc10 + 1;

      // Read the values to make the interpolation more legible.
      const T src00 = inSrc[idxSrc00];
      const T src01 = inSrc[idxSrc01];
      const T src10 = inSrc[idxSrc10];
      const T src11 = inSrc[idxSrc11];

      // Interpolation weights.
      const T weightX0 = static_cast<T>(1) - fracX;
      const T weightX1 = fracX;
      const T weightY0 = static_cast<T>(1) - fracY;
      const T weightY1 = fracY;

      // Handle all possible cases of grid points being outside of the grain.
      // TODO(Niclas): This can probably be done in a nicer way.
      if (inside00 && inside01 && inside10 && inside11) {
        // Case 01: 1111
        const T interpX0 = weightX0 * src00 + weightX1 * src01;
        const T interpX1 = weightX0 * src10 + weightX1 * src11;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (!inside00 && inside01 && inside10 && inside11) {
        // Case 02: 0111
        const T interpX0 = src01;
        const T interpX1 = weightX0 * src10 + weightX1 * src11;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (inside00 && !inside01 && inside10 && inside11) {
        // Case 03: 1011
        const T interpX0 = src00;
        const T interpX1 = weightX0 * src10 + weightX1 * src11;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (inside00 && inside01 && !inside10 && inside11) {
        // Case 04: 1101
        const T interpX0 = weightX0 * src00 + weightX1 * src01;
        const T interpX1 = src11;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (inside00 && inside01 && inside10 && !inside11) {
        // Case 05: 1110
        const T interpX0 = weightX0 * src00 + weightX1 * src01;
        const T interpX1 = src10;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (inside00 && inside01 && !inside10 && !inside11) {
        // Case 6: 1100
        outDst[idxDst] = weightX0 * src00 + weightX1 * src01;
      } else if (!inside00 && inside01 && inside10 && !inside11) {
        // Case 7: 0110
        const T interpX0 = src01;
        const T interpX1 = src10;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (!inside00 && !inside01 && inside10 && inside11) {
        // Case 08: 0011
        outDst[idxDst] = weightX0 * src10 + weightX1 * src11;
      } else if (inside00 && !inside01 && !inside10 && inside11) {
        // Case 09: 1001
        const T interpX0 = src00;
        const T interpX1 = src11;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (inside00 && !inside01 && inside10 && !inside11) {
        // Case 10: 1010
        const T interpX0 = src00;
        const T interpX1 = src10;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (!inside00 && inside01 && !inside10 && inside11) {
        // Case 11: 0101
        const T interpX0 = src01;
        const T interpX1 = src11;
        outDst[idxDst] = weightY0 * interpX0 + weightY1 * interpX1;
      } else if (inside00 && !inside01 && !inside10 && !inside11) {
        // Case 12: 1000
        outDst[idxDst] = src00;
      } else if (!inside00 && inside01 && !inside10 && !inside11) {
        // Case 13: 0100
        outDst[idxDst] = src01;
      } else if (!inside00 && !inside01 && inside10 && !inside11) {
        // Case 14: 0010
        outDst[idxDst] = src10;
      } else if (!inside00 && !inside01 && !inside10 && inside11) {
        // Case 15: 0001
        outDst[idxDst] = src11;
      } else {
        // Case 16: 0000
        outDst[idxDst] = static_cast<T>(0);
      }
    } else {
      // If outside of the destination grain, or outside of the source grid.
      outDst[idxDst] = static_cast<T>(0);
    }
  }
}
} // namespace internal

/// @brief Extend values outside of the grain boundary.
/// @tparam T Commonly float or double.
/// @param inDomainLabels The domain labels describing the geometry.
/// @param inOutTarget The grid to be extended.
template <typename T>
void extendValuesAtBoundary(const GridGPU<char> &inDomainLabels,
                            GridGPU<T> &inOutTarget) {
  // Sanity checks.
  assert(inDomainLabels.dimX() == inOutTarget.dimX());
  assert(inDomainLabels.dimY() == inOutTarget.dimY());

  // Dimensions.
  const int dimX = inOutTarget.dimX();
  const int dimY = inOutTarget.dimY();
  const int complexFactor = inOutTarget.isComplex() ? 2 : 1;
  const int dimZ = complexFactor * inOutTarget.numFields();

  // This is a sensible value. It probably does not need to be exposed to the
  // user. Note that 2 is chosen due to corner artifacts otherwise.
  // TODO(niclas): Have a separate domain label for corners, and handle them
  // separately.
  const int numExtend = 2;
  const int margin = 2 * numExtend;

  // Kernel parameters.
  const auto [blocksPerGrid, threadsPerBlock] =
      inOutTarget.getKernelDimensions(dimX - margin, dimY - margin, dimZ);

  // Launch kernel.
  internal::extendValuesAtBoundary<T><<<blocksPerGrid, threadsPerBlock>>>(
      dimX, dimY, dimZ, numExtend, inDomainLabels.getDataPointer(),
      inOutTarget.getDataPointer());
}

/// @brief Rotate a grid.
/// @tparam T Commonly float or double.
/// @param inAngle The angle (in radians) to rotate the grid.
/// @param inSrc The grid to be rotated.
/// @param outDst The result.
template <typename T>
void rotate(const T inAngle, const GridGPU<T> &inSrc, GridGPU<T> &outDst) {
  assert(inSrc.isComplex() == outDst.isComplex());
  assert(inSrc.numFields() == outDst.numFields());

  // Dimensions.
  const int srcDimX = inSrc.dimX();
  const int srcDimY = inSrc.dimY();
  const int dstDimX = outDst.dimX();
  const int dstDimY = outDst.dimY();
  const int numFields = outDst.numFields();
  const bool isComplex = outDst.isComplex();
  const int dimZ = numFields * (1 + static_cast<T>(isComplex));

  // To avoid doing trigonometry in the GPU kernel.
  const T cosAngle = std::cos(inAngle);
  const T sinAngle = std::sin(inAngle);

  const auto [blocksPerGrid, threadsPerBlock] =
      outDst.getKernelDimensionsFieldsComplex();

  internal::rotate<<<blocksPerGrid, threadsPerBlock>>>(
      srcDimX, srcDimY, dimZ, dstDimX, dstDimY, cosAngle, sinAngle,
      inSrc.getDataPointer(), outDst.getDataPointer());
}

/// @brief Rotate a grid, but only interpolate between values within the domain,
/// and only write to values within the domain.
/// @tparam T Commonly float or double.
/// @param inAngle The angle (in radians) to rotate the grid.
/// @param inDomainLabelsSrc The unrotated domain labels describing the
/// geometry.
/// @param inDomainLabelsDst The rotated domain labels describing the geometry.
/// @param inSrc The grid to be rotated.
/// @param outDst The result.
template <typename T>
void rotate(const T inAngle, const GridGPU<char> &inDomainLabelsSrc,
            const GridGPU<char> &inDomainLabelsDst, const GridGPU<T> &inSrc,
            GridGPU<T> &outDst) {
  assert(inSrc.dimX() == inDomainLabelsSrc.dimX());
  assert(inSrc.dimY() == inDomainLabelsSrc.dimY());
  assert(outDst.dimX() == inDomainLabelsDst.dimX());
  assert(outDst.dimY() == inDomainLabelsDst.dimY());
  assert(inSrc.isComplex() == outDst.isComplex());
  assert(inSrc.numFields() == outDst.numFields());

  // Dimensions.
  const int srcDimX = inSrc.dimX();
  const int srcDimY = inSrc.dimY();
  const int dstDimX = outDst.dimX();
  const int dstDimY = outDst.dimY();
  const int numFields = outDst.numFields();
  const bool isComplex = outDst.isComplex();
  const int dimZ = numFields * (1 + static_cast<T>(isComplex));
  const int offsetZ = 0;

  // To avoid doing trigonometry in the GPU kernel.
  const T cosAngle = std::cos(inAngle);
  const T sinAngle = std::sin(inAngle);

  const auto [blocksPerGrid, threadsPerBlock] =
      outDst.getKernelDimensionsFieldsComplex();

  internal::rotate<<<blocksPerGrid, threadsPerBlock>>>(
      srcDimX, srcDimY, dimZ, dstDimX, dstDimY, dimZ, offsetZ, cosAngle,
      sinAngle, inDomainLabelsSrc.getDataPointer(),
      inDomainLabelsDst.getDataPointer(), inSrc.getDataPointer(),
      outDst.getDataPointer());
}

/// @brief Rotate parts of a grid, but only interpolate between values within
/// the domain, and only write to values within the domain.
/// @tparam T Commonly float or double.
/// @param inAngle The angle (in radians) to rotate the grid.
/// @param inDomainLabelsSrc The unrotated domain labels describing the
/// geometry.
/// @param inDomainLabelsDst The rotated domain labels describing the geometry.
/// @param inFieldOffset The number of fields to ignore from source grid.
/// @param inSrc The grid to be rotated.
/// @param outDst The result.
template <typename T>
void rotate(const T inAngle, const GridGPU<char> &inDomainLabelsSrc,
            const GridGPU<char> &inDomainLabelsDst, const int inFieldOffset,
            const GridGPU<T> &inSrc, GridGPU<T> &outDst) {
  assert(inSrc.dimX() == inDomainLabelsSrc.dimX());
  assert(inSrc.dimY() == inDomainLabelsSrc.dimY());
  assert(outDst.dimX() == inDomainLabelsDst.dimX());
  assert(outDst.dimY() == inDomainLabelsDst.dimY());
  assert(inSrc.isComplex() == outDst.isComplex());
  assert(inSrc.numFields() > inFieldOffset);

  // Dimensions.
  const int complexFactor = 1 + static_cast<int>(outDst.isComplex());
  const int srcDimX = inSrc.dimX();
  const int srcDimY = inSrc.dimY();
  const int srcDimZ = inSrc.numFields() * complexFactor;
  const int dstDimX = outDst.dimX();
  const int dstDimY = outDst.dimY();
  const int dstDimZ = outDst.numFields() * complexFactor;
  const int offsetZ = inFieldOffset * complexFactor;

  // To avoid doing trigonometry in the GPU kernel.
  const T cosAngle = std::cos(inAngle);
  const T sinAngle = std::sin(inAngle);

  const auto [blocksPerGrid, threadsPerBlock] =
      outDst.getKernelDimensionsFieldsComplex();

  internal::rotate<<<blocksPerGrid, threadsPerBlock>>>(
      srcDimX, srcDimY, srcDimZ, dstDimX, dstDimY, dstDimZ, offsetZ, cosAngle,
      sinAngle, inDomainLabelsSrc.getDataPointer(),
      inDomainLabelsDst.getDataPointer(), inSrc.getDataPointer(),
      outDst.getDataPointer());
}
} // namespace geometry
} // namespace conga

#endif // CONGA_DOMAIN_OPS_H_
