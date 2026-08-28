/**
 * @file    new_enc_3particle.cc
 *
 * @brief   Code for generating histograms for "new angles on"
 *          n-point projected energy correlators (ENCs);
 *          in this file, we consider three particles, and are
 *          differential in three angles:
 *          theta1, theta2, and the azimuthal angle phi_{2*1}.
 */


// ---------------------------------
// Basic imports
// ---------------------------------
#include <iostream>
#include <cmath>
#include <locale>
#include <fstream>
#include <sstream>
#include <string.h>
#include <vector>
#include <map>
#include <utility>
#include <stdexcept>
#include <filesystem>

#include <chrono>
using namespace std::chrono;

// for including infinity as an overflow bin
#include <limits>

// ---------------------------------
// HEP imports
// ---------------------------------
#include "Pythia8/Pythia.h"
#include "fastjet/PseudoJet.hh"
#include "fastjet/ClusterSequence.hh"

// ROOT Classes
#include "TROOT.h"
#include "TH3.h"
#include "TH2.h"
#include "TFile.h"
#include "TCanvas.h"
#include "TPad.h"
#include "TStyle.h"
#include "TLegend.h"
#include "TLine.h"
#include "TLatex.h"
#include "TGraph2D.h"
#include "TPaletteAxis.h"

// Local imports:
#include "../include/general_utils.h"
#include "../include/jet_utils.h"
#include "../include/pythia2fastjet.h"
#include "../include/cmdln.h"
#include "../include/pythia_cmdln.h"

#include "../include/enc_utils.h"

#include "../include/opendata_utils.h"


// =====================================
// Histogram Utilities
// =====================================
// Using pairs of weights to specify the doubly-projected correlator
typedef std::pair<double, double> weight_t;

// (Arjun's) Utility function for log-normalizing a 3D ROOT histogram
void BinLogX3D(TH3* h) {
    TAxis* axis = h->GetXaxis();
    int bins = axis->GetNbins();
    Axis_t from = axis->GetXmin();
    Axis_t to = axis->GetXmax();
    Axis_t width = (to - from) / bins;
    Axis_t* new_bins = new Axis_t[bins + 1];

    for (int i = 0; i <= bins; i++) {
        new_bins[i] = std::pow(10, from + i * width);
    }
    axis->Set(bins, new_bins);
    delete new_bins;
}

// =====================================
// Additional Utilities
// =====================================
inline double mod2pi(double phi) {
    while (phi > PI)
        phi -= TWOPI;
    while (phi <= -PI)
        phi += TWOPI;

    return phi;
}

double enc_azimuth(const PseudoJet part1,
                   const PseudoJet part_sp,
                   const PseudoJet part2) {
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
    phi = phi > PI ? phi - TWOPI : phi;
    if (phi < -PI or PI < phi)
        throw std::range_error(
                "Found azimuthal angle not between -pi and pi.");

    return phi;
}

// =====================================
// Plotting Utilities
// =====================================
const std::string plots_dir = "output/new_enc_figures";

std::vector<int> special_r1_bins(int nbins) {
    return {
        3*nbins/4,
        7*nbins/8-2,
        7*nbins/8,
        7*nbins/8+2};
}


// Helper function to set up axis styling
void setupAxisStyling(TH1* hist, const std::string& xTitle, const std::string& yTitle,
                     bool logx = false, bool logy = false) {
    hist->GetXaxis()->SetTitle(xTitle.c_str());
    hist->GetXaxis()->SetTitleSize(0.06);
    hist->GetXaxis()->SetLabelSize(0.06);
    hist->GetXaxis()->SetTitleOffset(1.3);
    hist->GetXaxis()->SetNdivisions(505);

    hist->GetYaxis()->SetTitle(yTitle.c_str());
    hist->GetYaxis()->SetTitleSize(0.05);
    hist->GetYaxis()->SetLabelSize(0.05);
    hist->GetYaxis()->SetTitleOffset(1.8);
    hist->GetYaxis()->SetNdivisions(505);

    hist->GetZaxis()->SetTitleSize(0.05);
    hist->GetZaxis()->SetLabelSize(0.05);
    hist->GetZaxis()->SetNdivisions(505);

    if (logx) gPad->SetLogx();
    if (logy) gPad->SetLogy();

    gStyle->SetOptStat(0);
}

// Helper function to add descriptive text
void addPlotDescription(const std::string& description, double x = 0.15, double y = 0.85) {
    TLatex* latex = new TLatex();
    latex->SetTextSize(0.04);
    latex->SetNDC(true);
    latex->DrawLatex(x, y, description.c_str());
}


// Function to create R1-R2 projection plot
void makeR1R2Projection(TH3D* hist3d, const std::string& nu_str,
                       double minbin, double maxbin,
                       double theta = 60, double phi = 135,
                       double z_max = -1) {
    // Project onto X-Y plane (R1 vs R2/R1) - use safer projection method
    TH2D* proj_r1ratio = (TH2D*) hist3d->Project3D("yx");
    if (!proj_r1ratio) {
        std::cerr << "Failed to create projection for " << nu_str << std::endl;
        return;
    }

    std::string proj_name = "proj_r1ratio_" + nu_str;
    proj_r1ratio->SetName(proj_name.c_str());
    proj_r1ratio->SetDirectory(0); // Detach from directory to prevent auto-delete

    TCanvas* c1 = new TCanvas(("c_r1ratio_" + nu_str).c_str(),
                             "R1-R2 Projection", 800, 600);

    // Set up the plot
    proj_r1ratio->GetXaxis()->SetTitle("log_{10}(R_{1})");
    proj_r1ratio->GetXaxis()->SetRangeUser(minbin, maxbin);
    proj_r1ratio->GetYaxis()->SetTitle("R_{2}/R_{1}");
    proj_r1ratio->GetYaxis()->SetRangeUser(0.0, 1.0);
    proj_r1ratio->GetZaxis()->SetTitle("RE3C");
    proj_r1ratio->SetTitle("");


    // Draw as LEGO2
    proj_r1ratio->Draw("LEGO2");
    setupAxisStyling(proj_r1ratio, "log_{10}(R_{1})", "R_{2}/R_{1}");

    // Set manual Z-range if specified
    proj_r1ratio->SetMinimum(0.0);
    if (z_max > 0) {
        proj_r1ratio ->SetMaximum(z_max);
    }

    // Rotate
    gPad->SetTheta(theta);  // Polar angle (0-180)
    gPad->SetPhi(phi);      // Azimuthal angle (0-360)

    // Add description
    addPlotDescription("R_{1} vs R_{2}/R_{1} projection");

    // Save
    std::string filename = plots_dir + "/enc_r1ratio_proj_" + nu_str + ".png";
    c1->Update();
    c1->SaveAs(filename.c_str());

    // Clean up
    delete proj_r1ratio;
    delete c1;

    std::cout << "Saved " << filename << std::endl;
}


