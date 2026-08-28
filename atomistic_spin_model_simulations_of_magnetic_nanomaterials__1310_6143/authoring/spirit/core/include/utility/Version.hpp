#pragma once
#ifndef SPIRIT_CORE_UTILITY_VERSION_HPP
#define SPIRIT_CORE_UTILITY_VERSION_HPP

#include <string>

namespace Utility
{

const int version_major = 2;
const int version_minor = 2;
const int version_patch = 0;

const std::string version          = "2.2.0";
const std::string version_revision = "e82250d3b1441";
const std::string version_full     = "2.2.0 (e82250d3b1441)";

const std::string compiler         = "GNU";
const std::string compiler_version = "11.4.0";
const std::string compiler_full    = "GNU (11.4.0)";

const std::string scalartype = "double";

const std::string pinning = "ON";
const std::string defects = "OFF";

const std::string cuda    = "OFF";
const std::string openmp  = "OFF";
const std::string threads = "OFF";

const std::string fftw = "OFF";

} // namespace Utility

#endif
