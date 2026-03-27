#include "swarm_mission/mission_loader.hpp"
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <algorithm>

namespace lrs_mission
{
static inline std::string trim(const std::string& s)
{
  auto b = s.find_first_not_of(" \t\r\n");
  auto e = s.find_last_not_of(" \t\r\n");
  if (b == std::string::npos) return "";
  return s.substr(b, e - b + 1);
}

std::vector<MissionItem> MissionLoader::load_from_file(const std::string& path)
{
  std::ifstream f(path);
  if (!f.is_open()) throw std::runtime_error("Cannot open mission file: " + path);

  std::vector<MissionItem> items;
  std::string line;
  int ln = 0;

  while (std::getline(f, line)) {
    ln++;
    line = trim(line);
    if (line.empty() || line[0] == '#') continue;

    // allow commas too: "x,y,z,tol,cmd"
    std::replace(line.begin(), line.end(), ',', ' ');

    std::istringstream iss(line);
    MissionItem it;
    std::string tol_s;
    if (!(iss >> it.x >> it.y >> it.z >> tol_s >> it.command)) {
      throw std::runtime_error("Bad mission line " + std::to_string(ln) + ": " + line);
    }

    if (tol_s == "soft") it.tol = ToleranceType::SOFT;
    else if (tol_s == "hard") it.tol = ToleranceType::HARD;
    else throw std::runtime_error("Unknown tolerance on line " + std::to_string(ln) + ": " + tol_s);

    items.push_back(it);
  }

  if (items.empty()) throw std::runtime_error("Mission file empty: " + path);
  return items;
}
}  // namespace lrs_mission