void makePolarR2PhiPlot(TH3D* hist3d, const std::string& nu_str,
                           int r1_bin_idx, const std::string& r1_desc,
                           double theta = 60, double phi = 45,
                           double z_min = 5e-3, double z_max = -1) {
    std::filesystem::create_directories(plots_dir);

    int nbins_ratio = hist3d->GetNbinsY();
    int nbins_phi = hist3d->GetNbinsZ();

    // Create canvas with polar coordinate system
    std::string canvas_name = "c_polar_" + nu_str + "_r1bin" + std::to_string(r1_bin_idx);
    TCanvas* c_polar = new TCanvas(canvas_name.c_str(), "True Polar R2-Phi Plot", 800, 800);

    // Create a polar pad
    TPad* polar_pad = new TPad("polar_pad", "Polar Pad", 0, 0, 1, 1);
    polar_pad->SetFrameFillColor(0);
    polar_pad->Draw();
    polar_pad->cd();

    // Create vectors to store polar data
    std::vector<double> x_cart, y_cart, z_values;

    // Convert histogram data to polar coordinates
    double ratio_max = hist3d->GetYaxis()->GetXmax();

    for (int jratio = 1; jratio <= nbins_ratio; ++jratio) {
        for (int jphi = 1; jphi <= nbins_phi; ++jphi) {
            // Getting radius value
            double ratio = hist3d->GetYaxis()->GetBinCenter(jratio);

            // Getting histogram value
            double content = hist3d->GetBinContent(r1_bin_idx, jratio, jphi);
            // and including jacobian factor
            content = content / ratio;

            // Only plot non-zero content
            if (content > 0) {
                // Get bin centers
                double phival = hist3d->GetZaxis()->GetBinCenter(jphi);

                // Convert to Cartesian coordinates for plotting
                // ratio is our radius, phi is our angle
                double x = ratio * cos(phival);
                double y = ratio * sin(phival);

                x_cart.push_back(x);
                y_cart.push_back(y);
                z_values.push_back(content);
            }
        }
    }

    if (x_cart.empty()) {
        std::cerr << "No data points for polar plot " << nu_str << std::endl;
        delete polar_pad;
        delete c_polar;
        return;
    }

    // Create TH2D for the polar plot
    int polar_nbins = std::min(nbins_phi, nbins_ratio)/2;

    TH2D* polar_hist = new TH2D(
        ("polar_hist_" + nu_str + "_" + std::to_string(r1_bin_idx)).c_str(),
        "", polar_nbins, -1.0, 1.0, polar_nbins, -1.0, 1.0);

    polar_hist->SetDirectory(0);  // Detach from current directory

    // Set manual Z-range if specified
    if (z_min > 0)
        polar_hist->SetMinimum(z_min);
    else
        z_min = polar_hist->GetZaxis()->GetXmin();
    if (z_max > 0)
        polar_hist->SetMaximum(z_max);

    // Set axis ranges to be symmetric (circular)
    double max_r = ratio_max;
    polar_hist->GetXaxis()->SetRangeUser(-max_r, max_r);
    polar_hist->GetYaxis()->SetRangeUser(-max_r, max_r);
    // and make the z-axis logarithmic
    gPad->SetLogz();

    // Fill the polar histogram
    for (size_t i = 0; i < x_cart.size(); ++i) {
        polar_hist->Fill(x_cart[i], y_cart[i], z_values[i]);
    }
    /* // and add an epsilonic value to all bins within plot bounds, */
    /* // so that they appear in the plot */
    /* for (int ix = 1; ix <= polar_nbins; ++ix) { */
    /*     double x_val = polar_hist->GetXaxis()->GetBinCenter(ix) - 1./polar_nbins; */
    /*     for (int iy = 1; iy <= polar_nbins; ++iy) { */
    /*         double y_val = polar_hist->GetYaxis()->GetBinCenter(iy) - 1./polar_nbins; */

    /*         if (x_val*x_val + y_val*y_val <= max_r*max_r) { */
    /*             int bin = polar_hist->GetBin(ix, iy); */
    /*             if (polar_hist->GetBinContent(bin) < z_min*1.1) */
    /*                 polar_hist->SetBinContent(bin, z_min*1.1); */
    /*         } */
    /*     } */
    /* } */

    // Set titles - remove axis labels for cleaner polar appearance
    polar_hist->SetTitle("");
    polar_hist->GetXaxis()->SetTitle("");
    polar_hist->GetYaxis()->SetTitle("");

    // Remove axis ticks and labels for cleaner polar plot
    polar_hist->GetXaxis()->SetTickLength(0);
    polar_hist->GetYaxis()->SetTickLength(0);
    polar_hist->GetZaxis()->SetTickLength(0);
    polar_hist->GetXaxis()->SetLabelOffset(999);  // Hide labels by offsetting far away
    polar_hist->GetYaxis()->SetLabelOffset(999);
    /* polar_hist->GetZaxis()->SetLabelOffset(999); */

    // Set the color for zero/background values to white
    polar_hist->SetFillColor(kWhite);

    // Draw with COLZ to get automatic colorbar
    polar_hist->Draw("LEGO2Z0FBBBA");
    // DEBUG: get polar working like Arjun
    /* setupAxisStyling(polar_hist, "R_{2}/R_{1}", "#phi"); */
    setupAxisStyling(polar_hist, "", "");

    // Add description
    c_polar->cd(); // Switch back to main canvas for text
    addPlotDescription(r1_desc.c_str(), 0.15, 0.9);
    addPlotDescription("RE3C", 0.87, 0.94);

    // Rotate
    gPad->SetTheta(theta);  // Polar angle (0-180)
    gPad->SetPhi(phi);      // Azimuthal angle (0-360)

    // Spacing margins
    c_polar->SetRightMargin(0.15);  // space for colorbar

    // Grab the palette axis object
    TPaletteAxis* palette =
        (TPaletteAxis*) polar_hist->GetListOfFunctions()->FindObject("palette");

    if (palette) {
        // Move palette slightly left (values are in NDC: 0=left, 1=right)
        palette->SetX1NDC(0.87);  // left edge of palette
        palette->SetX2NDC(0.90);  // right edge of palette
        // You can also adjust vertical placement:
        // palette->SetY1NDC(0.15);
        // palette->SetY2NDC(0.95);
    }

    c_polar->Modified();
    c_polar->Update();
    gPad->Update();

    // Save as png
    std::string filename = plots_dir + "/enc_polar_" +
                           nu_str + "_r1bin" +
                           std::to_string(r1_bin_idx) + ".png";

    c_polar->SaveAs(filename.c_str());

    // TOGGLE: Save as pdf
    /* std::string filename_pdf = plots_dir + "/enc_jacobian_polar_" + */
    /*                           nu_str + "_r1bin" + */
    /*                           std::to_string(r1_bin_idx) + ".pdf"; */
    /* c_polar->SaveAs(filename_pdf.c_str()); */

    // Clearing memory
    /* delete polar_graph; */
    delete polar_hist;
    delete polar_pad;
    delete c_polar;
    std::cout << "Saved " << filename << std::endl;
}


