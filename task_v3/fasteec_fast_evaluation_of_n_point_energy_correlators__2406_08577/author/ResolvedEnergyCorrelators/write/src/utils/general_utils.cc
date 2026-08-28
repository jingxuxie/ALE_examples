/**
 * @file    general_utils.cc
 *
 * @brief   A set of miscellaneous utilities for C++.
 *
 * @author: Samuel Alipour-fard
 * */

// ---------------------------------
// Basic imports
// ---------------------------------
#include <cstring>
#include <cmath>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <iomanip>
#include <algorithm>
#include <cassert>
#include <limits>

#include <iostream>  // for DEBUG

#include "../../include/general_utils.h"

// =====================================
// Utility functions
// =====================================

// ---------------------------------
// General utilities
// ---------------------------------



/**
* @brief:   Gives a boolean value associated with a string.
*
* @param: boolstr   The input string.
*
* @return: bool     The boolean value associated with
*                   the string.
*/
bool str_to_bool(const std::string boolstr) {
    if (str_eq(boolstr, "true") or str_eq(boolstr, "True")
     or str_eq(boolstr, "Yes") or str_eq(boolstr, "Y")
     or str_eq(boolstr, "yes") or str_eq(boolstr, "y")
     or str_eq(boolstr, "On") or str_eq(boolstr, "on")
     or str_eq(boolstr, "1"))
        return true;
    if (str_eq(boolstr, "false") or str_eq(boolstr, "False")
     or str_eq(boolstr, "No") or str_eq(boolstr, "N")
     or str_eq(boolstr, "no") or str_eq(boolstr, "n")
     or str_eq(boolstr, "Off") or str_eq(boolstr, "off")
     or str_eq(boolstr, "0"))
        return false;

    throw std::invalid_argument(
            "Could not cast " + boolstr + " as a boolean.\n"
          + "Strings like 'true', 'yes', 'on', '1', etc. "
          + " should be cast to `true`, while their negations"
          + " will be cast to `false`.");
}


/**
* @brief:   Rounds a number to the specified number of
*           decimal places, returning a string.
*
* @param: x         A double we wish to round.
* @param: num_dec   The number of decimal places to
*                   which we would like to round.
*
* @return: std::string  The rounded string.
*/
std::string str_round(double x, const int num_dec) {
    std::ostringstream ss;
    ss << std::fixed << std::setprecision(num_dec);

    if (fabs(x) < pow(10, -1*num_dec)) x = 0;
    ss << x;
    return ss.str();
}


/**
* @brief: C++ equivalent of numpy.arange function.
*         See https://stackoverflow.com/a/21217377
*
* @param: start, stop, step   Start, stop, and step size.
*
* @return: vector             std::vector associated with
*                             the arange.
*/
template<typename T>
std::vector<T> arange(const T start, const T stop, const T step /*= 1*/) {
    std::vector<T> values;
    for (T value = start; value < stop; value += step)
        values.push_back(value);
    return values;
}


/**
* @brief: Concatenates two vectors v1 and v2.
*         See https://stackoverflow.com/a/3154256
*
* @param: a, b          vectors
*
* @return: vector       Concatenated vector.
*/
std::vector<int> concat_ints(const std::vector<int> a, const std::vector<int> b){
    std::vector<int> ab = a;
    ab.insert(ab.end(), b.begin(), b.end());
    return ab;
}

// ---------------------------------
// Histogram Utilities
// ---------------------------------
/**
* @brief: Returns the bin edges of a histogram.
*
* @param: minbin     The leftmost bin edge
* @param: maxbin     The rightmost bin edge
* @param: nbins      The number of bins
* @param: underflow   Whether to use an underflow bin
* @param: overflow    Whether to use an overflow bin
*
* @return: std::vector<double>
*                     The bin edges
*
* Note that in a logarithmic bin_scheme, this will return the
* logarithm of the true bin edge values.
*/
std::vector<double> get_bin_edges(const double minbin,
                                  const double maxbin,
                                  const int nbins,
                                  const bool underflow,
                                  const bool overflow){
    // ==================================
    // Bin Setup
    // ==================================
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Outflow bins
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Number of finite (non-outflow) bins
    int nbins_finite = nbins;
    // i.e. If using outflow bins,
    // first "finite" bin has index 1
    // and the number of finite bins is nbins-2
    if (underflow)
        nbins_finite -= 1;
    if (overflow)
        nbins_finite -= 1;

    // ==================================
    // Getting bin edges
    // ==================================
    std::vector<double> bin_edges;

    // -------------------------------
    // Setting up underflow bin
    // -------------------------------
    if (underflow) {
        double underflow_val = -1.*std::numeric_limits<double>::infinity();
        bin_edges.push_back(underflow_val);
    }

    // -------------------------------
    // Setting up finite bins
    // -------------------------------
    for (int ibin=0; ibin < nbins_finite; ibin++) {
        double bin_edge   = minbin + (maxbin-minbin)*ibin/(nbins_finite);
        bin_edges.push_back(bin_edge);
    }
    // Final finite bin edge
    bin_edges.push_back(maxbin);

    // -------------------------------
    // Setting up overflow bin
    // -------------------------------
    if (overflow) {
        double overflow_val = std::numeric_limits<double>::infinity();
        bin_edges.push_back(overflow_val);
    }

    assert(int(bin_edges.size()) == nbins+1);
    return bin_edges;
}


