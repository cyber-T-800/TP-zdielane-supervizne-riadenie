#pragma once

#include <rclcpp/rclcpp.hpp>
#include <vector>

#include <geometry_msgs/msg/pose_stamped.hpp>

#include "lrs_mission/mission_types.hpp"
#include "lrs_mission/mavros_interface.hpp"

namespace lrs_mission
{
class MissionExecutor : public rclcpp::Node
{
public:
  MissionExecutor();

private:
  // Main state machine
  enum class Phase { WAIT_CONN, WAIT_POSE, STREAM_SP, SET_GUIDED, ARM, EXECUTE, DONE, FAIL };

  // landtakeoff internal state (because autopilot switches to LAND and disarms after landing)
  enum class LTPhase { NONE, LANDING, SET_GUIDED, ARMING, TAKEOFFING };

  void tick();                  // main loop
  void publish_hold_setpoint();  // publish sp_ to MAVROS
  bool reached(double x, double y, double z, ToleranceType tol) const;

  void start_item(const MissionItem& it);
  void step_item(const MissionItem& it);

  // yaw helpers
  static double yaw_from_quat(const geometry_msgs::msg::Quaternion& q);
  static geometry_msgs::msg::Quaternion quat_from_yaw(double yaw);

  // params
  std::string mission_path_;
  double soft_tol_{0.6};
  double hard_tol_{0.25};
  double rate_hz_{20.0};

  // mission state
  Phase phase_{Phase::WAIT_CONN};
  std::vector<MissionItem> mission_;
  size_t idx_{0};

  // mavros wrapper
  MavrosInterface mav_;

  // setpoint we keep publishing (when needed)
  geometry_msgs::msg::PoseStamped sp_;
  rclcpp::TimerBase::SharedPtr timer_;
  int stream_count_{0};

  // per-command flags
  bool cmd_sent_{false};
  bool yaw_initialized_{false};
  double target_yaw_{0.0};

  // landtakeoff internal vars
  LTPhase lt_phase_{LTPhase::NONE};
  rclcpp::Time lt_last_action_;
  int lt_takeoff_tries_{0};
};
}  // namespace lrs_mission