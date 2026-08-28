/**
 * @file    opendata_utils.cc
 *
 * @brief   A utility file for reading/processing open data.
 *
 * @author: Samuel Alipour-fard
 */
#include <sstream>
#include <iomanip>

#include "fastjet/PseudoJet.hh"

// Local imports
#include "../../include/opendata_utils.h"


// =====================================
// Switches, flags, and options
// =====================================
// Cut on jets from the CMS Jet 2011A Dataset
const float CMS_ETA_CUT       = 1.9;
const float CMS_R_JET         = 0.5;
const std::string CMS_JET_ALG = "akt";
const float CMS_PT_MIN        = 500;
const float CMS_PT_MAX        = 550;

namespace od
{
    // =====================================
    // File Reading Utilities
    // =====================================
    /**
    * @brief: Takes in a text file containing processed data.
    *         Reads events into a given vector of PseudoJets when
    *         read_jet is called.
    *
    * @param: inputfile   The text file containing CMS Open Data
    */
    EventReader::EventReader(const std::string& inputfile)
                : current_event(-1) {
        source.open(inputfile);
        if (!source.good()) {
            throw std::runtime_error("od::EventReader: Error: "
                                     "Input file not found.");
        }
    }

    /**
    * @brief: Destructor for EventReader
    */
    EventReader::~EventReader() {
        if (source.is_open()) {
            source.close();
        }
    }

    /**
    * @brief: Read a line and return the linestream
    */
    const std::istringstream EventReader::read_line(
                                        const std::string line) {
        // If the string is not a particle, returning "empty"
        if (line.substr(0, 1) == "#") {
            std::istringstream linestream("-1 0 0 0");
            return linestream;
        }

        // Preparing to read line
        std::istringstream linestream(line);
        return linestream;
    }


    /**
    * @brief: Append a particle to a jet
    */
    void EventReader::append_to_jet(fastjet::PseudoJet& jet,
             const double pt, const double eta, const double phi) {
        // Not adding empty particles to jet
        if (pt == 0)
            return;

        // Preparing kinematic variables
        const double px = pt * cos(phi);
        const double py = pt * sin(phi);
        const double pz = pt * sinh(eta);
        const double E = sqrt(px * px + py * py + pz * pz);

        // Adding particle to jet
        jet = join(jet, fastjet::PseudoJet(px, py, pz, E));
    }


    /**
    * @brief: Read a jet within the source file into a PseudoJet
    */
    bool EventReader::read_jet(
            fastjet::PseudoJet& jet) {
        if (prev_line.length() != 0) {
            // Reading line
            std::istringstream linestream = read_line(prev_line);

            // Storing particle data
            int event_number;
            double pt, eta, phi;
            linestream >> event_number >> pt >> eta >> phi;

            // Throwing appropriate errors if incorrect format
            if (linestream.fail()) {
                throw std::runtime_error("od::EventReader: Error:"
                   " Incorrect input format in line: " + prev_line);
            }

            // Adding particle to jet
            append_to_jet(jet, pt, eta, phi);
        }

        std::string line;
        while (std::getline(source, line)) {
            // Reading line
            std::istringstream linestream = read_line(line);

            // Storing particle data
            int event_number;
            double pt, eta, phi;
            linestream >> event_number >> pt >> eta >> phi;

            // Throwing appropriate errors if incorrect format
            if (linestream.fail()) {
                throw std::runtime_error("od::EventReader: Error:"
                   " Incorrect input format in line: " + line);
            }

            // Setting up for first event
            if (current_event == -1) {
                current_event = event_number;
            }
            // Preparing to end reading if footer found
            if (line.substr(0, 4) == "#END") {
                return false;
            }

            // Checking if this particle belongs in a new event
            if (event_number > current_event) {
                // We've reached a new event; update current_event
                current_event = event_number;

                // Storing current particle (it's in the next jet)
                prev_line = line;

                // Return the jet we've built so far
                return true;
            }

            // Storing particle information in the current jet
            append_to_jet(jet, pt, eta, phi);

        }
        return false;
    }


    // =====================================
    // File Writing Utilities
    // =====================================
    /**
    * @brief: Takes in a target text file for storing data.
    *         Writes a vector of pseudojets (an event and/or jet)
    *         when write_jet is called.
    *
    * @param: inputfile   The text file containing CMS Open Data
    */
    EventWriter::EventWriter(const std::string& targetfile)
                : current_event(-1) {
        target.open(targetfile);
        if (!target.good()) {
            throw std::runtime_error("od::EventWriter: Error: "
                                     "Input file not found.");
        }
    }

    /**
     * @brief: Destructor for EventWriter
     */
    EventWriter::~EventWriter() {
        if (target.is_open()) {
            target.close();
        }
    }


    /**
     * @brief: Writes a jet to the output file
     *
     * @param: event_number   The event number
     * @param: jet            The jet to write
     */
    void EventWriter::write_jet(const fastjet::PseudoJet& jet) {
        // Decompose the jet into constituent particles if necessary
        std::vector<fastjet::PseudoJet> particles = jet.constituents();

        // Update the current event number
        current_event += 1;

        // Loop over particles and write them
        for (const auto& particle : particles) {
            double pt  = particle.perp();
            double eta = particle.eta();
            double phi = particle.phi();

            if (pt == 0)
                continue;

            // Write to the file
            target << std::setprecision(12) << std::noshowpoint
                   << current_event << " "
                   << pt << " "
                   << eta << " "
                   << phi << "\n";
        }
    }
}
