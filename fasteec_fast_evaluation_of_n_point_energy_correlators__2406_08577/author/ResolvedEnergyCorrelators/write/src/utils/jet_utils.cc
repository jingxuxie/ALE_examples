/**
 * @file    ewoc_utils.cc
 *
 * @brief   A file containing utility functions for jet analyses.
 *
 * @author: Samuel Alipour-fard
 */

// ---------------------------------
// Basic imports
// ---------------------------------
#include <iostream>
#include <ostream>
#include <string>
#include <string.h>
#include <limits>
#include <locale>
#include <string>
#include <vector>
#include <stdexcept>
#include <algorithm>  // std::max and std::min
#include <random>

#include <assert.h>

#include <sys/types.h>
#include <sys/stat.h>


#define _USE_MATH_DEFINES
#include <cmath>

// Random numbers for ghost grids
#include <stdlib.h>

// ---------------------------------
// HEP imports
// ---------------------------------
#include "fastjet/PseudoJet.hh"
#include "fastjet/ClusterSequence.hh"

#include "../../include/general_utils.h"
#include "../../include/jet_utils.h"

using namespace fastjet;


// =====================================
// Global Flags
// =====================================
float EPSILON = 1e-6;


// =====================================
// File Labelling Utilities
// =====================================
std::string jet_alg_int_to_str(int alg_int) {
    assert(alg_int == 2 or alg_int == 1 or alg_int == 0);

    return (alg_int == 2) ? "akt" : (
        (alg_int == 1) ? "ca" : (
        (alg_int == 0) ? "kt" :
        "_ERR"));
}


int jet_alg_str_to_int(std::string alg_str) {
    assert(str_eq(alg_str, "akt") or str_eq(alg_str, "antikt")
           or str_eq(alg_str, "ca") or str_eq(alg_str, "kt")
           or str_eq(alg_str, "2") or str_eq(alg_str, "1")
           or str_eq(alg_str, "0"));

    return (str_eq(alg_str, "akt") or str_eq(alg_str, "2")
            or str_eq(alg_str, "antikt")) ? 2 : (
        (str_eq(alg_str, "ca") or str_eq(alg_str, "1")) ? 1 : (
        (str_eq(alg_str, "kt") or str_eq(alg_str, "0")) ? 0 :
        -1));
}


// =====================================
// Pseudojet utilities
// =====================================
// ---------------------------------
// Particle utilities
// ---------------------------------
// PIDs for QCD particles:
const std::vector<int> qcd_pids{
            1, -1, 2, -2, 3, -3,    // light quarks
            4, -4, 5, -5,           // heavy quarks
            111, 211, -211, 221,    // light mesons
            21,                     // gluon
            // Probably should include more?
            2212, -2212, 2112, -2112,  // protons and neutrons
};

// PIDs for leptons and lepton neutrinos
const std::vector<int> lepton_pids{11, -11, 13, -13, 15, -15};
const std::vector<int> nu_pids{12, -12, 14, -14, 16, -16};
const std::vector<int> lepton_and_nu_pids = concat_ints(lepton_pids,
                                                        nu_pids);

// Checking whether PIDs lie in certain categories
bool is_qcd_pid(int pid) {
    return std::find(qcd_pids.begin(), qcd_pids.end(), pid) != qcd_pids.end();
}

bool is_leptonic_pid(int pid) {
    return std::find(lepton_pids.begin(), lepton_pids.end(), pid) != lepton_pids.end();
}


// PseudoJet utilities
bool valid_status(int status,
                  bool allow_beam, bool allow_initial,
                  bool allow_hard, bool allow_fsr,
                  bool allow_remnants) {
    status = abs(status);
    if (allow_beam and 10 < status and status < 20)
        return true;
    else if (allow_initial and 40 < status and status < 50)
        return true;
    if (allow_hard and 20 < status and status < 30)
        return true;
    else if (allow_fsr and 50 < status and status < 60)
        return true;
    else if (allow_remnants and 60 < status and status < 70)
        return true;
    else {
        return false;
    }
}



