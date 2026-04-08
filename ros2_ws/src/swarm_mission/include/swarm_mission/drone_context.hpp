#pragma once

#include <memory>
#include <string>
#include <vector>

#include <geometry_msgs/msg/pose_stamped.hpp>
#include <rclcpp/rclcpp.hpp>

#include "swarm_mission/mavros_interface.hpp"
#include "swarm_mission/mission_types.hpp"

namespace lrs_mission
{

struct DroneContext
{
  enum class Phase
  {
    WAIT_CONN,
    WAIT_POSE,
    STREAM_SP,
    SET_GUIDED,
    ARM,
    EXECUTE,
    DONE,
    FAIL
  };

  enum class LTPhase
  {
    NONE,
    LANDING,
    SET_GUIDED,
    ARMING,
    TAKEOFFING
  };

  std::string name;
  std::string mavros_ns;
  std::string mission_path;

  std::shared_ptr<MavrosInterface> mav;

  std::vector<MissionItem> mission;
  std::size_t mission_idx{0};

  bool paused_for_collision{false};
  std::size_t pause_partner{static_cast<std::size_t>(-1)};
  bool mission_started{false};
  bool collision_enabled{false};

  Phase phase{Phase::WAIT_CONN};
  LTPhase lt_phase{LTPhase::NONE};

  geometry_msgs::msg::PoseStamped sp;

  rclcpp::Time last_mode_req;
  rclcpp::Time last_arm_req;
  rclcpp::Time lt_last_action;

  int stream_count{0};
  int lt_takeoff_tries{0};

  bool initialized{false};
  bool cmd_sent{false};
  bool yaw_initialized{false};

  double target_yaw{0.0};

  DroneContext() = default;
};

}  // namespace lrs_mission
