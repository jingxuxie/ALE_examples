#include <iostream>
#include "fastjet/PseudoJet.hh"

// Local imports
#include "../include/opendata_utils.h"

int main() {
    const std::string input_file = od::cms_jets_file;
    const std::string output_file = "cms_jet_COPY.opendata.txt";

    try {
        // Create an EventReader to read the input file
        od::EventReader reader(input_file);
        // and a jet to store event info
        fastjet::PseudoJet jet(0.0, 0.0, 0.0, 0.0);

        // Create an EventWriter to write to the output file
        od::EventWriter writer(output_file);

        // Read jets from input file and write them to output
        while (reader.read_jet(jet)) {
            // Write the jet to the output file
            writer.write_jet(jet);

            // Reset the jet for the next event
            jet.reset(0.0, 0.0, 0.0, 0.0);
        }

        std::cout << "Finished reading and writing events.\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << "\n";
        return 1;
    }

    return 0;
}