// Function to apply homogeneous multiplicative rescaling of 4-momentum
PseudoJet rescale_momentum(const PseudoJet& particle,
                           const double scaling_factor) {
    PseudoJet pj(particle.px() * scaling_factor,
                 particle.py() * scaling_factor,
                 particle.pz() * scaling_factor,
                 particle.e() * scaling_factor);
    pj.set_user_index(particle.user_index());
    return pj;
}


// Function to create a new jet with only charged particles
PseudoJet create_charged_jet(const fastjet::PseudoJet& original_jet) {
    // Filter charged particles into new jet
    PseudoJet charged_jet;
    for (const auto& particle : original_jet.constituents()) {
        // user index stores charge information
        if (particle.user_index() != 0) {
            charged_jet = join(charged_jet, particle);
        }
    }

    // Mark this as a charged-only jet
    charged_jet.set_user_index(1);

    return charged_jet;
}

// ---------------------------------
// Jet-Pair utilities
// ---------------------------------

/**
* @brief: Returns the angle between a pair of pseudojets.
*
* @param: pj1, pj2  The given pseudojets.
*
* @return: double   Angle between the pseudojets (in radians).
*/
double pj_dtheta(const PseudoJet pj1, const PseudoJet pj2) {
    std::vector<double> p1 = {pj1.px(), pj1.py(), pj1.pz()};
    std::vector<double> p2 = {pj2.px(), pj2.py(), pj2.pz()};

    double th = theta(p1, p2);

    if(std::isnan(th)) {
        std::string p1_str = "<" + std::to_string(pj1.px()) + " " + std::to_string(pj1.py()) + " " + std::to_string(pj1.pz()) + ">";
        std::string p2_str = "<" + std::to_string(pj2.px()) + " " + std::to_string(pj2.py()) + " " + std::to_string(pj2.pz()) + ">";

        throw std::runtime_error("Found theta = nan, from"
                   "\n\tp_1 = " + p1_str
                 + "\n\tp_2 = "  + p2_str
                 + "\n\tcos(theta) = " + std::to_string(pj_cos(pj1, pj2))
             );
    }

    return th;
}

double pj_dphi(const PseudoJet pj1, const PseudoJet pj2) {
    // Getting difference mod 2pi of azimuthal angle
    double dphiabs = fabs(pj1.phi() - pj2.phi());
    double dphi = dphiabs > M_PI ? 2*M_PI - dphiabs : dphiabs;

    return dphi;
}



/**
* @brief: Returns the cosine of the angle between a pair of pseudojets.
*
* @param: pj1, pj2  The given pseudojets.
*
* @return: double   Cosine of the angle between the pseudojets.
*/
double pj_cos(const PseudoJet pj1, const PseudoJet pj2) {
    // Getting magnitudes of vectors
    double abs_p_1 = sqrt( pow(pj1.px(), 2) + pow(pj1.py(), 2) + pow(pj1.pz(), 2));
    double abs_p_2 = sqrt( pow(pj2.px(), 2) + pow(pj2.py(), 2) + pow(pj2.pz(), 2));

    // Finding dot product
    double cos = (
            pj1.px()*pj2.px() + pj1.py()*pj2.py() + pj1.pz()*pj2.pz()
        )/( abs_p_1 * abs_p_2 );

    // Checking for invalid result of the form |cos| > 1
    // (when comparing, |cos| - 1 > epsilon
    if(abs(cos) - 1.0 > EPSILON)
        throw std::runtime_error("Invalid value "
                                 + std::to_string(cos) +
                                 " found for cosine " +
                                 "of angle between subjets.");

    return cos;
}


// ---------------------------------
// Event utilities
// ---------------------------------
PseudoJets add_events(const PseudoJets event1, const PseudoJets event2) {
    PseudoJets full_event = event1;
    for (auto particle : event2)
        full_event.push_back(particle);

    return full_event;
}


