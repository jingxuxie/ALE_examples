#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""
Functionality for creating the argument parser for the setup tool.
"""

import argparse
import sys


def make_parser(parser: argparse.ArgumentParser):
    """Given a parser, add all arguments for the setup tool."""

    parser.set_defaults(which="setup")

    parser.description = "Setup a SuperConga build. This is the first step, the second being 'compile', in order to build the C++ backend. Quick start: Run 'python superconga.py setup --type <type>', where <type> is e.g. 'Release' or 'Debug'. Please note that when on a cluster, setup and compilation usually does not work on the login node (due to missing correct GPU hardware): do these steps on the run node instead (at the start of your job script)."

    # Let the user choose which GPU architecture to build for. In the future, one could for example add OpenSYCL, or a CPU-only build.
    parser.add_argument(
        "--gpu-framework",
        choices=["cuda", "hip"],
        default="cuda",
        help="Choose which GPU framework to build for, e.g. CUDA for NVIDIA GPUs, or HIP for AMD/NVIDIA GPUs. (Default: %(default)s)",
    )

    parser.add_argument(
        "--type",
        dest="build_type",
        type=str,
        choices=["Debug", "Release"],
        default="Release",
        help="What build to setup. (Default: %(default)s)",
    )

    parser.add_argument(
        "--float-precision",
        type=str,
        choices=["double", "single", "both"],
        default="both",
        help="Which floating point precisions to build SuperConga backend interfaces (e.g. src/simulation.cu and src/postprocess.cu) with. (Default: %(default)s)",
    )

    parser.add_argument(
        "--gpu-arch",
        type=int,
        default=None,
        help="Manual specification of GPU architecture, CMAKE_<LANG>_ARCHITECTURES, where <LANG> is CUDA (valid arguments are then e.g. 61, 75, 86) or HIP (valid arguments are then e.g. gfx90a, gfx803, gfx900, gfx1030). (Default: %(default)s)",
    )

    parser.add_argument(
        "--no-ninja",
        action="store_true",
        help="Do not use Ninja build system, let CMake decide instead. (Default: %(default)s)",
    )

    parser.add_argument(
        "--no-visualize",
        action="store_true",
        help="Build without visualization support. (Default: %(default)s)",
    )

    parser.add_argument(
        "--use-cuda-opengl-interop",
        action="store_true",
        help="Build with CUDA-OpenGL interopability. If using a single GPU then this yields faster visualization. (Default: %(default)s)",
    )

    parser.add_argument(
        "--no-hdf5",
        action="store_true",
        help="Build without HDF5 support. (Default: %(default)s)",
    )

    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Do not build tests. (Default: %(default)s)",
    )

    parser.add_argument(
        "--no-print-setup-args",
        action="store_true",
        help="Do not print setup arguments before running setup. (Default: %(default)s)",
    )

    parser.add_argument(
        "--cmake-verbose",
        action="store_true",
        help="Build CMake with verbose makefile. (Default: %(default)s)",
    )

    parser.add_argument(
        "--cmake-dump-parameters",
        action="store_true",
        help="Print all CMake variables. (Default: %(default)s)",
    )
