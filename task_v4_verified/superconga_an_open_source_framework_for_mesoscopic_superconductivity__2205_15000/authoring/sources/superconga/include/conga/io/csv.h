//===---- read_utils.h - utils functions for reading data from files. ----===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Functions for reading/writing CSV files.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_IO_CSV_H_
#define CONGA_IO_CSV_H_

#include "../Type.h"
#include "../geometry/domain_ops.h"
#include "../order_parameter/OrderParameter.h"
#include "CSVGridWriter.h"
#include "CSVIterationWriter.h"
#include "CSVPostprocessIterationWriter.h"
#include "CSVReader.h"
#include "CSVSimulationIterationWriter.h"

#include <thrust/device_vector.h>

#include <cassert>
#include <filesystem>
#include <iostream>
#include <map>
#include <string>
#include <vector>

namespace conga {
namespace io {
// ========================== WRITE ========================== //

/// \brief Write a grid to a CSV file.
///
/// \param inGrid The grid to be written.
/// \param inFieldTitles Titles of the "fields".
/// \param inFileName Path to CSV file.
///
/// \return Success.
template <typename T, class Device>
bool write(const GridData<T, Device> &inGrid,
           const std::vector<std::string> &inFieldTitles,
           const std::filesystem::path &inFileName) {
  CSVGridWriter<T> writer;
  const bool success = writer.write(inGrid, inFieldTitles, inFileName);
  return success;
}

// ========================== READ ========================== //

namespace internal {
/// \brief Copy two vectors to a grid. If the grid is complex it will be the
/// real/imag parts. Otherwise the first/second channel.
///
/// \param inSrc1 The first vector.
/// \param inSrc2 The second vector.
/// \param inOutDst The grid to copy the vectors into.
template <typename T>
void copy(const std::vector<T> inSrc1, const std::vector<T> inSrc2,
          GridGPU<T> &inOutDst) {
  // Grid info.
  const int dimX = inOutDst.dimX();
  const int dimY = inOutDst.dimY();
  const int numFields = inOutDst.numFields();
  const bool isComplex = inOutDst.isComplex();
  const std::size_t numElements = inOutDst.numElements();

  // Sanity checks.
  assert(inSrc1.size() + inSrc2.size() == numElements);
  assert(isComplex || (numFields == 2));

  // Copy to the GPU.
  const thrust::device_vector<T> src1 = inSrc1;
  const thrust::device_vector<T> src2 = inSrc2;

  // Get the grid data.
  thrust::device_vector<T> &data = inOutDst.getVector();

  const std::size_t stride = static_cast<std::size_t>(dimX * dimY);

  if (isComplex) {
    for (int i = 0; i < numFields; ++i) {
      const std::size_t srcOffset = i * stride;
      const std::size_t dstOffset = 2 * i * stride;
      thrust::copy(src1.begin() + srcOffset, src1.begin() + srcOffset + stride,
                   data.begin() + dstOffset);
      thrust::copy(src2.begin() + srcOffset, src2.begin() + srcOffset + stride,
                   data.begin() + dstOffset + stride);
    }
  } else if (numFields == 2) {
    thrust::copy(src1.begin(), src1.end(), data.begin());
    thrust::copy(src2.begin(), src2.end(), data.begin() + stride);
  } else {
    std::cerr << "-- ERROR! Could not copy data." << std::endl;
  }
}
} // namespace internal

/// \brief Read the domain from file.
///
/// \param inFileName The full path the data file.
/// \param inOutGrid The grid to put the data in. If the spatial dimensions to
/// not match it will be resized.
///
/// \return Success.
bool readDomain(const std::filesystem::path &inFileName,
                GridGPU<char> &inOutGrid) {
  // Read the CSV-file to a map.
  // Note that we are creating an "int" reader. This is because the domain is
  // actually saved as int, not char.
  const CSVReader<int> csvReader(inFileName);

  // Abort if something went wrong.
  if (!csvReader.success()) {
    return false;
  }

  // Get the resulting map.
  const std::map<std::string, std::vector<int>> &map = csvReader.getMap();

  // Construct the key.
  const std::string key = "domain";

  // Check if the keys exist.
  const bool keyExists = csvReader.contains(key);

  if (!keyExists) {
    std::cerr << "-- ERROR! The file does not contain the column, '" << key
              << "'." << std::endl;
    return false;
  }

  // Get the vectors.
  // Note, 'map' does not have a const overload for the access operator '[]'. So
  // either the map must not be const, or we must use 'at'.
  const std::vector<int> &tmp = map.at(key);

  // Cast to char.
  std::vector<char> domainCPU;
  for (const auto val : tmp) {
    domainCPU.push_back(static_cast<char>(val));
  }

  // Fetch the dimensions of the data.
  const auto [dimX, dimY, numFields] = csvReader.getDimensions();

  // Check if it is a square.
  if (dimX != dimY) {
    std::cerr << "-- ERROR! The data is not square." << std::endl;
    return false;
  }

  // Sanity check the number of components (fields).
  if (numFields != 1) {
    std::cerr << "-- ERROR! There must be only one field." << std::endl;
    return false;
  }

  // Resize the domain.
  const Type::type representation = Type::real;
  inOutGrid = GridGPU<char>(dimX, dimY, numFields, representation);

  // Copy data.
  inOutGrid.setVector(domainCPU);

  return true;
}

/// \brief Read a grid from file.
///
/// \param inFileName The full path the data file.
/// \param inColumnTitles The columns to read from the file.
/// \param inIsDefinedEverywhere Whether the grid is defined everywhere (e.g.
/// the vector potential).
/// \param inOutGrid The grid to put the data in. If the
/// spatial dimensions to not match it will be interpolated.
///
/// \return Success.
template <typename T>
bool read(const std::filesystem::path &inFileName,
          const std::vector<std::string> &inColumnTitles,
          const bool inIsDefinedEverywhere, GridGPU<T> &inOutGrid) {
  // Read the CSV-file to a map.
  const CSVReader<T> csvReader(inFileName);

  // Abort if something went wrong.
  if (!csvReader.success()) {
    return false;
  }

  // Get the resulting map.
  const std::map<std::string, std::vector<T>> &map = csvReader.getMap();

  // Check if the number of columns match.
  // TODO(Niclas): Remove this later when the impurity self-energies are written
  // to the same file.
  if (inColumnTitles.size() != map.size()) {
    std::cerr
        << "-- ERROR! The number of requested columns do not match the data."
        << std::endl;
    return false;
  }

  // Check if the columns exist.
  for (const auto &columnTitle : inColumnTitles) {
    const bool success = csvReader.contains(columnTitle);
    if (!success) {
      std::cerr << "-- ERROR! The file does not contain the column '"
                << columnTitle << "'." << std::endl;
      return false;
    }
  }

  // Fetch the dimensions of the data.
  const auto [dimX, dimY, numFields] = csvReader.getDimensions();

  // Check if it is a square.
  if (dimX != dimY) {
    std::cerr << "-- ERROR! The data is not square." << std::endl;
    return false;
  }

  // Sanity check the number of components (fields).
  const int numEffectiveFields = numFields * static_cast<int>(map.size());
  const int expectedNumEffectiveFields =
      inOutGrid.numFields() * (1 + static_cast<int>(inOutGrid.isComplex()));
  if (numEffectiveFields != expectedNumEffectiveFields) {
    std::cerr
        << "-- ERROR! The number of fields (times two if complex) do not match."
        << std::endl;
    return false;
  }

  // Get the expected dimensions of the grid.
  const int expectedDimX = inOutGrid.dimX();
  const int expectedDimY = inOutGrid.dimY();

  // Sanity check the sizes.
  if ((expectedDimX != dimX) || (expectedDimY != dimY)) {
    // Resize the grid.
    inOutGrid = GridGPU<T>(dimX, dimY, inOutGrid.numFields(),
                           inOutGrid.representation());

    // Copy data.
    internal::copy(map.at(inColumnTitles[0]), map.at(inColumnTitles[1]),
                   inOutGrid);

    if (!inIsDefinedEverywhere) {
      // Read the domain labels from file.
      // Note, the dimensions do not matter, it will be resized.
      GridGPU<char> domainLabels(1, 1, 1, Type::real);
      const std::filesystem::path domainFileName =
          inFileName.parent_path() / "domain.csv";
      const bool domainSuccess = readDomain(domainFileName, domainLabels);

      // Abort if something went wrong.
      if (!domainSuccess) {
        return false;
      }

      // Extend values outside of the domain (to avoid boundary interpolation
      // issues).
      geometry::extendValuesAtBoundary(domainLabels, inOutGrid);
    }

    // Resize (via interpolation), to the desired size.
    inOutGrid.resample(expectedDimX, expectedDimY);
  } else {
    // Copy data.
    internal::copy(map.at(inColumnTitles[0]), map.at(inColumnTitles[1]),
                   inOutGrid);
  }

  return true;
}

/// \brief Read the order parameter from file.
template <typename T>
bool read(const std::filesystem::path &inFileName,
          OrderParameter<T> &inOutOrderParameter) {
  // Read the CSV-file to a map.
  const CSVReader<T> csvReader(inFileName);

  // Abort if something went wrong.
  if (!csvReader.success()) {
    return false;
  }

  // Get the resulting map.
  const std::map<std::string, std::vector<T>> &map = csvReader.getMap();

  // The number of order-parameter components.
  const int numComponents = inOutOrderParameter.getNumComponents();

  // The types of the order-parameter components.
  const std::vector<std::string> types = inOutOrderParameter.getTypes();

  // Read the domain labels from file.
  // Note, the dimensions do not matter, it will be resized.
  GridGPU<char> domainLabels(1, 1, 1, Type::real);
  const std::filesystem::path domainFileName =
      inFileName.parent_path() / "domain.csv";
  const bool domainSuccess = readDomain(domainFileName, domainLabels);

  // Abort if something went wrong.
  if (!domainSuccess) {
    return false;
  }

  for (int i = 0; i < numComponents; ++i) {
    // Get the component grid.
    GridGPU<T> &component = *(inOutOrderParameter.getComponentGrid(i));

    // Get the type of the component, e.g. 'dx2-y2'.
    const std::string type = types[i];

    // Construct the keys.
    const std::string keyReal = type + "_re";
    const std::string keyImag = type + "_im";

    // Check if the keys exist.
    const bool keyRealExists = csvReader.contains(keyReal);
    const bool keyImagExists = csvReader.contains(keyImag);

    if (!(keyRealExists && keyImagExists)) {
      std::cerr << "-- ERROR! The file does not contain the columns, '"
                << keyReal << "' and '" << keyImag << "'." << std::endl;
      return false;
    }

    // Get the vectors.
    // Note, 'map' does not have a const overload for the access operator '[]'.
    // So either the map must not be const, or we must use 'at'.
    const std::vector<T> &cpuReal = map.at(keyReal);
    const std::vector<T> &cpuImag = map.at(keyImag);

    // Fetch the dimensions of the data.
    const auto [dimX, dimY, numFields] = csvReader.getDimensions();

    // Check if it is a square.
    if (dimX != dimY) {
      std::cerr << "-- ERROR! The data is not square." << std::endl;
      return false;
    }

    // Sanity check the number of components (fields).
    if (numFields != 1) {
      std::cerr << "-- ERROR! There must be only one field." << std::endl;
      return false;
    }

    // Get the expected dimensions of the grid.
    const int expectedDimX = component.dimX();
    const int expectedDimY = component.dimY();

    // Sanity check the sizes.
    if ((expectedDimX != dimX) || (expectedDimY != dimY)) {
      // Resize the component.
      const Type::type representation = Type::complex;
      component = GridGPU<T>(dimX, dimY, numFields, representation);

      // Copy data.
      internal::copy(cpuReal, cpuImag, component);

      // Extend values outside of the domain (to avoid boundary interpolation
      // issues).
      geometry::extendValuesAtBoundary(domainLabels, component);

      // Resize (via interpolation), to the desired size.
      component.resample(expectedDimX, expectedDimY);
    } else {
      // Copy data.
      internal::copy(cpuReal, cpuImag, component);
    }
  }

  return true;
}
} // namespace io
} // namespace conga

#endif // CONGA_IO_CSV_H_
