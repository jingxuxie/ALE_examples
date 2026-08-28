# Install script for directory: /srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit

# Set the install prefix
if(NOT DEFINED CMAKE_INSTALL_PREFIX)
  set(CMAKE_INSTALL_PREFIX "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install")
endif()
string(REGEX REPLACE "/$" "" CMAKE_INSTALL_PREFIX "${CMAKE_INSTALL_PREFIX}")

# Set the install configuration name.
if(NOT DEFINED CMAKE_INSTALL_CONFIG_NAME)
  if(BUILD_TYPE)
    string(REGEX REPLACE "^[^A-Za-z0-9_]+" ""
           CMAKE_INSTALL_CONFIG_NAME "${BUILD_TYPE}")
  else()
    set(CMAKE_INSTALL_CONFIG_NAME "Release")
  endif()
  message(STATUS "Install configuration: \"${CMAKE_INSTALL_CONFIG_NAME}\"")
endif()

# Set the component getting installed.
if(NOT CMAKE_INSTALL_COMPONENT)
  if(COMPONENT)
    message(STATUS "Install component: \"${COMPONENT}\"")
    set(CMAKE_INSTALL_COMPONENT "${COMPONENT}")
  else()
    set(CMAKE_INSTALL_COMPONENT)
  endif()
endif()

# Install shared libraries without execute permission?
if(NOT DEFINED CMAKE_INSTALL_SO_NO_EXE)
  set(CMAKE_INSTALL_SO_NO_EXE "1")
endif()

# Is this installation the result of a crosscompile?
if(NOT DEFINED CMAKE_CROSSCOMPILING)
  set(CMAKE_CROSSCOMPILING "FALSE")
endif()

# Set default install directory permissions.
if(NOT DEFINED CMAKE_OBJDUMP)
  set(CMAKE_OBJDUMP "/usr/bin/objdump")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_root_filesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/docs/Spirit/" TYPE DIRECTORY FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/docs/")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_root_filesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/." TYPE FILE FILES
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/README.md"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/VERSION.txt"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/." TYPE FILE FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/LICENSE.txt")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "qhull.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/COPYING.txt")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "cub.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/thirdparty/cub/LICENSE.TXT")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "eigen.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/thirdparty/Eigen/COPYING.BSD")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "fmt.rst" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/thirdparty/fmt/LICENSE.rst")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "kiss_fft.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/thirdparty/kiss_fft/COPYING")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "ovf.md" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/thirdparty/ovf/README.md")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "spectra.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/thirdparty/spectra/LICENSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "termcolor.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/thirdparty/termcolor/LICENSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "lyra.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/thirdparty/Lyra/LICENSE.txt")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "filesystem.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/ui-imgui/thirdparty/filesystem/LICENSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "glad.md" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/ui-imgui/thirdparty/glad/LICENSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "glfw.md" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/ui-imgui/thirdparty/glfw/LICENSE.md")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "imgui.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/ui-imgui/thirdparty/imgui/LICENSE.txt")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "implot.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/ui-imgui/thirdparty/implot/LICENSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "json.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/ui-imgui/thirdparty/json/LICENSE.MIT")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "nativefiledialog.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/ui-imgui/thirdparty/nativefiledialog/LICENSE")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_licensesx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/licenses" TYPE FILE RENAME "stb.txt" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/ui-cpp/ui-imgui/thirdparty/stb/LICENSE")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/thirdparty/qhull/cmake_install.cmake")
  include("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/core/cmake_install.cmake")

endif()

if(CMAKE_INSTALL_COMPONENT)
  set(CMAKE_INSTALL_MANIFEST "install_manifest_${CMAKE_INSTALL_COMPONENT}.txt")
else()
  set(CMAKE_INSTALL_MANIFEST "install_manifest.txt")
endif()

string(REPLACE ";" "\n" CMAKE_INSTALL_MANIFEST_CONTENT
       "${CMAKE_INSTALL_MANIFEST_FILES}")
file(WRITE "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/${CMAKE_INSTALL_MANIFEST}"
     "${CMAKE_INSTALL_MANIFEST_CONTENT}")