// TODO: make polar by copying above
void makeR2PhiProjections(TH3D* hist3d, const std::string& nu_str,
                         int nbins_r1_to_plot = 6,
                         double theta = 60, double phi = 45) {

    // Get histogram dimensions
    int nbins_r1 = hist3d->GetNbinsX();
    int nbins_ratio = hist3d->GetNbinsY();
    int nbins_phi = hist3d->GetNbinsZ();

    // Create canvas with multiple pads
    std::string canvas_name = "enc_polar_multi" + nu_str;
    TCanvas* c_multi = new TCanvas(canvas_name.c_str(),
                                  "R2-Phi Projections", 1200, 800);
    c_multi->Divide(3, ceil(nbins_r1_to_plot/3.0)); // 3xN grid

    // Select R1 bins to plot (evenly spaced)
    std::vector<int> r1_bins_to_plot;
    int effective_nbins = std::min(nbins_r1_to_plot, nbins_r1);

    for (int i = 0; i < effective_nbins; ++i) {
        int bin_idx = 1 + i * (nbins_r1 - 1) / (effective_nbins - 1);
        r1_bins_to_plot.push_back(bin_idx);
    }

    std::vector<TH2D*> temp_hists; // Keep track for cleanup

    for (size_t ipad = 0; ipad < r1_bins_to_plot.size() && ipad < 6; ++ipad) {
        c_multi->cd(ipad + 1);

        int r1_bin = r1_bins_to_plot[ipad];
        double r1_value = hist3d->GetXaxis()->GetBinCenter(r1_bin);

        // Create 2D histogram for this R1 slice
        std::string hist_name = "proj_ratiophi_r1bin" + std::to_string(r1_bin) + "_" + nu_str;
        TH2D* proj_ratiophi = new TH2D(
            hist_name.c_str(),
            "", nbins_ratio,
            hist3d->GetYaxis()->GetXmin(), hist3d->GetYaxis()->GetXmax(),
            nbins_phi,
            hist3d->GetZaxis()->GetXmin(), hist3d->GetZaxis()->GetXmax());

        proj_ratiophi->SetDirectory(0); // Detach from current directory
        temp_hists.push_back(proj_ratiophi);

        // Fill the projection
        for (int jratio = 1; jratio <= nbins_ratio; ++jratio) {
            for (int jphi = 1; jphi <= nbins_phi; ++jphi) {
                double content = hist3d->GetBinContent(r1_bin, jratio, jphi);
                proj_ratiophi->SetBinContent(jratio, jphi, content);
            }
        }

        // Set up axes
        /* proj_ratiophi->GetXaxis()->SetTitle("R_{2}/R_{1}"); */
        /* proj_ratiophi->GetYaxis()->SetTitle("#phi"); */
        proj_ratiophi->SetTitle("");

        // Draw as polar-like plot
        proj_ratiophi->Draw("LEGO2");

        // Add R1 value label
        std::string r1_label = "R_{1} = " + std::to_string(std::pow(10, r1_value));
        addPlotDescription(r1_label, 0.15, 0.85);

        gPad->SetTheta(theta);  // Polar angle (0-180)
        gPad->SetPhi(phi);      // Azimuthal angle (0-360)
        gPad->Update();
    }

    // Save multi-panel plot
    std::string filename = plots_dir + "/enc_ratiophi_multi_" + nu_str + ".png";
    c_multi->SaveAs(filename.c_str());

    std::cout << "Saved " << filename << std::endl;

    // Clean up
    for (auto* h : temp_hists) {
        delete h;
    }
    delete c_multi;
}




