/**
 * @file    cmdln.h
 *
 * @brief   A command line utility header file for pythia event generation.
 */
#ifndef CMDLN
#define CMDLN

#include <string>
#include <string.h>

#include "cmdln_defaults.h"

// =====================================
// Command Line Basics
// =====================================
// String Options
std::string cmdln_string(std::string opt, int argc, char* argv[],
                         std::string default_val="", bool required=false);

// Integer Options
int cmdln_int(std::string opt, int argc, char* argv[],
              int default_val=0, bool required=false);

// Double/Float Options
double cmdln_double(std::string opt, int argc, char* argv[],
                    double default_val=0, bool required=false);

// Boolean Options
bool cmdln_bool(std::string opt, int argc, char* argv[],
                bool default_bool=true, bool required=false);

#endif
