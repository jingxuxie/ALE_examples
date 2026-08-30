//===------ defines.h - Application-level (global) definitions. -----------===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// This file contains definitions (constants, functions etcetera) that should
/// be accessible on an application level (global level).
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_DEFINES_H_
#define CONGA_DEFINES_H_

#include <array>
#include <cmath>

namespace conga {
// Convenient 2D vector definition.
template <typename T> using vector2d = std::array<T, 2>;

namespace constants {
// Margin around superconducting grain in simulation space, in pixels.
const int GRAIN_SIZE_MARGIN = 3;

// Size of coordinate system where grain is allowed to be, as seen by the user:
// [-MAXIMUM_COORDINATE, +MAXIMUM_COORDINATE], used when specifying size
// and coordinates of of discs/polygons.
// Maximum grain "radius": MAXIMUM_COORDINATE
// Maximum grain "diameter": 2*MAXIMUM_COORDINATE
const double MAXIMUM_COORDINATE = 0.5;

// The Euler-Mascheroni constant, gamma. Value taken from Wikipedia:
// https://en.wikipedia.org/wiki/Euler%E2%80%93Mascheroni_constant
const double EULER_MASCHERONI = 0.57721566490153286060651209008240243;

// The bulk s-wave order parameter at zero temperature has a nice analytical
// expression. See page 104 of P. Holmvall PhD Thesis.
// Note that we are using 2*pi*kB*Tc as our energy scale.
const double S_WAVE_BULK = 0.5 * std::exp(-EULER_MASCHERONI);

// The bulk d-wave order parameter at zero temperature has a nice analytical
// expression. See page 104 of P. Holmvall PhD Thesis.
// Note that we are using 2*pi*kB*Tc as our energy scale.
const double D_WAVE_BULK = std::exp(-EULER_MASCHERONI - 0.5) / std::sqrt(2.0);

// Small number to avoid 0/0 when computing residuals.  What epsilon should be
// is up for debate. It is needed for quantities that converge to zero. If
// epsilon > 0 then the residual converges to 0/epsilon instead of 0/0.
constexpr double RESIDUAL_EPSILON = 1e-4;

} // namespace constants
} // namespace conga

#endif // CONGA_DEFINES_H_
