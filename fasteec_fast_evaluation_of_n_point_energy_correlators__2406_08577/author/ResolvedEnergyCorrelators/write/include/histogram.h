#ifndef HISTOGRAM_H
#define HISTOGRAM_H

#include <vector>
#include <string>
#include <cmath>
#include <limits>
#include <fstream>
#include <iostream>
#include <iomanip>



// Base class for histogram-based observables
class Histogram {
public:
    Histogram(double minbin, double maxbin, int nbins,
              bool uflow = true, bool oflow = true,
              std::string scaling = "log");
    virtual ~Histogram() = default;

    int nBins() {return nbins_;}
    int nFiniteBins() {return nbins_finite_;}
    int firstFiniteBin() {return bins_finite_start_;}
    std::vector<double> binEdges() {return bin_edges_;}
    std::vector<double> binCenters() {return bin_centers_;}

    // Common utility functions
    int binPosition(double value) const;

protected:
    // Histogram parameters
    const double minbin_;
    const double maxbin_;
    const int nbins_;
    const bool uflow_;
    const bool oflow_;
    const std::string scaling_;

    // Histogram data
    std::vector<double> bin_edges_;
    std::vector<double> bin_centers_;
    int bins_finite_start_;
    int nbins_finite_;

    // Output formatting
    std::string getHistDelim() const;

    // Function to calculate bin edges and centers
    void initializeBins();
};



// Implementation of the Histogram base class
Histogram::Histogram(
        double minbin, double maxbin, int nbins,
        bool uflow, bool oflow, std::string scaling)
    : minbin_(minbin), maxbin_(maxbin), nbins_(nbins),
      uflow_(uflow), oflow_(oflow), scaling_(scaling)
{
    initializeBins();
}

void Histogram::initializeBins() {
    // Setting up under/overflow
    nbins_finite_ = nbins_;
    bins_finite_start_ = 0;

    if (uflow_) {
        nbins_finite_ -= 1;
        bins_finite_start_ += 1;
    }
    if (oflow_) {
        nbins_finite_ -= 1;
    }

    // Initialize bin edges and centers (logarithmic scale)
    bin_edges_.resize(nbins_ + 1);
    bin_centers_.resize(nbins_);

    // Calculate logarithmic bin edges
    double delta = (maxbin_ - minbin_) / (nbins_finite_);

    // Start with underflow if needed
    int idx = 0;
    if (uflow_) {
        bin_edges_[idx++] = -std::numeric_limits<double>::infinity();
    }

    // Regular bins
    for (int i = 0; i <= nbins_finite_; ++i) {
        bin_edges_[idx++] = minbin_ + i * delta;
    }

    // Overflow if needed
    if (oflow_) {
        bin_edges_[nbins_] = std::numeric_limits<double>::infinity();
    }

    // Calculate bin centers
    idx = 0;
    if (uflow_) {
        bin_centers_[idx++] = -std::numeric_limits<double>::infinity();
    }

    // Regular bin centers
    for (int i = 0; i < nbins_finite_; ++i) {
        bin_centers_[idx++] = minbin_ + (i + 0.5) * delta;
    }

    // Overflow center if needed
    if (oflow_) {
        bin_centers_[nbins_ - 1] = std::numeric_limits<double>::infinity();
    }
}



int Histogram::binPosition(double value) const {
    // Convert value to log scale if needed
    double scaled_value = value;
    if (scaling_ == "log") {
        scaled_value = std::log10(value);
    }

    // Handle underflow
    if (scaled_value < minbin_) {
        if (uflow_) return 0;

        /* throw std::underflow_error( */
        /*         "Invalid val "+std::to_string(scaled_value)+ */
        /*         " is smaller than minimum bin edge "+ */
        /*         std::to_string(minbin)+"." */
        /*     ); */
        return -1;
    }

    // Handle overflow
    if (scaled_value >= maxbin_) {
        if (oflow_) return nbins_ - 1;

        /* throw std::overflow_error( */
        /*         "Invalid val "+std::to_string(scaled_value)+ */
        /*         " is larger than maximum bin edge "+ */
        /*         std::to_string(maxbin)+"." */
        /*     ); */
        return -1;
    }

    // Regular bin
    int bin = static_cast<int>((scaled_value - minbin_) / (maxbin_ - minbin_) * nbins_finite_);
    if (uflow_) bin++; // Account for underflow bin

    return bin;
}



#endif // HISTOGRAM_H
