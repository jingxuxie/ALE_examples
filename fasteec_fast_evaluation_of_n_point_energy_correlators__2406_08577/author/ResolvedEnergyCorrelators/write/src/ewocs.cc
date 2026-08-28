/**
 * @file    ewocs.cc
 *
 * @brief   Code for generating EEC and EWOC histograms in Pythia.
 */


// ---------------------------------
// Basic imports
// ---------------------------------
#include <iostream>
#include <cmath>
#include <limits>
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

#include "../include/ewoc_utils.h"

#include "../include/opendata_utils.h"


// Type definitions for EWOCs
typedef std::pair<double, double> radius_pair;

// Type definition for histograms
typedef std::vector<double> Hist;


// =====================================
// Pair observables
// =====================================
/**
* @brief: Returns the angle between a pair of pseudojets.
*
* @param: pj1, pj2  The given pseudojets.
*
* @return: double   Angle between the pseudojets (in radians).
*/
double angle(const PseudoJet pj1, const PseudoJet pj2) {
    std::vector<double> p1 = {pj1.px(), pj1.py(), pj1.pz()};
    std::vector<double> p2 = {pj2.px(), pj2.py(), pj2.pz()};

    double th = theta(p1, p2);

    if(std::isnan(th)) {
        std::string p1_str = "<" + std::to_string(pj1.px()) + " " + std::to_string(pj1.py()) + " " + std::to_string(pj1.pz()) + ">";
        std::string p2_str = "<" + std::to_string(pj2.px()) + " " + std::to_string(pj2.py()) + " " + std::to_string(pj2.pz()) + ">";

        throw std::runtime_error("Found theta = nan, from"
                   "\n\tp_1 = " + p1_str
                 + "\n\tp_2 = "  + p2_str
             );
    }

    return th;
}
double angle_squared(PseudoJet pj1, PseudoJet pj2){
    return pow(angle(pj1, pj2), 2.);
}

double deltaR(PseudoJet pj1, PseudoJet pj2){
    return pj1.delta_R(pj2);
}
double deltaR_squared(PseudoJet pj1, PseudoJet pj2){
    return pow(pj1.delta_R(pj2), 2.);
}

