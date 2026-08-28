/**
 * @file    new_enc_2particle.cc
 *
 * @brief   Code for generating histograms for "new angles on"
 *          n-point projected energy correlators ('EnC's);
 *          in this file, we consider two particles, and are
 *          differential in a single angle:
 *          R_1
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
#include <numeric>
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
#include "../../include/general_utils.h"
#include "../../include/jet_utils.h"
#include "../../include/pythia2fastjet.h"
#include "../../include/cmdln.h"
#include "../../include/pythia_cmdln.h"

#include "../../include/enc_utils.h"

#include "../../include/opendata_utils.h"


// Type definition for histograms
typedef std::vector<double> Hist;
// (we are only differential in a single angle)

// =====================================
// Switches, flags, and options
// =====================================
// Cut on jets from the CMS Jet 2011A Dataset
float CMS_ETA_CUT       = 1.9;
float CMS_R_JET         = 0.5;
std::string CMS_JET_ALG = "akt";
float CMS_PT_MIN        = 500;
float CMS_PT_MAX        = 550;

// Define the set of desired M (number of jet constituents) values
std::set<size_t> desired_M = {5, 10, 25, 50, 100, 130};
const int num_repeats = 10000; // Number of repetitions per jet

const int target_count = 1;


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
    if (verbose >= 0) std::cout << enc_banner;

    // Initialize a counter for each M
    std::map<size_t, int> M_counts;
    for (size_t M_value : desired_M) {
        M_counts[M_value] = 0;
    }

    // ---------------------------------
    // =====================================
    // Command line setup
    // =====================================
    // ---------------------------------
    // Ensuring valid command line inputs
    if (checkPythiaInputs(argc, argv) == 1) return 1;

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
    const int   nbins  = cmdln_int("nbins", argc, argv, 100, false);
    // NOTE: using logarithmically spaced bins,
    // NOTE:   with minbin and maxbin in base 10

    const double minbin  = cmdln_double("minbin", argc, argv,
                                  -8, false);
    const double maxbin  = cmdln_double("maxbin", argc, argv,
                                  1, false);
    const bool uflow = true, oflow = true;


    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Initializing bin edges and centers
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    // Input Settings
    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    const bool use_opendata = cmdln_bool("use_opendata", argc, argv,
                                         true);


    // =====================================
    // Output Setup
    // =====================================
    // Set up histograms
    Hist enc_hist (nbins);

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
    std::vector<std::pair<double, double>> sorted_angsweights;

    // Reserving memory
    particles.reserve(150);
    all_jets.reserve(20);
    good_jets.reserve(5);
    sorted_angsweights.reserve(50);

    // Preparing to store runtime info
    std::map<int, std::vector<double>> jet_runtimes;

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
            particles = get_particles_pythia(pythia.event);

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

                // Adding jets that satisfy certain criteria to good jets list
                if (is_proton_collision) {
                    // For pp, ensuring pt_min < pt < pt_max
                    // and |eta| < eta_cut   (or no eta_cut given)
                    if (pt_min <= jet.pt() and jet.pt() <= pt_max
                            and (abs(jet.eta()) <= eta_cut
                                 or eta_cut < 0)) {
                        good_jets.push_back(jet);
                    }
                } else {
                    // For other collisions, ensuring E_min < E < E_max
                    // (for now, keeping confusing notation with, e.g.,
                    //    E_min represented by `pt_min` below)
                    if (pt_min <= jet.E() and jet.E() <= pt_max) {
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
            const std::vector<PseudoJet>& constituents = jet.constituents();
            size_t M = constituents.size();

            // Check if this jet has a desired M
            if (desired_M.find(M) != desired_M.end() && M_counts[M] < target_count) {
            // Start timing
            auto start = std::chrono::high_resolution_clock::now();

            // Repeat the computation num_repeats times
            for (int repeat = 0; repeat < num_repeats; ++repeat) {
                progressbar(static_cast<double>(repeat+1)/
                            double(num_repeats));
                double weight_tot = 0;
                for (const auto& particle : constituents) {
                    weight_tot += use_pt ? particle.pt() : particle.e();
                    }

                // ---------------------------------
                // Loop on "special" particle
                for (const auto& part_sp : constituents) {
                    // Energy-weighting factor for "special" particle
                    double weight_sp = use_pt ?
                            part_sp.pt() / weight_tot :
                            part_sp.e() / weight_tot;
                    // Initializing sum of weights
                    // within an angle of 1st particle
                    double sum_weight1 = weight_sp;
                    // At particle j within the loop below,
                    // sum_weight1 = \sum_{thetak < thetaj} weight1_k

                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                    // Preparing contact term:
                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                    if (contact_terms) {
                        enc_hist[0] += std::pow(sum_weight1, 2);
                    }
                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-

                    // (Sorting:
                    //   * [theta1]: angle relative to special particle
                    //   * [weight1]: either E2/Ejet or pt2/ptjet
                    //  by theta1)
                    sorted_angsweights.clear();

                    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                    // Loop on particles
                    for (const auto& part1 : constituents) {
                        // Energy-weighting factor for particle 1
                        double weight1 = use_pt ?
                                part1.pt() / weight_tot :
                                part1.e() / weight_tot ;

                        // Angle relative to "special" particle
                        double theta1 = use_deltaR ?
                                part_sp.delta_R(part1) :
                                fastjet::theta(part_sp, part1);

                        sorted_angsweights.emplace_back(theta1, weight1);
                    } // end second particle loop
                    // Sorting angles/weights by angle as promised :)
                    std::sort(sorted_angsweights.begin(),
                              sorted_angsweights.end());
                    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-

                    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                    // Loop on second particle
                    for (size_t jpart=1; jpart<sorted_angsweights.size(); ++jpart){
                        double theta1 = sorted_angsweights[jpart].first;
                        double weight1 = sorted_angsweights[jpart].second;

                        // Calculating the theta1 bin in the histogram
                        int bin = bin_position(theta1, minbin, maxbin,
                                               nbins, "log",
                                               uflow, oflow);

                        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                        double hist_weight = weight_sp*(
                                    std::pow(sum_weight1+weight1, 1)
                                    -
                                    std::pow(sum_weight1, 1)
                                );
                        enc_hist[bin] += hist_weight;
                        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-

                        // Preparing for the next term in the loop!
                        sum_weight1 += weight1;
                    } // end calculation/particle loop
                    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                } // end "special particle" loop
                // ---------------------------------
            } // End loop over many computations on this jet

            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);

            // Store the runtime
            jet_runtimes[M].emplace_back(
                    static_cast<double>(duration.count())
                    /num_repeats
                    );
            ++M_counts[M];
            }
        } catch (const fastjet::Error& ex) {
            // ending try statement (sometimes I find empty jets)
            std::cerr << "Warning: FastJet: " << ex.message()
                      << std::endl;
            continue;
        }
        } // end loop on jets
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-

        // Check if we've collected enough data for all M
        bool all_collected = true;
        for (auto& pair : M_counts) {
            if (pair.second < target_count) {
                all_collected = false;
                break;
            }
        }
        if (all_collected) break;
    } // end event loop
    // =====================================

    // Compute and output mean runtimes
    for (const auto& pair : jet_runtimes) {
        size_t M = pair.first;
        const std::vector<double>& runtimes = pair.second;

        // Compute mean runtime
        double sum = std::accumulate(runtimes.begin(), runtimes.end(), 0.0);
        double mean = sum / runtimes.size();

        // Compute median runtime
        std::vector<double> sorted_runtimes = runtimes;
        std::sort(sorted_runtimes.begin(), sorted_runtimes.end());
        double median = sorted_runtimes[sorted_runtimes.size() / 2];

        // Output the results
        std::cout << std::endl << "M = " << M
                  << ", Mean Runtime = " << mean << " microseconds"
                  << ", Median Runtime = " << median << " microseconds"
                  << ", Samples Collected = " << runtimes.size();
    }
    std::cout << std::endl;

    return 0;
}
