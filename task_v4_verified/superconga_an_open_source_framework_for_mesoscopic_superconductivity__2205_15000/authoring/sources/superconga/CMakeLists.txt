cmake_minimum_required(VERSION 3.18)
project(
  SuperConga
  VERSION 1.1.0
  LANGUAGES CXX C)

# Output build messages
message(
  STATUS "Building ${CMAKE_PROJECT_NAME} version ${CMAKE_PROJECT_VERSION}")

# So we can download libs at build time.
include(FetchContent)

# Enable CTest.
if(CONGA_BUILD_TESTS)
  include(CTest)
endif(CONGA_BUILD_TESTS)

# Solves issues with finding std::filesystem in C++17 on some systems.
set(CMAKE_REQUIRED_LIBRARIES -lstdc++fs)

# Append CXX_FLAGS.
list(APPEND CONGA_CXX_FLAGS ${CMAKE_CXX_FLAGS})

set(CONGA_GPU_ARCH
  ""
  CACHE STRING "User-specified GPU architecture (autodetected otherwise).")

set(CONGA_GPU_FRAMEWORK
  "cuda"
  CACHE STRING "GPU framework to build SuperConga for (valid choices: cuda, hip).")

set(CONGA_FLOAT_PRECISION
  "both"
  CACHE STRING "Which floating-point precision to build (valid choices: single, double, both).")

# ##############################################################################
# FIND DEPENDENCIES
# ##############################################################################
find_package(BLAS REQUIRED)
find_package(LAPACK REQUIRED)
find_package(PkgConfig REQUIRED)

pkg_check_modules(JSONCPP jsoncpp)

# Try to fetch jsoncpp if not found.
if(NOT JSONCPP_FOUND)
  message(STATUS "Could not find jsoncpp. Fetching from repository.")
  set(JSONCPP_WITH_TESTS OFF CACHE BOOL "Do not build jsoncpp tests." FORCE)
  set(JSONCPP_WITH_POST_BUILD_UNITTEST OFF CACHE BOOL "Do not run jsoncpp tests." FORCE)
  set(JSONCPP_WITH_EXAMPLE OFF CACHE BOOL "Do not build jsoncpp example." FORCE)
  FetchContent_Declare(
    jsoncpp
    GIT_REPOSITORY https://github.com/open-source-parsers/jsoncpp.git
    GIT_TAG 1.9.6
  )

  FetchContent_GetProperties(jsoncpp)

  # Only populate if it is not already done.
  if(NOT jsoncpp_POPULATED)
    FetchContent_MakeAvailable(jsoncpp)

    message(STATUS "jsoncpp_SOURCE_DIR: ${jsoncpp_SOURCE_DIR}")
    message(STATUS "jsoncpp_BINARY_DIR: ${jsoncpp_BINARY_DIR}")
    set(JSONCPP_INCLUDE_DIRS "${jsoncpp_SOURCE_DIR}/include")
  endif(NOT jsoncpp_POPULATED)
endif(NOT JSONCPP_FOUND)

# If Armadillo is too old or not found it is fetched.
find_package(Armadillo 12.0 QUIET)

if(ARMADILLO_FOUND)
  message(STATUS "Found Armadillo ${ARMADILLO_VERSION_STRING}")
else(ARMADILLO_FOUND)
  # Download Armadillo, but don't build it: we want to use header-only version.
  message(STATUS "Fetching Armadillo")

  # version 11.4.x
  FetchContent_Declare(
    armadillo
    GIT_REPOSITORY https://gitlab.com/conradsnicta/armadillo-code.git
    GIT_TAG 14.0.2)

  # Fetch properties for target: POPULATED, SOURCE_DIR, BINARY_DIR.
  FetchContent_GetProperties(armadillo)

  # Only populate if it is not already done.
  if(NOT armadillo_POPULATED)
    FetchContent_Populate(armadillo)

    # Note: We intentionally avoid add_subdirectory. Otherwise we indicate that
    # CMake should include these to the build, and we want a header-only version
    # to include.
  endif(NOT armadillo_POPULATED)

  # Set variables with capital names, to conform with variables from
  # find_package.
  set(ARMADILLO_INCLUDE_DIRS "${armadillo_SOURCE_DIR}/include")
  set(ARMADILLO_LIBRARIES "")
endif(ARMADILLO_FOUND)

include(CheckLanguage)

