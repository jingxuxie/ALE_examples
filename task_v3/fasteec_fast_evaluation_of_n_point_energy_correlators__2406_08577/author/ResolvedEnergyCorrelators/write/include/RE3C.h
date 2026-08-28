#ifndef RENC_H
#define RENC_H

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
#include "fastjet/ClusterSequence.hh"

#include "histogram.h"


// Misc utilities
# define PI 3.14159265358979323846

typedef std::vector<double> Hist1d;
typedef std::vector< std::vector<double>> Hist2d;
typedef std::vector< std::vector< std::vector<double>>> Hist3d;


// Angle utilities
inline double mod2pi(double phi) {
    while (phi > PI)
        phi -= 2*PI;
    while (phi <= -PI)
        phi += 2*PI;

    return phi;
}

double enc_azimuth(const fastjet::PseudoJet part1,
                   const fastjet::PseudoJet part_sp,
                   const fastjet::PseudoJet part2) {
    // NOTE: I think this doesn't work for very fat jets --
    // NOTE:   roughly because fat jets require a bit more care
    // NOTE:   with mod(2pi) arithmetic
    // - - - - - - - - - - - - - - - - - - -
    // Normalized vectors in eta-phi plane
    // - - - - - - - - - - - - - - - - - - -
    // From part_sp to part1
    double x1 = part1.rap() - part_sp.rap();
    double y1 = mod2pi(part1.phi() - part_sp.phi());
    const double n1  = sqrt(std::pow(x1, 2.) + std::pow(y1, 2.));
    if (n1 == 0)
        return 0;
    x1 /= n1; y1 /= n1;

    // From part_sp to part2
    double x2;
    x2 = part2.rap() - part_sp.rap();
    double y2 = mod2pi(part2.phi() - part_sp.phi());
    const double n2  = sqrt(std::pow(x2, 2.) + std::pow(y2, 2.));
    if (n2 == 0)
        return 0;
    x2 /= n2; y2 /= n2;

    // - - - - - - - - - - - - - - - - - - -
    // Getting the "angle" between these vectors
    // - - - - - - - - - - - - - - - - - - -
    const double dot = x1*x2 + y1*y2;
    const double det = x1*y2 - y1*x2;
    double phi = mod2pi(atan2(det, dot));

    // Setting it to be between -pi and pi
    phi = phi > PI ? phi - 2*PI : phi;
    if (phi < -PI or PI < phi)
        throw std::range_error(
                "Found azimuthal angle not between -pi and pi.");

    return phi;
}




// ==============================================
// Resolved 3-point Energy Correlator class
// ==============================================
typedef std::pair<double, double> weight_pair;

class RE3C {
public:
    RE3C(const std::vector<weight_pair>& weights,
         double minbin, double maxbin, int nbins,
         int nphibins, bool lin_bin2,
         bool contact_terms = true,
         bool use_deltaR = true, bool use_pt = true,
         bool uflow = true, bool oflow = true,
         int verbose = 1,
         const std::string& file_prefix = "",
         const bool use_output_folder = true);

    ~RE3C() = default;

    // Process a jet and update histograms
    void processJet(const fastjet::PseudoJet& jet);

    // Normalize histograms and write to files
    void writeOutput();


    // Output histogram information
    std::vector<std::string> enc_outfiles;

    // Get the total number of jets processed
    int getTotalJets() const { return njets_tot_; }

    // Get runtime statistics for diagnostics
    const std::map<int, std::vector<double>>& getRuntimes() const { return jet_runtimes_; }

private:
    // RE3C specific parameters
    std::vector<weight_pair> weights_;
    bool lin_bin2_;
    bool contact_terms_;
    bool use_deltaR_;
    bool use_pt_;
    std::string file_prefix_;
    int verbose_;
    bool use_output_folder_;

    // Histogram data
    std::vector<Hist3d> enc_hists_;
    Histogram R1_;
    Histogram R2_;
    Histogram Phi_;
    int phizerobin_;

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

    // Internal computation of RE3C for a single jet
    void computeRE3C(const fastjet::PseudoJet& jet);
};



