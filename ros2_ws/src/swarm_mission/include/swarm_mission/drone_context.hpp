#pragma once

#include <memory>
#include <string>
#include <vector>

#include <geometry_msgs/msg/point.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <rclcpp/rclcpp.hpp>

#include "swarm_mission/mavros_interface.hpp"
#include "swarm_mission/mission_types.hpp"

#include <std_msgs/msg/string.hpp>

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

  enum class ControlMode
  {
    AUTO_MISSION,
    HOLD_FOR_HANDOVER,
    MANUAL_CONTROL,
    RETURN_TO_MISSION
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

  Phase phase{Phase::WAIT_CONN};
  ControlMode control_mode{ControlMode::AUTO_MISSION};
  LTPhase lt_phase{LTPhase::NONE};

  geometry_msgs::msg::PoseStamped sp;
  geometry_msgs::msg::Twist manual_cmd_vel;

  rclcpp::Time last_mode_req;
  rclcpp::Time last_arm_req;
  rclcpp::Time lt_last_action;
  rclcpp::Time last_manual_cmd_time;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr handover_state_pub;
  
  int stream_count{0};
  int lt_takeoff_tries{0};

  bool paused_for_collision{false};
  std::size_t pause_partner{static_cast<std::size_t>(-1)};

  bool pending_takeover{false};
  bool pending_release{false};
  std::size_t handover_checkpoint_idx{0};

  geometry_msgs::msg::Point world_position;
  bool have_world_position{false};

  double spawn_offset_x{0.0};
  double spawn_offset_y{0.0};
  double spawn_offset_z{0.0};

  bool selected_for_manual{false};
  bool initialized{false};
  bool cmd_sent{false};
  bool yaw_initialized{false};

  double target_yaw{0.0};

  DroneContext() = default;
};

}  // namespace lrs_mission