/**
* @brief: Returns the sum of scalar pT in a vector of pseudojets.
*
* @param: pjs   A vector containing the pseudojets to consider.
*
* @return: double The total energy.
*/
double SumScalarPt(const PseudoJets pjs) {
    // Finding total jet energy
    double pT = 0;
    for (auto pj : pjs) pT += pj.perp();
    return pT;
}


/**
* @brief: Returns the total energy in a vector of pseudojets.
*
* @param: pjs   A vector containing the pseudojets to consider.
*
* @return: double The total energy.
*/
double SumEnergy(const PseudoJets pjs) {
    // Finding total jet energy
    double Q = 0;
    for (auto pj : pjs) Q += pj.E();
    return Q;
}


double get_min_rap(const PseudoJets pjs, const double least_accepted) {
    return std::min_element(pjs.begin(), pjs.end(),
        [least_accepted](PseudoJet pj1, PseudoJet pj2) {
            return pj1.rap() < pj2.rap() and pj1.rap() > least_accepted;
        })->rap();
}

double get_max_rap(const PseudoJets pjs, const double greatest_accepted) {
    return std::max_element(pjs.begin(), pjs.end(),
        [greatest_accepted](PseudoJet pj1, PseudoJet pj2) {
            return pj1.rap() < pj2.rap() and pj2.rap() < greatest_accepted;
        })->rap();
}


double get_min_phi(const PseudoJets pjs) {
    return std::min_element(pjs.begin(), pjs.end(),
        [](PseudoJet pj1, PseudoJet pj2) {
            return pj1.phi() < pj2.phi();
        })->phi();
}

double get_max_phi(const PseudoJets pjs) {
    return std::max_element(pjs.begin(), pjs.end(),
        [](PseudoJet pj1, PseudoJet pj2) {
            return pj1.phi() < pj2.phi();
        })->phi();
}


// =====================================
// Jet Definition utilities
// =====================================
std::map<std::string, std::string> alg_label =
{
    // Anti-kt accepted flags
    { "anti-kt", "akt" },
    { "antikt", "akt" },
    { "akt", "akt" },
    { "2", "akt" },
    // Cambridge-Aachen accepted flags
    { "cambridge-aachen", "ca" },
    { "ca", "ca" },
    { "1", "ca" },
    // kt accepted flags
    { "kt", "kt" },
    { "0", "kt" },
    // e+e- Anti-kt accepted flags
    { "ee_anti-kt", "ee_akt" },
    { "ee_antikt", "ee_akt" },
    { "ee_akt", "ee_akt" },
    { "ee_2", "ee_akt" },
    // e+e- Cambridge-Aachen accepted flags
    { "ee_cambridge-aachen", "ee_ca" },
    { "ee_ca", "ee_ca" },
    { "ee_1", "ee_ca" },
    // e+e- kt accepted flags
    { "ee_kt", "ee_kt" },
    { "ee_0", "ee_kt" },
};


JetDefinition process_JetDef(const std::string algorithm, const double radius,
                             const RecombinationScheme recomb) {
    // - - - - - - - - - - - - - - - - -
    // proton-proton algorithms
    // - - - - - - - - - - - - - - - - -
    if (str_eq(alg_label[algorithm], "akt"))
        return JetDefinition(antikt_algorithm, radius, recomb);
    else if (str_eq(alg_label[algorithm], "ca"))
        return JetDefinition(cambridge_algorithm, radius, recomb);
    else if (str_eq(alg_label[algorithm], "kt"))
        return JetDefinition(kt_algorithm, radius, recomb);

    // - - - - - - - - - - - - - - - - -
    // electron-positron algorithms
    // - - - - - - - - - - - - - - - - -
    else if (str_eq(alg_label[algorithm], "ee_akt"))
        return JetDefinition(ee_genkt_algorithm, radius, -1,
                             recomb);
    else if (str_eq(alg_label[algorithm], "ee_ca"))
        return JetDefinition(ee_genkt_algorithm, radius, 0,
                             recomb);
    else if (str_eq(alg_label[algorithm], "ee_kt"))
        return JetDefinition(ee_genkt_algorithm, radius, 1,
                             recomb);

    // Plugin Algorithms and typos:
    else
        throw Error("Invalid jet algorithm " + algorithm);
}


