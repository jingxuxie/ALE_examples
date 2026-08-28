/**
 * @file    pythia_cmdln.cc
 *
 * @brief   A command line utility file for pythia event generation.
 *
 * @author: Samuel Alipour-fard
 */
#include <string>
#include <string.h>
#include <iostream>

#include <sys/types.h>
#include <sys/stat.h>

#include "Pythia8/Pythia.h"
#include "fastjet/ClusterSequence.hh"

// Local imports:
#include "../../include/general_utils.h"
#include "../../include/jet_utils.h"
#include "../../include/cmdln.h"
#include "../../include/pythia_cmdln.h"


std::string pythia_help_text = R"(
###################################
# Pythia command line parameters:
###################################

  # ================================================
  # Physics Options:
  # ================================================
  # Event generation
  [<--n_events> <int>] :                     Number of generated events (default: 50k);
  [<--level> <str: parton|hadron>] :         QCD level of generated events (parton or hadron; default: hadron);
  [<--pid_1(--pid_2)> <int>] :                  Particle ID of the particles making up the first (second)
                                                beam in the generated events (default: proton-proton);
  [<--outstate> <str>] :                     Possible outgoing states for generated events (qcd, quark, gluon, w, top; default: qcd);
  [<--energy> <double>] :                    Total center-of-mass energy of incoming particles (default: 14TeV);

  # Jet information
  [<--jet_alg|-j> <int>] :                      Jet algorithm (0 [kt], 1 [ca], 2 [antikt]; default: anti-kt);
  [<--jet_rad|-R> <double>] :                   Jet radii (default: 1.0; 1000.0 gives the whole event);
  # Phase Space constraints
  [<--pt_min> <double>] :                       Minimum value of jet p_T (default: 0);
  [<--pt_max> <double>] :                       Maximum value of jet p_T (default: 1e9);
  # Recombination Schemes
  [<--jet_scheme> <double>] :                   Jet recombination scheme
                                                (E, pt, WTA_modp, or WTA_pt; default: WTA_pt);

  # Subjet information
  [<--sub_alg|-s> <int>] :                      Subjet algorithm (0 [kt], 1 [ca: default], 2 [antikt]; default: ca);
  [<--sub_rad|-r> <double>] :                   Subjet radii (can be zero; default: 0.1);
  [<--sub_scheme> <double>] :                   Subjet recombination scheme (default: WTA_pt);

  # ================================================
  # Misc. Options:
  # ================================================
  [<--verbose|-v> <int>] :                    Verbosity of output (default: 1);
  [<--help|-h> ] :                              Get this help message!
)";


// =====================================
// Command Line Reading Utilities
// =====================================
// Format for command line reading
/**
* @brief: Set of functions that return arguments from command
*         line input.
*
* @param: argc/argv         Command line input.
*
* @return: variable type    The desired argument.
*/


// - - - - - - - - - - - - - - - - -
// Choosing event generator
// - - - - - - - - - - - - - - - - -
int showermodel_cmdln(int argc, char* argv[]) {
    for(int iarg=0;iarg<argc;iarg++) {
        // Choice of Pythia shower model
        if(str_eq(argv[iarg], "--shower_model")) {
            if (str_eq(argv[iarg+1], "1")
             or str_eq(argv[iarg+1], "pythia")
             or str_eq(argv[iarg+1], "basic"))
                return 1;

            if (str_eq(argv[iarg+1], "2")
             or str_eq(argv[iarg+1], "vincia"))
                return 2;

            if (str_eq(argv[iarg+1], "3")
             or str_eq(argv[iarg+1], "dire"))
                return 3;
        }
    }
    return 1;
}



