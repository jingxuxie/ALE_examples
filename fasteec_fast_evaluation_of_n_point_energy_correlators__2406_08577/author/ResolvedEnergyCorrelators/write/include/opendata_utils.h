#ifndef READ_EVENT_H
#define READ_EVENT_H

#include <vector>
#include <fstream>
#include <sstream>
#include <cmath>

#include "fastjet/PseudoJet.hh"

// =====================================
// Switches, flags, and options
// =====================================
// Cut on jets from the CMS Jet 2011A Dataset
extern const float CMS_ETA_CUT;
extern const float CMS_R_JET;
extern const std::string CMS_JET_ALG;
extern const float CMS_PT_MIN;
extern const float CMS_PT_MAX;


namespace od
{
    // Opendata Files
    const std::string cms_jets_file = "/home/samaf/Documents/Research/ResolvedEnergyCorrelators/write/data/cms_jet_run2011A.opendata.txt";

    // Class for reading files
    class EventReader {
    private:
        // Properties
        std::ifstream source;
        std::string prev_line;
        int current_event;
        // Methods
        const std::istringstream read_line(const std::string line);
        void append_to_jet(fastjet::PseudoJet& jet,
             const double pt, const double eta, const double phi);

    public:
        EventReader(const std::string& inputfile);
        ~EventReader();

        bool read_jet(fastjet::PseudoJet& jet);
    };

    // Class for writing files
    class EventWriter {
    private:
        std::ofstream target;
        int current_event;

    public:
        EventWriter(const std::string& targetfile);
        ~EventWriter();

        void write_jet(const fastjet::PseudoJet& jet);
    };
}
#endif
