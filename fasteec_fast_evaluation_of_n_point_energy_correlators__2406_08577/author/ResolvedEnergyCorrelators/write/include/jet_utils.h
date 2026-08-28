/**
 * @file    jet_utils.h
 *
 * @brief   A utility header file for jets.
 */
#ifndef JET_UTILS
#define JET_UTILS

// ---------------------------------
// Basic imports
// ---------------------------------
#include <iostream>
#include <ostream>
#include <vector>
#include <limits>
#include <locale>
#include <fstream>
#include <sstream>
#include <string>
#include <string.h>
#include <algorithm>
#include <random>

#include <utility>
#include <stdexcept>

#include <assert.h>

#include <sys/types.h>
#include <sys/stat.h>

#include <stdlib.h>

#define _USE_MATH_DEFINES
#include <cmath>

// ---------------------------------
// HEP imports
// ---------------------------------
#include "fastjet/PseudoJet.hh"
#include "fastjet/ClusterSequence.hh"

#include "general_utils.h"

using namespace fastjet;


// =====================================
// typedefs
// =====================================

// Type definitions for fastjet and pythia
typedef std::vector<PseudoJet> PseudoJets;

// Type definitions to keep track of jet radius pairs
typedef std::pair<std::vector<double>, std::vector<double>> radius_vector_pair_t;



// =====================================
// Pseudojet utilities
// =====================================

// ---------------------------------
// Particle utilities
// ---------------------------------
extern const std::vector<int> qcd_pids;
extern const std::vector<int> lepton_pids;
extern const std::vector<int> nu_pids;
extern const std::vector<int> lepton_and_nu_pids;

bool is_qcd_pid(int pid);
bool is_leptonic_pid(int pid);

bool valid_status(int status,
                  bool allow_beam, bool allow_initial,
                  bool allow_hard, bool allow_fsr,
                  bool allow_remnants);

PseudoJet rescale_momentum(const PseudoJet& particle,
                           const double scaling_factor);

PseudoJet create_charged_jet(const PseudoJet& original_jet);

// ---------------------------------
// Jet-Pair utilities
// ---------------------------------
double pj_dtheta(const PseudoJet pj1, const PseudoJet pj2);
double pj_dphi(const PseudoJet pj1, const PseudoJet pj2);
double pj_cos(const PseudoJet pj1, const PseudoJet pj2);


// ---------------------------------
// Event utilities
// ---------------------------------
const double CMS_PHOTON_SMEAR_FACTOR = 0.03;
const double CMS_CHARGED_SMEAR_FACTOR = 0.01;
const double CMS_NEUTRAL_SMEAR_FACTOR = 0.05;

PseudoJets add_events(const PseudoJets event1, const PseudoJets event2);

double SumScalarPt(const PseudoJets pjs);

double SumEnergy(const PseudoJets pjs);

double get_min_rap(const PseudoJets pjs,
                   const double least_accepted = -10);
double get_max_rap(const PseudoJets pjs,
                   const double greatest_accepted = 10);

double get_min_phi(const PseudoJets pjs);
double get_max_phi(const PseudoJets pjs);


// =====================================
// Jet Definition utilities
// =====================================
extern std::map<std::string, std::string> alg_label;

JetDefinition process_JetDef(std::string algorithm, double radius,
                             RecombinationScheme recomb);

std::string jetAlgorithmType(std::string algorithm);


// =====================================
// Visualization Utilities
// =====================================
void write_ptyphi_pj(const PseudoJet pj,
                     std::fstream& file,
                     std::string p_type = "P");

extern bool accept_all_nonempty(const PseudoJet pj);

void write_ptyphis_jets(const PseudoJets particles, const JetDefinition jet_def,
                        std::fstream& file,
                        bool (*write_jet)(PseudoJet) = &accept_all_nonempty);

// =====================================
// Command Line Utilities
// =====================================
extern const double                        _PTMIN_DEFAULT;
extern const double                        _PTMAX_DEFAULT;

extern const std::string                   _JETALG_DEFAULT;
extern const std::vector<double>           _JETRAD_DEFAULT;
extern const fastjet::RecombinationScheme  _JET_RECOMB_DEFAULT;

extern const std::string                   _SUBALG_DEFAULT;
extern const std::vector<double>           _SUBRAD_DEFAULT;
extern const fastjet::RecombinationScheme  _SUB_RECOMB_DEFAULT;

// Accepted recombination schemes for jet finding
extern std::map<fastjet::RecombinationScheme, std::string> scheme_string;

// Non-Standard Options
std::string jetalgstr_cmdln(int argc, char* argv[],
         std::string jetalg_default=_JETALG_DEFAULT);
std::string subalgstr_cmdln(int argc, char* argv[],
         std::string jetalg_default=_SUBALG_DEFAULT);

std::vector<double> jetrad_cmdln(int argc, char* argv[],
         std::vector<double> subrad_default=_JETRAD_DEFAULT);
std::vector<double> subrad_cmdln(int argc, char* argv[],
         std::vector<double> subrad_default=_SUBRAD_DEFAULT);
radius_vector_pair_t radius_pairs_cmdln(int argc, char* argv[]);

fastjet::RecombinationScheme jetrecomb_cmdln(int argc, char* argv[],
         fastjet::RecombinationScheme recomb_default=_JET_RECOMB_DEFAULT);
fastjet::RecombinationScheme subrecomb_cmdln(int argc, char* argv[],
         fastjet::RecombinationScheme recomb_default=_SUB_RECOMB_DEFAULT);


// =====================================
// Ghost Particle Utilities
// =====================================
// Ghost grid: Default boundaries
extern const double _ghost_maxrap;
extern const double _ghost_minrap;
extern const double _ghost_maxphi;
extern const double _ghost_minphi;
// Ghost grid: Default misc. params
extern const double _ghost_area;
extern const double _mean_ghost_pt;
extern const Selector _no_selector;

// Parameters controlling randomness for the uniform ghosts
extern const double _grid_scatter;
extern const double _pt_scatter;

// Extra information for ghost identification
extern const int _ghost_index;
bool is_ghost(const PseudoJet particle);
bool is_ghost_jet(const PseudoJet jet);
bool not_ghost_jet(const PseudoJet jet);


// ---------------------------------
// Ghost grid setup
// ---------------------------------
PseudoJets uniform_ghosts(
        const double mean_ghost_pt = _mean_ghost_pt,
        const double min_rap = -_ghost_maxrap,
        const double max_rap = _ghost_maxrap,
        const double min_phi = _ghost_minphi,
        const double max_phi = _ghost_maxphi,
        const double ghost_area = _ghost_area,
        const Selector selector = _no_selector,
        const double grid_scatter = _grid_scatter,
        const double pt_scatter = _pt_scatter);


// ---------------------------------
// Ghost grid setup
// ---------------------------------
PseudoJets add_uniform_ghosts(PseudoJets& particles,
        const double mean_ghost_pt = _mean_ghost_pt,
        const double min_rap = -_ghost_maxrap,
        const double max_rap = _ghost_maxrap,
        const double min_phi = _ghost_minphi,
        const double max_phi = _ghost_maxphi,
        const double ghost_area = _ghost_area,
        const Selector selector = _no_selector,
        const double grid_scatter = _grid_scatter,
        const double pt_scatter = _pt_scatter);


// ---------------------------------
// Visualization with ghosts
// ---------------------------------

void write_ptyphis_jets_with_ghosts(
        const PseudoJets particles,
        const JetDefinition jet_def,
        std::fstream& file,
        const std::string ghost_type = "active",
        bool write_ghost_jets = false);

#endif
