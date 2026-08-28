/**
 * @file    groomed_properties.cc
 *
 * @brief   Code for making histograms of several UE/MPI properties:
 *          // Single numbers (contained within nMPI file):
 *          sigma_nondiff
 *          sigma_tot
 *          nMPI_exp = sigma_tot / sigma_nondiff
 *          // Histograms:
 *          sHat
 *          pTHat
 *          nMPI
 *          pT_per_MPI
 *          sum_pT_MPI
 *          hard_pT_ratio = pT_MPI[0] / pTHat;
 *          leading_pT_ratio = pT_MPI[1] / pT_MPI[0];
 *          subleading_pT_ratio = pT_MPI[2] / pT_MPI[1];
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

// Local imports:
#include "../include/general_utils.h"
#include "../include/jet_utils.h"
#include "../include/pythia2fastjet.h"
#include "../include/cmdln.h"
#include "../include/pythia_cmdln.h"

#include "../include/opendata_utils.h"

// Type definition for histograms
typedef std::vector<double> Hist;


// =====================================
// Switches, flags, and options
// =====================================
// List of mpi properties we want to store
int MAX_N_MPI= 10;
std::vector<std::string> property_names = {"sHat", "pTHat", "nMPI",
                                           "pT_per_MPI",
                                           "sum_pT_MPI",
                                           "hard_pT_ratio",
                                           "leading_pT_ratio",
                                           "subleading_pT_ratio"};


bool is_logarithmic(std::string prop) {
    for (auto other_prop : property_names)
        if (str_eq(prop, other_prop))
            return false;
    throw std::runtime_error("Invalid property name " + prop);
}

std::string binspace(std::string prop) {
    if (is_logarithmic(prop))
        return "log";
    return "lin";
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
                                                 argc, argv, "",
                                                 true);

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Basic Pythia Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // 50k proton-proton --> hadrons events, by default
    const int         n_events      = cmdln_int("n_events",
                                          argc, argv,
                                          _NEVENTS_DEFAULT);
    const double      pt_max        = cmdln_double("pt_max",
                                                   argc, argv,
                                                   2212);
    const int         pid_1         = cmdln_int("pid_1", argc, argv,
                                          2212);
    const int         pid_2         = cmdln_int("pid_2", argc, argv,
                                          2212);
    const double      E_cm          = cmdln_double("energy",
                                                   argc, argv,
                                                   _ENERGY_DEFAULT);
    const std::string outstate_str  = cmdln_string("outstate",
                                          argc, argv,
                                          _OUTSTATE_DEFAULT);

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Output Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Whether to output hist in a mathematica friendly format
    const bool mathematica_format = cmdln_bool("mathematica",
                                               argc, argv, false);
    const std::string HIST_DELIM = mathematica_format ?  " " : ", ";
    const std::string file_ext   = mathematica_format ?  ".txt"
                                                      : ".py";

    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    // Histogram Settings
    // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
    const int   nbins  = cmdln_int("nbins", argc, argv, 500, false);

    const double shat_max_bin = cmdln_int("shat_max_bin",
                                          argc, argv, E_cm, false);
    const double pt_min_bin = cmdln_int("pt_min_bin", argc, argv,
                                        0, false);
    const double pt_max_bin = cmdln_int("pt_max_bin", argc, argv,
                                        pt_max, false);

    const bool uflow = false, oflow = true;


    // Initializing bin edges and centers
    // Setting up under/overflow for mass, pT, energy
    int nbins_finite = nbins, bins_finite_start = 0;
    if (uflow) {nbins_finite -= 1; bins_finite_start += 1;}
    if (oflow) nbins_finite -= 1;

    std::map<std::string, std::vector<double>> bin_centers;
    std::map<std::string, std::vector<double>> bin_edges;

    // centers
    bin_centers.insert(std::pair("sHat",
            get_bin_centers(0, shat_max_bin, nbins,
                            uflow, oflow)));
    bin_centers.insert(std::pair("pTHat",
            get_bin_centers(pt_min_bin, 10*pt_max_bin, nbins,
                            uflow, oflow)));
    bin_centers.insert(std::pair("nMPI",
            get_bin_centers(-0.5, MAX_N_MPI+0.5,
                            MAX_N_MPI+1,
                            false, false)));
    bin_centers.insert(std::pair("pT_per_MPI",
            get_bin_centers(pt_min_bin, pt_max_bin, nbins,
                            uflow, oflow)));
    bin_centers.insert(std::pair("sum_pT_MPI",
            get_bin_centers(pt_min_bin, 10*pt_max_bin, nbins,
                            uflow, oflow)));
    bin_centers.insert(std::pair("hard_pT_ratio",
            get_bin_centers(0, 1, nbins, false, false)));
    bin_centers.insert(std::pair("leading_pT_ratio",
            get_bin_centers(0, 1, nbins, false, false)));
    bin_centers.insert(std::pair("subleading_pT_ratio",
            get_bin_centers(0, 1, nbins, false, false)));

    // edges
    bin_edges.insert(std::pair("sHat",
            get_bin_edges(0, shat_max_bin, nbins,
                          uflow, oflow)));
    bin_edges.insert(std::pair("pTHat",
            get_bin_edges(pt_min_bin, 10*pt_max_bin, nbins,
                          uflow, oflow)));
    bin_edges.insert(std::pair("nMPI",
            get_bin_edges(-0.5, MAX_N_MPI+0.5,
                          MAX_N_MPI+1,
                          false, false)));
    bin_edges.insert(std::pair("pT_per_MPI",
            get_bin_edges(pt_min_bin, pt_max_bin, nbins,
                          uflow, oflow)));
    bin_edges.insert(std::pair("sum_pT_MPI",
            get_bin_edges(pt_min_bin, 10*pt_max_bin, nbins,
                          uflow, oflow)));
    bin_edges.insert(std::pair("hard_pT_ratio",
            get_bin_edges(0, 1, nbins, false, false)));
    bin_edges.insert(std::pair("leading_pT_ratio",
            get_bin_edges(0, 1, nbins, false, false)));
    bin_edges.insert(std::pair("subleading_pT_ratio",
            get_bin_edges(0, 1, nbins, false, false)));


    // =====================================
    // Output Setup
    // =====================================
    // Set up histograms
    std::map<std::string, Hist> mpi_properties;
    std::map<std::string, std::string> filenames;

    for (auto prop : property_names){
        // Setting up histograms
        Hist hist (str_eq(prop, "nMPI") ?
                     MAX_N_MPI+1 : nbins);
        mpi_properties.insert(std::pair(prop, hist));

        // Setting up output files
        std::string filename = "output/jet_properties/mpi";
        filename += "_"+file_prefix;
        filename += "_"+prop;
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
    std::cout << "Setting up pythia" << std::endl;
    // Setting up pythia based on command line arguments
    setup_pythia_cmdln(pythia, argc, argv);

    // Calculating
    double sigma_nondiff = pythia.getSigmaPartial(pid_1, pid_2,
                                                  E_cm, 1);
    double sigma_tot = pythia.getSigmaTotal(pid_1, pid_2, E_cm);

    // =====================================
    // Looping over events
    // =====================================
    for (int iev = 0; iev < n_events; ++iev){
        progressbar(static_cast<double>(iev+1)/
                    double(n_events));

        // Considering next event, if valid
        if(!pythia.next()) continue;

        // Getting event basics
        double sHat = pythia.info.sHat();
        double pTHat = pythia.info.pTHat();
        int nMPI = pythia.info.nMPI();

        ++mpi_properties["sHat"][bin_position(sHat,
                                      0, shat_max_bin, nbins,
                                      binspace("sHat"),
                                      uflow, oflow)];
        ++mpi_properties["pTHat"][bin_position(pTHat,
                                      pt_min_bin, 10*pt_max_bin,
                                      nbins, binspace("pTHat"),
                                      uflow, oflow)];
        ++mpi_properties["nMPI"][bin_position(nMPI,
                                      -0.5, MAX_N_MPI+0.5,
                                      MAX_N_MPI+1, "lin",
                                      "false", "false")];

        // Getting details regarding individual MPI instances
        // Collecting each MPI pT
        std::vector<double> pT_MPI;
        for (int i = 0; i < nMPI; ++i)
            pT_MPI.emplace_back(pythia.info.pTMPI(i));
        // and ordering
        std::sort(pT_MPI.begin(), pT_MPI.end());

        // pT distribution of all events
        double sum_pT_MPI = 0;
        for (int i = 1; i < nMPI; ++i) {
            double pT = pT_MPI[i];
            ++mpi_properties["pT_per_MPI"][bin_position(pT,
                                   pt_min_bin, pt_max_bin,
                                   nbins, binspace("pT_per_MPI"),
                                   uflow, oflow)];
            sum_pT_MPI += pT;
        }
        ++mpi_properties["sum_pT_MPI"][bin_position(sum_pT_MPI,
                                   pt_min_bin, 10*pt_max_bin,
                                   nbins, binspace("sum_pT_MPI"),
                                   uflow, oflow)];

        double hard_pT_ratio = pT_MPI[0]/pTHat;
        double leading_pT_ratio = pT_MPI[1]/pT_MPI[0];
        double subleading_pT_ratio = pT_MPI[2]/pT_MPI[1];
        ++mpi_properties["hard_pT_ratio"][bin_position(
                                      hard_pT_ratio,
                                      0, 1, nbins, "lin",
                                      false, false)];
        ++mpi_properties["leading_pT_ratio"][bin_position(
                                      leading_pT_ratio,
                                      0, 1, nbins, "lin",
                                      false, false)];
        ++mpi_properties["subleading_pT_ratio"][bin_position(
                                      subleading_pT_ratio,
                                      0, 1, nbins, "lin",
                                      false, false)];
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
        // Adding expected nMPI info to nMPI file
        if (str_eq(prop, "nMPI"))
            outfile << "sigma_nondiff = " << sigma_nondiff << "\n"
                    << "sigma_tot = " << sigma_tot << "\n"
                    << "# Expected nMPI = sigma_tot/sigma_nondiff\n"
                    << "nMPI_exp = " << sigma_tot/sigma_nondiff
                    << "\n";

        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        // Edges
        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
        if (not(mathematica_format))
            outfile << prop << "_edges = [\n\t";
        else outfile << "(* " << prop << "_edges *)\n";

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

        for (size_t bin=0; bin<mpi_properties[prop].size(); ++bin){
            // Expectation values over N jets
            mpi_properties[prop][bin] /= n_events;

            // Not normalizing outflow bins further
            // If not in an outflow bin
            if (not(is_logarithmic(prop) and
                    (int(bin) < bins_finite_start
                     or int(bin) >= nbins_finite))) {
                // getting differential "volume" element
                double dvol = (bin_edges[prop][bin+1]-bin_edges[prop][bin]);
                // and normalizing
                mpi_properties[prop][bin] /= dvol;
            }

            // Printing histogram
            outfile << std::setprecision(10)
                    << mpi_properties[prop][bin];
            if (bin != mpi_properties[prop].size() - 1)
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
