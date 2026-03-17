#pragma once
#include <vector>
#include <string>
#include "lrs_mission/mission_types.hpp"

namespace lrs_mission
{
class MissionLoader
{
public:
  static std::vector<MissionItem> load_from_file(const std::string& path);
};
}  // namespace lrs_mission
