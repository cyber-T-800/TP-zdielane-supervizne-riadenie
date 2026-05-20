#pragma once

#include <rclcpp/rclcpp.hpp>
#include <vector>
#include <string>

#include <geometry_msgs/msg/twist.hpp>
#include <std_msgs/msg/string.hpp>

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

  bool should_switch_to_manual_at_checkpoint(const DroneContext& d) const;
  void switch_to_manual_control(DroneContext& d);
  void switch_to_auto_mission(DroneContext& d);

  bool reached(const DroneContext& d, double x, double y, double z, ToleranceType tol) const;

  static double yaw_from_quat(const geometry_msgs::msg::Quaternion& q);
  static geometry_msgs::msg::Quaternion quat_from_yaw(double yaw);

  double distance_between(const DroneContext& a, const DroneContext& b) const;
  bool collision_check_enabled(const DroneContext& d) const;
  void hold_current_position(DroneContext& d);
  void update_collision_stops();

  void update_world_position_from_local(DroneContext& d);

  void restart_drone_cycle(DroneContext& d);
  void advance_mission(DroneContext& d);

  void takeover_cb(const std_msgs::msg::String::SharedPtr msg);
  void release_cb(const std_msgs::msg::String::SharedPtr msg);
  void manual_cmd_cb(const geometry_msgs::msg::Twist::SharedPtr msg);

  DroneContext* find_drone(const std::string& name);
  void release_manual_control(DroneContext& d);

  std::vector<std::string> drone_names_;
  std::vector<std::string> mission_paths_;

  double rate_hz_{20.0};
  double soft_tol_{0.6};
  double hard_tol_{0.25};
  double pose_timeout_sec_{1.0};

  double collision_stop_dist_{0.5};
  double collision_resume_dist_{0.8};
  bool cycle_missions_{true};

  std::vector<DroneContext> drones_;
  rclcpp::TimerBase::SharedPtr timer_;

  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr takeover_sub_;
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr release_sub_;
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr manual_cmd_sub_;

  std::string active_manual_drone_;
  double manual_cmd_timeout_sec_{0.5};
};

}  // namespace lrs_mission