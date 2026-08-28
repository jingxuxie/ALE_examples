#ifndef ENC_HEADER
#define ENC_HEADER

#include <string>
#include <vector>
#include <fstream>
#include <sstream>

#include "jet_utils.h"

extern const std::string enc_banner;

void write_enc_header(std::string filename,
                           int argc, char* argv[],
                           std::vector<double> weight,
                           bool python_format = true);

#endif
