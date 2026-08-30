// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
#ifndef CONGA_SIMULATION_WRITER_H_
#define CONGA_SIMULATION_WRITER_H_

#include "../Context.h"
#include "../grid.h"
#include "DataFormat.h"
#include "csv.h"
#include "json.h"
#ifdef CONGA_USE_HDF5
#include "h5.h"
#endif // CONGA_USE_HDF5
#include "print.h"

#include <filesystem>

namespace conga {
namespace io {
/// \brief Class for writing simulation data and parameters to file.
template <typename T> class SimulationWriter {
public:
  /// \brief Constructor.
  ///
  /// \param inDataPath Path to data directory.
  /// \param inDataFormat Data format of large data files.
  /// \param inVerbose Whether to print to terminal or not.
  /// \param inSaveOrderParameter Save the order parameter.
  /// \param inSaveCurrentDensity Save the current density.
  /// \param inSaveVectorPotential Save the induced vector potential.
  /// \param inSaveFluxDensity Save the flux density.
  /// \param inSaveImpuritySelfEnergy Save the impurity self-energy.
  SimulationWriter(const std::filesystem::path &inDataPath,
                   const DataFormat inDataFormat, const bool inVerbose,
                   const bool inSaveOrderParameter,
                   const bool inSaveCurrentDensity,
                   const bool inSaveVectorPotential,
                   const bool inSaveFluxDensity,
                   const bool inSaveImpuritySelfEnergy)
      : m_dataPath(inDataPath), m_dataFormat(inDataFormat),
        m_verbose(inVerbose), m_saveOrderParameter(inSaveOrderParameter),
        m_saveCurrentDensity(inSaveCurrentDensity),
        m_saveVectorPotential(inSaveVectorPotential),
        m_saveFluxDensity(inSaveFluxDensity),
        m_saveImpuritySelfEnergy(inSaveImpuritySelfEnergy) {}

  /// \brief Write data and paramters.
  ///
  /// \param inContext The context object.
  ///
  /// \return Void.
  void write(const Context<T> &inContext) const;

private:
  /// \brief Save config params, internal params, and results to JSON files.
  ///
  /// This function saves two json files: one for internal parameters, and one
  /// for scalar results. Motivation, there are some internal parameters that
  /// are not possible to infer without running the program (the exact number of
  /// lattice points inside the grain), these are very useful to have access to
  /// when post-processing (e.g. for doing area normalization). Finally, there
  /// are some scalar results (e.g. area-averaged quantities) that are more
  /// appropriate and convenient to have in json rather than csv.
  ///
  /// \param inContext The context object.
  ///
  /// \return Void.
  void writeParameters(const Context<T> &inContext) const;

  /// \brief Write simulation data to file(s).
  ///
  /// \param inContext The context object.
  ///
  /// \return Void.
  void writeData(const Context<T> &inContext) const;

  // Path to data directory.
  const std::filesystem::path m_dataPath;

  // Data format of large data files.
  const DataFormat m_dataFormat;

  // Whether to print to terminal or not.
  const bool m_verbose;

  // What to write to file.
  const bool m_saveOrderParameter;
  const bool m_saveCurrentDensity;
  const bool m_saveVectorPotential;
  const bool m_saveFluxDensity;
  const bool m_saveImpuritySelfEnergy;
};

template <typename T>
void SimulationWriter<T>::write(const Context<T> &inContext) const {
  writeParameters(inContext);
  writeData(inContext);
}

template <typename T>
void SimulationWriter<T>::writeParameters(const Context<T> &inContext) const {
  // Number of lattice sites in grain.
  const int numGrainLatticeSites =
      inContext.getGeometry()->getNumGrainLatticeSites();

  // Side length of lattice site.
  const T latticeElementSize = inContext.getParameters()->getGridElementSize();

  // Json for various results.
  Json::Value resultsJSON;

  // Free energy per unit area.
  const bool freeEnergyExist = inContext.getComputeFreeEnergy();
  if (freeEnergyExist) {
    resultsJSON["free_energy_per_unit_area"] =
        inContext.getComputeFreeEnergy()->getFreeEnergyPerUnitArea();
    resultsJSON["magnetic_free_energy_per_unit_area"] =
        inContext.getComputeFreeEnergy()->getMagneticFreeEnergyPerUnitArea();
  }

  // Average order-parameter magnitude.
  const bool orderParameterExist = inContext.getComputeOrderParameter();
  if (orderParameterExist) {
    resultsJSON["order_parameter_average_magnitude"] =
        inContext.getOrderParameter()->sumMagnitude() /
        static_cast<T>(numGrainLatticeSites);
  }

  // Average current-density magnitude.
  const bool currentDensityExist = inContext.getComputeCurrent();
  if (currentDensityExist) {
    resultsJSON["current_density_average_magnitude"] =
        inContext.getComputeCurrent()->getResult()->sumMagnitude() /
        static_cast<T>(numGrainLatticeSites);

    // Magnetic moment per unit area.
    resultsJSON["magnetic_moment_per_unit_area"] =
        inContext.getComputeCurrent()->getResult()->moment(latticeElementSize) /
        inContext.getGeometry()->area();
  }

  const bool vectorPotentialExist = inContext.getInducedVectorPotential();
  if (vectorPotentialExist) {
    // Get the vector potential. It is used both for the average vector
    // potential, and average flux density.
    // The vector potential is scaled by the squared penetration depth
    // internally. Undo the scaling here.
    const T penetrationDepth = inContext.getParameters()->getPenetrationDepth();
    const T vectorPotentialScale =
        penetrationDepth > static_cast<T>(0)
            ? static_cast<T>(1) / (penetrationDepth * penetrationDepth)
            : static_cast<T>(0);
    GridGPU<T> vectorPotential =
        *(inContext.getInducedVectorPotential()) * vectorPotentialScale;

    // Average flux density.
    // TODO(niclas): Should this be computed outside of the grain?
    GridGPU<T> fluxDensity = vectorPotential.curl(latticeElementSize);
    inContext.getGeometry()->zeroValuesOutsideDomainRef(&fluxDensity);
    resultsJSON["flux_density_average"] =
        fluxDensity.sumField() / static_cast<T>(numGrainLatticeSites);

    // Average vector-potential magnitude.
    // TODO(niclas): Should this be computed outside of the grain?
    inContext.getGeometry()->zeroValuesOutsideDomainRef(&vectorPotential);
    resultsJSON["vector_potential_average_magnitude"] =
        vectorPotential.sumMagnitude() / static_cast<T>(numGrainLatticeSites);
  }

  // Save various results to JSON file.
  const std::filesystem::path resultsPath =
      m_dataPath / "simulation_results.json";
  io::write(resultsPath, resultsJSON);
  printWrite(m_verbose, true, "scalar results", resultsPath);

  // Internal parameters useful for post-processing.
  Json::Value internalParamJSON;
  internalParamJSON["area_compute"] = inContext.getGeometry()->area();
  internalParamJSON["internal_lattice_points"] = numGrainLatticeSites;
  internalParamJSON["grain_margin"] = constants::GRAIN_SIZE_MARGIN;
  const int numLatticeSitesPerSide =
      inContext.getParameters()->getGridResolutionBase();
  internalParamJSON["num_lattice_points"] =
      numLatticeSitesPerSide * numLatticeSitesPerSide;
  internalParamJSON["num_ozaki_energies"] =
      inContext.getParameters()->getNumOzakiEnergies();

  // Save internal parameters to JSON file.
  const std::filesystem::path internalParametersPath =
      m_dataPath / "internal_parameters.json";
  io::write(internalParametersPath, internalParamJSON);
  printWrite(m_verbose, true, "internal parameters", internalParametersPath);
}

template <typename T>
void SimulationWriter<T>::writeData(const Context<T> &inContext) const {
  // All objects to save.
  // TODO(Niclas): We should probably check that all objects exists, i.e. get
  // pointers instead of grids.
  const GridGPU<char> &domain = *(inContext.getGeometry()->getDomainGrid());
  const OrderParameter<T> &orderParameter = *(inContext.getOrderParameter());
  const GridGPU<T> &currentDensity =
      *(inContext.getComputeCurrent()->getResult());
  const ImpuritySelfEnergy<T> *const impuritySelfEnergy =
      inContext.getImpuritySelfEnergy();

  // Scale vector potential to our external units.
  const T penetrationDepth = inContext.getParameters()->getPenetrationDepth();
  const T vectorPotentialScale =
      penetrationDepth > static_cast<T>(0)
          ? static_cast<T>(1) / (penetrationDepth * penetrationDepth)
          : static_cast<T>(0);
  const GridGPU<T> vectorPotential =
      *(inContext.getInducedVectorPotential()) * vectorPotentialScale;

  // Compute flux density.
  const T latticeSpacing = inContext.getParameters()->getGridElementSize();
  const GridGPU<T> fluxDensity = vectorPotential.curl(latticeSpacing);

  switch (m_dataFormat) {
#ifdef CONGA_USE_HDF5
  case DataFormat::H5: {
    const std::filesystem::path fileName =
        m_dataPath / std::string("simulation.h5");
    auto file = fileOverWrite(fileName);

    // Write.
    io::write(domain, "domain", file);
    if (m_saveOrderParameter) {
      io::write(orderParameter, "order_parameter", file);
    }
    if (m_saveCurrentDensity) {
      io::write(currentDensity, "current_density", file);
    }
    if (m_saveVectorPotential) {
      io::write(vectorPotential, "vector_potential", file);
    }
    if (m_saveFluxDensity) {
      io::write(fluxDensity, "magnetic_flux_density", file);
    }
    if (m_saveImpuritySelfEnergy && impuritySelfEnergy) {
      io::write(*impuritySelfEnergy, "impurity_self_energy", file);
    }

    // Can it never fail?
    const bool success = true;
    printWrite(m_verbose, success, "all simulation data", fileName);
    break;
  }
#endif // CONGA_USE_HDF5
  case DataFormat::CSV: {
    // CSV is the default.
  }
  default: {
    // Write domain.
    {
      const std::filesystem::path fileName = m_dataPath / "domain.csv";
      const bool success = io::write(domain, {"domain"}, fileName);
      printWrite(m_verbose, success, "domain", fileName);
    }

    // Write order parameter.
    if (m_saveOrderParameter) {
      // This is an ugly hack due to the CSVWriter not accepting an order
      // parameter as input.
      const GridGPU<T> &orderParameterGrid =
          *(inContext.getComputeOrderParameter()->getResult());
      const std::filesystem::path fileName = m_dataPath / "order_parameter.csv";
      const bool success =
          io::write(orderParameterGrid, orderParameter.getTypes(), fileName);
      printWrite(m_verbose, success, "order parameter", fileName);
    }

    // Write curent density.
    if (m_saveCurrentDensity) {
      const std::filesystem::path fileName = m_dataPath / "current_density.csv";
      const bool success = io::write(currentDensity, {"j_x", "j_y"}, fileName);
      printWrite(m_verbose, success, "current density", fileName);
    }

    // Write vector potential.
    if (m_saveVectorPotential) {
      const std::filesystem::path fileName =
          m_dataPath / "vector_potential.csv";
      const bool success = io::write(vectorPotential, {"a_x", "a_y"}, fileName);
      printWrite(m_verbose, success, "vector potential", fileName);
    }

    // Write impurity self-energy.
    if (m_saveImpuritySelfEnergy && impuritySelfEnergy) {
      // Sigma.
      {
        const std::filesystem::path fileName =
            m_dataPath / "impurity_self_energy_sigma.csv";
        const bool success =
            io::write(impuritySelfEnergy->sigma, {"sigma"}, fileName);
        printWrite(m_verbose, success, "impurity self-energy sigma", fileName);
      }

      // Delta.
      {
        const std::filesystem::path fileName =
            m_dataPath / "impurity_self_energy_delta.csv";
        const bool success =
            io::write(impuritySelfEnergy->delta, {"delta"}, fileName);
        printWrite(m_verbose, success, "impurity self-energy delta", fileName);
      }
    }

    // Write flux density.
    if (m_saveFluxDensity) {
      const std::filesystem::path fileName =
          m_dataPath / "magnetic_flux_density.csv";
      const bool success = io::write(fluxDensity, {"b_z"}, fileName);
      printWrite(m_verbose, success, "magnetic flux density", fileName);
    }
    break;
  }
  }
}

} // namespace io
} // namespace conga

#endif // CONGA_SIMULATION_WRITER_H_
