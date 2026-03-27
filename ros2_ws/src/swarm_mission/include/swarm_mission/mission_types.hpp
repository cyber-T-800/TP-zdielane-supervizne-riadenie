#pragma once
#include <string>

namespace lrs_mission
{
enum class ToleranceType { SOFT, HARD };

struct MissionItem
{
  double x{0}, y{0}, z{0};
  ToleranceType tol{ToleranceType::SOFT};
  std::string command;   // "takeoff", "land", "landtakeoff", "yaw180", "-"
};
}  // namespace lrs_mission
