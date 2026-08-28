# Install script for directory: /srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core

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

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_core_documentationx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/docs/Spirit/core/" TYPE DIRECTORY FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/docs/")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_core_headersx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/include" TYPE DIRECTORY FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/include/Spirit" FILES_MATCHING REGEX "/[^/]*\\.h$")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_core_pythonx" OR NOT CMAKE_INSTALL_COMPONENT)
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/libSpirit.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/libSpirit.so")
    file(RPATH_CHECK
         FILE "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/libSpirit.so"
         RPATH "")
  endif()
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/bin" TYPE SHARED_LIBRARY FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/python/spirit/libSpirit.so")
  if(EXISTS "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/libSpirit.so" AND
     NOT IS_SYMLINK "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/libSpirit.so")
    if(CMAKE_INSTALL_DO_STRIP)
      execute_process(COMMAND "/usr/bin/strip" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/bin/libSpirit.so")
    endif()
  endif()
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_core_pythonx" OR NOT CMAKE_INSTALL_COMPONENT)
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_core_pythonx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/python" TYPE DIRECTORY FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/python/spirit" FILES_MATCHING REGEX "/[^/]*\\.py$")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xspirit_core_pythonx" OR NOT CMAKE_INSTALL_COMPONENT)
  file(INSTALL DESTINATION "${CMAKE_INSTALL_PREFIX}/test/python" TYPE DIRECTORY FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/core/python/test/" FILES_MATCHING REGEX "/[^/]*\\.py$")
endif()

if(NOT CMAKE_INSTALL_LOCAL_ONLY)
  # Include the install script for each subdirectory.
  include("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/core/thirdparty/kiss_fft/cmake_install.cmake")
  include("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/core/thirdparty/ovf/cmake_install.cmake")
  include("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/core/src/cmake_install.cmake")
  include("/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/core/include/cmake_install.cmake")

endif()

