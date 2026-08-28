/**
 * @file    new_enc_2special.cc
 *
 * @brief   Code for generating histograms for "new angles on"
 *          n-point projected energy correlators ('ENC's);
 *          in this file, we use four particles, and are
 *          differential in three angles:
 *          R_1, R_1', and R_*
 *
 * @author: Samuel Alipour-fard
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

#include "../include/enc_utils.h"

#include "../include/opendata_utils.h"


// =====================================
// Type definitions for histograms
// =====================================
// Multi-dimensional Histograms
typedef std::vector<double> Hist1d;
typedef std::vector<std::vector<double>> Hist2d;
typedef std::vector<Hist2d> Hist3d;

// Using pairs of weights to specify the 2-special correlator
typedef std::pair<double, double> weight_t;


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
    std::string file_prefix = cmdln_string("file_prefix",
                                           argc, argv, "",
                                           true); /* required */


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


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // ENC Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Whether to include contact terms in the computation
    const bool contact_terms = cmdln_bool("contact_terms",
                                          argc, argv,
                                          false);
    if (contact_terms)
        throw std::invalid_argument(
                "No support for contact terms yet.");

    // Getting the list of energy weight pairs (nu1, nu2)
    std::vector <weight_t> nu_weights;
    for(int iarg=0; iarg<argc; ++iarg) {
        if(str_eq(argv[iarg], "--weights"))
            while (iarg+1 < argc and
                    // next arg doesn't start with '--'
                    std::string(argv[iarg+1]).find("--") == std::string::npos) {
                ++iarg;
                // Ensuring we are given pairs of weights
                if (iarg+1 >= argc or // next arg starts with '--'
                        std::string(argv[iarg+1]).find("--") != std::string::npos)
                    throw std::invalid_argument(
                        "Need to give an even number "
                        "of weights for the 2-special-"
                        "particle distribution.");

                nu_weights.emplace_back(
                            atof(argv[iarg]),atof(argv[iarg+1])
                        );
                ++iarg;
            }
    }

    if (nu_weights.size() == 0)
        throw std::invalid_argument(
            "Must be given at least 2 weights.");


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


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Histogram Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const int    nbins    = cmdln_int("nbins", argc, argv,
                                      100, false);
    // NOTE: using logarithmically spaced bins,
    // NOTE:   with minbin and maxbin in base 10

    const double minbin   = cmdln_double("minbin", argc, argv,
                                   -8, false);
    const double maxbin   = cmdln_double("maxbin", argc, argv,
                                   0.05, false);

    // Bins for separation of special particles
    const bool bin_sp_uflow = true, bin_sp_oflow = true;

    // For particles around the special particles
    const bool bin1_uflow = true, bin1_oflow = true;


    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Initializing bin edges and centers
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // - - - - - - - - - - - - - - -
    // For theta_sp
    // - - - - - - - - - - - - - - -
    // Setting up under/overflow
    int nbins_sp_finite = nbins, bin_sp_finite_start = 0;
    if (bin_sp_uflow) {
        nbins_sp_finite -= 1; bin_sp_finite_start += 1;}
    if (bin_sp_oflow) nbins_sp_finite -= 1;

    // (logarithmic, from 10^minbin to 10^maxbin)
    const std::vector<double> bin_sp_edges = get_bin_edges(
                                        minbin, maxbin, nbins,
                                        bin_sp_uflow, bin_sp_oflow);
    const std::vector<double> bin_sp_centers = get_bin_centers(
                                        minbin, maxbin, nbins,
                                        bin_sp_uflow, bin_sp_oflow);


    // - - - - - - - - - - - - - - -
    // For theta1 and theta1'
    // - - - - - - - - - - - - - - -
    // Setting up under/overflow
    int nbins1_finite = nbins, bin1_finite_start = 0;
    if (bin1_uflow) {nbins1_finite -= 1; bin1_finite_start += 1;}
    if (bin1_oflow) nbins1_finite -= 1;

    // (logarithmic, from 10^minbin to 10^maxbin)
    const std::vector<double> bin1_edges = get_bin_edges(
                                        minbin, maxbin, nbins,
                                        bin1_uflow, bin1_oflow);
    const std::vector<double> bin1_centers = get_bin_centers(
                                        minbin, maxbin, nbins,
                                        bin1_uflow, bin1_oflow);

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Output Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Whether to output hist in a mathematica friendly format
    const bool mathematica_format = cmdln_bool("mathematica",
                                               argc, argv, false);
    const std::string HIST_DELIM  = mathematica_format ?  " " : ", ";
    const std::string file_ext    = mathematica_format ?  ".txt"
                                                      : ".py";


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Input Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const bool use_opendata = cmdln_bool("use_opendata",
                                         argc, argv,
                                         true);


    // =====================================
    // Output Setup
    // =====================================
    // Set up histograms
    // NOTE: The full histogram is the outer product
    // NOTE:   of two independent histograms.
    std::vector<Hist1d> hist_1;
    std::vector<Hist2d> hist_2;
    std::vector<Hist3d> enc_hists;
    // Set up histogram output files
    std::vector<std::string> enc_outfiles;

    for (auto nus : nu_weights){
        hist_1.emplace_back(Hist1d(nbins));
        hist_2.emplace_back(Hist2d (nbins, Hist1d(nbins)));

        // TODO: remove this if procedure is correct
        enc_hists.emplace_back(Hist3d (nbins,
                    Hist2d(nbins, Hist1d(nbins))));

        // Setting up output files
        std::string filename = "output/new_encs/2special_" +
                file_prefix +
                "_nus_" + str_round(nus.first, 2) +
                "_" + str_round(nus.second, 2);

        filename = periods_to_hyphens(filename);
        filename += file_ext;
        // writing a header with relevant information
        write_enc_header(filename, argc, argv,
                     std::vector<double> {nus.first,
                                          nus.second},
                     not(mathematica_format));
        // and adding them to the dict of output files
        enc_outfiles.push_back(filename);
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

    // Initializing list of of which particles are closest to others
    std::vector<std::vector<std::pair<double, double>>>
                all_angweight_pairs;
    std::vector<std::pair<double, double>> angs_weights_sp1;
    std::vector<std::pair<double, double>> angs_weights_sp2;

    // Reserving memory
    particles.reserve(150);
    all_jets.reserve(20);
    good_jets.reserve(5);

    all_angweight_pairs.reserve(150);
    angs_weights_sp1.reserve(150);
    angs_weights_sp2.reserve(150);

    // Preparing to store runtime info
    std::map<int, std::vector<double>> jet_runtimes;

    // =====================================
    // Looping over events
    // =====================================
    for (int iev = 0; iev < n_events; ++iev) {
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
                std::stringstream fastjetstream;
                fastjetstream.str("");
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
                PseudoJet jet = all_jets[i];

                // Getting jets that satisfy certain criteria
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
        for (auto jet : good_jets) {
        try {
            // Start timing
            auto jet_start = std::chrono::high_resolution_clock::now();

            // Counting total num_jets across events
            ++njets_tot;

            // Storing jet constituents
            const std::vector<PseudoJet>& constituents =
                                            jet.constituents();
            double weight_tot = 0;
            for (const auto& particle : constituents) {
                weight_tot += use_pt ? particle.pt() : particle.e();
            }


            all_angweight_pairs.clear();

            // ---------------------------------
            // Loop on first special particle
            for (size_t isp1=0; isp1 < constituents.size(); ++isp1) {
                // Getting the first special particle
                const PseudoJet& part_sp_1 = constituents[isp1];

                // Energy-weighting factor for "special" particle
                double weight_sp1 = use_pt ?
                        part_sp_1.pt() / weight_tot :
                        part_sp_1.e() / weight_tot;
                // Initializing sum of weights within an
                // angle of the first special particle
                double sum_weight1  = weight_sp1;
                double sum_weight_sp  = weight_sp1;

                // =*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=
                // First Histogram
                // =*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=
                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                // Preparing contact terms:
                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                if (contact_terms) {
                    for (size_t inu = 0; inu < nu_weights.size(); ++inu) {
                        hist_1[inu][0] +=
                            std::pow(weight_sp1,
                                     nu_weights[inu].first);
                    }
                }
                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-

                // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                // Sorting:
                //     * [theta1] : angle relative to special particle
                //     * [weight1]: weight of particle
                //  by theta1
                angs_weights_sp1.clear();
                for (const auto& part1 : constituents) {
                    angs_weights_sp1.emplace_back(
                        // theta_1,
                        use_deltaR ? part_sp_1.delta_R(part1)
                                   : fastjet::theta(part_sp_1,
                                                    part1),
                        // weight_1
                        use_pt ? part1.pt() / weight_tot
                               : part1.e() / weight_tot
                       );
                } // end particle sorting loop
                // Sorting angles/weights by angle as promised :)
                std::sort(angs_weights_sp1.begin(),
                          angs_weights_sp1.end());
                // Storing for second special particle
                all_angweight_pairs.push_back(angs_weights_sp1);
                // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-

                // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                // Loop on first non-special particle
                for (auto angweight : angs_weights_sp1) {
                    // Calculating the theta1 (angweight.first)
                    // bin in the histogram
                    int bin1 = bin_position(angweight.first,
                                            minbin, maxbin,
                                            nbins, "log",
                                            bin1_uflow, bin1_oflow);
                    const double weight1 = angweight.second;

                    // Adding to histogram
                    for (size_t inu = 0;
                            inu < nu_weights.size();
                            ++inu) {
                        hist_1[inu][bin1] +=
                                std::pow(sum_weight1
                                        +weight1,
                                        nu_weights[inu].first)
                                - std::pow(weight1,
                                           nu_weights[inu].first);
                    }

                    sum_weight1 += weight1;
                }
                // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-

                // =*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=
                // Second Histogram
                // =*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=*=
                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                // Preparing contact terms:
                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                if (contact_terms) {
                    for (size_t inu = 0;
                            inu < nu_weights.size();
                            ++inu) {
                        // TODO: Make this placeholder correct
                        hist_2[inu][0][0] +=
                            std::pow(weight_sp1,
                                    2 + nu_weights[inu].second);
                    }
                }
                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-

                // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                // Loop on second special particle
                for (size_t isp2=0; isp2<isp1; ++isp2) {
                    // Getting second special particle
                    const PseudoJet& part_sp_2 = constituents[isp2];

                    // And its properties
                    double R_sp = use_deltaR
                                    ? part_sp_2.delta_R(part_sp_1)
                                    : fastjet::theta(part_sp_2,
                                                     part_sp_1);
                    double weight_sp2 = use_pt
                                    ? part_sp_2.pt() / weight_tot
                                    : part_sp_2.e() / weight_tot;
                    // Initializing sum of weights within an
                    // angle of the second special particle
                    double sum_weight2 = weight_sp2;

                    // Calculating the R_sp bin in the histogram
                    int bin_sp = bin_position(R_sp, minbin, maxbin,
                                              nbins, "log",
                                              bin_sp_uflow,
                                              bin_sp_oflow);

                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                    // Preparing contact terms:
                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                    if (contact_terms) {
                        for (size_t inu = 0;
                                inu < nu_weights.size();
                                ++inu) {
                            // TODO: Make this placeholder correct
                            hist_2[inu][bin_sp][0] += weight_sp1 *
                                std::pow(weight_sp2,
                                         1 + nu_weights[inu].second);
                        }
                    }
                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-

                    // Special particle histogram contribution
                    const double delta_sp =
                        weight_sp1 * weight_sp2;

                    // Getting stored list of sorted angles/weights
                    angs_weights_sp2.clear();
                    angs_weights_sp2 = all_angweight_pairs[isp2];

                    // -----------------------------------
                    // Loop on second non-special particle
                    for (auto angweight : angs_weights_sp2) {
                        // Calculating bin position
                        int bin1p = bin_position(
                                angweight.first,
                                minbin, maxbin,
                                nbins, "log",
                                bin1_uflow, bin1_oflow);

                        // Add weight to Histogram
                        for (size_t inu = 0;
                                inu < nu_weights.size();
                                ++inu) {
                            const double delta2 =
                                 std::pow(sum_weight2
                                          +angweight.second,
                                          nu_weights[inu].second)
                               - std::pow(sum_weight2,
                                          nu_weights[inu].second);
                            hist_2[inu][bin_sp][bin1p] +=
                                delta_sp*delta2;
                        }
                        // -----------------------------
                        // Preparing for next particle
                        sum_weight2 += angweight.second;
                    } // end non-special particle loop
                    // -------------------------------

                    // Preparing for next particle
                    sum_weight_sp += weight_sp2;
                } // end 2nd special particle loop
                // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
            } // end first special particle loop
            // ---------------------------------

            // ---------------------------------
            // Finished with this jet!
            // ---------------------------------
            // End timing
            if (nu_weights.size() == 1) {
                auto jet_end = std::chrono::high_resolution_clock::now();
                auto jet_duration = std::chrono::duration_cast
                        <std::chrono::microseconds>(jet_end - jet_start);

                // Store the runtime for this jet
                jet_runtimes[constituents.size()].emplace_back(
                        static_cast<double>(jet_duration.count()));
            }
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

    // ===================================
    // Writing histograms to output files
    // ===================================
    std::vector<std::string> bin_names =
                {"R_sp", "theta1", "theta1p"};

        for (size_t inu = 0; inu < nu_weights.size(); ++inu) {
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // Output setup
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Opening histogram output file
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        std::string filename = enc_outfiles[inu];
        std::fstream outfile;
        outfile.open(filename, std::ios_base::in |
                               std::ios_base::out |
                               std::ios_base::app);

        // Checking for existence
        if (!outfile.is_open()) {
            std::stringstream errMsg;
            errMsg << "File for EnC output was expected "
                   << "to be open, but was not open.\n\n"
                   << "It is possible the file was unable to "
                   << "be created at the desired location:\n\n\t"
                   << "filename = " << filename << "\n\n"
                   << "Is the filename an absolute path? If not, "
                   << "that might be the problem.";
            throw std::runtime_error(errMsg.str().c_str());
        }


        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // Writing bins to files
        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=

        // All bins have the same range
        for (auto bin_name : bin_names) {
            // -:-:-:-:-:-:-:-:-:-:-:-:
            // bin edges
            // -:-:-:-:-:-:-:-:-:-:-:-:
            if (not(mathematica_format)) outfile << bin_name
                                                 << "_edges = [\n\t";
            else outfile << "(* " << bin_name << "_edges *)\n";

            // nbins+1 bin edges:
            //   include -infty and infty for under/overflow
            for (int ibin = 0; ibin < nbins; ++ibin)
                outfile << std::pow(10, bin1_edges[ibin]) << HIST_DELIM;
            if (std::isinf(bin1_edges[nbins]) and not(mathematica_format))
                outfile << "np.inf\n";
            else
                outfile << std::pow(10, bin1_edges[nbins]) << "\n";

            if (not(mathematica_format)) outfile << "]\n\n";

            // -:-:-:-:-:-:-:-:-:-:-:-:
            // bin centers
            // -:-:-:-:-:-:-:-:-:-:-:-:
            if (not(mathematica_format)) outfile << bin_name
                                                 << "_centers = [\n\t";
            else outfile << "(* " << bin_name << "s *)\n";

            for (int ibin = 0; ibin < nbins-1; ++ibin)
                outfile << std::pow(10, bin1_centers[ibin]) << HIST_DELIM;
            if (std::isinf(bin1_centers[nbins-1]) and not(mathematica_format))
                outfile << "np.inf\n";
            else
                outfile << std::pow(10, bin1_centers[nbins-1]) << "\n";

            if (not(mathematica_format)) outfile << "]\n\n";
        }

        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // Processing/writing histogram
        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Normalizing histograms
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        double sum_1 = 0.0;
        double sum_2 = 0.0;

        // Normalizing first histogram
        for (int bin1=0; bin1<nbins; ++bin1) {
            // Dealing with expectation values over N jets
            hist_1[inu][bin1] /= njets_tot;
            sum_1 += hist_1[inu][bin1];

            // Not normalizing outflow bins further
            if (bin1 < bin1_finite_start or bin1 >= nbins1_finite)
                continue;

            // Otherwise, log-normalizing the histogram
            hist_1[inu][bin1] /= (bin1_edges[bin1+1]
                                  - bin1_edges[bin1]);
        }

        // Normalizing second histogram
        for (int bin_sp=0; bin_sp<nbins; ++bin_sp) {
            for (int bin1p=0; bin1p<nbins; ++bin1p) {
                // Dealing with expectation values over N jets
                hist_2[inu][bin_sp][bin1p] /= njets_tot;
                sum_2 += hist_2[inu][bin_sp][bin1p];

                // Not normalizing outflow bins further
                if (bin_sp < bin_sp_finite_start
                        or bin_sp >= nbins_sp_finite
                        or bin1p < bin1_finite_start
                        or bin1p >= nbins1_finite)
                    continue;

                // Otherwise, log-normalizing the histogram
                double dlog_sp = (bin_sp_edges[bin_sp+1]
                                  - bin_sp_edges[bin_sp]);
                double dlog_1p = (bin1_edges[bin1p+1]
                                  - bin1_edges[bin1p]);
                hist_2[inu][bin_sp][bin1p] /= dlog_sp*dlog_1p;
            }
        }

        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Taking the outer product
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        for (int bin_sp=0; bin_sp<nbins; ++bin_sp) {
            for (int bin1=0; bin1<nbins; ++bin1) {
                for (int bin1p=0; bin1p<nbins; ++bin1p) {
                    // Taking the outer product
                    enc_hists[inu][bin_sp][bin1][bin1p] =
                        hist_1[inu][bin1]
                        * hist_2[inu][bin_sp][bin1p];
                }
            }
        }

        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Printing normalization info
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        if (verbose >= 0) {
            double total_integral = 0.0;
            // Looping over all bins
            for (int bin_sp=0; bin_sp<nbins; ++bin_sp) {
                for (int bin1=0; bin1<nbins; ++bin1) {
                    for (int bin1p=0; bin1p<nbins; ++bin1p) {
                        if (bin_sp < bin_sp_finite_start
                                or bin_sp >= nbins_sp_finite
                                or bin1 < bin1_finite_start
                                or bin1 >= nbins1_finite
                                or bin1p < bin1_finite_start
                                or bin1p >= nbins1_finite) {
                            total_integral += enc_hists[inu][bin_sp][bin1][bin1p];
                            continue;
                        }

                        // Getting differential "volume" element
                        double dlog_sp = (bin_sp_edges[bin_sp+1]
                                          - bin_sp_edges[bin_sp]);
                        double dlog_1  = (bin1_edges[bin1+1]
                                          - bin1_edges[bin1]);
                        double dlog_1p = (bin1_edges[bin1p+1]
                                          - bin1_edges[bin1p]);

                        double dvol = dlog_sp*dlog_1*dlog_1p;
                        total_integral += enc_hists[inu][bin_sp][bin1][bin1p] * dvol;
                    }
                }
            }

            // Printing normalization
            weight_t nu = nu_weights[inu];
            std::cout << "\nTotal weight for nu=("
                      << nu.first << "," << nu.second << "): "
                      << sum_1*sum_2;
            // for sub-histograms as well
            if (verbose >= 1) {
                std::cout << "\n\tSub-histograms: "
                          << sum_1 << " and " << sum_2;
            }

            // And integral
            std::cout << "\nIntegrated weight for nu=("
                      << nu.first << "," << nu.second << "): "
                      << total_integral;
        }

        // Then getting the finalized histogram
        Hist3d hist = enc_hists[inu];

        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Writing histogram
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        if (not(mathematica_format)) outfile << "hist = [\n\t";
        else outfile << "\n(* hist *)\n";
        for (int bin_sp=0; bin_sp<nbins; ++bin_sp) {
            if (not(mathematica_format)) outfile << "[\n\t";
            for (int bin1=0; bin1<nbins; ++bin1) {
                if (not(mathematica_format)) outfile << "\t[\n\t\t\t";

                // Printing histogram
                for (int bin1p=0; bin1p<nbins-1; ++bin1p) {
                    outfile << std::setprecision(10)
                            << hist[bin_sp][bin1][bin1p]
                            << HIST_DELIM;
                }
                outfile << hist[bin_sp][bin1][nbins-1] << "\n";
                // END

                if (not(mathematica_format))
                    outfile << (bin1 != nbins-1 ? "\t\t],\n\t"
                                                : "\t\t]\n");
            }
            if (not(mathematica_format))
                outfile << (bin_sp != nbins-1 ? "\t],\n\t"
                                            : "\t]\n");
        }
        if (not(mathematica_format)) outfile << "]";


        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // Writing runtimes
        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        if (nu_weights.size() != 1) {
            outfile.close();
            continue;
        }

        std::vector<double> runtime_means;
        std::vector<double> runtime_stds;

        // Looping over number of particles in a jet
        for (int num=0; num<200; ++num) {
            // Finding the runtimes associated with this
            // number of particles
            std::map<int, std::vector<double>>::iterator it
                    = jet_runtimes.find(num);
            if(it == jet_runtimes.end()) {
                runtime_means.emplace_back(
                        std::numeric_limits<double>::quiet_NaN());
                runtime_stds.emplace_back(
                        std::numeric_limits<double>::quiet_NaN());
                continue;
            }

            // If found, calculate mean and standard deviation:
            const std::vector<double>& runtimes = it->second;
            double mean  = vector_mean(runtimes);
            double stdev = vector_std(runtimes);
            runtime_means.push_back(mean);
            runtime_stds.push_back(stdev);
        }

        // Adding mean runtimes to file
        if (not(mathematica_format))
            outfile << "\n\nruntime_means = [\n\t";
        else outfile << "\n(* mean runtimes *)\n";
        for (size_t inum = 0; inum < runtime_means.size(); ++inum) {
            !std::isnan(runtime_means[inum])    ?
                outfile << runtime_means[inum] :
                outfile << "np.nan";
            if (inum < runtime_means.size()) outfile << HIST_DELIM;
            else outfile << "\n";
        }
        if (not(mathematica_format)) outfile << "]\n";

        // Adding stdev runtimes to file
        if (not(mathematica_format))
            outfile << "runtime_stds = [\n\t";
        else outfile << "\n(* stdev runtimes *)\n";
        for (size_t inum = 0; inum < runtime_stds.size(); ++inum) {
            !std::isnan(runtime_stds[inum])    ?
                outfile << runtime_stds[inum] :
                outfile << "np.nan";
            if (inum < runtime_stds.size()) outfile << HIST_DELIM;
            else outfile << "\n";
        }
        if (not(mathematica_format)) outfile << "]";

        // Closing file
        outfile.close();
    }

    // ---------------------------------
    // =====================================
    // Verifying successful run
    // =====================================
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