/**
* @brief: Returns the bin centers of a histogram.
*
* @param: minbin     The leftmost bin edge
* @param: maxbin     The rightmost bin edge
* @param: nbins      The number of bins
* @param: underflow   Whether to use an underflow bin
* @param: overflow    Whether to use an overflow bin
*
* @return: std::vector<double>
*                     The bin centers
*
* Note that in a logarithmic bin_scheme, this will return the
* logarithm of the true bin edge values.
*/
std::vector<double> get_bin_centers(const double minbin,
                                    const double maxbin,
                                    const int nbins,
                                    const bool underflow,
                                    const bool overflow){
    // ==================================
    // Bin Setup
    // ==================================
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Outflow bins
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Number of finite (non-outflow) bins
    int nbins_finite = nbins;
    // i.e. If using outflow bins,
    // first "finite" bin has index 1
    // and the number of finite bins is nbins-2
    if (underflow)
        nbins_finite -= 1;
    if (overflow)
        nbins_finite -= 1;

    // ==================================
    // Getting bin centers
    // ==================================
    std::vector<double> bin_centers;

    // -------------------------------
    // Setting up underflow bin
    // -------------------------------
    if (underflow) {
        double underflow_val = -1.*std::numeric_limits<double>::infinity();
        bin_centers.push_back(underflow_val);
    }

    // -------------------------------
    // Setting up finite bins
    // -------------------------------
    for (int ibin=0; ibin < nbins_finite; ibin++) {
        double bin_edge   = minbin + (maxbin-minbin)*(ibin+1./2.)/(nbins_finite);
        bin_centers.push_back(bin_edge);
    }

    // -------------------------------
    // Setting up overflow bin
    // -------------------------------
    if (overflow) {
        double overflow_val = std::numeric_limits<double>::infinity();
        bin_centers.push_back(overflow_val);
    }

    assert(int(bin_centers.size()) == nbins);
    return bin_centers;
}


/**
* @brief: Returns the bin position of a given
*         value in a histogram.
*
* @param: val        The given value
* @param: minbin     The leftmost bin edge
* @param: maxbin     The rightmost bin edge
* @param: nbins      The number of bins
* @param: bin_schem  The scheme for bin spacing
*                    ('linear'/'lin' for linear spacing,
*                     'logarithmic'/'log' for log spacing)
* @param: outflow    Whether to use underflow and overflow bins
*                    (supports using both or neither, not one
*                     of the two)
*
* @return: int       The index of the bin containing val
*/
int bin_position(const double val,
                 const double minbin,
                 const double maxbin,
                 const int nbins,
                 const std::string bin_scheme,
                 const bool underflow,
                 const bool overflow){
    // ==================================
    // Bin Setup
    // ==================================
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Bin spacing
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Asserting valid bin spacing scheme
    const bool linear_bins = (bin_scheme == "linear" or bin_scheme == "lin");
    assert (linear_bins or bin_scheme == "logarithmic" or bin_scheme == "log");

    // Getting actual bin edges to shorten code
    const double minbin_val = linear_bins ? minbin : pow(10, minbin);
    const double maxbin_val = linear_bins ? maxbin : pow(10, maxbin);

    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Outflow bins
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // Effective bin positions for "finite" bins
    const int base_bin  = underflow ? 1: 0;
    int nbins_finite = nbins;
    // i.e. If using outflow bins,
    // first "finite" bin has index 1
    // and the number of finite bins is nbins-2

    // ==================================
    // Getting bin index for given value
    // ==================================
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // If using outflow bins
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    if (underflow) {
        if (val < minbin_val)
            return 0;
        nbins_finite -= 1;
    } else if (val < minbin_val) {
        throw std::underflow_error(
                "Invalid val "+std::to_string(val)+" is smaller than "
                "minimum bin edge "+std::to_string(minbin_val)+"."
            );
    }

    // Overflow
    if (overflow) {
        if (maxbin_val < val)
            return nbins-1;
        nbins_finite -= 1;
    }
    // No overflow
    else if (maxbin_val == val) {
        return nbins - 1;
    }
    else if (maxbin_val < val) {
        throw std::overflow_error(
                "Invalid val "+std::to_string(val)+" is larger than "
                "maximum bin edge "+std::to_string(maxbin_val)+"."
            );
    }
    // We are strict, in that if we don't use
    // under(over)flow bins, then we require
    // that all values are within the given
    // bin boundaries.

    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // If using lin-spaced bins
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    if (linear_bins)
        return std::trunc(base_bin + nbins_finite*
                                     (val-minbin)/
                                     (maxbin-minbin));
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    // If using log-spaced bins
    // -*-*-*-*-*-*-*-*-*-*-*-*-*-
    else
        return std::trunc(base_bin + nbins_finite*
                                    (log10(val)-minbin)/
                                    (maxbin-minbin));
}


// ---------------------------------
// Command Line Utilities
// ---------------------------------
/**
* @brief:   Parses command line arguments.
*          See https://stackoverflow.com/a/39883532
*
* @param: arguments   A vector of strings describing the command line
*                     arguments.
*
* @return: std::vector<char*>      An appropriate `argv` for the
*                                  command line arguments.
*/
std::vector<char*> strings_to_argv(std::vector<std::string> arguments) {
    std::vector<char*> argv;

    for (const auto& arg : arguments)
        argv.push_back((char*)arg.data());
    argv.push_back(nullptr);

    return argv;
}


// ---------------------------------
// Progress Bar
// ---------------------------------
void progressbar(double percent) {
    int complete = floor(PBWIDTH * percent);
    std::cout <<
        "\r[" <<         //'\r' aka carriage return
                         // moves printer's cursor back at the beginning of the current line
        std::string(complete, PBCHAR) <<        // filled
        std::string(PBWIDTH-complete, EMCHAR) <<  // empty
        "] " <<
        std::setprecision(3) << 100 * percent << "%" <<    // percent
        std::flush;
}
