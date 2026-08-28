/**
 * @file    pythia2fastjet.h
 *
 * @brief   A utility header file for converting pythia output into psuedojets
 * */
#ifndef PYTHIA2FASTJET_H
#define PYTHIA2FASTJET_H

#include "Pythia8/Pythia.h"

#include "jet_utils.h"

using namespace fastjet;


PseudoJet pythia_particle_to_pseudojet(const Pythia8::Particle& p);

std::vector<PseudoJet> get_particles_pythia(
        const Pythia8::Event event,
        const double photon_smear_factor = 0,
        const double charged_smear_factor = 0,
        const double neutral_smear_factor = 0,
        const bool charged_only = false,
        const bool final_only = true,
        const std::vector<int> use_pids = {},
        const std::vector<int> exclude_pids = nu_pids,
        const std::vector<int> use_status_codes = {},
        const std::vector<int> exclude_status_codes = {}
        );

#endif
