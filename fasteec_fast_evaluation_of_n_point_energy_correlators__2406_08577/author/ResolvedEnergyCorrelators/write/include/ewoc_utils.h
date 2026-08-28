#ifndef EWOC_HEADER
#define EWOC_HEADER

#include <string>
#include <string.h>
#include <iostream>

#include "cmdln.h"
#include "pythia_cmdln.h"

extern const std::string ewoc_banner;
extern const double _DEFAULT_WEIGHT;


void write_ewocfile_header(std::string filename,
                           int argc, char* argv[],
                           double jet_rad, double sub_rad,
                           bool python_format);
#endif