std::string jetAlgorithmType(std::string algorithm) {
    // - - - - - - - - - - - - - - - - -
    // proton-proton algorithms
    // - - - - - - - - - - - - - - - - -
    if (str_eq(alg_label[algorithm], "akt")
     or str_eq(alg_label[algorithm], "ca")
     or str_eq(alg_label[algorithm], "kt"))
        return "pp";

    // - - - - - - - - - - - - - - - - -
    // electron-positron algorithms
    // - - - - - - - - - - - - - - - - -
    if (str_eq(alg_label[algorithm], "ee_akt")
     or str_eq(alg_label[algorithm], "ee_ca")
     or str_eq(alg_label[algorithm], "ee_kt"))
        return "ee";

    else
        throw Error("Invalid jet algorithm " + algorithm);
}



// =====================================
// Visualization Utilities
// =====================================
void write_ptyphi_pj(const PseudoJet pj,
                     std::fstream& file,
                     std::string p_type) {
    file << p_type + " " << pj.pt() << " " << pj.rap()
        << " " << pj.phi();
    if (pj.user_index() != -1) file << " " << pj.user_index();
    file << "\n";
}


void write_ptyphis_event(const PseudoJets particles,
                         std::fstream& file) {
    for (auto part : particles) {
        // Writing particle information for each particle
        write_ptyphi_pj(part, file, (!is_ghost(part) ? "P" : "G"));
    }
}


bool accept_all_nonempty(const PseudoJet pj) {
    if (pj.has_constituents())
        return true;
    return false;
}


void write_ptyphis_jets(const PseudoJets particles,
                        const JetDefinition jet_def,
                        std::fstream& file,
                        bool (*write_jet)(PseudoJet)) {
    file << "\n# Storing particles and jet information associated with this event.\n";
    file << "\n# Using jet definition with description:\n# "
         << jet_def.description() << "\n";
    file << "radius = " << jet_def.R() << "\n\n";
    // Finding jets
    ClusterSequence sub_cluster_seq(particles, jet_def);
    PseudoJets jets = sorted_by_pt(sub_cluster_seq.inclusive_jets());

    for (size_t ijet=0; ijet < jets.size(); ijet++) {
        // Looping over jets, hardest first
        PseudoJet jet = jets.at(ijet);

        // If this jet does not pass a selection criterion
        // (Default selection: must have constituents)
        if (!write_jet(jet)) continue;

        jet.set_user_index(ijet+1);
        write_ptyphi_pj(jet, file, "J");
        for (auto part : jet.constituents()) {
            // Storing info about which jet includes this particle
            std::string p_type = (!is_ghost(part) ? "P" : "G");
            part.set_user_index(ijet+1);
            // Writing particle information for each particle
            write_ptyphi_pj(part, file, p_type);
        }
    }
}


// =====================================
// Command Line Basics
// =====================================
// ---------------------------------
// Command Line Defaults
// ---------------------------------
// Jet options
const std::string _JETALG_DEFAULT    = "antikt";
const double      _PTMIN_DEFAULT     = 0.;
const double      _PTMAX_DEFAULT     = pow(10.,9.);

// radius and recombination scheme:
const std::vector<double> _JETRAD_DEFAULT = {1.0};
const fastjet::RecombinationScheme _JET_RECOMB_DEFAULT = fastjet::E_scheme;

// Subjet options
const std::string _SUBALG_DEFAULT    = "cambridge-aachen";
// radius and recombination scheme:
const std::vector<double> _SUBRAD_DEFAULT = {0.1};
const fastjet::RecombinationScheme _SUB_RECOMB_DEFAULT = fastjet::WTA_modp_scheme;

// Accepted recombination schemes for jet finding
std::map<fastjet::RecombinationScheme, std::string> scheme_string = {
    { fastjet::WTA_pt_scheme, "WTA_pt" },
    { fastjet::WTA_modp_scheme, "WTA_modp" },
    { fastjet::E_scheme, "E_scheme" },
    { fastjet::pt_scheme, "pt_scheme" },
};


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

