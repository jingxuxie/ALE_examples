#ifndef PENC_H
#define PENC_H

#include <vector>
#include <string>
#include <map>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <stdexcept>
#include <memory>
#include <algorithm>
#include <limits>

#include "fastjet/PseudoJet.hh"

#include "histogram.h"


// Projected Energy-Energy Correlator class
class PENC : public Histogram {
public:
    PENC(const std::vector<double>& weights,
         double minbin, double maxbin, int nbins,
         bool contact_terms = true,
         bool use_deltaR = true, bool use_pt = true,
         bool uflow = true, bool oflow = true,
         int verbose = 1,
         const std::string& file_prefix = "",
         const bool use_output_folder = true);

    ~PENC() = default;

    // Process a jet and update histograms
    void processJet(const fastjet::PseudoJet& jet);

    // Normalize histograms and write to files
    void writeOutput();

    // Reset histograms and counters
    void reset();


    // Output histogram information
    std::vector<std::string> enc_outfiles;

    // Get the total number of jets processed
    int getTotalJets() const { return njets_tot_; }

    // Get runtime statistics for diagnostics
    const std::map<int, std::vector<double>>& getRuntimes() const { return jet_runtimes_; }

private:
    // PENC specific parameters
    std::vector<double> weights_;
    bool contact_terms_;
    bool use_deltaR_;
    bool use_pt_;
    std::string file_prefix_;
    int verbose_;
    bool use_output_folder_;

    // Histogram data
    std::vector<std::vector<double>> enc_hists_;

    // Statistics
    int njets_tot_;
    std::map<int, std::vector<double>> jet_runtimes_;

    // Initialize histogram data structures
    void initializeHistograms();

    // Compute histogram normalization factors
    void normalizeHistograms();

    // Write histogram data to files
    void writeHistogram(size_t inu);

    // Write runtime statistics
    void writeRuntimes(std::fstream& outfile);

    // Internal computation of PENC for a single jet
    void computePENC(const fastjet::PseudoJet& jet);
};



// Implementation of the PENC class
PENC::PENC(const std::vector<double>& weights,
           double minbin, double maxbin, int nbins,
           bool contact_terms, bool use_deltaR,
           bool use_pt, bool uflow, bool oflow,
           int verbose,
           const std::string& file_prefix,
           const bool use_output_folder)
    : Histogram(minbin, maxbin, nbins,
                uflow, oflow, "log"),
      weights_(weights), contact_terms_(contact_terms),
      use_deltaR_(use_deltaR), use_pt_(use_pt),
      file_prefix_(file_prefix),
      verbose_(verbose),
      use_output_folder_(use_output_folder),
      njets_tot_(0)
{
    initializeHistograms();
}


void PENC::initializeHistograms() {
    // Initialize histograms, one for each nu weight
    enc_hists_.clear();
    enc_outfiles.clear();

    for (auto nu : weights_) {
        // Create histogram with zeros
        enc_hists_.emplace_back(std::vector<double>(nbins_, 0.0));

        // Create output filename
        std::string filename;
        if (use_output_folder_)
            filename += "output/new_encs/2particle_";

        filename += file_prefix_ + "_nu" + std::to_string(nu);

        // Replace periods with hyphens
        std::replace(filename.begin(), filename.end(), '.', '-');

        // Add file extension
        filename += ".py";

        // Store filename for later
        enc_outfiles.push_back(filename);
    }
}


void PENC::reset() {
    // Reset PENC specific data
    njets_tot_ = 0;
    jet_runtimes_.clear();

    // Reset all histograms
    for (auto& hist : enc_hists_) {
        std::fill(hist.begin(), hist.end(), 0.0);
    }
}


void PENC::processJet(const fastjet::PseudoJet& jet) {
    try {
        // Start timing if we're only tracking one weight (for efficiency)
        auto jet_start = std::chrono::high_resolution_clock::now();

        // Increment jet counter
        ++njets_tot_;

        // Compute PENC for this jet
        computePENC(jet);

        // Record timing statistics if appropriate
        if (weights_.size() == 1) {
            auto jet_end = std::chrono::high_resolution_clock::now();
            auto jet_duration = std::chrono::duration_cast<std::chrono::microseconds>(jet_end - jet_start);

            // Store runtime for jets with this number of constituents
            jet_runtimes_[jet.constituents().size()].push_back(
                static_cast<double>(jet_duration.count()));
        }
    }
    catch (const fastjet::Error& ex) {
        std::cerr << "Warning: FastJet: " << ex.message() << std::endl;
    }
}

