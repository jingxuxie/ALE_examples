# Install script for directory: /srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull

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

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/libqhull.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/geom.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/io.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/mem.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/merge.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/poly.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qhull_a.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qset.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/random.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/stat.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/user.h")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull" TYPE FILE FILES
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/libqhull.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/geom.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/io.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/mem.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/merge.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/poly.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qhull_a.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qset.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/random.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/stat.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/user.h"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/index.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-geom.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-globa.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-io.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-mem.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-merge.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-poly.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-qhull.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-set.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-stat.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/qh-user.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull/DEPRECATED.txt")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull" TYPE FILE FILES
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/index.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-geom.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-globa.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-io.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-mem.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-merge.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-poly.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-qhull.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-set.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-stat.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/qh-user.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull/DEPRECATED.txt"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/libqhull_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/geom_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/io_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/mem_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/merge_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/poly_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qhull_ra.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qset_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/random_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/stat_r.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/user_r.h")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r" TYPE FILE FILES
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/libqhull_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/geom_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/io_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/mem_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/merge_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/poly_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qhull_ra.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qset_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/random_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/stat_r.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/user_r.h"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/index.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-geom_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-globa_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-io_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-mem_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-merge_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-poly_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-qhull_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-set_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-stat_r.htm;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r/qh-user_r.htm")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhull_r" TYPE FILE FILES
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/index.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-geom_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-globa_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-io_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-mem_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-merge_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-poly_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-qhull_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-set_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-stat_r.htm"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhull_r/qh-user_r.htm"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/Coordinates.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/functionObjects.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/PointCoordinates.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/Qhull.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullError.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullFacet.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullFacetList.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullFacetSet.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullHyperplane.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullIterator.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullLinkedList.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullPoint.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullPoints.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullPointSet.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullQh.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullRidge.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullSet.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullSets.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullStat.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullVertex.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/QhullVertexSet.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/RboxPoints.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/RoadError.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/RoadLogEvent.h;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp/RoadTest.h")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/include/libqhullcpp" TYPE FILE FILES
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/Coordinates.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/functionObjects.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/PointCoordinates.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/Qhull.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullError.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullFacet.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullFacetList.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullFacetSet.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullHyperplane.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullIterator.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullLinkedList.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullPoint.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullPoints.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullPointSet.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullQh.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullRidge.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullSet.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullSets.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullStat.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullVertex.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/QhullVertexSet.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/RboxPoints.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/RoadError.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/libqhullcpp/RoadLogEvent.h"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/src/qhulltest/RoadTest.h"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/man/man1/qhull.1")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/man/man1" TYPE FILE RENAME "qhull.1" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/html/qhull.man")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/man/man1/rbox.1")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/man/man1" TYPE FILE RENAME "rbox.1" FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/html/rbox.man")
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/doc/qhull/README.txt;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/doc/qhull/REGISTER.txt;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/doc/qhull/Announce.txt;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/doc/qhull/COPYING.txt;/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/doc/qhull/index.htm")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/doc/qhull" TYPE FILE FILES
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/README.txt"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/REGISTER.txt"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/Announce.txt"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/COPYING.txt"
    "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/index.htm"
    )
endif()

if("x${CMAKE_INSTALL_COMPONENT}x" STREQUAL "xUnspecifiedx" OR NOT CMAKE_INSTALL_COMPONENT)
  list(APPEND CMAKE_ABSOLUTE_DESTINATION_FILES
   "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/doc/qhull/")
  if(CMAKE_WARN_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(WARNING "ABSOLUTE path INSTALL DESTINATION : ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  if(CMAKE_ERROR_ON_ABSOLUTE_INSTALL_DESTINATION)
    message(FATAL_ERROR "ABSOLUTE path INSTALL DESTINATION forbidden (by caller): ${CMAKE_ABSOLUTE_DESTINATION_FILES}")
  endif()
  file(INSTALL DESTINATION "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/build-cpu-reference/install/share/doc/qhull" TYPE DIRECTORY FILES "/srv/home/xuandong/mnt/jingxu/ALE/tasks_v3/atomistic_spin_model_simulations_of_magnetic_nanomaterials__1310_6143/authoring/spirit/thirdparty/qhull/html/")
endif()

