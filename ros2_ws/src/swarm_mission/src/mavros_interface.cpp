#include "swarm_mission/mavros_interface.hpp"

using namespace std::chrono_literals;

namespace lrs_mission
{
MavrosInterface::MavrosInterface(rclcpp::Node* node, const std::string& mavros_ns)
: node_(node), mavros_ns_(mavros_ns), last_pose_time_(node->now())
{
  state_sub_ = node_->create_subscription<mavros_msgs::msg::State>(
      mavros_ns_ + "/state",
      10,
      std::bind(&MavrosInterface::state_cb, this, std::placeholders::_1));

  rmw_qos_profile_t qos_profile = rmw_qos_profile_default;
  qos_profile.depth = 1;
  qos_profile.reliability = RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT;
  auto qos = rclcpp::QoS(rclcpp::QoSInitialization(qos_profile.history, 1), qos_profile);

  pose_sub_ = node_->create_subscription<geometry_msgs::msg::PoseStamped>(
      mavros_ns_ + "/local_position/pose",
      qos,
      std::bind(&MavrosInterface::pose_cb, this, std::placeholders::_1));

  sp_pub_ = node_->create_publisher<geometry_msgs::msg::PoseStamped>(
      mavros_ns_ + "/setpoint_position/local", 10);

  set_mode_cli_ = node_->create_client<mavros_msgs::srv::SetMode>(
      mavros_ns_ + "/set_mode");

  arm_cli_ = node_->create_client<mavros_msgs::srv::CommandBool>(
      mavros_ns_ + "/cmd/arming");

  takeoff_cli_ = node_->create_client<mavros_msgs::srv::CommandTOL>(
      mavros_ns_ + "/cmd/takeoff");

  land_cli_ = node_->create_client<mavros_msgs::srv::CommandTOL>(
      mavros_ns_ + "/cmd/land");
}

void MavrosInterface::state_cb(const mavros_msgs::msg::State::SharedPtr msg)
{
  state_ = *msg;
}

void MavrosInterface::pose_cb(const geometry_msgs::msg::PoseStamped::SharedPtr msg)
{
  pose_ = *msg;
  have_pose_ = true;
  last_pose_time_ = node_->now();
}

void MavrosInterface::publish_setpoint(const geometry_msgs::msg::PoseStamped& sp)
{
  sp_pub_->publish(sp);
}

bool MavrosInterface::set_mode(const std::string& mode)
{
  if (!set_mode_cli_->wait_for_service(200ms)) return false;
  auto req = std::make_shared<mavros_msgs::srv::SetMode::Request>();
  req->custom_mode = mode;
  (void)set_mode_cli_->async_send_request(req);
  return true;
}

bool MavrosInterface::arm(bool value)
{
  if (!arm_cli_->wait_for_service(200ms)) return false;
  auto req = std::make_shared<mavros_msgs::srv::CommandBool::Request>();
  req->value = value;
  (void)arm_cli_->async_send_request(req);
  return true;
}

bool MavrosInterface::takeoff(double alt)
{
  if (!takeoff_cli_->wait_for_service(200ms)) return false;
  auto req = std::make_shared<mavros_msgs::srv::CommandTOL::Request>();
  req->min_pitch = 0.0;
  req->yaw = 0.0;
  req->altitude = alt;
  (void)takeoff_cli_->async_send_request(req);
  return true;
}

bool MavrosInterface::land()
{
  if (!land_cli_->wait_for_service(200ms)) return false;
  auto req = std::make_shared<mavros_msgs::srv::CommandTOL::Request>();
  (void)land_cli_->async_send_request(req);
  return true;
}
}  // namespace lrs_mission