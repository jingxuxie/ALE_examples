//===----------- main.cu - Main file for setting up simulations -----------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// This is the main file for setting up simulations. Never modify this file
/// directly. Instead, to set up a simulation, specify a parameter file, and/or
/// use command-line flags. The main file parses these in turn, and sets up a
/// self-consistent simulation in a confined geometry. For more advanced
/// simulations, create a new main file.
///
//===----------------------------------------------------------------------===//

#include "conga/BulkSolver.h"
#include "conga/Context.h"
#include "conga/Parameters.h"
#include "conga/Type.h"
#include "conga/accelerators.h"
#include "conga/boundary/BoundaryConditionSpecular.h"
#include "conga/compute/ComputeCurrent.h"
#include "conga/compute/ComputeFreeEnergy.h"
#include "conga/compute/ComputeImpuritySelfEnergy.h"
#include "conga/compute/ComputeOrderParameter.h"
#include "conga/compute/ComputeVectorPotential.h"
#include "conga/configure.h"
#include "conga/geometry/GeometryGroup.h"
#include "conga/geometry/geometry_utils.h"
#include "conga/impurities/ImpuritySelfEnergy.h"
#include "conga/integration/IntegrationIteratorOzaki.h"
#include "conga/io.h"
#include "conga/order_parameter/OrderParameter.h"
#include "conga/riccati/RiccatiSolverConfined.h"
#include "conga/run_simulation.h"

#ifdef CONGA_VISUALIZE
#include "conga/visualization/Visualizer.h"
#endif // CONGA_VISUALIZE

#include <json/json.h>

#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <string>
#include <utility>
#include <vector>

//*******************************************************
// PRECISION
//*******************************************************
#ifdef CONGA_SINGLE_PRECISION
typedef float T;
#else
typedef double T;
#endif

/// @brief Helper function to parse the order-parameter from the JSON
/// configuration file.
/// @param inJSON The order-parameter part of the configuration file.
/// @param inCoordinateTransform The transform from user defined geometry to
/// internal coordinate system.
/// @return A vector of ComponentOptions used to initialize the order-parameter
/// components.
std::vector<conga::ComponentOptions<T>> parseOrderParameterJSON(
    const Json::Value &inJSON,
    const conga::geometry::CoordinateTransform<T> &inCoordinateTransform);