void PENC::computePENC(const fastjet::PseudoJet& jet) {
    // Get jet constituents
    const std::vector<fastjet::PseudoJet>& constituents = jet.constituents();

    // Calculate total weight of jet (energy or pt)
    double weight_tot = 0;
    for (const auto& particle : constituents) {
        weight_tot += use_pt_ ? particle.pt() : particle.e();
    }

    // Vector to store angle/weight pairs for sorting
    std::vector<std::pair<double, double>> sorted_angsweights;
    sorted_angsweights.reserve(constituents.size());

    // Loop over "special" particles
    for (const auto& part_sp : constituents) {
        // Energy-weighting factor for "special" particle
        double weight_sp = use_pt_ ?
                part_sp.pt() / weight_tot :
                part_sp.e() / weight_tot;

        // Initialize sum of weights within an angle of special particle
        double sum_weight1 = weight_sp;

        // Handle contact term
        if (contact_terms_) {
            // Add contribution for each nu weight
            for (size_t inu = 0; inu < weights_.size(); ++inu) {
                enc_hists_[inu][0] += std::pow(sum_weight1, 1 + weights_[inu]);
            }
        }

        // Clear and prepare for sorting angles/weights
        sorted_angsweights.clear();

        // Calculate angles and weights for all particles
        for (const auto& part1 : constituents) {
            // Energy-weighting factor for particle 1
            double weight1 = use_pt_ ?
                    part1.pt() / weight_tot :
                    part1.e() / weight_tot;

            // Angle relative to "special" particle
            double theta1 = use_deltaR_ ?
                    part_sp.delta_R(part1) :
                    fastjet::theta(part_sp, part1);

            sorted_angsweights.emplace_back(theta1, weight1);
        }

        // Sort by angle (theta1)
        std::sort(sorted_angsweights.begin(), sorted_angsweights.end());

        // Loop over sorted particles and calculate PENC
        for (size_t jpart = 1; jpart < sorted_angsweights.size(); ++jpart) {
            double theta1 = sorted_angsweights[jpart].first;
            double weight1 = sorted_angsweights[jpart].second;

            // Find histogram bin for this angle
            int bin = binPosition(theta1);

            // Skip if bin is invalid
            if (bin < 0) continue;

            // Calculate contributions to histograms for each nu weight
            for (size_t inu = 0; inu < weights_.size(); ++inu) {
                double hist_weight = weight_sp * (
                    std::pow(sum_weight1 + weight1, weights_[inu]) -
                    std::pow(sum_weight1, weights_[inu])
                );

                // Add to appropriate histogram bin
                enc_hists_[inu][bin] += hist_weight;
            }

            // Update sum for next iteration
            sum_weight1 += weight1;
        }
    }
}

void PENC::normalizeHistograms() {
    for (size_t inu = 0; inu < weights_.size(); ++inu) {
        double total_sum = 0.0;

        // Normalize by dividing by total number of jets
        for (int bin = 0; bin < nbins_; ++bin) {
            enc_hists_[inu][bin] /= njets_tot_;
            total_sum += enc_hists_[inu][bin];

            // Skip normalization for under/overflow bins
            if (bin < bins_finite_start_ || bin >= nbins_finite_ + bins_finite_start_) {
                continue;
            }

            // Normalize finite bins by bin width
            double dlogtheta1 = bin_edges_[bin + 1] - bin_edges_[bin];
            if (dlogtheta1 == 0) {
                throw std::runtime_error("Found invalid bin width dlogtheta1=0.");
            }

            enc_hists_[inu][bin] /= dlogtheta1;
        }

        // Print diagnostic information if verbose
        if (verbose_ >= 0) {
            float total_integral = 0;

            for (int bin = 0; bin < nbins_; ++bin) {
                // Skip normalization for under/overflow bins
                if (bin < bins_finite_start_ || bin >= nbins_finite_ + bins_finite_start_) {
                    total_integral += enc_hists_[inu][bin];
                    continue;
                }

                // Add bin contribution to total integral
                double dlogtheta1 = bin_edges_[bin + 1] - bin_edges_[bin];
                if (dlogtheta1 == 0) {
                    throw std::runtime_error("Found invalid bin width dlogtheta1=0.");
                }

                total_integral += enc_hists_[inu][bin] * dlogtheta1;
            }

            // Print diagnostics
            double nu = weights_[inu];
            std::cout << "\nTotal weight for nu=" << nu << ": " << total_sum;
            std::cout << "\nIntegrated weight for nu=" << nu << ": " << total_integral;
        }
    }
}