// ---------------------------------
// Jet Definition
// ---------------------------------
// - - - - - - - - - - - - - - - - -
// Jet and subjet algorithms
// - - - - - - - - - - - - - - - - -
std::string jetalgstr_cmdln(int argc, char* argv[],
                            std::string jetalg_default) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "-j") or
          str_eq(argv[iarg], "--jet_algorithm") or
          str_eq(argv[iarg], "--jet_alg")) {
            return argv[iarg+1];
        }
    }
    return jetalg_default;
}

std::string subalgstr_cmdln(int argc, char* argv[],
                            std::string subalg_default) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "-s") or
          str_eq(argv[iarg], "--subjet_algorithm") or
          str_eq(argv[iarg], "--sub_alg")) {
            return argv[iarg+1];
        }
    }
    return subalg_default;
}


// - - - - - - - - - - - - - - - - -
// Jet and subjet radii
// - - - - - - - - - - - - - - - - -
std::vector<double> jetrad_cmdln(int argc, char* argv[],
                         std::vector<double> jetrad_default) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "-R") or
          str_eq(argv[iarg], "--jet_radius") or
          str_eq(argv[iarg], "--jet_rad")) {
            std::vector<double> jetrads{};
            while(argv[iarg+1][0] != '-') {
                iarg++;
                // Allowing infinite jet radius (whole event)
                if(str_eq(argv[iarg+1], "inf") or
                 str_eq(argv[iarg+1], "infty") )
                    jetrads.push_back(1000);
            // Otherwise, we assume it is finite
            else
                jetrads.push_back(atof(argv[iarg]));
            }
            return jetrads;
        }
    }
    return jetrad_default;
}

std::vector<double> subrad_cmdln(int argc, char* argv[],
                         std::vector<double> subrad_default) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "-r") or
          str_eq(argv[iarg], "--subjet_radius") or
          str_eq(argv[iarg], "--sub_rad")) {
            std::vector<double> subrads{};
            while(argv[iarg+1][0] != '-') {
                iarg++;
                subrads.push_back(atof(argv[iarg]));
            }
        return subrads;
        }
    }
    return subrad_default;
}

// - - - - - - - - - - - - - - - - -
// Grouping sub/jet radii together
// - - - - - - - - - - - - - - - - -
radius_vector_pair_t radius_pairs_cmdln(int argc, char* argv[]) {
    // If we explicitly receive a command for radius pairs,
    // generate pairs using the given radii
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "--radius_pairs")) {
            std::vector<double> jetrads{};
            std::vector<double> subrads{};
            while (iarg+1 < argc and argv[iarg+1][0] != '-') {
                iarg++;
                double jetrad = atof(argv[iarg]);
                jetrads.push_back(jetrad);
                iarg++;
                double subrad = atof(argv[iarg]);
                subrads.push_back(subrad);
            }
        return std::make_pair(jetrads, subrads);
        }
    }

    // Otherwise, use the individually specified radii
    // (doing a 'cartesian product': if we are given
    //  jet radii R1 R2 R3
    //  and //  subjet radii r1 r2 r3
    //  we will return the pair of vectors
    //  < {R1, R1, R1, R2, R2, R2, R3, R3, R3},
    //    {r1, r2, r3, r1, r2, r3, r1, r2, r3} >
    radius_vector_pair_t radius_pairs;
    std::vector<double> jetrads = jetrad_cmdln(argc, argv);
    std::vector<double> subrads = subrad_cmdln(argc, argv);
    for (auto jetrad : jetrads) {
        for (auto subrad : subrads) {
            radius_pairs.first.push_back(jetrad);
            radius_pairs.second.push_back(subrad);
        }
    }
    return radius_pairs;
}

