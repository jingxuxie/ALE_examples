#include <iostream>
#include <cmath>
#include <vector>
#include <limits>

#include "../include/general_utils.h"


// =======================================
// Parameters for histogram tests
// =======================================
// log tests
double minbin_log     = -5;
double maxbin_log     = 2;
int nbins_finite_log  = 8;

std::vector<double> log_test_vals{
    pow(10, -6), pow(10, -5), pow(10, -4.6),
    pow(10, -4), pow(10, -3), pow(10, -2),
    pow(10, -1.6), pow(10, -1.4), pow(10, -0.5),
    pow(10, 1), pow(10, 1.12), pow(10, 1.2),
    pow(10, 1.9), pow(10, 2.0), pow(10, 3.0)
};
std::vector<std::string> log_test_str{
    "1e-6", "1e-5", "1e-4.6",
    "1e-4", "1e-3", "1e-2",
    "1e-1.6", "1e-1.4", "1e-0.5",
    "1e1", "1e1.12", "1e1.2",
    "1e1.9", "1e2.0", "1e3.0",
};

// lin tests
double minbin_lin    = 0;
double maxbin_lin    = 10;
int nbins_finite_lin = 10;
std::vector<double> lin_test_vals{
    -100, -1, -0.01, 0.01, 1.4, 2.5, 4.6,
    5, 8, 8.95, 9.5, 9.9, 10.0, 12.5, 100
};


// =======================================
// Histogram tests
// =======================================
void test_log_hist(bool underflow, bool overflow) {
    // Number of bins
    int nbins = nbins_finite_log;
    if (underflow) nbins += 1;
    if (overflow)  nbins += 1;

    // Getting bin edges and center
    std::vector<double> bin_edges = get_bin_edges(
            minbin_log, maxbin_log, nbins,
            underflow, overflow);
    std::vector<double> xs = get_bin_centers(
            minbin_log, maxbin_log, nbins,
            underflow, overflow);

    // Printing edges
    std::cout << "\tedges = ";
    for (unsigned int i=0; i < nbins; i++)
        std::cout << bin_edges[i] << "\t|"
                  << "(" << i << ")" << "|\t";
    std::cout << bin_edges[nbins];
    std::cout << std::endl;

    // Printing x values
    std::cout << "xs = ";
    for (auto x : xs)
        std::cout << x << "\t\t";
     std::cout << std::endl;

     // Looping over test values
     for (unsigned int i=0; i < log_test_vals.size(); i++) {
         try {
             int bin_pos = bin_position(log_test_vals[i],
                                  minbin_log, maxbin_log,
                                  nbins, "log",
                                  underflow, overflow);

             std::cout << "\tbin_position("
                       << log_test_str[i] << ") = "
                       << bin_pos << std::endl;
         } catch (std::underflow_error) {
            std::cout << "\t" << log_test_vals[i]
                      << " not accepted: underflow.\n";
         } catch (std::overflow_error) {
            std::cout << "\t" << log_test_vals[i]
                      << " not accepted: overflow.\n";
         }
     }
     std::cout << std::endl;
}


void test_lin_hist(bool underflow, bool overflow) {
    // Number of bins
    int nbins = nbins_finite_lin;
    if (underflow) nbins += 1;
    if (overflow)  nbins += 1;

    std::cout << nbins << std::endl;

    // Getting bin edges and center
    std::vector<double> bin_edges = get_bin_edges(
            minbin_lin, maxbin_lin, nbins,
            underflow, overflow);
    std::vector<double> xs = get_bin_centers(
            minbin_lin, maxbin_lin, nbins,
            underflow, overflow);

    // Printing edges
    std::cout << "\tedges = ";
    for (unsigned int i=0; i < nbins; i++)
        std::cout << bin_edges[i] << "\t|"
                  << "(" << i << ")" << "|\t";
    std::cout << bin_edges[nbins];
    std::cout << std::endl;

    // Printing x values
    std::cout << "xs = ";
    for (auto x : xs)
        std::cout << x << "\t\t";
     std::cout << std::endl;

     // Looping over test values
     for (unsigned int i=0; i < lin_test_vals.size(); i++) {
         try {
             int bin_pos = bin_position(lin_test_vals[i],
                                  minbin_lin, maxbin_lin,
                                  nbins, "lin",
                                  underflow, overflow);

             std::cout << "\tbin_position("
                       << lin_test_vals[i] << ") = "
                       << bin_pos << std::endl;
         } catch (std::underflow_error) {
            std::cout << "\t" << lin_test_vals[i]
                      << " not accepted: underflow.\n";
         } catch (std::overflow_error) {
            std::cout << "\t" << lin_test_vals[i]
                      << " not accepted: overflow.\n";
         }
     }
     std::cout << std::endl;
}


// =======================================
// Main
// =======================================
int main (int argc, char* argv[]) {
    std::cout <<
    "// ==================================\n"
    "// Testing logarithmic binning\n"
    "// ==================================\n";
    std::cout << std::endl;

    std::cout <<
    "// ----------------------------------\n"
    "// Testing without over/underflow\n"
    "// ----------------------------------\n";
    std::cout << std::endl;

    test_log_hist(false, false);

    std::cout <<
    "// ----------------------------------\n"
    "// Testing overflow and underflow\n"
    "// ----------------------------------\n";
    std::cout << std::endl;

    test_log_hist(true, true);

    std::cout <<
    "// ----------------------------------\n"
    "// Testing underflow (no overflow)\n"
    "// ----------------------------------\n";
    std::cout << std::endl;

    test_log_hist(true, false);

    std::cout <<
    "// ----------------------------------\n"
    "// Testing overflow (no underflow)\n"
    "// ----------------------------------\n";
    std::cout << std::endl;

    test_log_hist(false, true);


    std::cout << "\n\n\n"
    "// ==================================\n"
    "// Testing linear binning\n"
    "// ==================================\n";
    std::cout << std::endl;

    std::cout <<
    "// ----------------------------------\n"
    "// Testing without over/underflow\n"
    "// ----------------------------------\n";
    std::cout << std::endl;

    test_lin_hist(false, false);

    std::cout <<
    "// ----------------------------------\n"
    "// Testing overflow and underflow\n"
    "// ----------------------------------\n";
    std::cout << std::endl;

    test_lin_hist(true, true);

    std::cout <<
    "// ----------------------------------\n"
    "// Testing underflow (no overflow)\n"
    "// ----------------------------------\n";
    std::cout << std::endl;

    test_lin_hist(true, false);

    std::cout <<
    "// ----------------------------------\n"
    "// Testing overflow (no underflow)\n"
    "// ----------------------------------\n";
    std::cout << std::endl;

    test_lin_hist(false, true);
}