// ####################################
// Main
// ####################################
/**
* @brief: Generates events with Pythia and creates EWOC histograms.
*
* @return: int
*/
int main (int argc, char* argv[]) {
    // Printing if told to be verbose
    int verbose = cmdln_int("verbose", argc, argv, 1);
    if (verbose >= 0) std::cout << enc_banner;

    // Starting timer
    auto start = high_resolution_clock::now();

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Getting command line variables
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // File to which we want to write
    std::string file_prefix = cmdln_string("file_prefix",
                                           argc, argv, "",
                                           true); /* required */
    std::string filename_str = "output/new_encs/3particle_" + file_prefix + ".ROOT";
    const char* filename = filename_str.c_str();

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Histogram Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const int   nbins     = cmdln_int("nbins", argc, argv,
                                      100, false);
    // NOTE: using logarithmically spaced bins,
    // NOTE:   with minbin and maxbin in base 10

    const double minbin   = cmdln_double("minbin", argc, argv,
                                   -8, false);
    const double maxbin   = cmdln_double("maxbin", argc, argv,
                                   0.05, false);
    const bool bin1_uflow = true, bin1_oflow = true;

    // Phi is binned linearly, with same nbins by default
    const int   nphibins  = cmdln_int("nphibins", argc, argv,
                                nbins, false);

    // theta2/theta1 is binned linearly
    const bool lin_bin2   = true;
    /* cmdln_bool("lin_bin2", argc, argv, true, false); */

    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Initializing bin edges and centers
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    // - - - - - - - - - - - - - - -
    // For theta1
    // - - - - - - - - - - - - - - -
    // Setting up under/overflow
    int nbins1_finite = nbins, bin1_finite_start = 0;
    if (bin1_uflow) {nbins1_finite -= 1; bin1_finite_start += 1;}
    if (bin1_oflow) nbins1_finite -= 1;

    // (logarithmic, from 10^minbin to 10^maxbin)
    const std::vector<double> bin1_edges   = get_bin_edges(
                                            minbin, maxbin, nbins,
                                            bin1_uflow, bin1_oflow);
    const std::vector<double> bin1_centers = get_bin_centers(
                                            minbin, maxbin, nbins,
                                            bin1_uflow, bin1_oflow);

    // - - - - - - - - - - - - - - -
    // Bins for theta2/theta
    // - - - - - - - - - - - - - - -
    // (from 0 to 1, with a variable bin-spacing scheme)
    // Options dependent on the binning of theta2/theta1:
    const std::string bin2_scheme = lin_bin2 ? "lin" : "log";
    // t2/t1 in (0, 1) in linear bins, or
    // t2/t1 in (1e-minbin, 1) if logarithmic bins
    const double bin2_min = lin_bin2 ?   0   : minbin;
    const double bin2_max = lin_bin2 ?   1   : 0;
    // Use underflow only if binning logarithmically
    const bool bin2_uflow        = lin_bin2 ? false : true;

    const std::vector<double> bin2_edges = get_bin_edges(
                                        bin2_min, bin2_max,
                                        nbins, bin2_uflow, false);
                            /* underflow = (!bin_lin2) */
                            /* but overflow = false */
    const std::vector<double> bin2_centers = get_bin_centers(
                                        bin2_min, bin2_max,
                                        nbins, bin2_uflow, false);

    // - - - - - - - - - - - - - - -
    // For "azimuthal" angle phi
    // - - - - - - - - - - - - - - -
    // (linear, from -pi to pi)
    const std::vector<double> phi_edges   = get_bin_edges(
                                                -PI, PI, nphibins,
                                                false, false);
    const std::vector<double> phi_centers = get_bin_centers(
                                                -PI, PI, nphibins,
                                                false, false);
    // Bin for phi = 0
    const int phizerobin = bin_position(0, -PI, PI, nphibins,
                                        "linear", false, false);




    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Getting the list of energy weight pairs (nu1, nu2)
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    std::vector <weight_t> nu_weights;
    // (We are calculating the projected `E^(1+nu1+nu2) C`)
    for(int iarg=0; iarg<argc; ++iarg) {
        if(str_eq(argv[iarg], "--weights"))
            while (iarg+1 < argc and
                    // next arg doesn't start with '--'
                    std::string(argv[iarg+1]).find("--") == std::string::npos) {
                ++iarg;
                // Ensuring we are given pairs of weights
                if (iarg+1 >= argc or // next arg starts with '--'
                        std::string(argv[iarg+1]).find("--") != std::string::npos)
                    throw std::invalid_argument(
                            "Need to give an even number of weights "
                            "for the doubly-differential distribution.");

                nu_weights.emplace_back(
                            atof(argv[iarg]),atof(argv[iarg+1])
                        );
                ++iarg;
            }
    }

    if (nu_weights.size() == 0)
        throw std::invalid_argument(
            "Must be given at least 2 weights.");


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Plotting histograms if file exists
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const bool recreate_hists = cmdln_bool("recreate_hists",
                                          argc, argv, false);

    if (!recreate_hists)
        std::cout << "Looking for file." << std::endl;

    if (std::filesystem::exists(filename) and !recreate_hists) {
        TFile* ROOTFile_read = TFile::Open(filename);
        if (!ROOTFile_read || ROOTFile_read->IsZombie()) {
            std::cerr << "Error: Existing ROOT file found, at" <<
                std::endl << "\t" << filename << std::endl <<
                "but cannot be opened." << std::endl;
            return 1;
        }


        std::cout << "Found file with requested data." << std::endl;

        // Print what's actually in the file
        std::cout << "\n=============================" << std::endl;
        std::cout << "\n=== Contents of ROOT file ===" << std::endl;
        ROOTFile_read->ls(); // This will list everything in the file
        std::cout << "\n=============================\n" << std::endl;

        // Print what we're looking for
        std::cout << "Looking for these histogram names:" << std::endl;
        for (auto nus : nu_weights) {
            std::string nu_str = periods_to_hyphens(str_round(nus.first, 2)
                                 + "_" + str_round(nus.second, 2));
            std::cout << "  " << nu_str << std::endl;
        }
        std::cout << std::endl;


        // List all objects in the file for debugging
        std::cout << "Available objects:" << std::endl;
        TList* keyList = ROOTFile_read->GetListOfKeys();
        if (keyList) {
            for (int i = 0; i < keyList->GetEntries(); i++) {
                TObject* obj = keyList->At(i);
                if (obj) {
                    std::cout << "  Object " << i << ": " << obj->GetName()
                             << " (class: " << obj->ClassName() << ")" << std::endl;
                }
            }
        }

        // Processing and plotting from histograms
        for (auto nus : nu_weights) {
            std::string nu_str = periods_to_hyphens(str_round(nus.first, 2)
                                 + "_" + str_round(nus.second, 2));

            TH3D* hist3d = (TH3D*) ROOTFile_read->Get(nu_str.c_str());

            // If the specified hist is not found
            if (!hist3d) {
                std::cerr << "Histogram " << nu_str << " not found!" << std::endl;

                // Try alternative names that might exist
                std::vector<std::string> alt_names = {
                    nu_str + ";1",  // ROOT sometimes appends cycle numbers
                    nu_str + ";2"
                };

                for (const auto& alt_name : alt_names) {
                    std::cout << "\tTrying alternative name: " << alt_name << std::endl;
                    hist3d = (TH3D*) ROOTFile_read->Get(alt_name.c_str());
                    if (hist3d) {
                        std::cout << "Found histogram with name: " << alt_name << std::endl;
                        break;
                    }
                }

                if (!hist3d) {
                    std::cerr << "\tHistogram not found!" << std::endl;
                    continue;
                }
            }

            std::cout << "Creating plots for weights (" << nus.first
                      << ", " << nus.second << ")..." << std::endl;

            // Create R1-R2 projection
            makeR1R2Projection(hist3d, nu_str, minbin, maxbin,
                               50, 110, 30);

            // Create multiple R2-Phi projections
            makeR2PhiProjections(hist3d, nu_str, 6);

            // Create individual polar plots for specific R1 bins
            int nbins_r1 = hist3d->GetNbinsX();

            for (int r1_bin : special_r1_bins(nbins_r1)) {
                if (r1_bin > 0 && r1_bin <= nbins_r1) {
                    double r1_value = hist3d->GetXaxis()->GetBinCenter(r1_bin);
                    std::string r1_desc = "R_{1} = " + std::to_string(std::pow(10, r1_value));
                    makePolarR2PhiPlot(hist3d, nu_str, r1_bin, r1_desc);
                }
            }
        }

        ROOTFile_read->Close();
        delete ROOTFile_read;
        std::cout << "All plots saved to `output/new_enc_figures` "
                  << " directory." << std::endl;
        return 0;
    }

    if (!recreate_hists)
        std::cout << "File not found." << std::endl;


    // ---------------------------------
    // =====================================
    // Command line setup
    // =====================================
    // ---------------------------------
    // Ensuring valid command line inputs
    if (checkPythiaInputs(argc, argv) == 1) return 1;

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Basic Pythia Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // 50k e+ e=:=> hadrons events, by default
    const int         n_events      = cmdln_int("n_events",
                                          argc, argv,
                                          _NEVENTS_DEFAULT);
    const int         pid_1         = cmdln_int("pid_1", argc, argv,
                                          _PID_1_DEFAULT);
    const int         pid_2         = cmdln_int("pid_2", argc, argv,
                                          _PID_2_DEFAULT);
    const std::string outstate_str  = cmdln_string("outstate",
                                          argc, argv,
                                          _OUTSTATE_DEFAULT);


    const bool is_proton_collision = (pid_1 == 2212 and
                                      pid_2 == 2212);


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Jet Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const double              jet_rad    = cmdln_double("jet_rad",
                                             argc, argv,
                                             is_proton_collision
                                             ? CMS_R_JET
                                         : 1000.);
    const std::string         jet_alg    = jetalgstr_cmdln(
                                              argc, argv,
                                              CMS_JET_ALG);
    const RecombinationScheme jet_recomb = jetrecomb_cmdln(
                                              argc, argv);

    // Number of inclusive jets
    const int n_exclusive_jets           = cmdln_int(
                                              "n_exclusive_jets",
                                              argc, argv, -1);
    // i.e. max number of jets per event to include in analysis
    // (Ordered by energy, e.g. 1 = leading jet. -1 = all jets)
    // (Default is -1, i.e. fully inclusive)
    // (does not override pt_min/pt_max options, below:)

    const double pt_min  = cmdln_double("pt_min", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_PT_MIN
                                 : _PTMIN_DEFAULT);
    const double pt_max  = cmdln_double("pt_max", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_PT_MAX
                                 : _PTMAX_DEFAULT);

    // Require |eta| < eta_cut, but only for proton-proton collisions
    const double eta_cut = cmdln_double("eta_cut",
                                 argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? CMS_ETA_CUT
                                 : -1.0);


    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // ENC Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Whether to include contact terms in the computation
    const bool contact_terms = cmdln_bool("contact_terms",
                                          argc, argv,
                                          true);

    // Use deltaR rather than real-space opening angle by default
    const bool use_deltaR = cmdln_bool("use_deltaR", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? true
                                 : false);

    // Use pT rather than energy by default
    const bool use_pt     = cmdln_bool("use_pt", argc, argv,
                                 // default depends on collision
                                 is_proton_collision ? true
                                 : false);

    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    // Input Settings
    // =:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=:=
    const bool use_opendata = cmdln_bool("use_opendata", argc, argv,
                                         true);
    // Exclude neutrals
    const bool charged_only = cmdln_bool("charged_only",
                                         argc, argv, false);

    // Momentum smearing
    const bool smear_momenta = cmdln_bool("smear_momenta",
                                          argc, argv, false);

    double photon_smear_factor  = 0,
           charged_smear_factor = 0,
           neutral_smear_factor = 0;

    // Ghosts
    const bool add_ghosts    = cmdln_bool("add_uniform_ghosts",
                                          argc, argv, false);
    const double mean_ghost_pt = cmdln_double("mean_ghost_pt",
                                              argc, argv, 1.0,
                                              false);

    // Processing
    if (charged_only)
        std::cout << "Charged particles only." << std::endl;
    if (smear_momenta) {
        std::cout << "Smearing momenta roughly commensurate w/CMS "
                  << "(2402.13864)." << std::endl;

        photon_smear_factor = CMS_PHOTON_SMEAR_FACTOR;
        charged_smear_factor = CMS_CHARGED_SMEAR_FACTOR;
        neutral_smear_factor = CMS_NEUTRAL_SMEAR_FACTOR;
    }
    if (add_ghosts) {
        std::cout << "Adding a grid of nearly uniform ghosts with "
                  << "<pt>=" << mean_ghost_pt << " GeV."
                  << std::endl;
    }

    // Validating input options
    if (use_opendata && charged_only) {
        throw std::invalid_argument("Cannot do ''charged_only'' "
               "analysis with CMS open data: "
               "Particle IDs are not stored in the local dataset.");
    }
    if (use_opendata && smear_momenta) {
        throw std::invalid_argument("Cannot smear CMS open data: "
               "Particle IDs are not stored in the local dataset.");
    }
    if (use_opendata && add_ghosts) {
        throw std::invalid_argument("Adding uniform ghosts to "
               "CMS open data is not yet supported.");
    }


    // =====================================
    // Output Setup
    // =====================================
    // Set up histograms
    std::vector<TH3D*> enc_hists;
    enc_hists.clear();


    // Create ROOT file BEFORE creating histograms
    TFile* ROOTFile = TFile::Open(filename, "RECREATE");
    if (!ROOTFile || ROOTFile->IsZombie()) {
        std::cerr << "Error: Cannot create ROOT file " << filename << std::endl;
        return 1;
    }

    // Now create histograms with the file as current directory
    ROOTFile->cd(); // Make sure we're in the right directory

    for (auto nus : nu_weights) {
        std::string nu_str = periods_to_hyphens(str_round(nus.first, 2)
                             + "_" + str_round(nus.second, 2));

        TH3D* hist = new TH3D(nu_str.c_str(),
                              "RE3C in R1, R2/R1, phi coordinates",
                              nbins, minbin, maxbin,
                              nbins, bin2_min, bin2_max,
                              nphibins, -PI, PI);
        hist->SetName(nu_str.c_str());
        hist->SetDirectory(ROOTFile); // Explicitly associate w/file
        enc_hists.push_back(hist);
    }

    // =====================================
    // Event Generation Setup
    // =====================================
    // Usual output stream (std::cout)
    std::streambuf *old = std::cout.rdbuf();

    // ---------------------------------
    // Pythia
    // ---------------------------------
    // Declarations (muting Pythia banner)
    std::stringstream pythiastream; pythiastream.str("");
    if (verbose < 3)
        // Muting Pythia banner
        std::cout.rdbuf(pythiastream.rdbuf());

    Pythia8::Pythia pythia;  // Declaring Pythia8

    std::cout.rdbuf(old);    // Restore std::cout
    if (not use_opendata) {
        std::cout << "Setting up pythia" << std::endl;
        // Setting up pythia based on command line arguments
        setup_pythia_cmdln(pythia, argc, argv);
    }

    // ---------------------------------
    // FastJet
    // ---------------------------------
    const JetDefinition jet_def = process_JetDef(jet_alg, jet_rad,
                                                 jet_recomb);

    // ---------------------------------
    // CMS Open Data
    // ---------------------------------
    od::EventReader cms_jet_reader(od::cms_jets_file);

    // ---------------------------------
    // =====================================
    // Analyzing events
    // =====================================
    // ---------------------------------

    // Initializing total number of jets,
    //   summed over all events
    //   (used to normalize the histogram)
    int njets_tot = 0;

    // Initializing particles, good_jets, sorted angles and weights
    std::vector<PseudoJet> particles;
    std::vector<PseudoJet> all_jets;
    std::vector<PseudoJet> good_jets;
    std::vector<std::pair<double, PseudoJet>> sorted_angs_parts;

    bool passes_cuts;

    // Reserving memory
    particles.reserve(150);
    all_jets.reserve(20);
    good_jets.reserve(5);
    sorted_angs_parts.reserve(50);

    // =====================================
    // Looping over events
    // =====================================
    for (int iev = 0; iev < n_events; ++iev) {
        progressbar(static_cast<double>(iev+1)/
                    double(n_events));

        // -#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-
        // Jet finding (with cuts)
        // -#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-
        good_jets.clear();
        std::unique_ptr<ClusterSequence> cluster_seq_ptr = nullptr;

        // -----------------------------------------
        // CMS Open Data (gives jets from the start)
        // -----------------------------------------
        if (use_opendata) {
            PseudoJet jet;
            cms_jet_reader.read_jet(jet);
            good_jets.emplace_back(std::move(jet));
        } else {
        // -----------------------------------------
        // If using Pythia, find jets manually
        // -----------------------------------------
            // Considering next event, if valid
            if(!pythia.next()) continue;

            // Initializing particles for this event
            particles.clear();
            particles = get_particles_pythia(pythia.event,
                    photon_smear_factor, charged_smear_factor,
                    neutral_smear_factor);
            if (add_ghosts) {
                particles = add_uniform_ghosts(particles,
                                               mean_ghost_pt);
            }

            // Initializing jets
            if (iev == 0) {  // Muting FastJet banner
                std::stringstream fastjetstream;
                fastjetstream.str("");
                // Starting fastjet; redirect output
                std::cout.rdbuf(fastjetstream.rdbuf());
            }


            cluster_seq_ptr = std::make_unique
                <ClusterSequence>(particles, jet_def);

            if (iev == 0) {
                std::cout.rdbuf(old);  // Restore std::cout
            }

            // ---------------------------------
            // Jet finding (with cuts)
            // ---------------------------------
            if (jet_rad < 1000) {
                // If given a generic value of R,
                // cluster the event with the given jet definition
                all_jets = sorted_by_pt(
                        cluster_seq_ptr->inclusive_jets(pt_min));
            } else {
                // If we are given the maximum possible value of R,
                // use the whole event as a single "jet"
                PseudoJet full_event;
                for (auto part : particles)
                    if (part.modp() > 0)
                        full_event = join(full_event, part);

                all_jets.push_back(std::move(full_event));
            }

            // Getting all jets which satisfy other requirements
            for (size_t i = 0; i < all_jets.size()
                               &&
                // Only working up to the Nth jet if doing exclusive analysis
                     (n_exclusive_jets <= 0
                      ||
                      i < static_cast<size_t>(n_exclusive_jets));
             ++i) {
                const PseudoJet& jet = all_jets[i];
                passes_cuts = false;

                // Getting jets that satisfy certain criteria
                if (is_proton_collision) {
                    // For pp, ensuring pt_min < pt < pt_max
                    // and |eta| < eta_cut   (or no eta_cut given)
                    if (pt_min <= jet.pt() and jet.pt() <= pt_max
                            and (abs(jet.eta()) <= eta_cut
                                or eta_cut < 0)) {
                        passes_cuts = true;
                    }
                } else {
                    // For other collisions, ensuring E_min < E < E_max
                    // (for now, keeping confusing notation with, e.g.,
                    //    E_min represented by `pt_min` below)
                    if (pt_min <= jet.E() and jet.E() <= pt_max) {
                        passes_cuts = true;
                    }
                }

                // If we have a jet that passes cuts
                if (passes_cuts) {
                    // If we only want charged, remove neutrals
                    if (charged_only) {
                        good_jets.push_back(
                                create_charged_jet(jet));
                    } else {
                        good_jets.push_back(jet);
                    }
                }
            }

            all_jets.clear();
        }

        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        // Loop on jets
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
        for (auto jet : good_jets) {
        try {
            // Counting total num_jets across events
            ++njets_tot;

            // Storing jet constituents
            const std::vector<PseudoJet>& constituents = jet.constituents();
            double weight_tot = 0;
            for (const auto& particle : constituents) {
                weight_tot += use_pt ? particle.pt() : particle.e();
            }

            // ---------------------------------
            // Loop on "special" particle
            for (const auto& part_sp : constituents) {
                // Energy-weighting factor for "special" particle
                double weight_sp = use_pt ?
                        part_sp.pt() / weight_tot :
                        part_sp.e() / weight_tot;
                // Initializing sum of weights
                // within an angle of 1st particle
                double sum_weight1 = weight_sp;
                // At particle j within the loop below,
                // sum_weight1 = \sum_{thetak < thetaj} weight1_k

                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                // Preparing contact terms:
                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                if (contact_terms) {
                    for (size_t inu = 0; inu < nu_weights.size(); ++inu) {
                        weight_t nus = nu_weights[inu];
                        double nu1   = nus.first;
                        double nu2   = nus.second;

                        enc_hists[inu]->Fill(0.0, 0.0, 0.0,
                                    std::pow(weight_sp, 1+nu1+nu2));
                    }
                }
                // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-

                // (Sorting:
                //   * [theta1]: angle relative to special particle
                //   * [weight1]: either E2/Ejet or pt2/ptjet
                //  by theta1)
                sorted_angs_parts.clear();

                // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                // Loop on particles
                for (const auto& part1 : constituents) {
                    // Angle relative to "special" particle
                    double theta1 = use_deltaR ?
                            part_sp.delta_R(part1) :
                            fastjet::theta(part_sp, part1);

                    sorted_angs_parts.emplace_back(theta1, part1);
                } // end second particle loop
                // Sorting angles/weights by angle as promised :)
                std::sort(sorted_angs_parts.begin(),
                          sorted_angs_parts.end(),
                          [](auto& left, auto& right) {
                              return left.first < right.first;
                         });
                // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-

                // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
                // Loop on first non-special particle
                // (calculating change in cumulative E^nu C)
                for (size_t jpart=1; jpart<sorted_angs_parts.size(); ++jpart) {
                    // Properties of 1st particle
                    double theta1    = sorted_angs_parts[jpart].first;
                    PseudoJet& part1 = sorted_angs_parts[jpart].second;
                    double weight1 = use_pt ?
                            part1.pt() / weight_tot :
                            part1.e() / weight_tot;

                    // Initializing the sum of weights
                    // within an angle of the 2nd non-special particle
                    std::vector<double> sum_weight2(nphibins);

                    sum_weight2[phizerobin] += weight_sp;

                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                    // Preparing contact terms:
                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-
                    if (contact_terms) {
                        // Looping on _E^nu C_ weights [`nu's]
                        for (size_t inu = 0; inu < nu_weights.size(); ++inu) {
                            weight_t nus = nu_weights[inu];
                            double nu1   = nus.first;
                            double nu2   = nus.second;

                            // part2 = part_sp != part_1
                            enc_hists[inu]->Fill(log10(theta1), 0.0, 0.0,
                                        2*std::pow(weight_sp, 1+nu2)
                                        *std::pow(weight1, nu1));

                            // part2 = part1 != part_sp
                            enc_hists[inu]->Fill(log10(theta1), 1, phizerobin,
                                            std::pow(weight_sp, 1)
                                            *std::pow(weight1, nu1+nu2));
                        }
                    }
                    // -|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-|-

                    // -----------------------------------
                    // Loop on second non-special particle
                    for (size_t kpart=1; kpart<jpart; ++kpart) {
                        // Getting 2nd particle
                        double theta2    = sorted_angs_parts[kpart].first;
                        PseudoJet& part2 = sorted_angs_parts[kpart].second;
                        double weight2 = use_pt ?
                                part2.pt() / weight_tot :
                                part2.e() / weight_tot;
                        double theta2_over_theta1 =
                            theta1 == 0 ? 0 : theta2/theta1;

                        // Getting azimuthal angle
                        // (angle from part1 to part_sp to part2
                        //  in rapidity-azimuth plane)
                        double phi = enc_azimuth(
                                part1, part_sp, part2);

                        // Calculating the phi bin
                        int binphi = bin_position(phi, -PI, PI,
                                              nphibins, "linear",
                                              false, false);

                        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                        // Looping on _E^nu C_ weights [`nu's]
                        for (size_t inu = 0;
                                inu < nu_weights.size(); ++inu) {
                            // Preparing properties of the correlator
                            weight_t nus = nu_weights[inu];
                            double nu1   = nus.first;
                            double nu2   = nus.second;

                            // *:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*
                            // Filling the histogram
                            // *:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*:*
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
                            double perm = 2;
                            // imagine a triangle with theta_j < theta_i;
                            // need to count twice to get the full
                            // sum on all pairs (see also contact term)

                            double hist_weight = weight_sp *
                                        delta_weight1 *
                                        delta_weight2;

                            enc_hists[inu]->Fill(log10(theta1), theta2_over_theta1,
                                                 phi, perm*hist_weight);
                        } // end EEC weight [nu] loop
                        // -:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-:-
                        // Preparing for the next particle in the loop!
                        sum_weight2[binphi] += weight2;
                    } // end calculation/2nd particle loop
                    // -----------------------------------

                    // Preparing for the particle in the loop!
                    sum_weight1 += weight1;
                } // end 1st particle loop
                // -#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-#-

            // ---------------------------------
            } // end "special particle" loop
            // ---------------------------------

            // ---------------------------------
            // Finished with this jet!
            // ---------------------------------
        } catch (const fastjet::Error& ex) {
            // ending try statement (sometimes I find empty jets)
            std::cerr << "Warning: FastJet: " << ex.message()
                      << std::endl;
            continue;
        }
        } // end loop on jets
        // -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-
    } // end event loop
    // =====================================


    // ===================================
    // Writing histograms to output files
    // ===================================
    std::cout << std::endl << "Writing histograms." << std::endl;

    ROOTFile->cd();
    for (size_t inu = 0; inu < nu_weights.size(); ++inu) {
        // Log-normalizing histograms
        enc_hists[inu]->Scale(1.0/njets_tot, "width");
        /* BinLogX3D(enc_hists[inu]); */


        // Write histogram to ROOT file
        enc_hists[inu]->Write("", TObject::kOverwrite);
    }

    // Writing ROOT output file itself
    ROOTFile->Write();
    ROOTFile->ls();  // printing contents of ROOT file


    // ===================================
    // Writing histograms to output files
    // ===================================
    // Processing and plotting from histograms
    for (auto nus : nu_weights) {
        std::string nu_str = periods_to_hyphens(str_round(nus.first, 2)
                             + "_" + str_round(nus.second, 2));

        TH3D* hist3d = (TH3D*) ROOTFile->Get(nu_str.c_str());

        // If the specified hist is not found
        if (!hist3d) {
            std::cerr << "Histogram " << nu_str << " not found!" << std::endl;

            // Try alternative names that might exist
            std::vector<std::string> alt_names = {
                nu_str + ";1",  // ROOT sometimes appends cycle numbers
                nu_str + ";2"
            };

            for (const auto& alt_name : alt_names) {
                std::cout << "\tTrying alternative name: " << alt_name << std::endl;
                hist3d = (TH3D*) ROOTFile->Get(alt_name.c_str());
                if (hist3d) {
                    std::cout << "Found histogram with name: " << alt_name << std::endl;
                    break;
                }
            }

            if (!hist3d) {
                std::cerr << "\tHistogram not found!" << std::endl;
                continue;
            }
        }

        std::cout << "Creating plots for weights (" << nus.first
                  << ", " << nus.second << ")..." << std::endl;

        // Create R1-R2 projection
        makeR1R2Projection(hist3d, nu_str, minbin, maxbin,
                           50, 110, 30);

        // Create multiple R2-Phi projections
        makeR2PhiProjections(hist3d, nu_str, 6);

        // Create individual polar plots for specific R1 bins
        int nbins_r1 = hist3d->GetNbinsX();

        for (int r1_bin : special_r1_bins(nbins_r1)) {
            if (r1_bin > 0 && r1_bin <= nbins_r1) {
                double r1_value = hist3d->GetXaxis()->GetBinCenter(r1_bin);
                std::string r1_desc = "R_{1} = " + std::to_string(std::pow(10, r1_value));
                makePolarR2PhiPlot(hist3d, nu_str, r1_bin, r1_desc);
            }
        }
    }


    // ---------------------------------
    // =====================================
    // Verifying successful run
    // =====================================
    // ---------------------------------
    ROOTFile->Close();

    if (verbose >= 0) {
        std::cout << "\nComplete!\n";
        auto stop = high_resolution_clock::now();
        auto duration = duration_cast<microseconds>(stop-start);
        std::cout << "Analyzed and saved data from "
                  << std::to_string(n_events)
                  << " events in "
                  << std::to_string(float(duration.count())/std::pow(10, 6))
                  << " seconds.\n";
    }


    return 0;
}