// - - - - - - - - - - - - - - - - -
// Jet and subjet recombination schemes
// - - - - - - - - - - - - - - - - -
// Command-line utilities
fastjet::RecombinationScheme jetrecomb_cmdln(int argc, char* argv[],
                         fastjet::RecombinationScheme recomb_default) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "--jet_recomb") or
                str_eq(argv[iarg], "--jet_scheme") or
                str_eq(argv[iarg], "--jet_recombination") or
                str_eq(argv[iarg], "--jet_recombination_scheme")) {
            // WTA p_T scheme
            if (str_eq(argv[iarg+1], "WTA_pt_scheme") or
                     str_eq(argv[iarg+1], "WTA_pt"))
                return fastjet::WTA_pt_scheme;
            // WTA |p| scheme
            if (str_eq(argv[iarg+1], "WTA_modp_scheme") or
                     str_eq(argv[iarg+1], "WTA_modp"))
                return fastjet::WTA_modp_scheme;
            // E scheme
            if (str_eq(argv[iarg+1], "E_scheme") or
                     str_eq(argv[iarg+1], "E"))
                return fastjet::E_scheme;
            // p_T scheme
            if (str_eq(argv[iarg+1], "pt_scheme") or
                     str_eq(argv[iarg+1], "pt"))
                return fastjet::pt_scheme;

            throw std::invalid_argument("Invalid jet recombination scheme.");
        }
    }
    return recomb_default;
}

fastjet::RecombinationScheme subrecomb_cmdln(int argc, char* argv[],
                         fastjet::RecombinationScheme recomb_default) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "--sub_recomb") or
                str_eq(argv[iarg], "--subjet_scheme") or
                str_eq(argv[iarg], "--subjet_recombination") or
                str_eq(argv[iarg], "--subjet_recombination_scheme")) {
            // WTA p_T scheme
            if (str_eq(argv[iarg+1], "WTA_pt_scheme") or
                     str_eq(argv[iarg+1], "WTA_pt"))
                return fastjet::WTA_pt_scheme;
            // WTA |p| scheme
            if (str_eq(argv[iarg+1], "WTA_modp_scheme") or
                     str_eq(argv[iarg+1], "WTA_modp"))
                return fastjet::WTA_modp_scheme;
            // E scheme
            if (str_eq(argv[iarg+1], "E_scheme") or
                     str_eq(argv[iarg+1], "E"))
                return fastjet::E_scheme;
            // p_T scheme
            if (str_eq(argv[iarg+1], "pt_scheme") or
                     str_eq(argv[iarg+1], "pt"))
                return fastjet::pt_scheme;

            throw std::invalid_argument("Invalid jet recombination scheme.");
        }
    }

    return recomb_default;
}


// =====================================
// Ghost Particle Utilities
// =====================================
// Ghost grid: Default boundaries
const double _ghost_maxrap = 5;         // maximum rapidity of the ghosts
const double _ghost_minrap = -5;        // minimum rapidity of the ghosts
const double _ghost_maxphi = twopi;     // maximum phi
const double _ghost_minphi = 0;         // minimum phi

// Ghost grid: Default misc. params
const double _ghost_area = 0.005;              // changes density of ghosts
const double _mean_ghost_pt = 1e-100;         // mean ghost pt
const Selector _no_selector = Selector();     // Selector which accepts all particles

// Parameters controlling randomness for the uniform ghosts
const double _grid_scatter = 1.0;             // grid scatter
const double _pt_scatter = 0.1;               // pt scatter

// Extra information for ghost identification
const int _ghost_index = -1000;               // User index for ghost particles
                                              //
bool is_ghost(const PseudoJet particle) {
    return (particle.user_index() == _ghost_index);
}

bool is_ghost_jet(const PseudoJet jet) {
    for (auto part : jet.constituents())
        if (!is_ghost(part)) return false;
    return true;
}

bool not_ghost_jet(const PseudoJet jet) { return !is_ghost_jet(jet); }