# Current choices are HIP and CUDA. Outlook: SYCL, CPU ... .
if(CONGA_GPU_FRAMEWORK STREQUAL "cuda")
  # ############################################################################
  # CUDA
  # ############################################################################
  message(STATUS "Building SuperConga for CUDA.")
  set(CONGA_BUILD_CUDA ON)
  set(CONGA_BUILD_HIP OFF)

  # Integers passed to backend for flexible build.
  set(CONGA_HIP 0)
  set(CONGA_CUDA 1)

  # Check the CUDA compiler
  check_language(CUDA)

  # Check that CUDA compiler can be found.
  if(NOT CMAKE_CUDA_COMPILER)
    message(FATAL_ERROR "ERROR! Could not find CUDA compiler!")
  endif(NOT CMAKE_CUDA_COMPILER)

  # Enable CUDA as project langauge.
  enable_language(CUDA)

  # Fetch CUDA CMake-CUDA functionality. NOTE: FindCUDA is formally deprecated,
  # but no standalone alternative exists as of yet for automatic detection of GPU
  # architecture, so we use it.
  find_package(CUDA REQUIRED)

  # Placeholder for warning if PTX is found in CUDA detection (which can signal
  # that proper GPU hardware is not present on the machine).
  set(CUDA_PTX_WARNING OFF)

  # Set CUDA architecture and flags from user-defined input, or detect automatically.
  if(CONGA_GPU_ARCH)
    message(STATUS "Setting user-defined arch: ${CONGA_GPU_ARCH}")
    set(ARCH_FLAGS "-gencode;arch=compute_${CONGA_GPU_ARCH},code=sm_${CONGA_GPU_ARCH}")
  else(CONGA_GPU_ARCH)
    # Autodetect architecture and fetch architecture version.
    cuda_detect_installed_gpus(DETECTED_CUDA_ARCH)
    message(STATUS "DETECTED_CUDA_ARCH: ${DETECTED_CUDA_ARCH}")

    # Convert to number valid in architecture flags: remove dots.
    string(REPLACE "." "" CONGA_GPU_ARCH "${DETECTED_CUDA_ARCH}")

    # Search for "PTX" in CUDA architecture.
    if(DETECTED_CUDA_ARCH MATCHES ".*PTX")
      set(CUDA_PTX_WARNING ON)
    endif(DETECTED_CUDA_ARCH MATCHES ".*PTX")

    # Remove leading and trailing whitespaces.
    string(STRIP "${CONGA_GPU_ARCH}" CONGA_GPU_ARCH)

    # Choose first architecture in list for one or more GPUs.
    # TODO(patric): Fix issue if GPUs have different architecture levels.
    string(REPLACE " " ";" CUDA_ARCH_LIST "${CONGA_GPU_ARCH}")
    list(GET CUDA_ARCH_LIST 0 CONGA_GPU_ARCH)

    # Atuodetect compilation flags.
    cuda_select_nvcc_arch_flags(ARCH_FLAGS Auto)

    message(STATUS "Detected CUDA architectures: ${CONGA_GPU_ARCH}")
    message(STATUS "Detected CUDA architecture flags: ${ARCH_FLAGS}")
  endif(CONGA_GPU_ARCH)

  # Format architecture flags for compiler.
  string(REPLACE ";" " " ARCH_FLAGS_DISPLAY "${ARCH_FLAGS}")
  message(STATUS "Add CUDA architecture flags: ${ARCH_FLAGS_DISPLAY}")

  set(NVCC_WARN
    "-Wall,\
    -Wextra,\
    -Wnon-virtual-dtor,\
    -Wunused,\
    -Wduplicated-cond,\
    -Wduplicated-branches,\
    -Wlogical-op,\
    -Wnull-dereference,\
    -Wdouble-promotion,\
    -Wformat=2")

  # Set CMAKE_CUDA_ARCHITECTURES, which is needed in CMake>=3.18.
  if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
    # Set CMake policies.
    cmake_policy(SET CMP0104 NEW)
    cmake_policy(SET CMP0105 NEW)

    # Set CUDA architecture flag (new in CMake>=3.18).
    set(CMAKE_CUDA_ARCHITECTURES "${CONGA_GPU_ARCH}")
    message(STATUS "Set CMAKE_CUDA_ARCHITECTURES: ${CMAKE_CUDA_ARCHITECTURES}")
  endif(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
elseif(CONGA_GPU_FRAMEWORK STREQUAL "hip")
  # ############################################################################
  # HIP
  # ############################################################################
  message(STATUS "Building SuperConga for HIP.")
  set(CONGA_BUILD_CUDA OFF)
  set(CONGA_BUILD_HIP ON)

  # Integers passed to backend for flexible build.
  set(CONGA_HIP 1)
  set(CONGA_CUDA 0)

  # Check the HIP compiler.
  check_language(HIP)

  # Check that HIP compiler can be found.
  if(NOT CMAKE_HIP_COMPILER)
    message(FATAL_ERROR "ERROR! Could not find HIP compiler!")
  endif(NOT CMAKE_HIP_COMPILER)

  # Enable HIP as project langauge.
  enable_language(HIP)

  # Fetch CMake-HIP functionality.
  find_package(HIP REQUIRED)

  message(STATUS "Auto-detected CMAKE_HIP_ARCHITECTURES: ${CMAKE_HIP_ARCHITECTURES}")
  message(STATUS "Auto-detected HIP_ARCHITECTURES: ${HIP_ARCHITECTURES}")
  message(STATUS "Auto-detected GPU_TARGETS: ${GPU_TARGETS}")

  # Set CMake policies and CMAKE_HIP_ARCHITECTURES (requires CMake >= 3.18).
  if(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")
    # Set CMake policies.
    cmake_policy(SET CMP0104 NEW)
    cmake_policy(SET CMP0105 NEW)

    # Set user-defined HIP architecture.
    if(CONGA_GPU_ARCH)
      message(STATUS "Setting user-defined GPU architecture: ${CONGA_GPU_ARCH}")
      set(CMAKE_HIP_ARCHITECTURES "${CONGA_GPU_ARCH}")
      set(GPU_TARGETS "${CONGA_GPU_ARCH}")
    endif(CONGA_GPU_ARCH)
  endif(CMAKE_VERSION VERSION_GREATER_EQUAL "3.18")

  message(STATUS "CMAKE_HIP_ARCHITECTURES is set to: ${CMAKE_HIP_ARCHITECTURES}")
  message(STATUS "GPU_TARGETS is set to: ${GPU_TARGETS}")

# TODO(patric):
# ? HIP ARCH_FLAGS?
# ? HIPCC compiler flags for warning level? (See NVCC_WARN above)
# ? PTX warning for HIP?
else()
  message(FATAL_ERROR "ERROR! Unknown GPU framework: CONGA_GPU_FRAMEWORK=${CONGA_GPU_FRAMEWORK}")
endif()

# ##############################################################################
# SUBDIRECTORIES
# ##############################################################################
# For some inexplicable reason the tests must be added first, otherwise the
# fetching of doctest somehow interferes with Forge.
if(CONGA_BUILD_TESTS)
  message(STATUS "Setting up tests/ ...")
  add_subdirectory(tests)
endif(CONGA_BUILD_TESTS)

message(STATUS "Setting up src/ ...")
add_subdirectory(src)

# ##############################################################################
# TEMPLATES
# ##############################################################################
# Export variables and macro defines to be synchronized throughout the project,
# in particular this is e.g. the version number, the project name and build
# paths. These variables can then be specified in a single place. Generate
# include/configure.h from include/configure.h.in.
configure_file(${CMAKE_SOURCE_DIR}/include/conga/templates/configure.h.in
  ${CMAKE_SOURCE_DIR}/include/conga/configure.h)

# Print custom warnings.
if(CUDA_PTX_WARNING)
  message(
    WARNING
    "WARNING! PTX found among CUDA architectures. This could \
                   mean that SuperConga is attempted to be set up without \
                   proper GPU hardware. If on a cluster for example, then it \
                   is recommended to run setup and compilation on the run \
                   node (in your job script), rather than on the login node.")
endif(CUDA_PTX_WARNING)

# ##############################################################################
# Debug: Print all CMAKE variables.
# ##############################################################################
if(CONGA_CMAKE_DUMP_PARAMS)
  message(STATUS "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
  message(STATUS "Dumping all CMake variables.")
  message(STATUS "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
  get_cmake_property(_variableNames VARIABLES)
  list(SORT _variableNames)

  foreach(_variableName ${_variableNames})
    message(STATUS "${_variableName}=${${_variableName}}")
  endforeach()

  message(STATUS "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
  message(STATUS "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::")
endif(CONGA_CMAKE_DUMP_PARAMS)
