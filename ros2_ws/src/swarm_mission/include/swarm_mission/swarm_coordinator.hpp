#pragma once

#include <rclcpp/rclcpp.hpp>
#include <vector>
#include <string>

#include "swarm_mission/drone_context.hpp"

namespace lrs_mission
{

class SwarmCoordinator : public rclcpp::Node
{
public:
  SwarmCoordinator();

private:
  void tick();

  bool any_pose_timeout() const;
  bool all_done() const;

  void init_drone_setpoint(DroneContext& d);
  void publish_setpoint(DroneContext& d);
  void start_item(DroneContext& d, const MissionItem& it);
  void step_item(DroneContext& d, const MissionItem& it);
  void step_drone(DroneContext& d);

  double collision_stop_dist_{0.5};
  double collision_resume_dist_{0.8};
  bool cycle_missions_{true};

  bool reached(const DroneContext& d, double x, double y, double z, ToleranceType tol) const;

  static double yaw_from_quat(const geometry_msgs::msg::Quaternion& q);
  static geometry_msgs::msg::Quaternion quat_from_yaw(double yaw);

  std::vector<std::string> drone_names_;
  std::vector<std::string> mission_paths_;

  double distance_between(const DroneContext& a, const DroneContext& b) const;
  bool collision_check_enabled(const DroneContext& d) const;
  void hold_current_position(DroneContext& d);
  void update_collision_stops();
  void restart_drone_cycle(DroneContext& d);
  void advance_mission(DroneContext& d);

  double rate_hz_{20.0};
  double soft_tol_{0.6};
  double hard_tol_{0.25};
  double pose_timeout_sec_{1.0};

  std::vector<DroneContext> drones_;
  rclcpp::TimerBase::SharedPtr timer_;
};

}  // namespace lrs_mission