// Implementation of the RE3C class
RE3C::RE3C(const std::vector<weight_pair>& weights,
           double minbin, double maxbin, int nbins,
           int nphibins, bool lin_bin2,
           bool contact_terms, bool use_deltaR,
           bool use_pt, bool uflow, bool oflow,
           int verbose,
           const std::string& file_prefix,
           const bool use_output_folder)
    : weights_(weights),
      lin_bin2_(lin_bin2),
      contact_terms_(contact_terms),
      use_deltaR_(use_deltaR), use_pt_(use_pt),
      file_prefix_(file_prefix),
      verbose_(verbose),
      use_output_folder_(use_output_folder),
      R1_(minbin, maxbin, nbins, uflow, oflow, "log"),
      R2_(lin_bin2 ? 0 : minbin, lin_bin2 ? 1 : 0,
          nbins, lin_bin2 ? false : true, false,
          lin_bin2 ? "linear" : "log"),
      Phi_(-PI, PI, nphibins, false, false, "linear"),
      njets_tot_(0)
{
    phizerobin_ = Phi_.binPosition(0);

    initializeHistograms();
}


void RE3C::initializeHistograms() {
    // Initialize histograms, one for each nu weight
    enc_hists_.clear();
    enc_outfiles.clear();

    for (auto nus : weights_){
        // Setting up histograms
        enc_hists_.emplace_back(Hist3d
                (R1_.nBins(), Hist2d(R2_.nBins(), Hist1d(Phi_.nBins()))));

        // Create output filename
        std::string filename;

        filename += file_prefix_ +
                    "_nus_" + std::to_string(nus.first) +
                    "_" + std::to_string(nus.second);

        // Replace periods with hyphens
        std::replace(filename.begin(), filename.end(), '.', '-');

        // Add file extension
        filename += ".py";

        // Store filename for later
        enc_outfiles.push_back(filename);
    }
}



