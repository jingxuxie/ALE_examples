#!/usr/bin/env python3
# Copyright (C) 2019 and after, SuperConga team.
# All rights reserved.
# This file is part of the SuperConga Project, under the GNU LGPL v3
# license or higher. See LICENSE.txt for license information.

"""
The main part of the setup tool.
"""

import argparse
import os
import shutil
import subprocess
import sys
from typing import Optional

# TODO(Niclas): I don't understand how Python imports work...
try:
    from .arguments import make_parser
except ImportError:
    from arguments import make_parser


# -----------------------------------------------------------------------------
# RUN
# -----------------------------------------------------------------------------
# TODO(Niclas): The default settings are duplicated here and in the parser.
def run(
    gpu_framework: str = "cuda",
    build_type: str = "Release",
    float_precision: str = "both",
    gpu_arch: Optional[int] = None,
    use_ninja: bool = True,
    use_visualize: bool = True,
    use_cuda_opengl_interop: bool = False,
    use_hdf5: bool = True,
    build_tests: bool = True,
    print_setup_args: bool = True,
    cmake_verbose: bool = False,
    cmake_dump_parameters: bool = False,
):
    # Create paths.
    src_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "../../"))
    build_dir = os.path.join(src_dir, os.path.join("build", build_type.lower()))

    # Create directory.
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)

    # Base commands.
    setup_args = [
        "cmake",
        "-S=" + src_dir,
        "-B=" + build_dir,
        "-DCONGA_GPU_FRAMEWORK=" + gpu_framework,
        "-DCMAKE_BUILD_TYPE=" + build_type,
        "-DCONGA_FLOAT_PRECISION=" + str(float_precision),
    ]

    # Set GPU architecture if specified (CUDA: CMAKE_CUDA_ARCHITECTURES, HIP: CMAKE_HIP_ARCHITECTURES).
    if gpu_arch is not None:
        setup_args.append("-DCONGA_GPU_ARCH=" + str(gpu_arch))

    # Set generator.
    if use_ninja:
        setup_args.append("-G=Ninja")

    # Set visualize.
    # TODO(patric): Make mutually exclusive with HIP (no visualize with HIP), or implement visualization support with HIP.
    if use_visualize:
        setup_args.append("-DCONGA_VISUALIZE=ON")

        # Set CUDA-OpenGL interopability.
        if use_cuda_opengl_interop:
            setup_args.append("-DCONGA_USE_CUDA_OPENGL_INTEROP=ON")
        else:
            setup_args.append("-DCONGA_USE_CUDA_OPENGL_INTEROP=OFF")
    else:
        setup_args.append("-DCONGA_VISUALIZE=OFF")

    # Set HDF5.
    if use_hdf5:
        setup_args.append("-DCONGA_USE_HDF5=ON")
    else:
        setup_args.append("-DCONGA_USE_HDF5=OFF")

    # Set build tests.
    if build_tests:
        setup_args.append("-DCONGA_BUILD_TESTS=ON")
    else:
        setup_args.append("-DCONGA_BUILD_TESTS=OFF")

    # CMake verbose: produce more information about build.
    if cmake_verbose:
        setup_args.append("-DCMAKE_VERBOSE_MAKEFILE=ON")
    else:
        setup_args.append("-DCMAKE_VERBOSE_MAKEFILE=OFF")

    # CMake debug: dump all variables to terminal.
    if cmake_dump_parameters:
        setup_args.append("-DCONGA_CMAKE_DUMP_PARAMS=ON")
    else:
        setup_args.append("-DCONGA_CMAKE_DUMP_PARAMS=OFF")

    # Do the setup.
    if print_setup_args:
        print(80 * "-")
        print("Setup is running:")
        print(*setup_args, sep=" ")
        print(80 * "-")

    subprocess.run(setup_args)


# -----------------------------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------------------------
def main(args: argparse.Namespace) -> None:
    """Run setup tool."""

    # Remove negatations etc.
    run(
        gpu_framework=args.gpu_framework,
        build_type=args.build_type,
        float_precision=args.float_precision,
        gpu_arch=args.gpu_arch,
        use_ninja=not args.no_ninja,
        use_visualize=not args.no_visualize,
        use_cuda_opengl_interop=args.use_cuda_opengl_interop,
        use_hdf5=not args.no_hdf5,
        build_tests=not args.no_tests,
        print_setup_args=not args.no_print_setup_args,
        cmake_verbose=args.cmake_verbose,
        cmake_dump_parameters=args.cmake_dump_parameters,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    make_parser(parser)
    args = parser.parse_args()
    main(args)
