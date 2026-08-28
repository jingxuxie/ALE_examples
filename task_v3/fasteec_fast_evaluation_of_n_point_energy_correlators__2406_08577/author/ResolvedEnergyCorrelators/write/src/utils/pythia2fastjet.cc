
#include <random>


#include "Pythia8/Pythia.h"
#include "fastjet/PseudoJet.hh"

#include "../../include/pythia2fastjet.h"

using namespace fastjet;


PseudoJet pythia_particle_to_pseudojet(const Pythia8::Particle& p) {
    PseudoJet pj(p.px(), p.py(), p.pz(), p.e());

    // Saving charge information for track-based substructure
    pj.set_user_index(p.charge());

    return pj;
}


// Setting up random number generation for smearing
std::default_random_engine generator;

/**
* @brief: Takes in a Pythia Event and return a vector of PseudoJets
*         containing all particles of a current event.
*
* @param: event     Pythia Event type, as in pythia.event().
*                   The event under consideration.
*
* @return: vector<PseudoJet>    A vector containing all particles in the event.
*/
PseudoJets get_particles_pythia(const Pythia8::Event event,
                        const double photon_smear_factor,
                        const double charged_smear_factor,
                        const double neutral_smear_factor,
                        const bool charged_only,
                        const bool final_only,
                        const std::vector<int> use_pids,
                        const std::vector<int> exclude_pids,
                        const std::vector<int> use_status_codes,
                        const std::vector<int> exclude_status_codes
                        ) {
    // Storing particles of an event as PseudoJets
    PseudoJets particles;

    // Gaussian random numbers for energy uncertainties
    // https://arxiv.org/pdf/2402.13864#page=5&view=fitH&zoom=100,0,500
    // only used if smear_momentum is true
    std::normal_distribution<double> photon_smearer(1.0,
                                        photon_smear_factor);
    std::normal_distribution<double> charged_smearer(1.0,
                                        charged_smear_factor);
    std::normal_distribution<double> neutral_smearer(1.0,
                                        neutral_smear_factor);

    // Extracting particles to PseudoJets
    for (int ipart = 0; ipart < event.size(); ipart++) {
        // If only using final states, skip intermediates
        if (final_only and not event[ipart].isFinal())
            continue;

        // If only using charged particles, skip neutrals
        // NOTE: this can lead to selection bias -- use mindfully
        if (charged_only and event[ipart].charge() == 0)
            continue;


        // Finding relevant final states and converting to pseudojets
        bool include_particle = (
            // Use only given PIDs if relevant
            (use_pids.size() == 0 or
             std::find(use_pids.begin(), use_pids.end(),
                 event[ipart].id()) != use_pids.end())
                and
            // Exclude given PIDs if relevant
            (exclude_pids.size() == 0 or
             std::find(exclude_pids.begin(), exclude_pids.end(),
                 event[ipart].id()) == exclude_pids.end())
                and
            // Use only given status codes if relevant
            (use_status_codes.size() == 0 or
             std::find(use_status_codes.begin(),
                 use_status_codes.end(),
                 event[ipart].id()) != use_status_codes.end())
                and
            // Exclude given status codes if relevant
            (exclude_status_codes.size() == 0 or
             std::find(exclude_status_codes.begin(),
                 exclude_status_codes.end(),
                 event[ipart].id()) == exclude_status_codes.end())
            );

        if (not include_particle)
            continue;

        // Converting the particle to a PseudoJet
        PseudoJet particle = pythia_particle_to_pseudojet(event[ipart]);

        // Smearing momentum if desired
        if (photon_smear_factor > 0 || charged_smear_factor > 0 ||
                neutral_smear_factor > 0) {
            double scaling_factor = 1.0;

            if (event[ipart].id() == 22) {
                if (photon_smear_factor > 0)
                    scaling_factor = photon_smearer(generator);
            }
            else if (event[ipart].charge() != 0) {
                if (charged_smear_factor > 0)
                    scaling_factor = charged_smearer(generator);
            }
            else {
                if (neutral_smear_factor > 0)
                    scaling_factor = neutral_smearer(generator);
            }

            particle = rescale_momentum(particle,
                                        scaling_factor);
            }

            // Storing the (potentially smeared) particle
            particles.push_back(particle);
    }

    return particles;
}