void RE3C::processJet(const fastjet::PseudoJet& jet) {
    try {
        // Start timing if we're only tracking one weight (for efficiency)
        auto jet_start = std::chrono::high_resolution_clock::now();

        // Increment jet counter
        ++njets_tot_;

        // Compute RE3C for this jet
        computeRE3C(jet);

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

void RE3C::computeRE3C(const fastjet::PseudoJet& jet) {
    // Get jet constituents
    const std::vector<fastjet::PseudoJet>& constituents = jet.constituents();

    // Calculate total weight of jet (energy or pt)
    double weight_tot = 0;
    for (const auto& particle : constituents) {
        weight_tot += use_pt_ ? particle.pt() : particle.e();
    }

    // Vector to store angle/weight pairs for sorting
    std::vector<std::pair<double, fastjet::PseudoJet>> sorted_angs_parts;
    sorted_angs_parts.reserve(constituents.size());

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
                double nu1 = weights_[inu].first;
                double nu2 = weights_[inu].second;
                enc_hists_[inu][0][0][phizerobin_] += std::pow(sum_weight1,
                                                              1+nu1+nu2);
            }
        }

        // Clear and prepare for sorting angles/weights
        sorted_angs_parts.clear();

        // Calculate angles and weights for all particles
        for (const auto& part1 : constituents) {
            // Angle relative to "special" particle
            double theta1 = use_deltaR_ ?
                    part_sp.delta_R(part1) :
                    fastjet::theta(part_sp, part1);

            sorted_angs_parts.emplace_back(theta1, part1);
        }
        // Sorting by angle
        std::sort(sorted_angs_parts.begin(),
                  sorted_angs_parts.end(),
                  [](auto& left, auto& right) {
                      return left.first < right.first;
                 });

        // Loop over sorted particles and calculate RE3C
        for (size_t jpart = 1; jpart < sorted_angs_parts.size(); ++jpart) {
            double theta1 = sorted_angs_parts[jpart].first;
            fastjet::PseudoJet& part1 = sorted_angs_parts[jpart].second;

            double weight1 = use_pt_ ?
                    part1.pt() / weight_tot :
                    part1.e() / weight_tot;

            // Calculating the theta1 bin in the histogram
            int bin1 = R1_.binPosition(theta1);

            // Skip if bin is invalid
            if (bin1 < 0) continue;


            // Initializing the sum of weights
            // within an angle of the 2nd non-special particle
            std::vector<double> sum_weight2(Phi_.nBins());

            sum_weight2[phizerobin_] += weight_sp;

            if (contact_terms_) {
                // Looping on _E^nu C_ weights [`nu's]
                for (size_t inu = 0; inu < weights_.size(); ++inu) {
                    std::pair<double, double> nus = weights_[inu];
                    double nu1   = nus.first;
                    double nu2   = nus.second;

                    // part2 = part_sp != part_1
                    enc_hists_[inu][bin1][0][phizerobin_] +=
                        2*std::pow(weight_sp, 1+nu2)*
                          std::pow(weight1, nu1);

                    // part2 = part1 != part_sp
                    enc_hists_[inu][bin1][R2_.nBins()-1][phizerobin_] +=
                                std::pow(weight_sp, 1)*
                                std::pow(weight1, nu1+nu2);
                }
            }

            // Loop on second non-special particle
            for (size_t kpart=1; kpart<jpart; ++kpart) {
                // Getting 2nd particle information
                double theta2    = sorted_angs_parts[kpart].first;
                fastjet::PseudoJet& part2 = sorted_angs_parts[kpart].second;
                double weight2 = use_pt_ ?
                        part2.pt() / weight_tot :
                        part2.e() / weight_tot;
                double theta2_over_theta1 =
                    theta1 == 0 ? 0 : theta2/theta1;

                // Calculating the theta2/theta1 bin position
                int bin2 = R2_.binPosition(theta2_over_theta1);

                // Getting azimuthal angle
                // (angle from part1 to part_sp to part2
                //  in rapidity-azimuth plane)
                double phi = enc_azimuth(
                        part1, part_sp, part2);

                // Calculating the phi bin
                int binphi = Phi_.binPosition(phi);

                // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                // Looping on _E^nu C_ weights [`nu's]
                for (size_t inu = 0;
                        inu < weights_.size(); ++inu) {
                    // Preparing properties of the correlator
                    std::pair<double, double> nus = weights_[inu];
                    double nu1   = nus.first;
                    double nu2   = nus.second;

                    // Adding to the histogram
                    double delta_weight1 = (
                           std::pow(sum_weight1+weight1, nu1)
                           -
                           std::pow(sum_weight1, nu1)
                         );
                    double delta_weight2 = (
                           std::pow(sum_weight2[binphi]
                                     + weight2, nu2)
                           -
                           std::pow(sum_weight2[binphi], nu2)
                         );

                    // need to count twice to get the full
                    // sum on all pairs (see also contact term)
                    double perm = 2;

                    double hist_weight = weight_sp *
                                delta_weight1 *
                                delta_weight2;

                    // Add to appropriate histogram bin
                    enc_hists_[inu][bin1][bin2][binphi] +=
                            perm*hist_weight;
                } // end EEC weight [nu] loop

                // Update sum for next iteration
                sum_weight2[binphi] += weight2;

            } // end calculation/2nd particle loop

            // Update sum for next iteration
            sum_weight1 += weight1;
        } // end 1st particle loop
    } // end special particle loop
}


