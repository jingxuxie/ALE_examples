/**
 * @file    jet_properties.cc
 *
 * @brief   Code for making histograms of several jet properties:
 *          Mass
 *          pT
 *          Energy
 *          ||3-momentum||
 *          Pseudorapidity
 *          Number of constituents
 */


// ---------------------------------
// Basic imports
// ---------------------------------
#include <iostream>
#include <cmath>
#include <locale>
#include <fstream>
#include <sstream>
#include <string.h>
#include <vector>
#include <map>
#include <utility>
#include <stdexcept>

#include <chrono>
using namespace std::chrono;

// for including infinity as an overflow bin
#include <limits>

// ---------------------------------
// HEP imports
// ---------------------------------
#include "Pythia8/Pythia.h"
#include "fastjet/PseudoJet.hh"
#include "fastjet/ClusterSequence.hh"

// Local imports:
#include "../include/general_utils.h"
#include "../include/jet_utils.h"
#include "../include/pythia2fastjet.h"
#include "../include/cmdln.h"
#include "../include/pythia_cmdln.h"

#include "../include/opendata_utils.h"


// Type definition for histograms
typedef std::vector<double> Hist;
// (we are only differential in a single angle)

// =====================================
// Switches, flags, and options
// =====================================
// List of jet properties we want to store
int MAX_N_CONSTITUENTS = 250;
std::vector<std::string> property_names = {"mass", "pT", "energy",
                                        "eta", "n_constituents"};
bool is_logarithmic(std::string prop) {
    return false;
    /* if (str_eq(prop, "mass") or str_eq(prop, "pT") */
    /*         or str_eq(prop, "energy")) */
    /*     return true; */
    /* if (str_eq(prop, "eta") or str_eq(prop, "n_constituents")) */
    /*     return false; */
    /* throw std::runtime_error("Invalid property name " + prop); */
}


