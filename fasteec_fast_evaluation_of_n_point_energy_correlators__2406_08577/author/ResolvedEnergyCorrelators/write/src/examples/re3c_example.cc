/**
 * @file    new_enc_3particle.cc
 *
 * @brief   Code for generating histograms for "new angles on"
 *          resolved 3-point energy correlators (RE3Cs);
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
#include "fastjet/PseudoJet.hh"

// Local imports:
#include "../../include/general_utils.h"
#include "../../include/jet_utils.h"
#include "../../include/cmdln.h"
#include "../../include/enc_utils.h"
#include "../../include/opendata_utils.h"
#include "../../include/RE3C.h"


// ####################################
int main (int argc, char* argv[]) {
// ####################################
    // Starting timer
    auto start = high_resolution_clock::now();
    const int n_events = cmdln_int("n_events",
                                   argc, argv,
                                   100000);

    // Getting the list of energy weight pairs (nu1, nu2)
    std::vector <std::pair<double, double>> nu_weights = {{1,1}};


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


    // =====================================
    // Output Setup
    // =====================================
    RE3C re3c_calculator(nu_weights, minbin, maxbin, nbins,
                         1, true,
                         true, true, true,
                         true, true, 1,
                         "output/re3c_example", false);


    for (size_t inu=0; inu < nu_weights.size(); ++inu){
        // Setting up output files
        std::string filename = re3c_calculator.enc_outfiles[inu];
        std::pair<double, double> nus = nu_weights[inu];
        write_enc_header(filename, argc, argv,
                     std::vector<double> {nus.first, nus.second},
                     true);
    }

    // ---------------------------------
    // CMS Open Data
    // ---------------------------------
    od::EventReader cms_jet_reader(od::cms_jets_file);


    // =====================================
    // Looping over events
    // =====================================
    for (int iev = 0; iev < n_events; ++iev) {
        progressbar(static_cast<double>(iev+1)/
                    double(n_events));

        // Reading jet from CMS Opendata
        PseudoJet jet;
        cms_jet_reader.read_jet(jet);

        // Performing RE3C computation
        re3c_calculator.processJet(jet);
    } // end event loop
    // =====================================

    // Writing output files
    // (writeOutput automatically normalizes the histogram)
    re3c_calculator.writeOutput();

    // ---------------------------------
    // =====================================
    // Verifying successful run
    // =====================================
    // ---------------------------------
    std::cout << "\nComplete!\n";
    auto stop = high_resolution_clock::now();
    auto duration = duration_cast<microseconds>(stop-start);
    std::cout << "Analyzed and saved data from "
              << std::to_string(n_events)
              << " events in "
              << std::to_string(float(duration.count())/std::pow(10, 6))
              << " seconds.\n";

    std::cout << "Output file: \n";
    for (auto filename : re3c_calculator.enc_outfiles)
        std::cout << filename << std::endl;

    return 0;
}
