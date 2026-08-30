//===----- geometry_utils.h - Useful geometry helper functions. --===//
//
// Part of the SuperConga Project, under the GNU LGPL v3 license or higher.
// See LICENSE.txt for license information.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// Useful geometry helper functions.
///
//===----------------------------------------------------------------------===//
#ifndef CONGA_GEOMETRY_UTILS_H_
#define CONGA_GEOMETRY_UTILS_H_

#include "../arg.h"
#include "../defines.h"
#include "DiscGeometry.h"
#include "GeometryGroup.h"
#include "PolygonGeometry.h"

#include <json/json.h>

#include <limits>
#include <string>
#include <vector>

namespace conga {
namespace geometry {
/// @brief Class for the transform from user defined geometry to internal
/// coordinate system.
/// @tparam T Float or double.
template <typename T> class CoordinateTransform {
public:
  /// @brief Constructor.
  /// @param inCenter The center of the user defined geometry.
  /// @param inSideLength The sidelength of the bounding square of the user
  /// defined geometry.
  CoordinateTransform(const vector2d<T> &inCenter, const T inSideLength)
      : m_center(inCenter), m_sideLength(inSideLength) {}

  /// @brief Convert user coordinate to internal coordinate system.
  /// @param inCoordinates The user xy-coordinates.
  /// @return The equivalent internal coordinates.
  vector2d<T> centerAndScale(const vector2d<T> &inCoordinates) const {
    const T x = (inCoordinates[0] - m_center[0]) / m_sideLength;
    const T y = (inCoordinates[1] - m_center[1]) / m_sideLength;
    return {x, y};
  }

  /// @brief Convert user length to internal coordinate system.
  /// @param inLength The length in user coordinates.
  /// @return The equivalent internal length.
  T scale(const T inLength) const { return inLength / m_sideLength; }

  // The center of the user defined geometry.
  CONGA_ARG(vector2d<T>, center);

  // The sidelength of the bounding square of the user defined geometry.
  CONGA_ARG(T, sideLength);
};

/// \brief Computet the coordinate transform from user specified geometry to
/// internal coordinate system.
///
/// Parse geometry dictionary for a list of geometry components, provided e.g.
/// via simulation parameters from user. Calculate the bounding box
/// of the compound geometry, and the offset to the geometry center point. The
/// bounding box is used to calculate the scaling factor to internal
/// coordinates.
///
/// \param inSimulationParameters User-defined simulation parameters.
///
/// \return Coordinate transform.
template <typename T>
CoordinateTransform<T>
computeCoordinateTransform(const Json::Value &inSimulationParameters) {
  // Access geometry dictionary in simulation paramters.
  const Json::Value geometryComponentVector =
      inSimulationParameters["geometry"];

  // Find out bounding box for compound geometry.
  T xMax = std::numeric_limits<T>::min();
  T xMin = std::numeric_limits<T>::max();
  T yMax = std::numeric_limits<T>::min();
  T yMin = std::numeric_limits<T>::max();

  const int numGeometryComponents =
      static_cast<int>(geometryComponentVector.size());
  for (int i = 0; i < numGeometryComponents; ++i) {
    // Fetch geometry component type (e.g. disc).
    const std::vector<std::string> geometryComponentNames =
        geometryComponentVector[i].getMemberNames();
    const std::string geometryComponentName = geometryComponentNames[0];

    // Only consider components that are added (not removed).
    if (!geometryComponentVector[i][geometryComponentName]["add"].asBool()) {
      continue;
    }

    // Update maxima and minima of geometry extent.
    if (geometryComponentName == "disc") {
      //***************************************************
      // DISC: GET EXTREMUM COORDINATES
      //***************************************************
      const T radius = static_cast<T>(
          geometryComponentVector[i][geometryComponentName]["radius"]
              .asDouble());
      const T centerX = static_cast<T>(
          geometryComponentVector[i][geometryComponentName]["center_x"]
              .asDouble());
      const T centerY = static_cast<T>(
          geometryComponentVector[i][geometryComponentName]["center_y"]
              .asDouble());

      xMax = std::max(xMax, centerX + radius);
      xMin = std::min(xMin, centerX - radius);
      yMax = std::max(yMax, centerY + radius);
      yMin = std::min(yMin, centerY - radius);
    } else if (geometryComponentName == "polygon") {
      //***************************************************
      // POLYGON: GET EXTREMUM COORDINATES
      //***************************************************
      // Loop over vertex coordinates.
      const Json::Value xVerticesDict =
          inSimulationParameters["geometry"][i][geometryComponentName]
                                ["vertices_x"];
      const Json::Value yVerticesDict =
          inSimulationParameters["geometry"][i][geometryComponentName]
                                ["vertices_y"];

      // Check that the length is the same for the x and y vertices.
      if (xVerticesDict.size() != yVerticesDict.size()) {
        // Unknown geometry component. Print error and exit.
        std::cerr << "-- ERROR! Different number of x- and y-components given "
                     "for polygon vertices: "
                  << xVerticesDict.size() << " != " << yVerticesDict.size()
                  << "." << std::endl;
        std::exit(EXIT_FAILURE);
      }

      // Note, having n as std::size_t causes a bug in JsonCpp...
      const int numVertics = static_cast<int>(xVerticesDict.size());
      for (int n = 0; n < numVertics; ++n) {
        const T x = static_cast<T>(xVerticesDict[n].asDouble());
        const T y = static_cast<T>(yVerticesDict[n].asDouble());

        xMax = std::max(xMax, x);
        xMin = std::min(xMin, x);
        yMax = std::max(yMax, y);
        yMin = std::min(yMin, y);
      }
    } else if (geometryComponentName == "regular_polygon") {
      //***************************************************
      // REGULAR POLYGON: GET EXTREMUM COORDINATES
      //***************************************************
      const T sideLength = static_cast<T>(
          geometryComponentVector[i][geometryComponentName]["side_length"]
              .asDouble());
      const T centerX = static_cast<T>(
          geometryComponentVector[i][geometryComponentName]["center_x"]
              .asDouble());
      const T centerY = static_cast<T>(
          geometryComponentVector[i][geometryComponentName]["center_y"]
              .asDouble());
      const T rotation = static_cast<T>(
          2.0 * M_PI *
          geometryComponentVector[i][geometryComponentName]["rotation"]
              .asDouble());
      const T numEdges =
          geometryComponentVector[i][geometryComponentName]["num_edges"]
              .asInt();

      const T angleStep = static_cast<T>(2.0 * M_PI) / static_cast<T>(numEdges);
      const T radius =
          sideLength / std::hypot(std::cos(angleStep) - static_cast<T>(1),
                                  std::sin(angleStep));
      const T angleOffset = static_cast<T>(0.5) * angleStep + rotation;

      for (int n = 0; n < numEdges; ++n) {
        const T angle = angleOffset + angleStep * static_cast<T>(n);
        const T x = centerX + radius * std::cos(angle);
        const T y = centerY + radius * std::sin(angle);

        xMax = std::max(xMax, x);
        xMin = std::min(xMin, x);
        yMax = std::max(yMax, y);
        yMin = std::min(yMin, y);
      }
    } else {
      // Unknown geometry component. Print error and exit.
      std::cout << "-- ERROR! Unknown geometry type: '" << geometryComponentName
                << "'." << std::endl;
      std::exit(EXIT_FAILURE);
    }
  }

  // Calculate offset for translating to internal coordinate system.
  const T offsetX = static_cast<T>(0.5) * (xMax + xMin);
  const T offsetY = static_cast<T>(0.5) * (yMax + yMin);

  // Calculate extent for scaling to internal coordinate system.
  const T xExtent = xMax - xMin;
  const T yExtent = yMax - yMin;

  // Calculate scaling factor for scaling to internal coordinate system.
  // Consequently, this is the side length of the compound geometry - this is
  // returned so that it can be used for the Parameter class instance.
  const T scale = std::max(xExtent, yExtent);

  return CoordinateTransform<T>({offsetX, offsetY}, scale);
}

/// \brief Create geometry from list of geometry components.
///
/// Parse geometry dictionary for a list of geometry components, provided e.g.
/// via simulation parameters from user. Start by calculating the bounding box
/// of the compound geometry. Translate and scale the compound geometry to fit
/// in internal geometry coordinate system. Loop through list and add/remove
/// geometry objects as specified.
///
/// \param outGeometry Geometry container: instance of GeometryGroup class.
/// \param inSimulationParameters User-defined simulation parameters.
/// \param scale Factor to scale geometry to internal coordinates.
/// \param offsetX Distance along x to translate geometry to origin.
/// \param offsetY Distance along y to translate geometry to origin.
/// \param inGrainFraction Simulation space size, minus margin.
///
/// \return void.
template <typename T>
void addGeometryComponents(GeometryGroup<T> *outGeometry,
                           const Json::Value &inSimulationParameters,
                           const CoordinateTransform<T> &inCoordinateTransform,
                           const T inGrainFraction) {
  // Access geometry dictionary in simulation paramters.
  const Json::Value geometryComponentVector =
      inSimulationParameters["geometry"];

  // Loop over list of geometry components.
  const int numGeometryComponents =
      static_cast<int>(geometryComponentVector.size());
  for (int i = 0; i < numGeometryComponents; ++i) {
    // Fetch geometry component type (e.g. disc).
    const std::vector<std::string> geometryComponentNames =
        geometryComponentVector[i].getMemberNames();
    const std::string geometryComponentName = geometryComponentNames[0];

    // Check whether component is to be added or removed.
    const Type::type addOrRemove =
        (geometryComponentVector[i][geometryComponentName]["add"].asBool())
            ? Type::add
            : Type::remove;

    // Add/remove the appropriate geometry component.
    if (geometryComponentName == "disc") {
      //***************************************************
      // DISC: ADD/REMOVE
      //***************************************************
      const Json::Value disc = geometryComponentVector[i]["disc"];

      // Translate and scale center coordinates.
      const T radius = inCoordinateTransform.scale(
          static_cast<T>(disc["radius"].asDouble()));
      const auto [xCenter, yCenter] = inCoordinateTransform.centerAndScale(
          {static_cast<T>(disc["center_x"].asDouble()),
           static_cast<T>(disc["center_y"].asDouble())});

      // Add/remove disc.
      outGeometry->add(
          new DiscGeometry<T>(inGrainFraction, radius, xCenter, yCenter),
          addOrRemove);
    } else if (geometryComponentVector[i].isMember("polygon")) {
      //***************************************************
      // POLYGON: ADD/REMOVE
      //***************************************************
      const Json::Value polygon = geometryComponentVector[i]["polygon"];

      // Fetch vertices.
      const int numVertices = int(polygon["vertices_x"].size());

      T xVertices[numVertices];
      T yVertices[numVertices];

      for (int vertex_idx = 0; vertex_idx < numVertices; ++vertex_idx) {
        // Translate and scale polygon vertex coordinates.
        const auto [xVertex, yVertex] = inCoordinateTransform.centerAndScale(
            {static_cast<T>(polygon["vertices_x"][vertex_idx].asDouble()),
             static_cast<T>(polygon["vertices_y"][vertex_idx].asDouble())});
        xVertices[vertex_idx] = xVertex;
        yVertices[vertex_idx] = yVertex;
      }

      // Add/remove polygon.
      outGeometry->add(new PolygonGeometry<T>(inGrainFraction, numVertices,
                                              xVertices, yVertices),
                       addOrRemove);
    } else if (geometryComponentVector[i].isMember("regular_polygon")) {
      //***************************************************
      // REGULAR POLYGON: ADD/REMOVE
      //***************************************************
      const Json::Value regularPolygon =
          geometryComponentVector[i]["regular_polygon"];

      // Translate and scale center coordinates.
      const auto [xCenter, yCenter] = inCoordinateTransform.centerAndScale(
          {static_cast<T>(regularPolygon["center_x"].asDouble()),
           static_cast<T>(regularPolygon["center_y"].asDouble())});

      // Side length of the regular polygon, in internal coordinate system.
      const T sideLength = inCoordinateTransform.scale(
          static_cast<T>(regularPolygon["side_length"].asDouble()));

      const int numEdges = regularPolygon["num_edges"].asInt();

      const T rotation =
          static_cast<T>(2.0 * M_PI * regularPolygon["rotation"].asDouble());

      // Add/remove regular polygon.
      outGeometry->add(new PolygonGeometry<T>(inGrainFraction, numEdges,
                                              sideLength, rotation, xCenter,
                                              yCenter),
                       addOrRemove);
    } else {
      // Unknown geometry component. Print error and exit.
      const std::vector<std::string> geometryComponentNames =
          geometryComponentVector[i].getMemberNames();
      std::cout << "-- ERROR! Unknown geometry type: '"
                << geometryComponentNames[i][0] << "'." << std::endl;
      std::exit(EXIT_FAILURE);
    }
  }
}
} // namespace geometry
} // namespace conga

#endif // CONGA_GEOMETRY_UTILS_H_