// ---------------------------------
// Ghost grid setup
// ---------------------------------
PseudoJets uniform_ghosts(const double mean_ghost_pt,
                          const double min_rap,
                          const double max_rap,
                          const double min_phi,
                          const double max_phi,
                          const double ghost_area,
                          const Selector selector,
                          const double grid_scatter,
                          const double pt_scatter) {
    // Initializing ghosts
    PseudoJets ghosts;

    // - - - - - - - - - - - - - - - - -
    // Setting up grid
    // - - - - - - - - - - - - - - - - -
    // Determining grid parameters
    double drap = sqrt(ghost_area);
    double dphi = drap;

    // Using nearest int for number of grid rows/cols
    double nrap = int((max_rap-min_rap) / (2*drap));
    int nphi = int((max_phi-min_phi) / (2*dphi));
    // Factor of 2 to go from -N to N in the iteration over ghosts;
    // legacy from fastjet code.

    // Re-evaluating grid spacing and parameters
    drap = (max_rap-min_rap) / (2*nrap);
    dphi = (max_phi-min_phi) / (2*nphi);

    // - - - - - - - - - - - - - - - - -
    // Adding to the list of ghosts
    // - - - - - - - - - - - - - - - - -
    // Iterating over grid
    for (int irap = -nrap; irap <= nrap-1; irap++) {
        for (int iphi = -nphi; iphi < nphi; iphi++) {
            // Grid points and pT, plus random offsets
            double phi = (iphi+0.5) * dphi + dphi*(rand()%1 - 0.5)*grid_scatter
                                                          + (max_phi+min_phi)/2.;
            double rap = (irap+0.5) * drap + drap*(rand()%1 - 0.5)*grid_scatter
                                                          + (max_rap+min_rap)/2.;
            double pt = mean_ghost_pt*(1 + (rand()%1 - 0.5)*pt_scatter);

            // Initializing ghost particle
            double exprap = exp(+rap);
            double pminus = pt/exprap;
            double pplus  = pt*exprap;
            double px = pt*cos(phi);
            double py = pt*sin(phi);
            PseudoJet ghost(px,py,0.5*(pplus-pminus),0.5*(pplus+pminus));
            ghost.set_cached_rap_phi(rap,phi);
            ghost.set_user_index(_ghost_index);

            // If our particle does not pass the condition placed by an active selector
            if (selector.worker().get() && !selector.pass(ghost)) continue;

            // Add the particle at this grid point to our list of ghost particles
            ghosts.push_back(ghost);
        }
    }

    return ghosts;
}


// ---------------------------------
// Add a grid of ghosts to existing event
// ---------------------------------
PseudoJets add_uniform_ghosts(PseudoJets& particles,
        const double mean_ghost_pt,
        const double min_rap,
        const double max_rap,
        const double min_phi,
        const double max_phi,
        const double ghost_area,
        const Selector selector,
        const double grid_scatter,
        const double pt_scatter) {
    // - - - - - - - - - - - - - - - - -
    // Setting up grid
    // - - - - - - - - - - - - - - - - -
    // Determining grid parameters
    double drap = sqrt(ghost_area);
    double dphi = drap;

    // Using nearest int for number of grid rows/cols
    double nrap = int((max_rap-min_rap) / (2*drap));
    int nphi = int((max_phi-min_phi) / (2*dphi));
    // Factor of 2 to go from -N to N in the iteration over ghosts;
    // legacy from fastjet code.

    // Re-evaluating grid spacing and parameters
    drap = (max_rap-min_rap) / (2*nrap);
    dphi = (max_phi-min_phi) / (2*nphi);

    // - - - - - - - - - - - - - - - - -
    // Adding to the list of ghosts
    // - - - - - - - - - - - - - - - - -
    // Iterating over grid
    for (int irap = -nrap; irap <= nrap-1; irap++) {
        for (int iphi = -nphi; iphi < nphi; iphi++) {
            // Grid points and pT, plus random offsets
            double phi = (iphi+0.5) * dphi + dphi*(rand()%1 - 0.5)*grid_scatter
                                                          + (max_phi+min_phi)/2.;
            double rap = (irap+0.5) * drap + drap*(rand()%1 - 0.5)*grid_scatter
                                                          + (max_rap+min_rap)/2.;
            double pt = mean_ghost_pt*(1 + (rand()%1 - 0.5)*pt_scatter);

            // Initializing ghost particle
            double exprap = exp(+rap);
            double pminus = pt/exprap;
            double pplus  = pt*exprap;
            double px = pt*cos(phi);
            double py = pt*sin(phi);
            PseudoJet ghost(px,py,0.5*(pplus-pminus),0.5*(pplus+pminus));
            ghost.set_cached_rap_phi(rap,phi);
            ghost.set_user_index(_ghost_index);

            // If our particle does not pass the condition placed by an active selector
            if (selector.worker().get() && !selector.pass(ghost)) continue;

            // Add the particle at this grid point to our list of ghost particles
            particles.push_back(ghost);
        }
    }

    return particles;
}


