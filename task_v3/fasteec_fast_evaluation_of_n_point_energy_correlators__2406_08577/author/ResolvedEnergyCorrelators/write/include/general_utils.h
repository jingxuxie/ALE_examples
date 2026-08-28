/**
 * @file    general_utils.h
 *
 * @brief   A utility header file for miscellaneous utilities in C++.
 * */
#ifndef GENERAL_UTILS
#define GENERAL_UTILS

// ---------------------------------
// Basic imports
// ---------------------------------
#include <cmath>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>


// =====================================
// Constants
// =====================================
# define PI 3.14159265358979323846  /* pi */
# define TWOPI 2*PI

// =====================================
// typedefs
// =====================================
typedef unsigned long size_t;


// =====================================
// Utility functions
// =====================================
// Inline functions
/**
 * @brief   Compute the mean of a vector of floats.
 *
 * @param   vec     The vector of floats.
 *
 * @return  The mean of the vector.
 * */
inline double vector_mean(std::vector<double> v) {
    double sum = 0;
    for (size_t i = 0; i < v.size(); i++) {
        sum += v[i];
    }
    return sum / v.size();
}

/**
 * @brief   Compute the standard deviation of a vector of floats.
 *
 * @param   vec     The vector of floats.
 *
 * @return  The standard deviation of the vector.
 * */
inline double vector_std(std::vector<double> v, double bias=-1) {
    double mean = vector_mean(v);
    double sum = 0;
    for (size_t i = 0; i < v.size(); i++) {
        sum += pow(v[i] - mean, 2);
    }
    return sqrt(sum / (v.size() + bias));
}

/**
 * @brief   Check if two strings are equal.
 *
 * @param   str_a   The first string.
 * @param   str_b   The second string.
 *
 * @return  True if the strings are equal, false otherwise.
 * */
inline bool str_eq(const std::string str_a, const std::string str_b){
    return (strcmp(str_a.c_str(), str_b.c_str()) == 0);
}


/**
* @brief:   Checks if one string (toCheck) starts with
*           another (prefix).
*
* @param: toCheck   String to check for a prefix
* @param: prefix    String prefix to look for in toCheck
*
* @return: bool     Whether toCheck starts with prefix
*/
inline bool starts_with(const std::string& toCheck, const std::string& prefix) {
    return toCheck.compare(0, prefix.length(), prefix) == 0;
}


/**
* @brief:   Removes a file extension from a string.
*
* @param: filename  The input string.
*
* @return: std::string  The truncated string.
*/
inline std::string remove_extension(std::string filename) {
    size_t lastindex = filename.find_last_of(".");
    std::string rawname = filename.substr(0, lastindex);
    return rawname;
}


/**
* @brief:   Replaces all periods in a string by hyphens.
*
* @param: str   The string to modify.
*
* @return: std::string      The modified string.
*/
inline std::string periods_to_hyphens(std::string str) {
    for (size_t i = 0; i < str.length(); ++i)
        if (str[i] == '.')
            str[i] = '-';
    return str;
}


// In general_utils.cc
bool str_to_bool(const std::string boolstr);
std::string str_round(double x, const int num_dec);
template<typename T>
std::vector<T> arange(const T start, const T stop, const T step = 1);
std::vector<int> concat_ints(const std::vector<int> a, const std::vector<int> b);


// ---------------------------------
// Histogram Utilities
// ---------------------------------
std::vector<double> get_bin_edges(const double minbin,
                                  const double maxbin,
                                  const int nbins,
                                  const bool underflow,
                                  const bool overflow);

std::vector<double> get_bin_centers(const double minbin,
                                    const double maxbin,
                                    const int nbins,
                                    const bool underflow,
                                    const bool overflow);

int bin_position(const double val,
                 const double minbin,
                 const double maxbin,
                 const int nbins,
                 const std::string bin_scheme,
                 const bool underflow,
                 const bool overflow);


// ---------------------------------
// Command Line Utilities
// ---------------------------------
std::vector<char*> strings_to_argv(std::vector<std::string> arguments);

// ---------------------------------
// Progress Bar
// ---------------------------------
#define S_(x) #x
#define S(x) S_(x)
#define PBWIDTH 64
#define PBCHAR '#'
#define EMCHAR ' '
void progressbar(double percent);

#endif