//*******************************************************
// MAIN
//*******************************************************
int main(int argc, char *argv[]) {
  //*******************************************************
  // PARSE SIMULATION CONFIG FILE
  //*******************************************************
  Json::Value simulationConfig;
  {
    if (argc < 2) {
      std::cerr << "-- ERROR! Please provide a config file." << std::endl;
      return EXIT_FAILURE;
    }
    const std::filesystem::path configPath = argv[1];
    const bool success = conga::io::read(configPath, simulationConfig);
    if (!success) {
      std::cerr << "-- ERROR! Could not find/open config file '" << configPath
                << "'." << std::endl;
      return EXIT_FAILURE;
    }
#ifndef NDEBUG
    std::cout << "-- Simulation configuration parameters:" << std::endl;
    std::cout << simulationConfig << std::endl;
#endif
  }

  // TODO(niclas): Add sanity check of all parameters here!?

  // Fetch the verbosity so we know whether to print stuff or not.
  const bool verbose = simulationConfig["misc"]["verbose"].asBool();

  //***************************************************
  // CREATE CONTEXT
  //***************************************************
  conga::Context<T> context;

  //***************************************************
  // APPLY PARAMETERS
  //***************************************************
  // Storage for system simulation parameters (e.g. temperature, lattice size).
  conga::Parameters<T> *parameters = new conga::Parameters<T>(&context);

  // Set temperature.
  const T temperature =
      static_cast<T>(simulationConfig["physics"]["temperature"].asDouble());
  parameters->setTemperature(temperature);

  // Set the number of lattice points per coherence length.
  const T pointsPerCoherenceLength = static_cast<T>(
      simulationConfig["numerics"]["points_per_coherence_length"].asDouble());
  parameters->setPointsPerCoherenceLength(pointsPerCoherenceLength);

  // Set energy cutoff.
  const T energyCutoff =
      static_cast<T>(simulationConfig["numerics"]["energy_cutoff"].asDouble());
  parameters->setEnergyCutoff(energyCutoff);

  // Number of discrete steps in momentum angle.
  const int numFermiMomenta =
      simulationConfig["numerics"]["num_fermi_momenta"].asInt();
  parameters->setAngularResolution(numFermiMomenta);

  // Set convergence criterion.
  const T convergenceCriterion = static_cast<T>(
      simulationConfig["numerics"]["convergence_criterion"].asDouble());
  parameters->setConvergenceCriterion(convergenceCriterion);

  // Set penetration depth.
  const T penetrationDepth = static_cast<T>(
      simulationConfig["physics"]["penetration_depth"].asDouble());
  parameters->setPenetrationDepth(penetrationDepth);

  // Set external magnetic field strength.
  const T externalFluxQuanta = static_cast<T>(
      simulationConfig["physics"]["external_flux_quanta"].asDouble());
  parameters->setNumFluxQuanta(externalFluxQuanta);

  // Set sign of charge.
  const int chargeSign = simulationConfig["physics"]["charge_sign"].asInt();
  parameters->setChargeSign(chargeSign);

  // The impurity scattering energy.
  const T scatteringEnergy = static_cast<T>(
      simulationConfig["physics"]["scattering_energy"].asDouble());
  parameters->setScatteringEnergy(scatteringEnergy);

  // The impurity scattering phase shift.
  if (scatteringEnergy > static_cast<T>(0)) {
    const T scatteringPhaseShift = static_cast<T>(
        2.0 * M_PI *
        simulationConfig["physics"]["scattering_phase_shift"].asDouble());
    parameters->setScatteringPhaseShift(scatteringPhaseShift);
  }

  // Set which norm to use when computing residuals.
  const std::string residualNorm(
      simulationConfig["numerics"]["norm"].asString());
  if (residualNorm == "l1") {
    parameters->setResidualNormType(conga::ResidualNorm::L1);
  } else if (residualNorm == "l2") {
    parameters->setResidualNormType(conga::ResidualNorm::L2);
  } else if (residualNorm == "linf") {
    parameters->setResidualNormType(conga::ResidualNorm::LInf);
  } else {
    std::cerr << "-- ERROR! Norm type, " << residualNorm << ", not understood"
              << std::endl;
    return EXIT_FAILURE;
  }

  //***************************************************
  // CREATE GEOMETRY
  //***************************************************
  // Parse user-defined geometry. Compute the transformation to internal
  // coordinate system.
  const conga::geometry::CoordinateTransform<T> coordinateTransform =
      conga::geometry::computeCoordinateTransform<T>(simulationConfig);

  // Set grain sidelength in coherence length.
  parameters->setGrainWidth(coordinateTransform.sideLength());

  // Fetch relative size of geometry to available simulation space, to account
  // for padding for boundary interpolation.
  const T grainFraction = parameters->getGrainFraction();

  // Create geometry group: add/remove geometry objects (e.g. discs, polygons)
  // from the geometry group.
  conga::GeometryGroup<T> *geometry = new conga::GeometryGroup<T>(&context);

  // Parse user-defined geometry, loop through geometry component list and
  // create compund geometry. Scale and translate to internal coordinate system.
  conga::geometry::addGeometryComponents(geometry, simulationConfig,
                                         coordinateTransform, grainFraction);

  //***************************************************
  // PARSE ORDERPARAMETER COMPONENTS FROM JSON
  //***************************************************
  auto orderParameterOptions = parseOrderParameterJSON(
      simulationConfig["physics"]["order_parameter"], coordinateTransform);
  if (orderParameterOptions.empty()) {
    std::cerr << "-- ERROR! No order-parameter component set." << std::endl;
    return EXIT_FAILURE;
  }

  //***************************************************
  // SOLVE BULK PROBLEM
  //***************************************************
  conga::BulkSolver<T> bulkSolver(parameters->getTemperature(),
                                  parameters->getEnergyCutoff(),
                                  parameters->getAngularResolution());
  bulkSolver.scatteringEnergy(parameters->getScatteringEnergy());
  bulkSolver.scatteringPhaseShift(parameters->getScatteringPhaseShift());
  for (const auto &options : orderParameterOptions) {
    const T initialPhaseShift = thrust::arg(options.initialValue());
    bulkSolver.addOrderParameterComponent(
        options.symmetry(), options.criticalTemperature(), initialPhaseShift);
  }
  const bool successBulk =
      bulkSolver.compute(parameters->getConvergenceCriterion());
  // TODO(Niclas): Use successBulk.

  //***************************************************
  // SET UP ORDER PARAMETER
  //***************************************************
  // Create order parameter (which might contain multiple components, i.e.
  // d+is).
  conga::OrderParameter<T> *orderParameter =
      new conga::OrderParameter<T>(&context);

  // Set rotation of crystal axes with respect to the grain geometry.
  const T crystalAxesRotation = static_cast<T>(
      2.0 * M_PI *
      simulationConfig["physics"]["crystal_axes_rotation"].asDouble());
  orderParameter->setCrystalAxesRotation(crystalAxesRotation);

  // Add all order-parameter components.
  for (auto &options : orderParameterOptions) {
    const thrust::complex<T> bulkValue =
        bulkSolver.orderParameterComponent(options.symmetry());
    orderParameter->addComponent(options.initialValue(bulkValue));
  }

  //***************************************************
  // SET IMPURITY SELF-ENERGY
  //***************************************************
  if (scatteringEnergy > static_cast<T>(0)) {
    const int gridResolution = parameters->getGridResolutionBase();
    const int numEnergies = parameters->getNumOzakiEnergies();
    auto impuritySelfEnergy = std::make_unique<conga::ImpuritySelfEnergy<T>>(
        gridResolution, gridResolution, numEnergies);
    const auto [impSigma, impDelta, impDeltaTilde] =
        bulkSolver.impuritySelfEnergy();
    impuritySelfEnergy->set(impSigma, impDelta, impDeltaTilde);
    context.set(std::move(impuritySelfEnergy));
  }

  //***************************************************
  // READ ORDER PARAMETER, VECTOR POTENTIAL, AND IMPURITY SELF-ENERGY FROM FILE
  //***************************************************
  // Path to directory containing data to load from.
  const std::filesystem::path loadDataPath(
      simulationConfig["misc"]["load_path"].asString());

  if (!loadDataPath.empty()) {
    // Create the placeholders for the vector potential and the impurity
    // self-energy.
    const int gridResolution = parameters->getGridResolutionBase();
    const int numEnergies = parameters->getNumOzakiEnergies();
    auto vectorPotential = std::make_unique<conga::GridGPU<T>>(
        gridResolution, gridResolution, 2, conga::Type::real);
    auto impuritySelfEnergy = std::make_unique<conga::ImpuritySelfEnergy<T>>(
        gridResolution, gridResolution, numEnergies);

    bool successOrderParameter = false;
    bool successVectorPotential = false;
    bool successImpuritySelfEnergy = false;

#ifdef CONGA_USE_HDF5
    // Check if the simulation file exists.
    const std::filesystem::path simulationDataPath =
        loadDataPath / "simulation.h5";
    const bool simulationExists = std::filesystem::exists(simulationDataPath);
    if (simulationExists) {
      // Open file.
      const auto file = conga::io::fileReadOnly(simulationDataPath);

      // Read order parameter.
      successOrderParameter =
          conga::io::read(file, "order_parameter", *orderParameter);
      conga::io::printRead(verbose, successOrderParameter, "order parameter",
                           simulationDataPath);

      // Read vector potential.
      successVectorPotential =
          conga::io::read(file, "vector_potential", *vectorPotential);
      conga::io::printRead(verbose, successVectorPotential, "vector potential",
                           simulationDataPath);

      // Read impurity self-energy.
      if (scatteringEnergy > static_cast<T>(0)) {
        successImpuritySelfEnergy =
            conga::io::read(file, "impurity_self_energy", *impuritySelfEnergy);
        conga::io::printRead(verbose, successImpuritySelfEnergy,
                             "impurity self-energy", simulationDataPath);
      }

    } else
#endif // CONGA_USE_HDF5
    {
      // Read order parameter.
      const std::filesystem::path orderParameterPath =
          loadDataPath / "order_parameter.csv";
      successOrderParameter =
          conga::io::read(orderParameterPath, *orderParameter);
      conga::io::printRead(verbose, successOrderParameter, "order parameter",
                           orderParameterPath);

      // Read vector potential.
      const std::filesystem::path vectorPotentialPath =
          loadDataPath / "vector_potential.csv";
      const bool vectorPotentialEverywhere = true;
      successVectorPotential =
          conga::io::read(vectorPotentialPath, {"a_x", "a_y"},
                          vectorPotentialEverywhere, *vectorPotential);
      conga::io::printRead(verbose, successVectorPotential, "vector potential",
                           vectorPotentialPath);

      // Read impurity self-energy.
      if (scatteringEnergy > static_cast<T>(0)) {
        const bool impuritiesEverywhere = false;

        const std::filesystem::path impuritySelfEnergySigmaPath =
            loadDataPath / "impurity_self_energy_sigma.csv";
        const bool successImpuritySelfEnergySigma = conga::io::read(
            impuritySelfEnergySigmaPath, {"sigma_re", "sigma_im"},
            impuritiesEverywhere, impuritySelfEnergy->sigma);
        conga::io::printRead(verbose, successImpuritySelfEnergySigma,
                             "impurity self-energy sigma",
                             impuritySelfEnergySigmaPath);

        const std::filesystem::path impuritySelfEnergyDeltaPath =
            loadDataPath / "impurity_self_energy_delta.csv";
        const bool successImpuritySelfEnergyDelta = conga::io::read(
            impuritySelfEnergyDeltaPath, {"delta_re", "delta_im"},
            impuritiesEverywhere, impuritySelfEnergy->delta);
        conga::io::printRead(verbose, successImpuritySelfEnergyDelta,
                             "impurity self-energy delta",
                             impuritySelfEnergyDeltaPath);

        successImpuritySelfEnergy =
            successImpuritySelfEnergySigma && successImpuritySelfEnergyDelta;
      }
    }

    // Abort if not successful.
    if (!successOrderParameter) {
      std::cerr << "-- ERROR! Could not find order parameter in "
                << loadDataPath << std::endl;
      return EXIT_FAILURE;
    }

    // Abort if not successful.
    if (!successVectorPotential) {
      std::cerr << "-- ERROR! Could not find vector potential in "
                << loadDataPath << std::endl;
      return EXIT_FAILURE;
    }

#ifndef NDEBUG
    // Warn if not successful.
    if (!successImpuritySelfEnergy && (scatteringEnergy > static_cast<T>(0))) {
      std::cerr << "-- WARNING! Could not find impurity self-energy in "
                << loadDataPath << std::endl;
    }
#endif

    // Set the vector potential in context.
    if (penetrationDepth > static_cast<T>(0)) {
      // Internally the induced vector potential is scaled by the squared
      // penetration depth.
      *vectorPotential *= (penetrationDepth * penetrationDepth);
    } else {
      vectorPotential->setZero();
    }
    context.set(std::move(vectorPotential));

    // Set the impurity self-energy in context.
    if (successImpuritySelfEnergy) {
      context.set(std::move(impuritySelfEnergy));
    }
  }

  //***************************************************
  // SET UP INTEGRATOR
  //***************************************************
  // A negative number means doing all of them at once.
  const int numEnergiesPerBlock =
      simulationConfig["numerics"]["num_energies_per_block"].asInt();
  new conga::IntegrationIteratorOzaki<T>(&context, numEnergiesPerBlock);

  //***************************************************
  // ACCELERATOR
  //***************************************************
  // Get the name.
  const std::string acceleratorName(
      simulationConfig["accelerator"]["name"].asString());

  // Make accelerator.
  std::unique_ptr<conga::accelerators::Accelerator<T>> accelerator;
  if (acceleratorName == "anderson") {
    // Create Anderson accelerator.
    accelerator = std::make_unique<conga::accelerators::Anderson<T>>(
        simulationConfig["accelerator"]);
  } else if (acceleratorName == "barzilai-borwein" || acceleratorName == "bb") {
    // Create Barzilai-Borwein accelerator.
    accelerator = std::make_unique<conga::accelerators::BarzilaiBorwein<T>>(
        simulationConfig["accelerator"]);
  } else if (acceleratorName == "congacc") {
    // Create CongAcc accelerator.
    accelerator = std::make_unique<conga::accelerators::CongAcc<T>>(
        simulationConfig["accelerator"]);
  } else if (acceleratorName == "picard") {
    // Create Picard accelerator.
    accelerator = std::make_unique<conga::accelerators::Picard<T>>(
        simulationConfig["accelerator"]);
  } else if (acceleratorName == "polyak") {
    // Create Polyak accelerator.
    accelerator = std::make_unique<conga::accelerators::Polyak<T>>(
        simulationConfig["accelerator"]);
  } else {
    std::cerr << "-- ERROR! Accelerator name, " << acceleratorName
              << ", not understood" << std::endl;
    return EXIT_FAILURE;
  }

  // Move to context.
  context.set(std::move(accelerator));

  //***************************************************
  // CHOOSE QUANTITIES TO CALCULATE
  //***************************************************
  // Order parameter compute object.
  new conga::ComputeOrderParameter<T>(&context);
  // Add current compute object.
  new conga::ComputeCurrent<T>(&context);

  if (scatteringEnergy > static_cast<T>(0)) {
    // Add impurity self-energy compute object.
    new conga::ComputeImpuritySelfEnergy<T>(&context);
#ifndef NDEBUG
    std::cout << "-- WARNING! Computing the free energy with impurities, i.e. "
                 "scattering_energy > 0, is not supported. The free energy "
                 "will not be computed."
              << std::endl;
#endif
  } else {
    // Add free energy compute object.
    // Note, the free energy only works without impurities.
    new conga::ComputeFreeEnergy<T>(&context);
  }

  // Add vector-potential compute object.
  if (penetrationDepth > static_cast<T>(0)) {
    const T maxError = static_cast<T>(
        simulationConfig["numerics"]["vector_potential_error"].asDouble());
    auto computeVectorPotential =
        std::make_unique<conga::ComputeVectorPotential<T>>(maxError);
    context.add(std::move(computeVectorPotential));
  }

  //***************************************************
  // CHOOSE RICCATI SOLVER AND BOUNDARY CONDITIONS
  //***************************************************
  conga::RiccatiSolver<T> *riccatiSolver;

  // Gauge choice.
  const std::string gauge(simulationConfig["physics"]["gauge"].asString());
  if (gauge == "landau") {
    riccatiSolver =
        new conga::RiccatiSolverConfined<T, conga::gauge::Landau>(&context);
  } else if (gauge == "solenoid") {
    riccatiSolver =
        new conga::RiccatiSolverConfined<T, conga::gauge::Solenoid>(&context);
  } else if (gauge == "symmetric") {
    riccatiSolver =
        new conga::RiccatiSolverConfined<T, conga::gauge::Symmetric>(&context);
  } else {
    std::cerr << "-- ERROR! Gauge, " << gauge << ", not understood"
              << std::endl;
    return EXIT_FAILURE;
  }

  // Add specular BC.
  riccatiSolver->add(new conga::BoundaryConditionSpecular<T>);

  //***************************************************
  // INITIALIZE SIMULATION
  //***************************************************
  context.initialize();

  //***********************************************
  // CREATE DIRECTORIES AND SAVE PARAMETERS
  //***********************************************
  const std::filesystem::path saveDataPath(
      simulationConfig["misc"]["save_path"].asString());

  // Set the save frequency. If the argument is negative we only save the grid
  // data at the very end.
  const int saveFrequency = simulationConfig["misc"]["save_frequency"].asInt();

  const bool saveData = !saveDataPath.empty() && (saveFrequency != 0);
  if (saveData) {
    // Create directories.
    std::filesystem::create_directories(saveDataPath);

    // Save config parameters to JSON file.
    const std::filesystem::path configPath =
        saveDataPath / "simulation_config.json";
    conga::io::write(configPath, simulationConfig);
    conga::io::printWrite(verbose, true, "configuration", configPath);

    // TODO(niclas): Write internal parameters here as well? They do not
    // change during the simulation.
  }

  //***********************************************
  // RUN SIMULATION UNTIL END CRITERIA
  //***********************************************
  const int numBurnInIterations =
      simulationConfig["numerics"]["num_iterations_burnin"].asInt();
  const int numIterationsMin =
      simulationConfig["numerics"]["num_iterations_min"].asInt();
  const int numIterationsMax =
      simulationConfig["numerics"]["num_iterations_max"].asInt();
  const conga::io::DataFormat dataFormat = conga::io::getDataFormat(
      simulationConfig["misc"]["data_format"].asString());

  // Make data writers.
  std::unique_ptr<conga::io::CSVIterationWriter<T>> iterationWriter;
  std::unique_ptr<conga::io::SimulationWriter<T>> simulationWriter;
  if (saveData) {
    // Iteration writer for writing residuals and the free energy for each
    // iteration.
    const std::filesystem::path convergencePath =
        saveDataPath / "simulation_convergence.csv";
    iterationWriter =
        std::make_unique<conga::io::CSVSimulationIterationWriter<T>>(
            convergencePath);

    // Simulation writer for saving entire grids, e.g. the order parameter, as
    // well as area averaged quantities.
    simulationWriter = std::make_unique<conga::io::SimulationWriter<T>>(
        saveDataPath, dataFormat, verbose,
        simulationConfig["misc"]["save_order_parameter"].asBool(),
        simulationConfig["misc"]["save_current_density"].asBool(),
        simulationConfig["misc"]["save_vector_potential"].asBool(),
        simulationConfig["misc"]["save_flux_density"].asBool(),
        simulationConfig["misc"]["save_impurity_self_energy"].asBool());
  }

#ifdef CONGA_VISUALIZE
  const bool visualize = simulationConfig["misc"]["visualize"].asBool();
  if (visualize) {
    // Create visualizer.
    const int numOrderParameterComponents =
        context.getOrderParameter()->getNumComponents();
    const conga::GridGPU<char> &domain =
        *(context.getGeometry()->getDomainGrid());
    // Magnitude and xy-components.
    const int rows = 3;

    // Extra columns: current density, vector potential, and flux density.
    const int extraCols = (penetrationDepth > static_cast<T>(0)) ? 3 : 1;
    const int cols = numOrderParameterComponents + extraCols;
    conga::Visualizer<T> visualizer("SuperConga", cols, rows, domain);

    conga::runSimulation(numBurnInIterations, numIterationsMin,
                         numIterationsMax, verbose, iterationWriter.get(),
                         simulationWriter.get(), saveFrequency, visualizer,
                         context);
  } else
#endif // CONGA_VISUALIZE
  {
    conga::runSimulation(numBurnInIterations, numIterationsMin,
                         numIterationsMax, verbose, iterationWriter.get(),
                         simulationWriter.get(), saveFrequency, context);
  }

  // Yay!
  return EXIT_SUCCESS;
}