// ####################################
// Main
// ####################################
/**
* @brief: Generates events with Pythia and creates EWOC histograms.
*
* @return: int
*/
int main (int argc, char* argv[]) {
    // Printing if told to be verbose
    int verbose = cmdln_int("verbose", argc, argv, 1);

    // Starting timer
    auto start = high_resolution_clock::now();

    // ---------------------------------
    // =====================================
    // Command line setup
    // =====================================
    // ---------------------------------
    // Ensuring valid command line inputs
    if (checkPythiaInputs(argc, argv) == 1) return 1;

    // ---------------------------------
    // Getting command line variables
    // ---------------------------------
    // File to which we want to write
    const std::string file_prefix = cmdln_string("file_prefix",
                                                 argc, argv, "");

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Basic Pythia Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // 50k e+ e=:=> hadrons events, by default
    const int         n_events      = cmdln_int("n_events",
                                          argc, argv,
                                          _NEVENTS_DEFAULT);
    const int         pid_1         = cmdln_int("pid_1", argc, argv,
                                          _PID_1_DEFAULT);
    const int         pid_2         = cmdln_int("pid_2", argc, argv,
                                          _PID_2_DEFAULT);
    const std::string outstate_str  = cmdln_string("outstate",
                                          argc, argv,
                                          _OUTSTATE_DEFAULT);

    const bool is_proton_collision = (pid_1 == 2212 and
                                      pid_2 == 2212);

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Output Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Whether to output hist in a mathematica friendly format
    const bool mathematica_format = cmdln_bool("mathematica",
                                               argc, argv, false);
    const std::string HIST_DELIM = mathematica_format ?  " " : ", ";
    const std::string file_ext   = mathematica_format ?  ".txt"
                                                      : ".py";

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Input Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const bool use_opendata = cmdln_bool("use_opendata", argc, argv,
                                         true);

    const bool charged_only = cmdln_bool("charged_only",
                                         argc, argv, false);

    const bool smear_momenta = cmdln_bool("smear_momenta",
                                          argc, argv, false);

    double photon_smear_factor  = 0,
           charged_smear_factor = 0,
           neutral_smear_factor = 0;

    if (charged_only)
        std::cout << "Charged particles only." << std::endl;
    if (smear_momenta)
        std::cout << "Smearing momenta roughly commensurate w/CMS "
                  << "(2402.13864)." << std::endl;

    if (smear_momenta) {
        photon_smear_factor = CMS_PHOTON_SMEAR_FACTOR;
        charged_smear_factor = CMS_CHARGED_SMEAR_FACTOR;
        neutral_smear_factor = CMS_NEUTRAL_SMEAR_FACTOR;
    }

    if (use_opendata && charged_only) {
        throw std::invalid_argument("Cannot do ''charged_only'' "
               "analysis with CMS open data: "
               "Particle IDs are not stored in the local dataset.");
    }
    if (use_opendata && smear_momenta) {
        throw std::invalid_argument("Cannot smear CMS open data: "
               "Particle IDs are not stored in the local dataset.");
    }


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Jet Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const double              jet_rad    = cmdln_double("jet_rad",
                                             argc, argv,
                                             is_proton_collision
                                             ? CMS_R_JET
                                         : 1000.);
    const std::string         jet_alg    = jetalgstr_cmdln(
                                              argc, argv,
                                              CMS_JET_ALG);
    const RecombinationScheme jet_recomb = jetrecomb_cmdln(
                                              argc, argv);

    // Number of inclusive jets
    const int n_exclusive_jets           = cmdln_int(
                                              "n_exclusive_jets",
                                              argc, argv, -1);
    // i.e. max number of jets per event to include in analysis
    // (Ordered by energy, e.g. 1 = leading jet. -1 = all jets)
    // (Default is -1, i.e. fully inclusive)
    // (does not override pt_min/pt_max options, below:)

    const double pt_min  = cmdln_double("pt_min", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_PT_MIN/1.5
                                 : _PTMIN_DEFAULT);
    const double pt_max  = cmdln_double("pt_max", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_PT_MAX*1.5
                                 : _PTMAX_DEFAULT);

    // Require |eta| < eta_cut, but only for proton-proton collisions
    const double eta_cut = cmdln_double("eta_cut",
                                 argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_ETA_CUT
                                 : -1.0);

    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    // Histogram Settings
    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    const int   nbins  = cmdln_int("nbins", argc, argv, 500, false);

    const double E_min = cmdln_double("E_min", argc, argv,
                                      0, false);
    const double m_min = cmdln_double("m_min", argc, argv,
                                      0, false);

    const double pt_min_bin = cmdln_int("pt_min_bin", argc, argv,
                                        pt_min, false);
    const double pt_max_bin = cmdln_int("pt_max_bin", argc, argv,
                                        3500, false);
    const double E_max_bin = cmdln_double("E_max_bin", argc, argv,
                                          2*pt_max_bin, false);
    const double m_max_bin = cmdln_double("m_max_bin", argc, argv,
                                          2*pt_max_bin, false);

    const bool uflow = charged_only or smear_momenta;
    const bool oflow = true;


    // Initializing bin edges and centers
    // Setting up under/overflow for mass, pT, energy
    int nbins_finite = nbins, bins_finite_start = 0;
    if (uflow) {nbins_finite -= 1; bins_finite_start += 1;}
    if (oflow) nbins_finite -= 1;

    std::map<std::string, std::vector<double>> bin_centers;
    std::map<std::string, std::vector<double>> bin_edges;

    bin_centers.insert(std::pair("mass",
            get_bin_centers(m_min, m_max_bin, nbins, uflow, oflow)));
    bin_centers.insert(std::pair("pT",
            get_bin_centers(pt_min_bin, pt_max_bin, nbins,
                            uflow, oflow)));
    bin_centers.insert(std::pair("energy",
            get_bin_centers(E_min, E_max_bin, nbins, uflow, oflow)));
    bin_centers.insert(std::pair("eta",
            get_bin_centers(-eta_cut, eta_cut, nbins,
                            false, false)));
    bin_centers.insert(std::pair("n_constituents",
            get_bin_centers(-0.5, MAX_N_CONSTITUENTS+0.5,
                            MAX_N_CONSTITUENTS+1,
                            false, false)));

    bin_edges.insert(std::pair("mass",
            get_bin_edges(m_min, m_max_bin, nbins, uflow, oflow)));
    bin_edges.insert(std::pair("pT",
            get_bin_edges(pt_min_bin, pt_max_bin, nbins, uflow, oflow)));
    bin_edges.insert(std::pair("energy",
            get_bin_edges(E_min, E_max_bin, nbins, uflow, oflow)));
    bin_edges.insert(std::pair("eta",
            get_bin_edges(-eta_cut, eta_cut, nbins,
                            uflow, oflow)));
    bin_edges.insert(std::pair("n_constituents",
            get_bin_edges(-0.5, MAX_N_CONSTITUENTS+0.5,
                          MAX_N_CONSTITUENTS+1,
                          uflow, oflow)));

    // =====================================
    // Output Setup
    // =====================================
    // Set up histograms
    std::map<std::string, Hist> jet_properties;
    std::map<std::string, std::string> filenames;

    for (auto prop : property_names) {
        // Setting up histograms
        Hist hist (str_eq(prop, "n_constituents") ?
                        MAX_N_CONSTITUENTS+1 : nbins);
        jet_properties.insert(std::pair(prop, hist));

        // Setting up output files
        std::string filename = "output/jet_properties/";
        if (!str_eq(file_prefix, ""))
            filename += file_prefix+"_";
        filename += prop;
        filename += file_ext;
        filenames.insert(std::pair(prop, filename));
        // Write a header
        write_jetproperty_header(filename, argc, argv,
                                 not(mathematica_format));
    }

    // =====================================
    // Event Generation Setup
    // =====================================
    // Usual output stream (std::cout)
    std::streambuf *old = std::cout.rdbuf();

    // ---------------------------------
    // Pythia
    // ---------------------------------
    // Declarations (muting Pythia banner)
    std::stringstream pythiastream; pythiastream.str("");
    if (verbose < 3)
        // Muting Pythia banner
        std::cout.rdbuf(pythiastream.rdbuf());

    Pythia8::Pythia pythia;  // Declaring Pythia8

    std::cout.rdbuf(old);    // Restore std::cout
    if (not use_opendata) {
        std::cout << "Setting up pythia" << std::endl;
        // Setting up pythia based on command line arguments
        setup_pythia_cmdln(pythia, argc, argv);
    }

    // ---------------------------------
    // FastJet
    // ---------------------------------
    const JetDefinition jet_def = process_JetDef(jet_alg, jet_rad,
                                                 jet_recomb);

    // ---------------------------------
    // CMS Open Data
    // ---------------------------------
    od::EventReader cms_jet_reader(od::cms_jets_file);

    // ---------------------------------
    // =====================================
    // Analyzing events
    // =====================================
    // ---------------------------------

    // Initializing total number of jets,
    //   summed over all events
    //   (used to normalize the histogram)
    int njets_tot = 0;

    // Initializing particles, good_jets, sorted angles and weights
    std::vector<PseudoJet> particles;
    std::vector<PseudoJet> all_jets;
    std::vector<PseudoJet> good_jets;

    bool passes_cuts;

    // Reserving memory
    particles.reserve(150);
    all_jets.reserve(20);
    good_jets.reserve(5);

    // =====================================
    // Looping over events
    // =====================================
    for (int iev = 0; iev < n_events; ++iev){
        progressbar(static_cast<double>(iev+1)/
                    double(n_events));

        // -#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-
        // Jet finding (with cuts)
        // -#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-
        good_jets.clear();
        std::unique_ptr<ClusterSequence> cluster_seq_ptr = nullptr;

        // -----------------------------------------
        // CMS Open Data (gives jets from the start)
        // -----------------------------------------
        if (use_opendata) {
            PseudoJet jet;
            cms_jet_reader.read_jet(jet);
            good_jets.emplace_back(std::move(jet));
        } else {
        // -----------------------------------------
        // If using Pythia, find jets manually
        // -----------------------------------------
            // Considering next event, if valid
            if(!pythia.next()) continue;

            // Initializing particles for this event
            particles.clear();
            particles = get_particles_pythia(pythia.event,
                    photon_smear_factor, charged_smear_factor,
                    neutral_smear_factor);

            // Initializing jets
            if (iev == 0) {  // Muting FastJet banner
                std::stringstream fastjetstream; fastjetstream.str("");
                // Starting fastjet; redirect output
                std::cout.rdbuf(fastjetstream.rdbuf());
            }


            cluster_seq_ptr = std::make_unique
                    <ClusterSequence>(particles, jet_def);

            if (iev == 0) {
                std::cout.rdbuf(old);  // Restore std::cout
            }

            // ---------------------------------
            // Jet finding (with cuts)
            // ---------------------------------
            if (jet_rad < 1000) {
                // If given a generic value of R,
                // cluster the event with the given jet definition
                all_jets = sorted_by_pt(
                        cluster_seq_ptr->inclusive_jets(pt_min));
            } else {
                // If we are given the maximum possible value of R,
                // use the whole event as a single "jet"
                PseudoJet full_event;
                for (auto part : particles)
                    if (part.modp() > 0)
                        full_event = join(full_event, part);

                all_jets.push_back(std::move(full_event));
            }

            // Getting all jets which satisfy other requirements
            for (size_t i = 0; i < all_jets.size()
                               &&
                // Only working up to the Nth jet if doing exclusive analysis
                     (n_exclusive_jets <= 0
                      ||
                      i < static_cast<size_t>(n_exclusive_jets));
             ++i) {
                const PseudoJet& jet = all_jets[i];
                passes_cuts = false;

                // Adding jets that satisfy certain criteria to good jets list
                if (is_proton_collision) {
                    // For pp, ensuring pt_min < pt < pt_max
                    // and |eta| < eta_cut   (or no eta_cut given)
                    if (pt_min <= jet.pt() and jet.pt() <= pt_max
                            and (abs(jet.eta()) <= eta_cut
                                 or eta_cut < 0)) {
                        passes_cuts = true;
                    }
                } else {
                    // For other collisions, E_min < E < E_max
                    // (note the confusing notation with, e.g.,
                    //  E_min represented by `pt_min` below)
                    if (pt_min <= jet.E() and jet.E() <= pt_max) {
                        passes_cuts = true;
                    }
                }

                // If we have a jet that passes cuts
                if (passes_cuts) {
                    // If we only want charged, remove neutrals
                    if (charged_only) {
                        good_jets.push_back(
                                create_charged_jet(jet));
                    } else {
                        good_jets.push_back(jet);
                    }
                }
            }

            all_jets.clear();
        }

        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // Loop on jets
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        for (const auto& jet : good_jets) {
        try {
            const double num  = jet.constituents().size();
            const double mass = jet.m() > 0 ? jet.m() : 0;
            const double pT   = jet.pt();
            const double E    = jet.e();
            const double eta  = jet.eta();

            // Histogramming properties of this jet
            jet_properties["n_constituents"][bin_position(num,
                                   -0.5, MAX_N_CONSTITUENTS+0.5,
                                   MAX_N_CONSTITUENTS+1, "lin",
                                   false, false)]
                += 1;
            jet_properties["mass"][bin_position(mass,
                                   m_min, m_max_bin,
                                   nbins, "lin", uflow, oflow)]
                += 1;
            jet_properties["pT"][bin_position(pT,
                                   pt_min_bin, pt_max_bin,
                                   nbins, "lin", uflow, oflow)]
                += 1;
            jet_properties["energy"][bin_position(E,
                                   E_min, E_max_bin,
                                   nbins, "lin", uflow, oflow)]
                += 1;
            jet_properties["eta"][bin_position(eta,
                                   -eta_cut, eta_cut,
                                   nbins, "lin", uflow, oflow)]
                += 1;

            // Counting total num jets for normalization
            ++njets_tot;
        } catch (const fastjet::Error& ex) {
            // ending try statement (sometimes I find empty jets)
            std::cerr << "Warning: FastJet: " << ex.message()
                      << std::endl;
            continue;
        }
        } // end loop on jets
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    } // end event loop
    // =====================================

    // =====================================
    // Writing output files
    // =====================================
    for (auto& prop : property_names) {
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Opening histogram output file
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        std::fstream outfile;
        outfile.open(filenames[prop], std::ios_base::in |
                                      std::ios_base::out |
                                      std::ios_base::app);

        // Checking for existence
        if (!outfile.is_open()) {
            std::stringstream errMsg;
            errMsg << "File for jet property output was expected "
                   << "to be open, but was not open.\n\n"
                   << "It is possible the file was unable to "
                   << "be created at the desired location:\n\n\t"
                   << "filename = " << filenames[prop] << "\n\n"
                   << "Is the filename an absolute path? If not, "
                   << "that might be the problem.";
            throw std::runtime_error(errMsg.str().c_str());
        }

        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // Writing to files
        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        if (not(mathematica_format))
            outfile << prop << "_edges = [\n\t";
        else outfile << "(* " << prop << "_edges *)\n";

        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Edges
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        for (int ibin = 0; ibin < nbins; ++ibin)
            if (is_logarithmic(prop))
                outfile << std::pow(10, bin_edges[prop][ibin])
                        << HIST_DELIM;
            else
                outfile << bin_edges[prop][ibin] << HIST_DELIM;
        if (std::isinf(bin_edges[prop][nbins])
                and not(mathematica_format))
            outfile << "np.inf\n";
        else
            if (is_logarithmic(prop))
                outfile << std::pow(10, bin_edges[prop][nbins])
                        << "\n";
            else
                outfile << bin_edges[prop][nbins] << "\n";
        if (not(mathematica_format)) outfile << "]\n\n";


        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Centers
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        if (not(mathematica_format))
            outfile << prop << "_centers = [\n\t";
        else outfile << "\n(* " << prop << "_centers *)\n";

        for (int ibin = 0; ibin < nbins-1; ++ibin)
            if (is_logarithmic(prop))
                outfile << std::pow(10, bin_centers[prop][ibin])
                        << HIST_DELIM;
            else
                outfile << bin_centers[prop][ibin]
                        << HIST_DELIM;
        if (std::isinf(bin_centers[prop][nbins-1]) and
                not(mathematica_format))
            outfile << "np.inf\n";
        else
            if (is_logarithmic(prop))
                outfile << std::pow(10, bin_centers[prop][nbins-1])
                        << "\n";
            else
                outfile << bin_centers[prop][nbins-1]
                        << "\n";

        if (not(mathematica_format)) outfile << "]\n\n";


        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Histogram
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        if (not(mathematica_format))
            outfile << "hist = [\n\t";
        else outfile << "\n(* " << prop << " hist *)\n";

        for (size_t bin=0; bin<jet_properties[prop].size(); ++bin){
            // Expectation values over N jets
            jet_properties[prop][bin] /= njets_tot;

            // Not normalizing outflow bins further
            // If not in an outflow bin
            if (not(is_logarithmic(prop) and
                    (int(bin) < bins_finite_start
                     or int(bin) >= nbins_finite))) {
                // getting differential "volume" element
                double dvol = (bin_edges[prop][bin+1]-bin_edges[prop][bin]);
                // and normalizing
                jet_properties[prop][bin] /= dvol;
            }

            // Printing histogram
            outfile << std::setprecision(10)
                    << jet_properties[prop][bin];
            if (bin != jet_properties[prop].size() - 1)
                outfile << HIST_DELIM;
            else
                outfile << "\n";
        }
        if (not(mathematica_format)) outfile << "]\n\n";

        outfile.close();
    }

    // =====================================
    // Verifying successful run
    // =====================================
    if (verbose >= 0) {
        std::cout << "\nComplete!\n";
        auto stop = high_resolution_clock::now();
        auto duration = duration_cast<microseconds>(stop-start);
        std::cout << "Analyzed and saved data from "
                  << std::to_string(n_events)
                  << " events in "
                  << std::to_string(float(duration.count())/std::pow(10, 6))
                  << " seconds.\n";
    }

    return 0;
}