// =====================================
// Command Line Parameter Verification
// =====================================
/**
* @brief: checks to ensure that valid command line input was given.
*
* @param: argc  Number of command line inputs;
* @param: argv  Vector of command line inputs.
*
* @return: int  0 if failed, 1 if successful
*/
int checkPythiaInputs(int argc, char* argv[]) {
    // ---------------------------------
    // Getting command line variables
    // ---------------------------------
    // Event generation settings
    // 50k 14TeV LHC -> hadrons events, by default
    int         n_events      = cmdln_int("n_events", argc, argv,
                                          _NEVENTS_DEFAULT);
    std::string level         = cmdln_string("level", argc, argv,
                                             _LEVEL_DEFAULT);
    double      E_cm          = cmdln_double("energy", argc, argv,
                                             _ENERGY_DEFAULT);
    std::string outstate_str  = cmdln_string("outstate", argc, argv,
                                             _OUTSTATE_DEFAULT);

    // Jet settings
    double      pt_min        = cmdln_double("pt_min", argc, argv,
                                             _PTMIN_DEFAULT);
    double      pt_max        = cmdln_double("pt_max", argc, argv,
                                             _PTMAX_DEFAULT);
    // Subjet settings
    std::string sub_alg       = subalgstr_cmdln(argc, argv);

    // Misc. Settings
    int verbose = cmdln_int("verbose", argc, argv, 0);

    // ---------------------------------
    // Help
    // ---------------------------------
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "-h") or
          str_eq(argv[iarg], "--help")) {
            std::cout << pythia_help_text;
            return 1;
        }
    }

    // Verbose output
    if (verbose >= 1) {
        std::cout << "# ================================ #\n"
                  << "Function call:\n"
                  << "# ================================ #\n";
        while( argc-- ) std::cout << *(argv++) << " ";
        std::cout << "\n\n";
    }

    // ---------------------------------
    // Checks on input parameters
    // ---------------------------------
    // Event generator checks
    if (n_events <= 0){
        std::cout << "Number of events must be given as a positive integer (given "
            << n_events << ").\n";
        return 1;
    }

    if (!str_eq(level, "parton") and !str_eq(level, "hadron")) {
        std::cout << "Invalid qcd level (given " << level
                  << "), must be 'parton' or 'hadron'.\n";
        return 1;
    }

    if (pt_min < 0){
        std::cout << "pt_min must be positive or zero (given "
            << pt_min << ").\n";
        return 1;
    }

    if (pt_max <= pt_min){
        std::cout << "pt_max must be larger than pt_min (given: pt_max = "
            << pt_max << ", pt_min = " << pt_min << ").\n";
        return 1;
    }

    if (E_cm <= 0){
        std::cout << "Center of mass energy must be positive (given: "
            << E_cm << ").\n";
        return 1;
    }


    if (!str_eq(outstate_str, "quark") and !str_eq(outstate_str, "gluon")
      and !str_eq(outstate_str, "qcd") and !str_eq(outstate_str, "hadrons")
      and !str_eq(outstate_str, "w")
      and !str_eq(outstate_str, "top")) {
        std::cout << "Invalid outstate (given " << outstate_str
                  << "), must be one of 'quark', 'gluon', 'qcd', 'w', 'top'.\n";
        return 1;
    }

    // Return 0 if all checks passed
    return 0;
}


