// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
#ifndef CONGA_CSV_SIMULATION_ITERATION_WRITER_H_
#define CONGA_CSV_SIMULATION_ITERATION_WRITER_H_

#include "../Context.h"
#include "CSVIterationWriter.h"

#include <filesystem>
#include <iostream>
#include <string>

namespace conga {
namespace io {
template <typename T>
class CSVSimulationIterationWriter : public CSVIterationWriter<T> {
public:
  CSVSimulationIterationWriter(const std::filesystem::path &inFilePath,
                               const std::string &inDelimiter = ",",
                               const int inFloatPrecision = 8)
      : CSVIterationWriter<T>(), m_filePath(inFilePath),
        m_floatPrecision(inFloatPrecision), m_delimiter(inDelimiter) {
    // Remove the file because the header might have changed.
    std::filesystem::remove(m_filePath);
  }

  bool write(const Context<T> &inContext) const override {
    const bool fileExists = std::filesystem::exists(m_filePath);
    if (!fileExists) {
      const bool successAddingHeader = appendHeader(inContext);
      if (!successAddingHeader) {
        return false;
      }
    }
    return appendRow(inContext);
  }

private:
  const std::filesystem::path m_filePath;
  const int m_floatPrecision;
  const std::string m_delimiter;

  bool appendHeader(const Context<T> &inContext) const {
    // WARNING! The header must be added in the same order as the residuals are
    // written in appendRow.
    std::ostringstream oss;

    // The number of iterations so far, and boundary coherence residual.
    oss << "iteration" << m_delimiter << "boundary_coherence_residual";

    // Order-parameter residual.
    const bool orderParameterExist = inContext.getComputeOrderParameter();
    if (orderParameterExist) {
      oss << m_delimiter << "order_parameter_residual";
    }

    // Current-density residual.
    const bool currentDensityExist = inContext.getComputeCurrent();
    if (currentDensityExist) {
      oss << m_delimiter << "current_density_residual";
    }

    // Vector-potential residual.
    const bool vectorPotentialExist = inContext.getComputeVectorPotential();
    if (vectorPotentialExist) {
      oss << m_delimiter << "vector_potential_residual";
    }

    // Impurity self-energy residual.
    const bool impuritySelfEnergyExist =
        inContext.getComputeImpuritySelfEnergy();
    if (impuritySelfEnergyExist) {
      oss << m_delimiter << "impurity_self_energy_residual";
    }

    // Free-energy residual.
    const bool freeEnergyExist = inContext.getComputeFreeEnergy();
    if (freeEnergyExist) {
      oss << m_delimiter << "free_energy_residual" << m_delimiter
          << "free_energy_per_unit_area";
    }

    return appendToFile(oss.str());
  };

  bool appendRow(const Context<T> &inContext) const {
    // WARNING! The residuals must be written in the same order as in the
    // header in appendHeader.
    std::ostringstream oss;
    oss << std::scientific << std::setprecision(m_floatPrecision);

    // The number of iterations so far.
    oss << inContext.getNumIterations();

    // Boundary coherence residual.
    oss << m_delimiter << inContext.getRiccatiSolver()->getResidual();

    // Order-parameter residual.
    const bool orderParameterExist = inContext.getComputeOrderParameter();
    if (orderParameterExist) {
      oss << m_delimiter << inContext.getComputeOrderParameter()->getResidual();
    }

    // Current-density residual.
    const bool currentDensityExist = inContext.getComputeCurrent();
    if (currentDensityExist) {
      oss << m_delimiter << inContext.getComputeCurrent()->getResidual();
    }

    // Vector-potential residual.
    const bool vectorPotentialExist = inContext.getComputeVectorPotential();
    if (vectorPotentialExist) {
      oss << m_delimiter
          << inContext.getComputeVectorPotential()->getResidual();
    }

    // Impurity self-energy residual.
    const bool impuritySelfEnergyExist =
        inContext.getComputeImpuritySelfEnergy();
    if (impuritySelfEnergyExist) {
      oss << m_delimiter
          << inContext.getComputeImpuritySelfEnergy()->getResidual();
    }

    // Free-energy residual.
    const bool freeEnergyExist = inContext.getComputeFreeEnergy();
    if (freeEnergyExist) {
      oss << m_delimiter << inContext.getComputeFreeEnergy()->getResidual()
          << m_delimiter
          << inContext.getComputeFreeEnergy()->getFreeEnergyPerUnitArea();
    }

    return appendToFile(oss.str());
  };

  bool appendToFile(const std::string &inLine) const {
    std::ofstream outFile(m_filePath, std::ios_base::app);
    if (!outFile.good()) {
      return false;
    }
    outFile << inLine << std::endl;
    return true;
  }
};
} // namespace io
} // namespace conga

#endif // CONGA_CSV_SIMULATION_ITERATION_WRITER_H_
