// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
#ifndef CONGA_CSV_POSTPROCESS_ITERATION_WRITER_H_
#define CONGA_CSV_POSTPROCESS_ITERATION_WRITER_H_

#include "../Context.h"
#include "CSVIterationWriter.h"

#include <filesystem>
#include <iostream>
#include <string>

namespace conga {
namespace io {
template <typename T>
class CSVPostprocessIterationWriter : public CSVIterationWriter<T> {
public:
  CSVPostprocessIterationWriter(const std::filesystem::path &inFilePath,
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

    // Impurity self-energy residual.
    const bool impuritySelfEnergyExist =
        inContext.getComputeImpuritySelfEnergy();
    if (impuritySelfEnergyExist) {
      oss << m_delimiter << "impurity_self_energy_residual";
    }

    // LDOS residual.
    const bool LDOSExist = inContext.getComputeLDOS();
    if (LDOSExist) {
      oss << m_delimiter << "ldos_residual";
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

    // Impurity self-energy residual.
    const bool impuritySelfEnergyExist =
        inContext.getComputeImpuritySelfEnergy();
    if (impuritySelfEnergyExist) {
      oss << m_delimiter
          << inContext.getComputeImpuritySelfEnergy()->getResidual();
    }

    // LDOS residual.
    const bool LDOSExist = inContext.getComputeLDOS();
    if (LDOSExist) {
      oss << m_delimiter << inContext.getComputeLDOS()->getResidual();
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

#endif // CONGA_CSV_POSTPROCESS_ITERATION_WRITER_H_