// ---------------------------------
// Visualization with ghosts
// ---------------------------------

void write_ptyphis_jets_with_ghosts(const PseudoJets particles,
                                    const JetDefinition jet_def,
                                    std::fstream& file,
                                    std::string ghost_type,
                                    bool write_ghost_jets) {
    // Ensuring that the ghost type is known
    if (!str_eq(ghost_type, "passive") and !str_eq(ghost_type, "active"))
        throw Error("Invalid ghost_type " + ghost_type + "for function "
                + "```write_ptyphis_jets_with_ghosts```");

    // - - - - - - - - - - - - - - - - -
    // Setting up ghost grid
    // - - - - - - - - - - - - - - - - -
    // Getting parameters associated with given particles
    double max_rap = get_max_rap(particles);
    double min_rap = get_min_rap(particles);
    double max_phi = get_max_phi(particles);
    double min_phi = get_min_phi(particles);

    double grid_area = (max_rap - min_rap) * (max_phi - min_phi);
    // Use same number of ghosts as for default full grid
    double ghost_area = .005 / (10 * twopi) * grid_area;

    // Initializing ghosts
    PseudoJets ghosts = uniform_ghosts(_mean_ghost_pt,
            min_rap-jet_def.R(),
            max_rap+jet_def.R(),
            // Extending limits by jet radius;
            std::max(min_phi-jet_def.R(), double(0.0)),
            std::min(max_phi + jet_def.R(), twopi),
            // also, respecting limits on phi.
            ghost_area);

    // - - - - - - - - - - - - - - - - -
    // Active Ghosts
    // - - - - - - - - - - - - - - - - -
    if (str_eq(ghost_type, "active")) {
        PseudoJets active_ghost_event = add_events(particles, ghosts);
        write_ptyphis_jets(active_ghost_event, jet_def, file,
                write_ghost_jets ? &accept_all_nonempty : &not_ghost_jet);
        return;
    }

    // - - - - - - - - - - - - - - - - -
    // Passive Ghosts
    // - - - - - - - - - - - - - - - - -
    if (str_eq(ghost_type, "passive")) {
        // Start by writing full event
        write_ptyphis_jets(particles, jet_def, file);

        // Write ghosts one by one to event
        for (auto ghost : ghosts) {
            // Adding single ghost to event (defn of "passive ghosts")
            PseudoJets passive_ghost_event = particles;
            passive_ghost_event.push_back(ghost);

            // Finding jets in passive ghost event
            ClusterSequence sub_cluster_seq(passive_ghost_event, jet_def);
            PseudoJets jets = sorted_by_pt(sub_cluster_seq.inclusive_jets());

            // Looping over jets, hardest first
            size_t ijet = 0;
            bool found_ghost = false;
            while (ijet < jets.size() and !found_ghost) {
                PseudoJet jet = jets.at(ijet);

                // If we only look at non-ghost jets
                if (is_ghost_jet(jet) and !write_ghost_jets) {ijet++; continue;}

                // Finding where the ghost was clustered manually
                // (std::find doesn't play well with fastjet classes)
                for (auto part : jet.constituents()) {
                    if (!is_ghost(part)) continue;
                    // Writing to file
                    ghost.set_user_index(ijet+1);
                    write_ptyphi_pj(ghost, file, "G");
                    break;
                }

                ijet++;
            }
        }
        return;
    }
}