void RE3C::normalizeHistograms() {
    for (size_t inu = 0; inu < weights_.size(); ++inu) {
        double total_sum = 0.0;

        // Looping over all bins
        for (int bin1=0; bin1<R1_.nBins(); ++bin1) {
            for (int bin2=0; bin2<R2_.nBins(); ++bin2) {
                for (int binphi=0; binphi<Phi_.nBins(); ++binphi) {
                    // Dealing with expectation value over N jets
                    enc_hists_[inu][bin1][bin2][binphi] /= njets_tot_;

                    total_sum += enc_hists_[inu][bin1][bin2][binphi];

                    // Not normalizing outflow bins further
                    if (bin1 < R1_.firstFiniteBin()
                            or bin1 >= R1_.nFiniteBins()
                            or bin2 < R2_.firstFiniteBin()
                            or bin2 >= R2_.nFiniteBins())
                        continue;

                    // Getting differential "volume" element
                    double dlogtheta1 = (R1_.binEdges()[bin1+1] - R1_.binEdges()[bin1]);
                    double dtheta2_over_theta1 = (R2_.binEdges()[bin2+1] - R2_.binEdges()[bin2]);
                    double dphi = (Phi_.binEdges()[binphi+1] - Phi_.binEdges()[binphi]);

                    double dvol = dlogtheta1 * dtheta2_over_theta1 * dphi;
                    enc_hists_[inu][bin1][bin2][binphi] /= dvol;

                    // NOTE: This is theta1^2 times the
                    // NOTE:    linearly normed distribution
                }
            }
        }

        // Print diagnostic information if verbose
        if (verbose_ >= 0) {
            double total_integral = 0.0;
            for (int bin1=0; bin1<R1_.nBins(); ++bin1) {
                for (int bin2=0; bin2<R2_.nBins(); ++bin2) {
                    for (int binphi=0; binphi<Phi_.nBins(); ++binphi) {
                        if (bin1 < R1_.firstFiniteBin()
                                or bin1 >= R1_.nFiniteBins()
                                or bin2 < R2_.firstFiniteBin()
                                or bin2 >= R2_.nFiniteBins()) {
                            total_integral += enc_hists_[inu][bin1][bin2][binphi];
                            continue;
                        }

                        // Getting differential "volume" element
                        double dlogtheta1 = (R1_.binEdges()[bin1+1] - R1_.binEdges()[bin1]);
                        double dtheta2_over_theta1 = (R2_.binEdges()[bin2+1] - R2_.binEdges()[bin2]);
                        double dphi = (Phi_.binEdges()[binphi+1] - Phi_.binEdges()[binphi]);

                        double dvol = dlogtheta1 * dtheta2_over_theta1 * dphi;

                        total_integral += enc_hists_[inu][bin1][bin2][binphi] * dvol;
                    }
                }
            }

            // Print diagnostics
            std::pair<double, double> nu = weights_[inu];
            std::cout << "\nTotal weight for nu=("
                      << nu.first << "," << nu.second << "): "
                      << total_sum;
            std::cout << "\nIntegrated weight for nu=("
                      << nu.first << "," << nu.second << "): "
                      << total_integral;
        }
    }
}

void RE3C::writeOutput() {
    // First normalize all histograms
    normalizeHistograms();

    // Write each histogram to its file
    for (size_t inu = 0; inu < weights_.size(); ++inu) {
        writeHistogram(inu);
    }
}

