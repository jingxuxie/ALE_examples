/**
 * @file    penc.cc
 *
 * @brief   Code for generating histograms for "new angles on"
 *          n-point projected energy correlators (PENCs).
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

#include "../include/cmdln.h"
#include "../include/pythia2fastjet.h"
#include "../include/pythia_cmdln.h"
#include "../include/enc_utils.h"
#include "../include/opendata_utils.h"
#include "../include/PENC.h"


// ####################################
// Main
// ####################################
/**
* @brief: Generates events with Pythia and creates PENC histograms.
*
* @return: int
*/
int main (int argc, char* argv[]) {
    // Printing if told to be verbose
    int verbose = cmdln_int("verbose", argc, argv, 1);
    if (verbose >= 0) std::cout << enc_banner;

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
                                                 argc, argv, "",
                                                 true); /*required*/

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

    // Number of exclusive jets
    const int n_exclusive_jets           = cmdln_int(
                                              "n_exclusive_jets",
                                              argc, argv, -1);
    // i.e. max number of jets per event to include in analysis
    // (Ordered by energy, e.g. 1 = leading jet. -1 = all jets)
    // (Default is -1, i.e. fully inclusive)
    // (does not override pt_min/pt_max options, below:)

    const double pt_min  = cmdln_double("pt_min", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_PT_MIN
                                 : _PTMIN_DEFAULT);
    const double pt_max  = cmdln_double("pt_max", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_PT_MAX
                                 : _PTMAX_DEFAULT);

    // Require |eta| < eta_cut, but only for proton-proton collisions
    const double eta_cut = cmdln_double("eta_cut",
                                 argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_ETA_CUT
                                 : -1.0);


    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    // ENC Settings
    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    // Whether to include contact terms in the computation
    const bool contact_terms = cmdln_bool("contact_terms", argc, argv,
                                          true);

    // Getting the list of energy weights (nu) from command line
    // (We are calculating the projected `E^(1+nu) C`)
    std::vector <double> weights;
    for(int iarg=0; iarg<argc; ++iarg) {
        if(str_eq(argv[iarg], "--weights"))
            while (iarg+1 < argc and
                    // next arg doesn't start with '--'
                   std::string(argv[iarg+1]).find("--") == std::string::npos) {
                ++iarg;
                weights.emplace_back(atof(argv[iarg]));
            }
    }

    if (weights.size() == 0)
        throw std::invalid_argument(
            "Must be given at least 1 weight.");

    // Use deltaR rather than real-space opening angle by default
    const bool use_deltaR = cmdln_bool("use_deltaR", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? true
                                 : false);

    // Use pT rather than energy by default
    const bool use_pt     = cmdln_bool("use_pt", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? true
                                 : false);

    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    // Histogram Settings
    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    const int    nbins   = cmdln_int("nbins", argc, argv, 100,
                                     false);
    // NOTE: using logarithmically spaced bins,
    // NOTE:   with minbin and maxbin in base 10

    const double minbin  = cmdln_double("minbin", argc, argv,
                                  -8, false);
    const double maxbin  = cmdln_double("maxbin", argc, argv,
                                  1, false);
    const bool   uflow = true, oflow = true;


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Input Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const bool use_opendata = cmdln_bool("use_opendata", argc, argv,
                                         true);

    // Exclude neutrals
    const bool charged_only = cmdln_bool("charged_only",
                                         argc, argv, false);

    // Momentum smearing
    const bool smear_momenta = cmdln_bool("smear_momenta",
                                          argc, argv, false);

    double photon_smear_factor  = 0,
           charged_smear_factor = 0,
           neutral_smear_factor = 0;

    // Ghosts
    const bool add_ghosts    = cmdln_bool("add_uniform_ghosts",
                                          argc, argv, false);
    const double mean_ghost_pt = cmdln_double("mean_ghost_pt",
                                              argc, argv, 1.0,
                                              false);

    // Processing
    if (charged_only)
        std::cout << "Charged particles only." << std::endl;
    if (smear_momenta) {
        std::cout << "Smearing momenta roughly commensurate w/CMS "
                  << "(2402.13864)." << std::endl;

        photon_smear_factor = CMS_PHOTON_SMEAR_FACTOR;
        charged_smear_factor = CMS_CHARGED_SMEAR_FACTOR;
        neutral_smear_factor = CMS_NEUTRAL_SMEAR_FACTOR;
    }
    if (add_ghosts) {
        std::cout << "Adding a grid of nearly uniform ghosts with "
                  << "<pt>=" << mean_ghost_pt << " GeV."
                  << std::endl;
    }

    // Validating input options
    if (use_opendata && charged_only) {
        throw std::invalid_argument("Cannot do ''charged_only'' "
               "analysis with CMS open data: "
               "Particle IDs are not stored in the local dataset.");
    }
    if (use_opendata && smear_momenta) {
        throw std::invalid_argument("Cannot smear CMS open data: "
               "Particle IDs are not stored in the local dataset.");
    }
    if (use_opendata && add_ghosts) {
        throw std::invalid_argument("Adding uniform ghosts to "
               "CMS open data is not yet supported.");
    }


    // =====================================
    // Output Setup
    // =====================================
    PENC penc_calculator(weights, minbin, maxbin, nbins,
                    contact_terms, use_deltaR, use_pt,
                    uflow, oflow, verbose,
                    file_prefix);


    // Writing header to output files
    for (size_t inu = 0; inu < weights.size(); ++inu) {
        std::string filename = penc_calculator.enc_outfiles[inu];
        double nu = weights[inu];
        write_enc_header(filename, argc, argv,
                         std::vector<double>{nu});
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
            if (add_ghosts) {
                particles = add_uniform_ghosts(particles,
                                               mean_ghost_pt);
            }

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
                    // For other collisions, ensuring E_min < E < E_max
                    // (for now, keeping confusing notation with, e.g.,
                    //    E_min represented by `pt_min` below)
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

        // Loop PENC computation on jets
        for (const auto& jet : good_jets) {
            penc_calculator.processJet(jet);
        }
    } // end event loop
    // =====================================


    // Writing output files
    // (writeOutput automatically normalizes the histogram)
    penc_calculator.writeOutput();


    // ---------------------------------
    // Verifying successful run
    // ---------------------------------
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
