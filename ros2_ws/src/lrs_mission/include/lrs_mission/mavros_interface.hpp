#pragma once
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <mavros_msgs/msg/state.hpp>
#include <mavros_msgs/srv/command_bool.hpp>
#include <mavros_msgs/srv/set_mode.hpp>
#include <mavros_msgs/srv/command_tol.hpp>

namespace lrs_mission
{
class MavrosInterface
{
public:
  explicit MavrosInterface(rclcpp::Node* node);

  // state getters
  bool connected() const { return state_.connected; }
  bool armed() const { return state_.armed; }
  std::string mode() const { return state_.mode; }
  bool have_pose() const { return have_pose_; }
  geometry_msgs::msg::PoseStamped current_pose() const { return pose_; }

  // setpoint publishing
  void publish_setpoint(const geometry_msgs::msg::PoseStamped& sp);

  // services
  bool set_mode(const std::string& mode);
  bool arm(bool value);
  bool takeoff(double alt);
  bool land();

private:
  void state_cb(const mavros_msgs::msg::State::SharedPtr msg);
  void pose_cb(const geometry_msgs::msg::PoseStamped::SharedPtr msg);

  rclcpp::Node* node_;

  rclcpp::Subscription<mavros_msgs::msg::State>::SharedPtr state_sub_;
  rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr pose_sub_;
  rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr sp_pub_;

  rclcpp::Client<mavros_msgs::srv::SetMode>::SharedPtr set_mode_cli_;
  rclcpp::Client<mavros_msgs::srv::CommandBool>::SharedPtr arm_cli_;
  rclcpp::Client<mavros_msgs::srv::CommandTOL>::SharedPtr takeoff_cli_;
  rclcpp::Client<mavros_msgs::srv::CommandTOL>::SharedPtr land_cli_;

  mavros_msgs::msg::State state_;
  geometry_msgs::msg::PoseStamped pose_;
  bool have_pose_{false};
};
}  // namespace lrs_mission