#include "swarm_mission/swarm_coordinator.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2/LinearMath/Quaternion.h>

#include "swarm_mission/mission_loader.hpp"

using namespace std::chrono_literals;

namespace lrs_mission
{

SwarmCoordinator::SwarmCoordinator()
: rclcpp::Node("swarm_coordinator_node")
{
  this->declare_parameter<std::vector<std::string>>(
      "drone_names", std::vector<std::string>{"drone1", "drone2", "drone3"});

  this->declare_parameter<std::vector<std::string>>(
      "mission_paths",
      std::vector<std::string>{
          std::string(std::getenv("HOME")) + "/ros2_ws/missions/drone1.csv",
          std::string(std::getenv("HOME")) + "/ros2_ws/missions/drone2.csv",
          std::string(std::getenv("HOME")) + "/ros2_ws/missions/drone3.csv"});

  this->declare_parameter<double>("rate_hz", rate_hz_);
  this->declare_parameter<double>("soft_tol", soft_tol_);
  this->declare_parameter<double>("hard_tol", hard_tol_);
  this->declare_parameter<double>("pose_timeout_sec", pose_timeout_sec_);

  drone_names_ = this->get_parameter("drone_names").as_string_array();
  mission_paths_ = this->get_parameter("mission_paths").as_string_array();
  rate_hz_ = this->get_parameter("rate_hz").as_double();
  soft_tol_ = this->get_parameter("soft_tol").as_double();
  hard_tol_ = this->get_parameter("hard_tol").as_double();
  pose_timeout_sec_ = this->get_parameter("pose_timeout_sec").as_double();

  if (drone_names_.empty()) {
    throw std::runtime_error("Parameter 'drone_names' must not be empty");
  }
  if (mission_paths_.size() != drone_names_.size()) {
    throw std::runtime_error("Parameter 'mission_paths' must have same size as 'drone_names'");
  }

  for (std::size_t i = 0; i < drone_names_.size(); ++i) {
    DroneContext d;
    d.name = drone_names_[i];
    d.mavros_ns = "/" + d.name;
    d.mission_path = mission_paths_[i];
    d.mav = std::make_shared<MavrosInterface>(this, d.mavros_ns);
    d.mission = MissionLoader::load_from_file(d.mission_path);
    d.last_mode_req = now();
    d.last_arm_req = now();
    d.lt_last_action = now();

    RCLCPP_INFO(
        get_logger(),
        "[%s] MAVROS ns=%s mission=%s items=%zu",
        d.name.c_str(),
        d.mavros_ns.c_str(),
        d.mission_path.c_str(),
        d.mission.size());

    drones_.push_back(d);
  }

  auto period = std::chrono::duration<double>(1.0 / std::max(1.0, rate_hz_));
  timer_ = this->create_wall_timer(
      std::chrono::duration_cast<std::chrono::nanoseconds>(period),
      std::bind(&SwarmCoordinator::tick, this));
}

double SwarmCoordinator::yaw_from_quat(const geometry_msgs::msg::Quaternion& q)
{
  tf2::Quaternion tq(q.x, q.y, q.z, q.w);
  double roll, pitch, yaw;
  tf2::Matrix3x3(tq).getRPY(roll, pitch, yaw);
  return yaw;
}

geometry_msgs::msg::Quaternion SwarmCoordinator::quat_from_yaw(double yaw)
{
  tf2::Quaternion tq;
  tq.setRPY(0.0, 0.0, yaw);

  geometry_msgs::msg::Quaternion q;
  q.x = tq.x();
  q.y = tq.y();
  q.z = tq.z();
  q.w = tq.w();
  return q;
}

bool SwarmCoordinator::reached(
    const DroneContext& d, double x, double y, double z, ToleranceType tol) const
{
  if (!d.mav->have_pose()) return false;

  const auto p = d.mav->current_pose().pose.position;
  const double dx = p.x - x;
  const double dy = p.y - y;
  const double dz = p.z - z;
  const double dist = std::sqrt(dx * dx + dy * dy + dz * dz);
  const double thr = (tol == ToleranceType::SOFT) ? soft_tol_ : hard_tol_;

  return dist <= thr;
}

void SwarmCoordinator::init_drone_setpoint(DroneContext& d)
{
  d.sp = d.mav->current_pose();
  d.sp.header.frame_id = "map";
  d.initialized = true;
}

void SwarmCoordinator::publish_setpoint(DroneContext& d)
{
  if (!d.initialized) return;
  d.sp.header.stamp = now();
  d.mav->publish_setpoint(d.sp);
}

void SwarmCoordinator::start_item(DroneContext& d, const MissionItem& it)
{
  d.cmd_sent = false;
  d.yaw_initialized = false;
  d.lt_phase = DroneContext::LTPhase::NONE;
  d.lt_takeoff_tries = 0;
  d.lt_last_action = now();

  d.sp.header.frame_id = "map";

  if (d.mav->have_pose()) {
    const double cyaw = yaw_from_quat(d.mav->current_pose().pose.orientation);
    d.sp.pose.orientation = quat_from_yaw(cyaw);
  }

  d.sp.pose.position.x = it.x;
  d.sp.pose.position.y = it.y;
  d.sp.pose.position.z = it.z;

  RCLCPP_INFO(
      get_logger(),
      "[%s] Start item %zu -> (%.2f, %.2f, %.2f) cmd=%s",
      d.name.c_str(),
      d.mission_idx,
      it.x, it.y, it.z,
      it.command.c_str());
}

void SwarmCoordinator::step_item(DroneContext& d, const MissionItem& it)
{
  const std::string cmd = it.command;
  auto do_publish = [&]() { publish_setpoint(d); };

  if (cmd == "-" || cmd.empty()) {
    do_publish();
    if (reached(d, it.x, it.y, it.z, it.tol)) {
      RCLCPP_INFO(get_logger(), "[%s] Reached waypoint %zu", d.name.c_str(), d.mission_idx);
      d.mission_idx++;
      if (d.mission_idx < d.mission.size()) start_item(d, d.mission[d.mission_idx]);
      else d.phase = DroneContext::Phase::DONE;
    }
    return;
  }

  if (cmd == "takeoff") {
    if (!d.cmd_sent) {
      RCLCPP_INFO(get_logger(), "[%s] TAKEOFF alt=%.2f", d.name.c_str(), it.z);
      d.cmd_sent = d.mav->takeoff(it.z);
    }
    if (d.mav->have_pose() && d.mav->current_pose().pose.position.z >= it.z - 0.15) {
      d.mission_idx++;
      if (d.mission_idx < d.mission.size()) start_item(d, d.mission[d.mission_idx]);
      else d.phase = DroneContext::Phase::DONE;
    }
    return;
  }

  if (cmd == "land") {
    if (!d.cmd_sent) {
      RCLCPP_INFO(get_logger(), "[%s] LAND", d.name.c_str());
      d.cmd_sent = d.mav->land();
    }
    if (d.mav->have_pose() && d.mav->current_pose().pose.position.z < 0.20) {
      d.phase = DroneContext::Phase::DONE;
    }
    return;
  }

  if (cmd == "landtakeoff") {
    using LT = DroneContext::LTPhase;

    if (d.lt_phase == LT::NONE) {
      d.lt_phase = LT::LANDING;
      d.lt_last_action = now();
      d.mav->land();
      return;
    }

    if (d.lt_phase == LT::LANDING) {
      if (d.mav->have_pose() && d.mav->current_pose().pose.position.z < 0.20) {
        d.lt_phase = LT::SET_GUIDED;
        d.lt_last_action = now() - rclcpp::Duration::from_seconds(2.0);
      }
      return;
    }

    if (d.lt_phase == LT::SET_GUIDED) {
      if ((now() - d.lt_last_action).seconds() > 1.0) {
        d.mav->set_mode("GUIDED");
        d.lt_last_action = now();
      }
      if (d.mav->mode() == "GUIDED") {
        d.lt_phase = LT::ARMING;
        d.lt_last_action = now() - rclcpp::Duration::from_seconds(2.0);
      }
      return;
    }

    if (d.lt_phase == LT::ARMING) {
      if ((now() - d.lt_last_action).seconds() > 1.0) {
        d.mav->arm(true);
        d.lt_last_action = now();
      }
      if (d.mav->armed()) {
        d.lt_phase = LT::TAKEOFFING;
        d.lt_last_action = now() - rclcpp::Duration::from_seconds(2.0);
        d.lt_takeoff_tries = 0;
      }
      return;
    }

    if (d.lt_phase == LT::TAKEOFFING) {
      if ((now() - d.lt_last_action).seconds() > 1.0 && d.lt_takeoff_tries < 5) {
        d.mav->takeoff(it.z);
        d.lt_takeoff_tries++;
        d.lt_last_action = now();
      }
      if (d.mav->have_pose() && d.mav->current_pose().pose.position.z >= it.z - 0.15) {
        d.mission_idx++;
        if (d.mission_idx < d.mission.size()) start_item(d, d.mission[d.mission_idx]);
        else d.phase = DroneContext::Phase::DONE;
      }
      return;
    }

    return;
  }

  if (cmd == "yaw180") {
    do_publish();
    if (!d.yaw_initialized && d.mav->have_pose()) {
      const double cyaw = yaw_from_quat(d.mav->current_pose().pose.orientation);
      d.target_yaw = cyaw + M_PI;
      d.sp.pose.orientation = quat_from_yaw(d.target_yaw);
      d.yaw_initialized = true;
    }
    if (reached(d, it.x, it.y, it.z, it.tol)) {
      d.mission_idx++;
      if (d.mission_idx < d.mission.size()) start_item(d, d.mission[d.mission_idx]);
      else d.phase = DroneContext::Phase::DONE;
    }
    return;
  }

  if (cmd == "yaw90") {
    do_publish();
    if (!d.yaw_initialized && d.mav->have_pose()) {
      const double cyaw = yaw_from_quat(d.mav->current_pose().pose.orientation);
      d.target_yaw = cyaw - M_PI_2;
      d.sp.pose.orientation = quat_from_yaw(d.target_yaw);
      d.yaw_initialized = true;
    }
    if (reached(d, it.x, it.y, it.z, it.tol)) {
      d.mission_idx++;
      if (d.mission_idx < d.mission.size()) start_item(d, d.mission[d.mission_idx]);
      else d.phase = DroneContext::Phase::DONE;
    }
    return;
  }

  do_publish();
  if (reached(d, it.x, it.y, it.z, it.tol)) {
    d.mission_idx++;
    if (d.mission_idx < d.mission.size()) start_item(d, d.mission[d.mission_idx]);
    else d.phase = DroneContext::Phase::DONE;
  }
}

void SwarmCoordinator::step_drone(DroneContext& d)
{
  using Phase = DroneContext::Phase;

  switch (d.phase) {
    case Phase::WAIT_CONN:
      if (d.mav->connected()) {
        RCLCPP_INFO(get_logger(), "[%s] connected", d.name.c_str());
        d.phase = Phase::WAIT_POSE;
      }
      return;

    case Phase::WAIT_POSE:
      if (d.mav->have_pose()) {
        RCLCPP_INFO(get_logger(), "[%s] have pose", d.name.c_str());
        init_drone_setpoint(d);
        d.stream_count = 0;
        d.phase = Phase::STREAM_SP;
      }
      return;

    case Phase::STREAM_SP:
      publish_setpoint(d);
      d.stream_count++;
      if (d.stream_count > 60) {
        d.phase = Phase::SET_GUIDED;
      }
      return;

    case Phase::SET_GUIDED:
      publish_setpoint(d);
      if ((now() - d.last_mode_req).seconds() > 1.0) {
        d.mav->set_mode("GUIDED");
        d.last_mode_req = now();
      }
      if (d.mav->mode() == "GUIDED") {
        d.phase = Phase::ARM;
      }
      return;

    case Phase::ARM:
      publish_setpoint(d);
      if (!d.mav->armed()) {
        if ((now() - d.last_arm_req).seconds() > 1.0) {
          d.mav->arm(true);
          d.last_arm_req = now();
        }
      } else {
        d.mission_idx = 0;
        start_item(d, d.mission[d.mission_idx]);
        d.phase = Phase::EXECUTE;
      }
      return;

    case Phase::EXECUTE:
      if (d.mission_idx >= d.mission.size()) {
        d.phase = Phase::DONE;
        return;
      }
      step_item(d, d.mission[d.mission_idx]);
      return;

    case Phase::DONE:
      publish_setpoint(d);
      return;

    case Phase::FAIL:
      publish_setpoint(d);
      return;
  }
}

bool SwarmCoordinator::any_pose_timeout() const
{
  const auto tnow = now();
  for (const auto& d : drones_) {
    if (d.phase == DroneContext::Phase::WAIT_CONN) continue;
    if (!d.mav->have_pose()) return true;
    if ((tnow - d.mav->last_pose_time()).seconds() > pose_timeout_sec_) {
      RCLCPP_ERROR(get_logger(), "[%s] pose timeout", d.name.c_str());
      return true;
    }
  }
  return false;
}

bool SwarmCoordinator::all_done() const
{
  for (const auto& d : drones_) {
    if (d.phase != DroneContext::Phase::DONE) return false;
  }
  return true;
}

void SwarmCoordinator::tick()
{
  if (any_pose_timeout()) {
    for (auto& d : drones_) {
      if (d.phase != DroneContext::Phase::DONE) {
        d.phase = DroneContext::Phase::FAIL;
      }
    }
  }

  for (auto& d : drones_) {
    step_drone(d);
  }

  if (all_done()) {
    RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 3000, "All drone missions DONE");
  }
}

}  // namespace lrs_mission