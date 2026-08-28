/**
 * @file    new_enc_4particle.cc
 *
 * @brief   Code for generating histograms for "new angles on"
 *          n-point projected energy correlators ('EnC's);
 *          in this file, we use four particles, and are
 *          differential in five angles:
 *          theta1, theta2, phi2, theta3, and phi3.
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


// =====================================
// Type definitions for histograms
// =====================================
// Multi-dimensional Histograms
typedef std::vector<double> Hist1d;
typedef std::vector<std::vector<double>> Hist2d;
typedef std::vector<Hist2d> Hist3d;
typedef std::vector<Hist3d> Hist4d;
typedef std::vector<Hist4d> Hist5d;

// Using triples of weights to specify the three-particle correlator
typedef std::tuple<double, double, double> weight_t;


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


// =====================================
// Additional Utilities
// =====================================
inline double mod2pi(double phi) {
    while (phi > PI)
        phi -= TWOPI;
    while (phi <= -PI)
        phi += TWOPI;

    return phi;
}

double enc_azimuth(const PseudoJet& part1,
                   const PseudoJet& part_sp,
                   const PseudoJet& part2) {
    // NOTE: I think this doesn't work for very fat jets --
    // NOTE:   roughly because fat jets require a bit more care
    // NOTE:   with mod(2pi) arithmetic
    // - - - - - - - - - - - - - - - - - - -
    // Normalized vectors in eta-phi plane
    // - - - - - - - - - - - - - - - - - - -
    // From part_sp to part1
    double x1 = part1.rap() - part_sp.rap();
    double y1 = mod2pi(part1.phi() - part_sp.phi());
    const double n1  = sqrt(std::pow(x1, 2.) + std::pow(y1, 2.));
    if (n1 == 0)
        return 0;
    x1 /= n1; y1 /= n1;

    // From part_sp to part2
    double x2;
    x2 = part2.rap() - part_sp.rap();
    double y2 = mod2pi(part2.phi() - part_sp.phi());
    const double n2  = sqrt(std::pow(x2, 2.) + std::pow(y2, 2.));
    if (n2 == 0)
        return 0;
    x2 /= n2; y2 /= n2;

    // - - - - - - - - - - - - - - - - - - -
    // Getting the "angle" between these vectors
    // - - - - - - - - - - - - - - - - - - -
    const double dot = x1*x2 + y1*y2;
    const double det = x1*y2 - y1*x2;
    double phi = mod2pi(atan2(det, dot));

    // Setting it to be between -pi and pi
    phi = phi > PI ? phi - TWOPI : phi;
    if (phi < -PI or PI < phi)
        throw std::range_error(
                "Found azimuthal angle not between -pi and pi.");

    return phi;
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
    const int   nbins     = cmdln_int("nbins", argc, argv,
                                      100, false);
    // NOTE: using logarithmically spaced bins,
    // NOTE:   with minbin and maxbin in base 10

    const double minbin   = cmdln_double("minbin", argc, argv,
                                   -8, false);
    const double maxbin   = cmdln_double("maxbin", argc, argv,
                                   0.05, false);
    const bool bin1_uflow = true, bin1_oflow = true;

    // Phi is binned linearly, with same nbins by default
    const int   nphibins  = cmdln_int("nphibins", argc, argv,
                                nbins, false);

    // theta2/theta1 is binned linearly by default, but can be log
    const bool lin_bin2   = cmdln_bool("lin_bin2", argc, argv,
                                 true, false);

    // theta3/theta2 is binned linearly by default, but can be log
    const bool lin_bin3   = cmdln_bool("lin_bin3", argc, argv,
                                 true, false);

    // Use a recursive definition for the azimuthal angle by default
    bool recursive_phi = cmdln_bool("recursive_phi", argc, argv,
                                    true);

    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Initializing bin edges and centers
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Bins for theta2/theta1
    const std::string bin2_scheme = lin_bin2 ? "lin" : "log";
    const double bin2_min = lin_bin2 ?   0   : minbin;
    const double bin2_max = lin_bin2 ?   1   : 0;
    const bool bin2_uflow        = lin_bin2 ? false : true;

    // Bins for theta3/theta2
    const std::string bin3_scheme = lin_bin3 ? "lin" : "log";
    const double bin3_min = lin_bin3 ?   0   : minbin;
    const double bin3_max = lin_bin3 ?   1   : 0;
    const bool bin3_uflow        = lin_bin3 ? false : true;
    const int phizerobin = bin_position(0, -PI, PI, nphibins,
                                  "linear", false, false);

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Input Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const bool use_opendata = cmdln_bool("use_opendata", argc, argv,
                                         true);

    // =====================================
    // Output Setup
    // =====================================
    // Set up histograms
    Hist5d enc_hist (nbins, Hist4d(nbins,
                    Hist3d(nphibins, Hist2d(nbins, Hist1d(nphibins)))));

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
    std::vector<std::pair<double, PseudoJet>> sorted_angs_parts;

    // Reserving memory
    particles.reserve(150);
    all_jets.reserve(20);
    good_jets.reserve(5);
    sorted_angs_parts.reserve(50);

    // Preparing to store runtime info
    std::map<int, std::vector<double>> jet_runtimes;

    // =====================================
    // Looping over events
    // =====================================
    for (int iev = 0; iev < n_events; ++iev) {
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
                const PseudoJet& jet = all_jets[i];

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

                    // (Sorting:
                    //   * [theta1]: angle relative to special particle
                    //   * [weight1]: either E2/Ejet or pt2/ptjet
                    //  by theta1)
                    sorted_angs_parts.clear();

                    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                    // Loop on particles
                    for (const auto& part1 : constituents) {
                        // Angle relative to "special" particle
                        double theta1 = use_deltaR ?
                                part_sp.delta_R(part1) :
                                fastjet::theta(part_sp, part1);

                        sorted_angs_parts.emplace_back(theta1, part1);
                    } // end second particle loop
                    // Sorting angles/weights by angle as promised :)
                    std::sort(sorted_angs_parts.begin(),
                              sorted_angs_parts.end(),
                              [](auto& left, auto& right) {
                                  return left.first < right.first;
                             });
                    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-

                    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                    // Loop on first non-special particle
                    // (calculating change in cumulative E^nu C)
                    for (size_t jpart=1; jpart<sorted_angs_parts.size(); ++jpart) {
                        // Getting 1st particle
                        double theta1 = sorted_angs_parts[jpart].first;
                        PseudoJet& part1  = sorted_angs_parts[jpart].second;
                        double weight1 = use_pt ?
                                part1.pt() / weight_tot :
                                part1.e() / weight_tot;

                        // Calculating the theta1 bin in the histogram
                        int bin1 = bin_position(theta1, minbin, maxbin,
                                                nbins, "log",
                                                bin1_uflow, bin1_oflow);

                        // Initializing the sum of weights
                        // within an angle of the 2nd particle
                        std::vector<double> sum_weight2(nphibins);

                        sum_weight2[phizerobin] += weight_sp;

                        // -----------------------------------
                        // Loop on second non-special particle
                        for (size_t kpart=1; kpart<jpart; ++kpart) {
                            // Getting 2nd particle
                            double theta2 = sorted_angs_parts[kpart].first;
                            PseudoJet& part2  = sorted_angs_parts[kpart].second;
                            double weight2 = use_pt ?
                                    part2.pt() / weight_tot :
                                    part2.e() / weight_tot;
                            double theta2_over_theta1 =
                                theta1 == 0 ? 0 : theta2/theta1;

                            // Calculating theta2/theta1 bin position
                            int bin2 = bin_position(theta2_over_theta1,
                                                bin2_min, bin2_max,
                                                nbins, bin2_scheme,
                                                bin2_uflow, false);
                                            /* Variable spacing scheme,
                                             * but with no overflow. */

                            // Getting azimuthal angle
                            // (angle from part1 to part_sp to part2
                            //  in rapidity-azimuth plane)
                            double phi2 = enc_azimuth(
                                    part1, part_sp, part2);

                            // Calculating the phi bin
                            int binphi2 = bin_position(phi2, -PI, PI,
                                                   nphibins, "linear",
                                                   false, false);

                            // Initializing the sum of weights
                            // within an angle of the 3rd particle
                            std::vector<double> sum_weight3(nphibins);
                            sum_weight3[phizerobin] += weight_sp;

                            // -----------------------------------
                            // Loop on third non-special particle
                            // Getting 2nd particle
                            for (size_t ellpart=1; ellpart<kpart; ++ellpart) {
                                double theta3 = sorted_angs_parts[ellpart].first;
                                PseudoJet& part3  = sorted_angs_parts[ellpart].second;
                                double weight3 = use_pt ?
                                        part3.pt() / weight_tot :
                                        part3.e() / weight_tot;
                                double theta3_over_theta2 =
                                    theta2 == 0 ? 0 : theta3/theta2;

                                // Calculating theta3/theta2 bin
                                int bin3 = bin_position(
                                        theta3_over_theta2,
                                        bin3_min, bin3_max,
                                        nbins, bin3_scheme,
                                        bin3_uflow, false);
                                   /* Variable spacing scheme,
                                    * but with no overflow. */

                                // Getting azimuthal angle
                                double phi3 = recursive_phi ?
                                    enc_azimuth(part2, part_sp, part3)
                                    :
                                    enc_azimuth(part1, part_sp, part3);

                                // Calculating the phi bin
                                int binphi3 = bin_position(phi3,
                                        -PI, PI, nphibins,
                                        "linear", false, false);

                                // *:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*
                                // Adding to the histogram
                                // *:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*
                                double delta_weight1 = (
                                   std::pow(sum_weight1
                                             + weight1, 1)
                                   -
                                   std::pow(sum_weight1, 1)
                                 );
                                double delta_weight2 = (
                                   std::pow(sum_weight2[binphi2]
                                             + weight2, 1)
                                   -
                                   std::pow(sum_weight2[binphi2],
                                            1)
                                 );
                                double delta_weight3 = (
                                   std::pow(sum_weight3[binphi3]
                                             + weight3, 1)
                                   -
                                   std::pow(sum_weight3[binphi3],
                                            1)
                                 );

                                double perm = 6;
                                double hist_weight = weight_sp *
                                        delta_weight1 *
                                        delta_weight2 *
                                        delta_weight3;

                                enc_hist[bin1]
                                    [bin2][binphi2]
                                    [bin3][binphi3] +=
                                        perm*hist_weight;

                                // Preparing for next particle
                                sum_weight3[binphi3] += weight3;
                            } // end 3rd particle loop
                            // -----------------------------------
                            // Preparing for next particle in the loop!
                            sum_weight2[binphi2] += weight2;
                        } // end 2nd particle loop
                        // -----------------------------------

                        // Preparing for the particle in the loop!
                        sum_weight1 += weight1;
                    } // end 1st particle loop
                    // -#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-
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