// =====================================
// Pythia Setup
// =====================================
/**
* @brief: Sets up a Pythia instance using given command line args
*
* @param: argc/argv         Command line input.
*/
void setup_pythia_cmdln(Pythia8::Pythia &pythia, int argc, char* argv[]) {
    // ---------------------------------
    // Convert command line variables
    // ---------------------------------
    // Event generation settings
    // 50k 14TeV LHC -> hadrons events, by default
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

    // Jet settings
    double      pt_min        = cmdln_double("pt_min", argc, argv,
                                             _PTMIN_DEFAULT);
    double      pt_max        = cmdln_double("pt_max", argc, argv,
                                             _PTMIN_DEFAULT);

    // Subjet settings
    std::string sub_alg       = subalgstr_cmdln(argc, argv);

    // Advanced Settings
    bool        pi0_decay     = cmdln_bool("pi0_decay", argc, argv,
                                           false);
    bool        use_isr       = cmdln_bool("isr", argc, argv,
                                           false);
    bool        use_fsr       = cmdln_bool("fsr", argc, argv,
                                           false);
    bool        use_mpi       = cmdln_bool("mpi", argc, argv,
                                           false);
    int         shower_model  = showermodel_cmdln(argc, argv);

    // Misc. Settings
    int verbose = cmdln_int("verbose", argc, argv, 1);
    int print_every = cmdln_int("print_every", argc, argv,
                                verbose>=2 ? 1000 :
                                 (verbose>=1 ? 100000 :
                                                -1));

    // ---------------------------------
    // Pythia setup
    // ---------------------------------
    // - - - - - - - - - - - - - - - - -
    // Setting up beams
    // - - - - - - - - - - - - - - - - -
    pythia.readString("Beams:idA = " + std::to_string(pid_1));
    pythia.readString("Beams:idB = " + std::to_string(pid_2));
    pythia.readString("Beams:eCM = " + str_round(E_cm, 2));

    // - - - - - - - - - - - - - - - - -
    // Setting up other radiation options
    // - - - - - - - - - - - - - - - - -
    // Parton or hadron level
    if (str_eq(level, "parton"))
        pythia.readString("HadronLevel:all = off");
    else if (str_eq(level, "hadron"))
        pythia.readString("HadronLevel:all = on");

    // Whether to allow neutral pion decay
    if (not pi0_decay)
        pythia.readString("111:mayDecay = off");

    // Radiation/interaction options
    if (not use_isr) {
        // ISR for leptons
        pythia.readString("PDF:lepton = off");
        // ISR for QCD
        pythia.readString("PartonLevel:ISR = off");
    }
    if (not use_fsr)
        pythia.readString("PartonLevel:FSR = off");
    if (not use_mpi)
        pythia.readString("PartonLevel:MPI = off");

    // Choosing shower model
    pythia.readString("PartonShowers:model = " + std::to_string(shower_model));

    // - - - - - - - - - - - - - - - - -
    // Phase space cuts
    // - - - - - - - - - - - - - - - - -
    // Producing events with partons which nearly satisfy
    // pt requirements for jets -- expanding boundaries for less
    // biased selection
    pythia.readString("PhaseSpace:pTHatMin = "
                      + std::to_string( std::max(0.0, pt_min*0.8) )
                     );
    pythia.readString("PhaseSpace:pTHatMax = "
                      +std::to_string(std::max(-1.0, pt_max*1.2) )
                     );

    // - - - - - - - - - - - - - - - - -
    // Telling the user
    // - - - - - - - - - - - - - - - - -
    std::cout << "# ==+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+= #\n"
              << pid_1 << " + " << pid_2 << "  -->  " << outstate_str
              << " at "
              << str_round(E_cm/1000., 3) << " TeV\n"
              << "# ==+=+=+=+=+=+=+=+=+=+=+=+=+=+=+=+= #\n";

    std::cout << "\t # " << level << " level, "
              << "ISR: " << (use_isr ? "on" : "off")
              << ", FSR: " << (use_fsr ? "on" : "off")
              << ", MPI: " << (use_mpi ? "on" : "off")
              << ";\n";

    if (verbose >= 2) {
        std::cout << "\t- Shower model: " << shower_model << ".\n";
    }

    // ---------------------------------
    // Process specific interactions
    // ---------------------------------
    // Outgoing quarks
    if (str_eq(outstate_str, "quarks")) {
        // Hadronic/QCD initial state
        if (is_qcd_pid(pid_1) and is_qcd_pid(pid_2)) {
            pythia.readString("HardQCD:gg2qqbar = on");
            pythia.readString("HardQCD:qqbar2qqbar = on");
            pythia.readString("HardQCD:qqbar2ccbar = on");
            pythia.readString("HardQCD:qqbar2bbbar = on");
            pythia.readString("HardQCD:qqbar2ttbar = on");
        }

        pythia.readString("WeakSingleBoson:ffbar2gmZ = on");

        // Excluding top quark decays of Z
        pythia.readString("23:onMode = off");
        pythia.readString("23:onIfAny = 1 2 3 4 5");
    }

    // Outgoing gluons
    if (str_eq(outstate_str, "gluons")) {
        if (is_qcd_pid(pid_1) and is_qcd_pid(pid_2)) {
            pythia.readString("HardQCD:qqbar2gg = on");
            pythia.readString("HardQCD:gg2gg = on");
            pythia.readString("HardQCD:gg2g = on");
        }
    }

    // Any outgoing hadronic state
    if (str_eq(outstate_str, "hadrons") or str_eq(outstate_str, "qcd")) {
        pythia.readString("HardQCD:all = on");

        if (is_leptonic_pid(pid_1) and is_leptonic_pid(pid_2)) {
            pythia.readString("WeakSingleBoson:ffbar2gmZ = on");

            // Excluding top quark decays of Z
            pythia.readString("23:onMode = off");
            pythia.readString("23:onIfAny = 1 2 3 4 5");
        }
    }

    // Outgoing W bosons
    if (str_eq(outstate_str, "w")) {
        if (is_qcd_pid(pid_1) and is_qcd_pid(pid_2)) {
            /* pythia.readString("HardQCD:all = on"); */
            pythia.readString("WeakDoubleBoson:ffbar2WW = on");
        }
        if (is_leptonic_pid(pid_1) and is_leptonic_pid(pid_2)) {
            pythia.readString("WeakDoubleBoson:ffbar2WW = on");
        }
    }

    // Outgoing top quarks
    if (str_eq(outstate_str, "top")) {
        if (is_qcd_pid(pid_1) and is_qcd_pid(pid_2)) {
            pythia.readString("Top:gg2ttbar = on");
            pythia.readString("Top:qqbar2ttbar = on");
        }
        if (is_leptonic_pid(pid_1) and is_leptonic_pid(pid_2)) {
            pythia.readString("Top:ffbar2ttbar(s:gmZ) = on");
        }
    }

    // Misc. options
    pythia.readString("Next:numberCount = "+print_every);

    if (verbose >= 2) {
        // list changed settings
        pythia.readString("Init:showChangedSettings = on");
    }
    else if (verbose < 2) {
        pythia.readString("Init:showChangedSettings = off");
        pythia.readString("Init:showProcesses = off");
        pythia.readString("Init:showMultipartonInteractions = off");
        pythia.readString("Init:showChangedParticleData = off");

        pythia.readString("Next:numberCount = 100000");
        pythia.readString("Next:numberShowLHA = 0");
        pythia.readString("Next:numberShowInfo = 0");
        pythia.readString("Next:numberShowProcess = 0");
        pythia.readString("Next:numberShowEvent = 0");
    }
    else if (verbose < 1) {
        pythia.readString("Stat:showProcessLevel = off");
        pythia.readString("Stat:showErrors = off");
    }

    pythia.init();
}


/**
* @brief: Writes a header containing information used in event
*         generation in Pythia using given command line args.
*
* @param: filename           Location of file which wants a header.
*
* @param: argc/argv          Command line input.
*
* @param: python_format         Whether to write in a python-friendly way.
*
*/
void write_jetproperty_header(std::string filename,
                              int argc, char* argv[],
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
        errMsg << "File for jet property output expected "
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
         << "outstate_str = \"" + outstate_str << "\"\n";

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
         << "# Output:\n"
         << "# ==================================\n";

    file.close();

    return;
}
