/**
 * @file    enc_utils.cc
 *
 * @brief   A utility file for (new angles on)
 *          N-point Energy Correlators (ENCs)
 *
 * @author: Samuel Alipour-fard
 */
#include <string>
#include <string.h>
#include <iostream>

#include "../../include/cmdln.h"
#include "../../include/enc_utils.h"


const std::string enc_banner = "";

/**
* @brief: Writes a header containing information used in event
*         generation in Pythia using given command line args.
*         Also contains weight information.
*         Used for singly differential new EnCs.
*
* @param: filename           Location of file which wants a header.
*
* @param: argc/argv          Command line input.
*
* @param: weights            Energy weights used for this file.
*
* @param: python_format         Whether to write in a python-friendly way.
*
*/
void write_enc_header(std::string filename,
                           int argc, char* argv[],
                           std::vector<double> weights,
                           bool python_format) {
    // ---------------------------------
    // Getting command line variables
    // ---------------------------------
    // Event generation settings
    int         n_events      = cmdln_int("n_events", argc, argv,
                                          _NEVENTS_DEFAULT);
    std::string level         = cmdln_string("level", argc, argv,
                                             _LEVEL_DEFAULT);
    double      E_cm          = cmdln_double("energy", argc, argv,
                                             _ENERGY_DEFAULT);
    int         pid_1         = cmdln_int("pid_1", argc, argv,
                                          _PID_1_DEFAULT);
    int         pid_2         = cmdln_int("pid_2", argc, argv,
                                          _PID_2_DEFAULT);
    std::string outstate_str  = cmdln_string("outstate", argc, argv,
                                             _OUTSTATE_DEFAULT);

    bool        use_opendata  = cmdln_bool("use_opendata", argc, argv,
                                           true);
    if (use_opendata) level = "data";

    // Jet settings
    double      jet_rad       = cmdln_double("jet_rad", argc, argv,
                                             1000.);
    std::string jet_alg       = jetalgstr_cmdln(argc, argv);
    std::string jet_scheme    = scheme_string[jetrecomb_cmdln(argc, argv)];

    // ---------------------------------
    // Writing the header
    // ---------------------------------
    // Opening the file
    std::ofstream file;
    file.open(filename);

    // Checking for existence
    if (!file.is_open()) {
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


    if (not(python_format)) {
        // Writing for loading into mathematica
        file << "(*(* Information *)*)\n";
        file << "(* Function call *)\n";
        while( argc-- ) file << *(argv++) << " ";
        file << "\n\n";

        file << "(* nevents  energy  level  pid1  pid2  outstate"
             <<  "  weight  jet_alg   jet_scheme  jet_radius *)\n";
        file << n_events << " " << E_cm << " " << level << " "
             << pid_1 << " " << pid_2 << " " << outstate_str << " ";

        for (auto weight : weights)
             file << weight << " ";

        file << jet_alg << " " << jet_scheme << " " << jet_rad
             << "\n\n";

        file << "(*(* Histogram *)*)\n";

        return;
    }

    // Add header with additional information
    file << "import numpy as np\n\n"
         << "# ==================================\n"
         << "# Information\n"
         << "# ==================================\n"
         << "# Function call ```";
    while( argc-- ) file << *(argv++) << " ";
    file << "```\n\n"
         << "# Number of events:\n"
         << "n_events = " + std::to_string(n_events) << "\n"

         << "# Process\n"
         << "energy = " << E_cm << "\n"
         << "level = \"" + level << "\"\n"
         << "pid_1, pid_2 = " << pid_1 << ", " << pid_2 << "\n"
         << "outstate_str = \"" + outstate_str << "\"\n"

         << "# Weight information:\n"
         << "weight = (";
         for (size_t iw=0; iw<weights.size()-1; iw++)
             file << weights[iw] << ", ";
         file << weights[weights.size()-1] << ")\n";

    if (use_opendata) {
        file <<"# CMS 2011A Jet Dataset:\n"
             << "jet_alg = \"anti-kt\"\n"
             << "jet_scheme = \"E?\"" << "\n"
             << "jet_rad = 0.5\n\n";
    } else if (jet_rad == 1000) {
        file <<"# Jet information (FULL EVENT):\n"
             << "jet_alg = None"<< "\n"
             << "jet_scheme = None" << "\n"
             << "jet_rad = None" << "\n\n";
    } else {
        file <<"# Jet information:\n"
             << "jet_alg = \"" + jet_alg << "\"\n"
             << "jet_scheme = \"" + jet_scheme << "\"\n"
             << "jet_rad = \"" + std::to_string(jet_rad) << "\"\n\n";
    }

    file << "# ==================================\n"
         << "# Output Histogram:\n"
         << "# ==================================\n";

    file.close();

    return;
}
