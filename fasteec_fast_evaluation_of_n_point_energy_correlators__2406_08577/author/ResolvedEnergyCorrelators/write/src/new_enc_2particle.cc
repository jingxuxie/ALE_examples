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


// Type definition for histograms
typedef std::vector<double> Hist;
// (we are only differential in a single angle)


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
    std::vector <double> nu_weights;
    for(int iarg=0; iarg<argc; ++iarg) {
        if(str_eq(argv[iarg], "--weights"))
            while (iarg+1 < argc and
                    // next arg doesn't start with '--'
                   std::string(argv[iarg+1]).find("--") == std::string::npos) {
                ++iarg;
                nu_weights.emplace_back(atof(argv[iarg]));
            }
    }

    if (nu_weights.size() == 0)
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


    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Initializing bin edges and centers
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // - - - - - - - - - - - - - - -
    // For theta1
    // - - - - - - - - - - - - - - -
    // Setting up under/overflow
    int nbins_finite = nbins, bins_finite_start = 0;
    if (uflow) {nbins_finite -= 1; bins_finite_start += 1;}
    if (oflow) nbins_finite -= 1;

    // (logarithmic, from 10^minbin to 10^maxbin)
    const std::vector<double> bin_edges   = get_bin_edges(
                                            minbin, maxbin, nbins,
                                            uflow, oflow);
    const std::vector<double> bin_centers = get_bin_centers(
                                            minbin, maxbin, nbins,
                                            uflow, oflow);


    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    // Output Settings
    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
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
    // Set up histograms
    std::vector<Hist> enc_hists;
    // Set up histogram output files
    std::vector<std::string> enc_outfiles;

    for (auto nu : nu_weights){
        // Setting up histograms
        enc_hists.emplace_back(Hist (nbins));

        // Setting up output files,
        std::string filename = "output/new_encs/2particle_" +
                file_prefix +
                "_nu" + str_round(nu, 2);

        filename = periods_to_hyphens(filename);
        filename += file_ext;
        // writing a header with relevant information
        // for a E^nC projected to depend on only a single angle,
        write_enc_header(filename, argc, argv,
                         std::vector<double> {nu},
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
    std::vector<std::pair<double, double>> sorted_angsweights;

    bool passes_cuts;

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

        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // Loop on jets
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        for (const auto& jet : good_jets) {
        try {
            // Start timing
            auto jet_start = std::chrono::high_resolution_clock::now();

            // Counting total num jets across events for normalization
            ++njets_tot;

            // Storing jet constituents
            const std::vector<PseudoJet>& constituents = jet.constituents();
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
                    // Looping on _E^nu C_ weights [`nu's]
                    for (size_t inu = 0; inu < nu_weights.size(); ++inu) {
                        enc_hists[inu][0] += std::pow(sum_weight1,
                                                  1+nu_weights[inu]);
                    }
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
                // (calculating change in cumulative E^nu C)
                for (size_t jpart=1; jpart<sorted_angsweights.size(); ++jpart){
                    double theta1 = sorted_angsweights[jpart].first;
                    double weight1 = sorted_angsweights[jpart].second;

                    // Calculating the theta1 bin in the histogram
                    int bin = bin_position(theta1, minbin, maxbin,
                                           nbins, "log",
                                           uflow, oflow);

                    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                    // Looping on _E^nu C_ weights [`nu's]
                    for (size_t inu = 0; inu < nu_weights.size(); ++inu) {
                        double hist_weight = weight_sp*(
                                    std::pow(sum_weight1+weight1,
                                             nu_weights[inu])
                                    -
                                    std::pow(sum_weight1,
                                              nu_weights[inu])
                                );
                        // NOTE: hist_weight is the change in the
                        // NOTE:   cumulative E^nu EC, DeltaSigma,
                        // NOTE:   between the current angle and
                        // NOTE:   the previous angle in the loop,
                        // NOTE:   due to the given first particle i.

                        // The total change in Sigma within a bin,
                        //     DeltaSigma_bin,
                        // is the sum of DeltaSigma within that bin:
                        enc_hists[inu][bin] += hist_weight;
                        // After the sum on the first particle,
                        // this gives the total DeltaSigma for the
                        // change in the cumulative E^nu C
                    }
                    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-

                    // Preparing for the next term in the loop!
                    sum_weight1 += weight1;
                } // end calculation/particle loop
                // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
            } // end "special particle" loop
            // ---------------------------------

            // ---------------------------------
            // Finished with this jet!
            // ---------------------------------
            // End timing
            if (nu_weights.size() == 1) {
                auto jet_end =
                    std::chrono::high_resolution_clock::now();
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


    // -----------------------------------
    // =====================================
    // Writing output files
    // =====================================
    // -----------------------------------
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
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // theta1s
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // -:-:-:-:-:-:-:-:-:-:-:-:
        // bin edges
        // -:-:-:-:-:-:-:-:-:-:-:-:
        if (not(mathematica_format)) outfile << "theta1_edges = [\n\t";
        else outfile << "(* theta1_edges *)\n";

        // nbins+1 bin edges:
        //   include -infty and infty for under/overflow
        for (int ibin = 0; ibin < nbins; ++ibin)
            outfile << std::pow(10, bin_edges[ibin]) << HIST_DELIM;
        if (std::isinf(bin_edges[nbins]) and not(mathematica_format))
            outfile << "np.inf\n";
        else
            outfile << std::pow(10, bin_edges[nbins]) << "\n";

        if (not(mathematica_format)) outfile << "]\n\n";

        // -:-:-:-:-:-:-:-:-:-:-:-:
        // bin centers
        // -:-:-:-:-:-:-:-:-:-:-:-:
        if (not(mathematica_format)) outfile << "theta1_centers = [\n\t";
        else outfile << "\n(* theta1s *)\n";

        for (int ibin = 0; ibin < nbins-1; ++ibin)
            outfile << std::pow(10, bin_centers[ibin]) << HIST_DELIM;
        if (std::isinf(bin_centers[nbins-1]) and not(mathematica_format))
            outfile << "np.inf\n";
        else
            outfile << std::pow(10, bin_centers[nbins-1]) << "\n";

        if (not(mathematica_format)) outfile << "]\n\n";


        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // Processing/writing histogram
        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Normalizing histogram
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Currently, hist contains
        //   hist[ibin] = N_jets * d Sigma[theta1]
        // Now, changing all finite bins:
        //   hist[ibin] -> (dSigma/dtheta1)
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        double total_sum = 0.0;

        // Looping over all bins
        for (int bin=0; bin < nbins; ++bin) {
            // Dealing with expectation value over N jets
            enc_hists[inu][bin] /= njets_tot;
            total_sum += enc_hists[inu][bin];

            // Not normalizing outflow bins further
            if (bin < bins_finite_start or bin >= nbins_finite)
                continue;

            // Otherwise, getting differential "volume" element
            double dlogtheta1 = (bin_edges[bin+1] - bin_edges[bin]);
            if (dlogtheta1 == 0) {
                throw std::runtime_error("Found invalid bin "
                                         "width dlogtheta1=0.");
            }
            enc_hists[inu][bin] /= dlogtheta1;

            // NOTE: This is theta1 times the
            // NOTE:    linearly normed distribution
        }

        // Printing out weight information if verbose
        if (verbose >= 0) {
            float total_integral = 0;
            // Looping over all bins
            for (int bin=0; bin < nbins; ++bin) {
                // Not normalizing outflow bins further
                if (bin < bins_finite_start or bin >= nbins_finite) {
                    total_integral += enc_hists[inu][bin];
                    continue;
                }

                // Otherwise, getting differential "volume" element
                double dlogtheta1 = (bin_edges[bin+1] - bin_edges[bin]);
                if (dlogtheta1 == 0) {
                    throw std::runtime_error("Found invalid bin "
                                             "width dlogtheta1=0.");
                }

                total_integral += enc_hists[inu][bin]*dlogtheta1;
            }

            // Printing normalization
            double nu = nu_weights[inu];
            std::cout << "\nTotal weight for nu=" << nu << ": "
                      << total_sum;
            std::cout << "\nIntegrated weight for nu=" << nu << ": "
                      << total_integral;
        }

        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Writing finalized histogram
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        if (not(mathematica_format)) outfile << "hist = [\n\t";
        else outfile << "\n(* hist *)\n";

        // loop over theta1s
        for (int bin = 0; bin < nbins; ++bin) {
            outfile << std::setprecision(10)
                    << enc_hists[inu][bin];
            if (bin != nbins-1)
                outfile << HIST_DELIM;
            else
                outfile << "\n";
        }
        if (not(mathematica_format)) outfile << "]";

        // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
        // Writing runtimes (if only one weight)
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

        // Closing the file
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
                  << std::to_string(float(duration.count())/std::pow(10, 6))
                  << " seconds.\n";
    }

    return 0;
}