double formation_time(PseudoJet pj1, PseudoJet pj2){
    return std::max(pj1.e(), pj2.e())/(pj1+pj2).m2();
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
    const int verbose = cmdln_int("verbose", argc, argv, 0);
    if (verbose >= 1) std::cout << ewoc_banner << "\n\n";

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
                                           true); /* required */

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Basic Pythia Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // 50k e+ e=:=> hadrons events, by default
    const int         n_events = cmdln_int("n_events", argc, argv,
                                          _NEVENTS_DEFAULT);
    const int         pid_1    = cmdln_int("pid_1", argc, argv,
                                          _PID_1_DEFAULT);
    const int         pid_2    = cmdln_int("pid_2", argc, argv,
                                          _PID_2_DEFAULT);

    const bool is_proton_collision = (pid_1 == 2212 and
                                        pid_2 == 2212);

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Jet Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const std::string jet_alg = jetalgstr_cmdln(argc, argv);
    const std::string sub_alg = subalgstr_cmdln(argc, argv);

    const radius_vector_pair_t radius_pairs = radius_pairs_cmdln(argc, argv);
    const std::vector<double> jet_rads = radius_pairs.first;
    const std::vector<double> sub_rads = radius_pairs.second;

    // Recombination schemes
    const RecombinationScheme jet_recomb = jetrecomb_cmdln(
                                                    argc, argv);
    const RecombinationScheme sub_recomb = subrecomb_cmdln(
                                                    argc, argv);

    // Number of exclusive jets
    const int n_exclusive_jets = cmdln_int("n_exclusive_jets",
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
    const double eta_cut = cmdln_double("eta_cut", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_ETA_CUT
                                 : -1.0);


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // EWOC Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Getting functional form of pair observable (required)
    const std::string pair_obs = cmdln_string("pair_obs",
                                              argc, argv, "",
                                              true);

    // Options for using pair or contact terms (default: use both)
    const bool pair_terms    = cmdln_bool("pair_terms", argc, argv,
                                          true);
    const bool contact_terms = cmdln_bool("contact_terms", argc, argv,
                                          true);

    // Use pT rather than energy by default
    const bool use_pt = cmdln_bool("use_pt", argc, argv,
                                   // default depends on collision
                                   is_proton_collision ? true
                                   : false);

    // Getting EWOC energy weight, with n1=n2 (default value 1)
    const double e_weight = cmdln_double("weight", argc, argv,
                                         _DEFAULT_WEIGHT);

    if (not(pair_terms) and not(contact_terms))
        throw std::runtime_error("Cannot create an EWOC histogram "
                "without including either pair terms or contact "
                "terms, but both were pair_terms and contact_terms "
                "were given as false.");

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Histogram Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const int    nbins  = cmdln_int("nbins", argc, argv, 100, false);

    // Required arguments
    const double minbin = cmdln_double("minbin", argc, argv,
                                       0, true);
    const double maxbin = cmdln_double("maxbin", argc, argv,
                                      0, true);

    // Optional
    // Default: logarithmically spaced bins
    const bool lin_bins = cmdln_bool("lin_bins", argc, argv,
                                     false); /* default: log bins */
    const std::string bin_scheme = lin_bins ? "linear"
                                            : "logarithmic";
    // Always using underflow and overflow bins
    const bool uflow = true;
    const bool oflow = true;

    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Initializing bin edges and centers
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Setting up under/overflow
    int nbins_finite = nbins, bins_finite_start = 0;
    if (uflow) {nbins_finite -= 1; bins_finite_start += 1;}
    if (oflow) nbins_finite -= 1;

    const std::vector<double> bin_edges   = get_bin_edges(
                                            minbin, maxbin, nbins,
                                            uflow, oflow);
    const std::vector<double> bin_centers = get_bin_centers(
                                            minbin, maxbin, nbins,
                                            uflow, oflow);


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Output Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Whether to output hist in a mathematica friendly format
    bool mathematica_format = cmdln_bool("mathematica",
                                         argc, argv, false);
    const std::string HIST_DELIM = mathematica_format ?  " " : ", ";
    const std::string file_ext   = mathematica_format ?  ".txt"
                                                      : ".py";


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Input Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    bool use_opendata = cmdln_bool("use_opendata", argc, argv,
                                   false);

    // Exclude neutrals
    const bool charged_only = cmdln_bool("charged_only",
                                         argc, argv, false);

    // Momentum smearing
    const double smear_factor = cmdln_double("smear_factor",
                                             argc, argv, 0, false);

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

    if (smear_factor > 0) {
        std::cout << "Smearing momenta roughly commensurate w/"
                  << smear_factor << " x CMS smearing"
                  << "(2402.13864)." << std::endl;

        photon_smear_factor  = smear_factor*CMS_PHOTON_SMEAR_FACTOR;
        charged_smear_factor = smear_factor*CMS_CHARGED_SMEAR_FACTOR;
        neutral_smear_factor = smear_factor*CMS_NEUTRAL_SMEAR_FACTOR;
    }

    if (add_ghosts) {
        std::cout << "Adding a grid of nearly uniform ghosts with "
                  << "<pt>=" << mean_ghost_pt << " GeV."
                  << std::endl;
    }

    if (use_opendata && charged_only) {
        throw std::invalid_argument("Cannot do ''charged_only'' "
               "analysis with CMS open data: "
               "Particle IDs are not stored in the local dataset.");
    }
    if (use_opendata && smear_factor > 0) {
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
    // Set up histograms
    std::vector<Hist> ewoc_hists;
    // Set up histogram output files
    std::vector<std::string> ewoc_outfiles;

    for (size_t irad = 0; irad < jet_rads.size(); ++irad) {
        // Looping over (jet, subjet) radius pairs
        double jet_rad = jet_rads[irad];
        double sub_rad = sub_rads[irad];

        // Setting up histograms
        Hist hist(nbins);
        ewoc_hists.push_back(hist);

        // Setting up output files,
        std::string filename = "output/ewocs/"
            + pair_obs + "_" + file_prefix +
            "_jet" + str_round(jet_rad, 2) +
            "_subjet" + str_round(sub_rad,2);
        filename = periods_to_hyphens(filename);
        filename += file_ext;
        // writing a header with relevant information,
        write_ewocfile_header(filename, argc, argv,
                              jet_rad, sub_rad,
                              not(mathematica_format));
        // and adding them to the dict of output files
        ewoc_outfiles.push_back(filename);
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
        // Setting up pythia based on command line arguments
        setup_pythia_cmdln(pythia, argc, argv);
    }

    // ---------------------------------
    // CMS Open Data
    // ---------------------------------
    od::EventReader cms_jet_reader(od::cms_jets_file);
    if (use_opendata) {
        // Require that all jets are AKT5 jets
        if (not(std::all_of(jet_rads.begin(), jet_rads.end(),
                            [&](int i) {return i == 0.5;})
                and (jet_alg == "akt" or jet_alg == "antikt")))
            throw std::invalid_argument("To use CMS "
                    "Open Data, must ask for AKT5 jets,\n"
                    "\t--jet_alg akt --jet_rad 0.5.");
    }



    // ---------------------------------
    // =====================================
    // Analyzing events
    // =====================================
    // ---------------------------------

    // Initializing total number of jets,
    //   summed over all events
    //   (used to normalize the histogram)
    std::vector<int> njets_tot(jet_rads.size(), 0);

    // Initializing particles, good_jets
    std::vector<PseudoJet> particles;
    std::vector<PseudoJet> all_jets;
    std::vector<PseudoJet> good_jets;
    std::vector<PseudoJet> subjets;

    bool passes_cuts;

    // Reserving memory
    particles.reserve(150);
    all_jets.reserve(20);
    good_jets.reserve(5);
    subjets.reserve(20);


    // =====================================
    // Looping over events
    // =====================================
    for (int iev = 0; iev < n_events; ++iev) {
        progressbar(double(iev+1)/double(n_events));

        if (not use_opendata) {
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
        }

        // ---------------------------------
        // Looping on jet definitions:
        // ---------------------------------
        for (size_t irad = 0; irad < jet_rads.size(); ++irad) {
            double jet_rad = jet_rads[irad];
            double sub_rad = sub_rads[irad];

            JetDefinition jet_def = process_JetDef(jet_alg, jet_rad,
                                                   jet_recomb);
            JetDefinition sub_def = process_JetDef(sub_alg, sub_rad,
                                                   sub_recomb);

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
                        // and |eta| < eta_cut (or no eta_cut given)
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
                // Counting total num of jets in all events for normalization
                ++njets_tot[irad];

                // Getting total weight associated with this jet
                double weight_tot = 0;
                for (const auto& particle : jet.constituents()) {
                    weight_tot += use_pt ? particle.pt()
                                         : particle.e();
                }

                // Getting subjets
                subjets.clear();

                if (sub_def.R() == 0) {
                    subjets = jet.constituents();
                }
                else {
                    ClusterSequence sub_cluster_seq(
                                jet.constituents(), sub_def);
                    if (use_pt)
                        subjets = sorted_by_pt(
                                    sub_cluster_seq.inclusive_jets());
                   else
                        subjets = sorted_by_E(
                                    sub_cluster_seq.inclusive_jets());
                }
                // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                // Loop on subjet pairs within the jet
                // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                for (size_t isub=0; isub < subjets.size(); ++isub) {
                    PseudoJet subjet1 = subjets[isub];

                    double weight1 = use_pt ?
                            subjet1.pt() / weight_tot :
                            subjet1.e() / weight_tot ;

                    for (size_t jsub=isub; jsub < subjets.size(); ++jsub) {
                        PseudoJet subjet2 = subjets[jsub];

                        double weight2 = use_pt ?
                                subjet2.pt() / weight_tot :
                                subjet2.e() / weight_tot ;

                        // Initialize num. permutations of subjet pair
                        int perms;
                        // and pairwise observable value
                        double val;

                        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
                        // Getting observable values
                        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
                        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                        // Contact Terms
                        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                        if (jsub == isub) {
                            // Contact terms
                            if (contact_terms)
                                perms = 1;
                            else
                                perms = 0;

                            // Mass
                            if (str_eq(pair_obs, "mass")
                                    or str_eq(pair_obs, "m")) {
                                val = subjet1.m();
                            }
                            // Mass-squared
                            else if (str_eq(pair_obs, "mass_squared")
                                    or str_eq(pair_obs, "mass2")
                                    or str_eq(pair_obs, "m2")) {
                                val = subjet1.m2();
                            }
                            // EECs:
                            else if (str_eq(pair_obs, "theta")
                                    or str_eq(pair_obs, "theta2")
                                    or str_eq(pair_obs, "deltaR")
                                    or str_eq(pair_obs, "deltaR2"))  {
                                val = 0;
                            }
                            // Formation time
                            else if (str_eq(pair_obs, "formtime") or
                                     str_eq(pair_obs, "formation_time") or
                                     str_eq(pair_obs, "tau")) {
                                val = std::numeric_limits<double>::infinity();
                            }
                            else
                                throw std::runtime_error("Invalid pair_obs " + pair_obs);
                        } else {
                        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                        // Pair Terms
                        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                            if (pair_terms)
                                perms = 2;
                            else
                                perms = 0;

                            // Mass
                            if (str_eq(pair_obs, "mass")) {
                                val = (subjet1+subjet2).m();
                            }
                            // Mass-squared
                            else if (str_eq(pair_obs, "mass_squared")
                                    or str_eq(pair_obs, "mass2")
                                    or str_eq(pair_obs, "m2")) {
                                val = (subjet1+subjet2).m2();
                            }
                            // e+e- EECs
                            else if (str_eq(pair_obs, "theta")) {
                                val = angle(subjet1, subjet2);
                            }
                            else if (str_eq(pair_obs, "theta2")) {
                                val = angle_squared(subjet1, subjet2);
                            }
                            // pp EECs
                            else if (str_eq(pair_obs, "deltaR")) {
                                val = deltaR(subjet1, subjet2);
                            }
                            else if (str_eq(pair_obs, "deltaR2")) {
                                val = deltaR_squared(subjet1, subjet2);
                            }
                            // Formation time
                            else if (str_eq(pair_obs, "formtime") or
                                     str_eq(pair_obs, "formation_time") or
                                     str_eq(pair_obs, "tau")) {
                                val = formation_time(subjet1, subjet2);
                            }
                            else
                                throw std::runtime_error(
                                        "Invalid pair_obs "
                                        + pair_obs);
                        }

                        // -/-/-/-/-/-/-/-/-
                        // Filling Histogram
                        // -/-/-/-/-/-/-/-/-
                        // Getting bin associated with given val
                        // (default: log-spaced bins; using outflow bins)
                        int ibin = bin_position(val, minbin, maxbin,
                                                nbins, bin_scheme,
                                                uflow, oflow);

                        // Fill histogram with the weight
                        ewoc_hists[irad][ibin] += perms
                                 *std::pow(weight1*weight2, e_weight);
                    }
                } // end subjet pair loop
                // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
            } catch (const fastjet::Error& ex) {
                // ending try statement (sometimes i find empty jets)
                std::cerr << "Warning: fastjet: " << ex.message()
                          << std::endl;
                continue;
              }
            } // end jet loop
            // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        } // end jet defn loop
        // ---------------------------------
    } // end event loop
    // =====================================

    // -----------------------------------
    // =====================================
    // Writing output files
    // =====================================
    // -----------------------------------
    for (size_t irad = 0; irad < jet_rads.size(); ++irad) {
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // Output setup
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        double jet_rad = jet_rads[irad];
        double sub_rad = sub_rads[irad];

        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Opening histogram output file
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        std::string filename = ewoc_outfiles[irad];
        std::fstream outfile;
        outfile.open(filename, std::ios_base::in |
                               std::ios_base::out |
                               std::ios_base::app);

        // Checking for existence
        if (!outfile.is_open()) {
            std::stringstream errMsg;
            errMsg << "File for EWOC output was expected "
                   << "to be open, but was not open.\n\n"
                   << "It is possible the file was unable to "
                   << "be created at the desired location:\n\n\t"
                   << "filename = " << filename << "\n\n"
                   << "Is the filename an absolute path? If not, "
                   << "that might be the problem.";
            throw std::runtime_error(errMsg.str().c_str());
        }

        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // Writing histograms to file
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // -:-:-:-:-:-:-:-:-:-:-:-:
        // bin edges
        // -:-:-:-:-:-:-:-:-:-:-:-:
        if (not(mathematica_format)) outfile << "pair_obs_edges = [\n\t";
        else outfile << "(* pair_obs_edges *)\n";

        for (int ibin = 0; ibin < nbins+1; ++ibin) {
            double edge = lin_bins ? bin_edges[ibin]
                                   : pow(10, bin_edges[ibin]);

            if (std::isinf(edge) and not(mathematica_format))
                outfile << "np.inf";
            else
                outfile << edge;

            if (ibin < nbins) outfile << HIST_DELIM;
            else outfile << std::endl;
        }

        if (not(mathematica_format)) outfile << "]\n\n";

        // -:-:-:-:-:-:-:-:-:-:-:-:
        // bin centers
        // -:-:-:-:-:-:-:-:-:-:-:-:
        if (not(mathematica_format)) outfile << "pair_obs_centers = [\n\t";
        else outfile << "\n(* pair_obs_centers *)\n";

        for (int ibin = 0; ibin < nbins; ++ibin) {
            double val = lin_bins ? bin_centers[ibin]
                                  : pow(10, bin_centers[ibin]);

            if (std::isinf(val) and not(mathematica_format))
                outfile << "np.inf";
            else
                outfile << val;

            if (ibin < nbins-1) outfile << HIST_DELIM;
            else outfile << std::endl;
        }

        if (not(mathematica_format)) outfile << "]\n\n";


        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // Processing/writing histogram
        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Normalizing histogram
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Currently, hist contains
        //   hist[ibin] = N_jets * d Sigma[pair_obs]
        // Now, changing all finite bins:
        //   hist[ibin] -> (d Sigma/d pair_obs)
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        double total_sum = 0.0;

        // Looping over all bins
        for (int bin=0; bin < nbins; ++bin) {
            // Dealing with expectation value over N jets
            ewoc_hists[irad][bin] /= njets_tot[irad];
            total_sum += ewoc_hists[irad][bin];

            // Not normalizing outflow bins further
            if (bin < bins_finite_start or bin >= nbins_finite)
                continue;

            // Otherwise, getting differential "volume" element
            double d_obs = (bin_edges[bin+1] - bin_edges[bin]);
            if (d_obs == 0) {
                throw std::runtime_error("Found invalid bin "
                                         "width d(pair_obs) = 0.");
            }
            // and normalizing
            ewoc_hists[irad][bin] /= d_obs;
            // NOTE: This is normalized linearly or logarithmically
            //       depending on `bin_scheme`/`lin_bins`
            //       (logarithmic normalization by default)
        }

        // Printing out weight information if verbose
        if (verbose >= 1) {
            float total_integral = 0;
            // Looping over all bins
            for (int bin=0; bin < nbins; ++bin) {
                // Not normalizing outflow bins further
                if (bin < bins_finite_start or bin >= nbins_finite) {
                    total_integral += ewoc_hists[irad][bin];
                    continue;
                }

                // Otherwise, getting differential "volume" element
                double dlogtheta1 = (bin_edges[bin+1] - bin_edges[bin]);
                if (dlogtheta1 == 0) {
                    throw std::runtime_error("Found invalid bin "
                                             "width dlogtheta1=0.");
                }

                total_integral += ewoc_hists[irad][bin]*dlogtheta1;
            }

            // Printing normalization
            std::cout << "\nTotal weight for (Rjet, rsub) = ("
                      << jet_rad << ", " << sub_rad << "): "
                      << total_sum;
            std::cout << "\nIntegrated total weight for "
                      << "(Rjet, rsub) = ("
                      << jet_rad << ", " << sub_rad << "): "
                      << total_integral;
        }


        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Writing finalized histogram
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        if (not(mathematica_format)) outfile << "hist = [\n\t";
        else outfile << "\n(* hist *)\n";

        for (int bin = 0; bin < nbins; ++bin) {
            outfile << std::setprecision(10)
                    << ewoc_hists[irad][bin];
            if (bin != nbins-1)
                outfile << HIST_DELIM;
            else
                outfile << "\n";
        }
        if (not(mathematica_format)) outfile << "]";

        // Closing file
        outfile.close();
    }

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
                  << std::to_string(float(duration.count())/pow(10, 6))
                  << " seconds.\n";
    }

    return 0;
}