void RE3C::writeHistogram(size_t inu) {
    const std::string& filename = enc_outfiles[inu];

    // Open output file
    std::fstream outfile;
    outfile.open(filename, std::ios_base::in | std::ios_base::out | std::ios_base::app);

    // Check if file opened successfully
    if (!outfile.is_open()) {
        std::stringstream errMsg;
        errMsg << "File for RE3C output was expected to be open, but was not open.\n\n"
               << "It is possible the file was unable to be created at the desired location:\n\n\t"
               << "filename = " << filename << "\n\n"
               << "Is the filename an absolute path? If not, that might be the problem.";
        throw std::runtime_error(errMsg.str().c_str());
    }

    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // theta1s
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // -:-:-:-:-:-:-:-:-:-:-:-:
    // bin edges
    // -:-:-:-:-:-:-:-:-:-:-:-:
    outfile << "theta1_edges = [\n\t";

    // nbins+1 bin edges:
    //   include -infty and infty for under/overflow
    for (int ibin = 0; ibin < R1_.nBins(); ++ibin)
        outfile << std::pow(10, R1_.binEdges()[ibin]) << ", ";
    if (std::isinf(R1_.binEdges()[R1_.nBins()]))
        outfile << "np.inf\n";
    else
        outfile << std::pow(10, R1_.binEdges()[R1_.nBins()]) << "\n";

    outfile << "]\n\n";

    // -:-:-:-:-:-:-:-:-:-:-:-:
    // bin centers
    // -:-:-:-:-:-:-:-:-:-:-:-:
    outfile << "theta1_centers = [\n\t";

    for (int ibin = 0; ibin < R1_.nBins()-1; ++ibin)
        outfile << std::pow(10, R1_.binCenters()[ibin]) << ", ";
    if (std::isinf(R1_.binCenters()[R1_.nBins()-1]))
        outfile << "np.inf\n";
    else
        outfile << std::pow(10, R1_.binCenters()[R1_.nBins()-1]) << "\n";

    outfile << "]\n\n";


    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // theta2_over_theta1s
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // -:-:-:-:-:-:-:-:-:-:-:-:
    // bin edges
    // -:-:-:-:-:-:-:-:-:-:-:-:
    outfile << "theta2_over_theta1_edges = [\n\t";

    // nbins+1 bin edges:
    for (int ibin = 0; ibin < R2_.nBins()+1; ++ibin) {
        double bin2_edge = lin_bin2_ ? R2_.binEdges()[ibin]
                                     : std::pow(10, R2_.binEdges()[ibin]);
        outfile << bin2_edge;
        if (ibin < R2_.nBins())
            outfile << ", ";
        else
            outfile << std::endl;
    }

    outfile << "]\n\n";

    // -:-:-:-:-:-:-:-:-:-:-:-:
    // bin centers
    // -:-:-:-:-:-:-:-:-:-:-:-:
    outfile << "theta2_over_theta1_centers = [\n\t";

    for (int ibin = 0; ibin < R2_.nBins(); ++ibin) {
        double bin2_val = lin_bin2_ ? R2_.binCenters()[ibin]
                                   : std::pow(10, R2_.binCenters()[ibin]);
        outfile << bin2_val;
        if (ibin < R2_.nBins()-1)
            outfile << ", ";
        else
            outfile << std::endl;
    }
    outfile << "]\n\n";


    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // phis
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // -:-:-:-:-:-:-:-:-:-:-:-:
    // bin edges
    // -:-:-:-:-:-:-:-:-:-:-:-:
    outfile << "phi_edges = [\n\t";

    // nphibins+1 bin edges:
    for (int ibin = 0; ibin < Phi_.nBins(); ++ibin)
        outfile << Phi_.binEdges()[ibin] << ", ";
    outfile << Phi_.binEdges()[Phi_.nBins()] << "\n";

    outfile << "]\n\n";

    // -:-:-:-:-:-:-:-:-:-:-:-:
    // bin centers
    // -:-:-:-:-:-:-:-:-:-:-:-:
    outfile << "phi_centers = [\n\t";

    for (int ibin = 0; ibin < Phi_.nBins()-1; ++ibin)
        outfile << Phi_.binCenters()[ibin] << ", ";
    outfile << Phi_.binCenters()[Phi_.nBins()-1] << "\n";

    outfile << "]\n\n";


    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Write histogram data
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    outfile << "hist = [\n\t";

    // theta1s
    for (int bin1 = 0; bin1 < R1_.nBins(); ++bin1) {
        outfile << "[\n\t";

        // theta2s
        for (int bin2 = 0; bin2 < R2_.nBins(); ++bin2) {
            // Phis
            if (Phi_.nBins() == 1){
                outfile << enc_hists_[inu][bin1][bin2][0];
                outfile << (bin2 != R2_.nBins()-1 ? ", "
                                                : "\n");
            } else {
                outfile << "\t[\n\t\t\t";

                // Loop over phis
                for (int binphi = 0; binphi < Phi_.nBins()-1; ++binphi) {
                    outfile << std::setprecision(10)
                            << enc_hists_[inu][bin1][bin2][binphi] << ", ";
                }
                outfile << enc_hists_[inu][bin1][bin2][Phi_.nBins()-1] << "\n";

                outfile << (bin2 != R2_.nBins()-1 ? "\t\t],\n\t"
                                            : "\t\t]\n");
            }
        }

        outfile << (bin1 != R1_.nBins()-1 ? "\t],\n\t"
                                    : "\t]\n");
    }
    outfile << "]";


    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Write runtime statistics if we only have one weight
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    if (weights_.size() == 1) {
        writeRuntimes(outfile);
    }

    // Close file
    outfile.close();
}

void RE3C::writeRuntimes(std::fstream& outfile) {
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

#endif // RENC_H
