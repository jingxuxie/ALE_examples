/**
 * @file    pythia_cmdln.cc
 *
 * @brief   A utility file for (potentially non-angular)
 *          Energy Weighted Observable Correlations (EWOCs)
 *
 * @author: Samuel Alipour-fard
 */
#include <string>
#include <string.h>
#include <iostream>

#include "../../include/cmdln.h"
#include "../../include/pythia_cmdln.h"
#include "../../include/ewoc_utils.h"


// Display for EWOC code
const std::string ewoc_banner = R"(
     ______    _____                  _____         _____           ______
 ___|\     \  |\    \   _____    ____|\    \    ___|\    \      ___|\     \
|     \     \ | |    | /    /|  /     /\    \  /    /\    \    |    |\     \
|     ,_____/|\/     / |    || /     /  \    \|    |  |    |   |    |/____/|
|     \--'\_|//     /_  \   \/|     |    |    |    |  |____|___|    \|   | |
|     /___/| |     // \  \   \|     |    |    |    |   ____|    \    \___|/
|     \____|\|    |/   \ |    |\     \  /    /|    |  |    |    |\     \
|____ '     /|\ ___/\   \|   /| \_____\/____/ |\ ___\/    /|\ ___\|_____|
|    /_____/ | |   | \______/ |\ |    ||    | | |   /____/ | |    |     |
|____|     | /\|___|/\ |    | | \|____||____|/ \|___|    | /\|____|_____|
  \( |_____|/    \(   \|____|/     \(    )/      \( |____|/    \(    )/
   '    )/        '      )/         '    '        '   )/        '    '
        '                '                            '
)";


// Default EWOC options
const double _DEFAULT_WEIGHT = 1;


/**
* @brief: Writes a header containing information used in event
*         generation in Pythia using given command line args.
*         Contains jet and subjet information
*
* @param: filename           Location of file which wants a header.
*
* @param: argc/argv          Command line input.
*
* @param: jet_rad/sub_rad    Jet and subjet radii used for this file.
*
* @param: python_format      Whether to write in a python-friendly way.
*
*/
void write_ewocfile_header(std::string filename,
                           int argc, char* argv[],
                           double jet_rad, double sub_rad,
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
    bool        mpi           = cmdln_bool("mpi", argc, argv,
                                           false);
    std::string outstate_str  = cmdln_string("outstate", argc, argv,
                                             _OUTSTATE_DEFAULT);

    bool        use_opendata  = cmdln_bool("use_opendata",
                                           argc, argv, false);
    if (use_opendata) level = "data";


    // Jet settings
    std::string jet_alg    = jetalgstr_cmdln(argc, argv);
    std::string jet_scheme = scheme_string[jetrecomb_cmdln(argc, argv)];

    // Subjet settings
    std::string sub_alg    = subalgstr_cmdln(argc, argv);
    std::string sub_scheme = scheme_string[subrecomb_cmdln(argc, argv)];

    // EWOC settings
    const double e_weight = cmdln_double("weight", argc, argv,
                                         _DEFAULT_WEIGHT);

    // ---------------------------------
    // Writing the header
    // ---------------------------------
    // Opening the file
    std::ofstream file;
    file.open(filename);

    // Checking for existence
    if (!file.is_open()) {
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


    if (not(python_format)) {
        // Writing for loading into mathematica
        file << "(*(* Information *)*)\n";
        file << "(* Function call *)\n";
        while( argc-- ) file << *(argv++) << " ";
        file << "\n\n";

        file << "(* nevents  energy  level  pid1  pid2  outstate"
             <<  "  jet_alg   jet_scheme  jet_radius  sub_alg"
             <<  "  sub_scheme  subjet_radius *)\n";
        file << n_events << " " << E_cm << " " << level << " "
             << pid_1 << " " << pid_2 << " " << outstate_str << " "
             << jet_alg << " " << jet_scheme << " " << jet_rad << " "
             << sub_alg << " " << sub_scheme << " " << sub_rad
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
         << "level = \"" << level << "\"\n"
         << "mpi = \"" << mpi << "\"\n"
         << "pid_1, pid_2 = " << pid_1 << ", " << pid_2 << "\n"
         << "outstate_str = \"" << outstate_str << "\"\n"

         << "# Weight information:\n"
         << "weight = " << e_weight << "\n";

    // Jet information
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

    // Subjet information
    file << "# Subjet information:\n"
         << "sub_alg = \"" + sub_alg << "\"\n"
         << "sub_scheme = \"" + sub_scheme << "\"\n"
         << "sub_rad = " + std::to_string(sub_rad) << "\n\n"

         << "# ==================================\n"
         << "# Output Histogram:\n"
         << "# ==================================\n";

    file.close();

    return;
}