std::vector<conga::ComponentOptions<T>> parseOrderParameterJSON(
    const Json::Value &inJSON,
    const conga::geometry::CoordinateTransform<T> &inCoordinateTransform) {

  std::vector<conga::ComponentOptions<T>> components;

  for (const std::string &symmetryStr : inJSON.getMemberNames()) {
    // Convert string to enum.
    const auto [successParse, symmetry] = conga::parseSymmetry(symmetryStr);
    if (!successParse) {
      std::cerr << "-- ERROR! Order-parameter component '" << symmetryStr
                << "' not understood." << std::endl;
      continue;
    }

    // For convenience.
    const Json::Value componentJSON = inJSON[symmetryStr];

    conga::ComponentOptions<T> options(symmetry);

    const T initialPhaseShift = static_cast<T>(
        2.0 * M_PI * componentJSON["initial_phase_shift"].asDouble());
    const thrust::complex<T> initialValue(std::cos(initialPhaseShift),
                                          std ::sin(initialPhaseShift));
    options.initialValue(initialValue);
    options.criticalTemperature(
        static_cast<T>(componentJSON["critical_temperature"].asDouble()));
    options.initialNoiseStdDev(
        static_cast<T>(componentJSON["initial_noise_stddev"].asDouble()));

    // Vortices.
    const Json::Value vorticesJSON = componentJSON["vortices"];

    // Initialize order parameter with a guess.
    if (vorticesJSON.size() > 0) {
      std::vector<conga::Vortex<T>> vortices;

      // Scale to internal coordinates and add to vectors.
      for (const Json::Value &vortex : vorticesJSON) {
        const T windingNumber =
            static_cast<T>(vortex["winding_number"].asDouble());
        const auto center = inCoordinateTransform.centerAndScale(
            {static_cast<T>(vortex["center_x"].asDouble()),
             static_cast<T>(vortex["center_y"].asDouble())});

        vortices.push_back(conga::Vortex<T>(windingNumber).center(center));
      }
      options.vortices(vortices);
    }

    // Normal inclusions.
    const Json::Value normalInclusionsJSON = componentJSON["normal_inclusions"];

    // Fetch normal inclusions that locally suppress the transition temperature
    // (i.e. coupling constant).
    if (normalInclusionsJSON.size() > 0) {
      std::vector<conga::NormalInclusion<T>> normalInclusions;

      // Scale to internal coordinates and add to vectors.
      for (const Json::Value &normalInclusion : normalInclusionsJSON) {
        const T radius = inCoordinateTransform.scale(
            static_cast<T>(normalInclusion["radius"].asDouble()));
        const T strength =
            static_cast<T>(normalInclusion["strength"].asDouble());
        const auto center = inCoordinateTransform.centerAndScale(
            {static_cast<T>(normalInclusion["center_x"].asDouble()),
             static_cast<T>(normalInclusion["center_y"].asDouble())});

        normalInclusions.push_back(
            conga::NormalInclusion<T>(radius, strength).center(center));
      }
      options.normalInclusions(normalInclusions);
    }

    components.push_back(options);
  }

  return components;
}
