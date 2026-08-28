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

#include "../../include/opendata_utils.h"

#include "../../include/enc_utils.h"
#include "../../include/PENC.h"

// Type definition for histograms
typedef std::vector<double> Hist;
// (we are only differential in a single angle)


// ####################################
int main (int argc, char* argv[]) {
// ####################################
    // Starting timer
    auto start = high_resolution_clock::now();
    const int n_events = cmdln_int("n_events",
                                   argc, argv,
                                   100000);

    // Getting the list of energy weights from command line
    // (We are calculating the projected `PENC`)
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
            "Must be given at least 1 weight (via `--weights`).");

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


    // =====================================
    // Output Setup
    // =====================================
    PENC penc_calculator(nu_weights, minbin, maxbin, nbins,
                    true, true, true,
                    uflow, oflow, 1,
                    "output/penc_example", false);


    // Writing header to output files
    for (size_t inu = 0; inu < nu_weights.size(); ++inu) {
        std::string filename = penc_calculator.enc_outfiles[inu];
        double nu = nu_weights[inu];
        write_enc_header(filename, argc, argv,
                         std::vector<double>{nu});
    }


    // ---------------------------------
    // CMS Open Data
    // ---------------------------------
    od::EventReader cms_jet_reader(od::cms_jets_file);


    // =====================================
    // Looping over events
    // =====================================
    for (int iev = 0; iev < n_events; ++iev){
        progressbar(static_cast<double>(iev+1)/
                    double(n_events));

        // Reading jet from CMS Opendata
        PseudoJet jet;
        cms_jet_reader.read_jet(jet);

        // Performing PENC computation
        penc_calculator.processJet(jet);
    } // end event loop
    // =====================================

    // Writing output files
    // (writeOutput automatically normalizes the histogram)
    penc_calculator.writeOutput();

    // ---------------------------------
    // Verifying successful run
    // ---------------------------------
    std::cout << "\nComplete!\n";
    auto stop = high_resolution_clock::now();
    auto duration = duration_cast<microseconds>(stop-start);
    std::cout << "Analyzed and saved data from "
              << std::to_string(n_events)
              << " events in "
              << std::to_string(float(duration.count())/std::pow(10, 6))
              << " seconds.\n";

    std::cout << "Output files: \n";
    for (auto filename : penc_calculator.enc_outfiles)
        std::cout << filename << std::endl;

    return 0;
}
