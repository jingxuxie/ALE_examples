/**
 * @file    cmdln.cc
 *
 * @brief   A command line utility file.
 *
 * @author: Samuel Alipour-fard
 */
#include <string>
#include <string.h>
#include <iostream>

// Local imports:
#include "../../include/general_utils.h"
#include "../../include/cmdln.h"


// =====================================
// Format for command line reading
// =====================================
/**
* @brief: Set of functions that return arguments
*         from command line input.
*
* @param: opt               Name of the command line
*                           option.
*
* @param: argc/argv         Command line input.
*
* @param: default_val       Default return value.
*
* @param: required            Whether the argument
*                           should be required.
*
* @return: variable type    The desired argument
*                           given to the command line.
*/
// =====================================


// String Options
std::string cmdln_string(std::string opt,
                         int argc, char* argv[],
                         std::string default_val /* "" by default */,
                         bool required /* false by default */) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "--"+opt))
            return argv[iarg+1];
    }

    if (required)
        throw std::runtime_error("Unable to find command line "
                "argument --"+opt);

    return default_val;
}


// Integer Options
int cmdln_int(std::string opt,
                 int argc, char* argv[],
                 int default_val /* 0 by default */,
                 bool required /* false by default */) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "--"+opt))
            return atoi(argv[iarg+1]);
    }

    if (required)
        throw std::runtime_error("Unable to find command line "
                "argument --"+opt);

    return default_val;
}


// Double/Float Options
double cmdln_double(std::string opt,
                    int argc, char* argv[],
                    double default_val /* 0 by default */,
                    bool required /* false by default */) {
    for(int iarg=0;iarg<argc;iarg++) {
        if(str_eq(argv[iarg], "--"+opt))
            return atof(argv[iarg+1]);
    }

    if (required)
        throw std::runtime_error("Unable to find command line "
                "argument --"+opt);

    return default_val;
}

// Boolean Options
bool cmdln_bool(std::string opt,
                int argc, char* argv[],
                bool default_bool /* true by default */,
                bool required /* false by default */) {
    for(int iarg=0;iarg<argc;iarg++) {
        // If argument found
        if(str_eq(argv[iarg], "--"+opt)) {
            // if no value is given, assume true
            bool no_val = (iarg == argc-1);
            if (not(no_val))
                no_val = starts_with(argv[iarg+1], "--");
            if (no_val) {
                // (either required -> raise error)
                if (required)
                    throw std::runtime_error(
                            "Option --"+opt+" found in commandline " +
                            "input but not given with an explicit " +
                            "value (e.g. 0, y, 1, true).");
                // (or assume true)
                return true;
            }

            // else, return the given value
            return str_to_bool(argv[iarg+1]);
        }
    }

    if (required)
        throw std::runtime_error("Unable to find command line "
                "argument --"+opt);

    return default_bool;
}