void PENC::writeOutput() {
    // First normalize all histograms
    normalizeHistograms();

    // Write each histogram to its file
    for (size_t inu = 0; inu < weights_.size(); ++inu) {
        writeHistogram(inu);
    }
}

void PENC::writeHistogram(size_t inu) {
    const std::string& filename = enc_outfiles[inu];

    // Open output file
    std::fstream outfile;
    outfile.open(filename, std::ios_base::in | std::ios_base::out | std::ios_base::app);

    // Check if file opened successfully
    if (!outfile.is_open()) {
        std::stringstream errMsg;
        errMsg << "File for PENC output was expected to be open, but was not open.\n\n"
               << "It is possible the file was unable to be created at the desired location:\n\n\t"
               << "filename = " << filename << "\n\n"
               << "Is the filename an absolute path? If not, that might be the problem.";
        throw std::runtime_error(errMsg.str().c_str());
    }

    // Write bin edges
    outfile << "theta1_edges = [\n\t";

    // Write bin edges (convert from log10 to linear)
    for (int ibin = 0; ibin < nbins_; ++ibin) {
        outfile << std::pow(10, bin_edges_[ibin]) << ", ";
    }

    // Handle last bin edge with potential infinity
    if (std::isinf(bin_edges_[nbins_])) {
        outfile << "np.inf\n";
    } else {
        outfile << std::pow(10, bin_edges_[nbins_]) << "\n";
    }

    outfile << "]\n\n";

    // Write bin centers
    outfile << "theta1_centers = [\n\t";

    for (int ibin = 0; ibin < nbins_ - 1; ++ibin) {
        outfile << std::pow(10, bin_centers_[ibin]) << ", ";
    }

    // Handle last bin center with potential infinity
    if (std::isinf(bin_centers_[nbins_ - 1])) {
        outfile << "np.inf\n";
    } else {
        outfile << std::pow(10, bin_centers_[nbins_ - 1]) << "\n";
    }

    outfile << "]\n\n";

    // Write histogram data
    outfile << "hist = [\n\t";

    for (int bin = 0; bin < nbins_; ++bin) {
        outfile << std::setprecision(10) << enc_hists_[inu][bin];
        if (bin != nbins_ - 1) {
            outfile << ", ";
        } else {
            outfile << "\n";
        }
    }

    outfile << "]";

    // Write runtime statistics if we only have one weight
    if (weights_.size() == 1) {
        writeRuntimes(outfile);
    }

    // Close file
    outfile.close();
}

void PENC::writeRuntimes(std::fstream& outfile) {
    std::vector<double> runtime_means;
    std::vector<double> runtime_stds;

    // Calculate statistics for each particle multiplicity
    for (int num = 0; num < 200; ++num) {
        auto it = jet_runtimes_.find(num);
        if (it == jet_runtimes_.end()) {
            // No data for this multiplicity
            runtime_means.emplace_back(std::numeric_limits<double>::quiet_NaN());
            runtime_stds.emplace_back(std::numeric_limits<double>::quiet_NaN());
            continue;
        }

        // Calculate mean and standard deviation
        const std::vector<double>& runtimes = it->second;
        double sum = 0.0;
        for (double time : runtimes) {
            sum += time;
        }
        double mean = sum / runtimes.size();

        // Calculate standard deviation
        double variance = 0.0;
        for (double time : runtimes) {
            variance += (time - mean) * (time - mean);
        }
        double stdev = std::sqrt(variance / runtimes.size());

        runtime_means.push_back(mean);
        runtime_stds.push_back(stdev);
    }

    // Write mean runtimes
    outfile << "\n\nruntime_means = [\n\t";

    for (size_t i = 0; i < runtime_means.size(); ++i) {
        if (!std::isnan(runtime_means[i])) {
            outfile << runtime_means[i];
        } else {
            outfile << "np.nan";
        }

        if (i < runtime_means.size() - 1) {
            outfile << ", ";
        } else {
            outfile << "\n";
        }
    }

    outfile << "]\n";

    // Write standard deviation of runtimes
    outfile << "runtime_stds = [\n\t";

    for (size_t i = 0; i < runtime_stds.size(); ++i) {
        if (!std::isnan(runtime_stds[i])) {
            outfile << runtime_stds[i];
        } else {
            outfile << "np.nan";
        }

        if (i < runtime_stds.size() - 1) {
            outfile << ", ";
        } else {
            outfile << "\n";
        }
    }

    outfile << "]";
}

#endif // PENC_H
