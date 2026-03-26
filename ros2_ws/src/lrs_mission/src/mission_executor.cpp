#include "lrs_mission/mission_executor.hpp"
#include "lrs_mission/mission_loader.hpp"

#include <cmath>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2/LinearMath/Matrix3x3.h>
#include <std_msgs/msg/bool.hpp>


using namespace std::chrono_literals;

namespace lrs_mission
{
MissionExecutor::MissionExecutor()
: rclcpp::Node("lrs_mission_node"), mav_(this)
{
  this->declare_parameter<std::string>("mission_path", "");
  this->declare_parameter<double>("soft_tol", soft_tol_);
  this->declare_parameter<double>("hard_tol", hard_tol_);
  this->declare_parameter<double>("rate_hz", rate_hz_);
  this->declare_parameter<std::string>("flight_mode", "GUIDED");

  mission_path_ = this->get_parameter("mission_path").as_string();
  soft_tol_ = this->get_parameter("soft_tol").as_double();
  hard_tol_ = this->get_parameter("hard_tol").as_double();
  rate_hz_ = this->get_parameter("rate_hz").as_double();

  if (mission_path_.empty()) {
    mission_path_ = std::string(getenv("HOME")) +
      "/TP-zdielane-supervizne-riadenie/ros2_ws/missions/hangar_mavros_pos.csv";
  }

  mission_ = MissionLoader::load_from_file(mission_path_);

  RCLCPP_INFO(get_logger(), "Loaded mission: %zu items from %s", mission_.size(), mission_path_.c_str());
  for (size_t i = 0; i < mission_.size(); i++) {
    const auto& it = mission_[i];
    RCLCPP_INFO(get_logger(), "[%zu] (%.2f, %.2f, %.2f) tol=%s cmd=%s",
                i, it.x, it.y, it.z,
                it.tol == ToleranceType::SOFT ? "soft" : "hard",
                it.command.c_str());
  }

  stop_sub_ = this->create_subscription<std_msgs::msg::Bool>(
  "stop",
  10,
  [this](const std_msgs::msg::Bool::SharedPtr msg) {
    if (!msg->data) return;
    stop_requested_ = true;
    land_at_loop_end_ = true;
    landing_active_ = false;
    RCLCPP_WARN(this->get_logger(), "STOP requested -> will LAND after finishing current loop");
  }
);

  sp_.header.frame_id = "map";
  lt_last_action_ = now();

  auto period = std::chrono::duration<double>(1.0 / std::max(1.0, rate_hz_));
  timer_ = this->create_wall_timer(std::chrono::duration_cast<std::chrono::nanoseconds>(period),
                                  std::bind(&MissionExecutor::tick, this));
}

double MissionExecutor::yaw_from_quat(const geometry_msgs::msg::Quaternion& q)
{
  tf2::Quaternion tq(q.x, q.y, q.z, q.w);
  double roll, pitch, yaw;
  tf2::Matrix3x3(tq).getRPY(roll, pitch, yaw);
  return yaw;
}

geometry_msgs::msg::Quaternion MissionExecutor::quat_from_yaw(double yaw)
{
  tf2::Quaternion tq;
  tq.setRPY(0.0, 0.0, yaw);
  geometry_msgs::msg::Quaternion q;
  q.x = tq.x(); q.y = tq.y(); q.z = tq.z(); q.w = tq.w();
  return q;
}

bool MissionExecutor::reached(double x, double y, double z, ToleranceType tol) const
{
  if (!mav_.have_pose()) return false;
  const auto p = mav_.current_pose().pose.position;
  double dx = p.x - x, dy = p.y - y, dz = p.z - z;
  double d = std::sqrt(dx*dx + dy*dy + dz*dz);
  double thr = (tol == ToleranceType::SOFT) ? soft_tol_ : hard_tol_;
  return d <= thr;
}

void MissionExecutor::publish_hold_setpoint()
{
  sp_.header.stamp = now();
  mav_.publish_setpoint(sp_);
}

void MissionExecutor::start_item(const MissionItem& it)
{
  cmd_sent_ = false;
  yaw_initialized_ = false;

  // reset landtakeoff state
  lt_phase_ = LTPhase::NONE;
  lt_takeoff_tries_ = 0;
  lt_last_action_ = now();

  // landtakeoff helper resets
  lt_hold_x_ = 0.0;
  lt_hold_y_ = 0.0;
  lt_hold_xy_initialized_ = false;
  lt_reached_alt_ = false;

  sp_.header.frame_id = "map";

  // keep current yaw
  if (mav_.have_pose()) {
    double cyaw = yaw_from_quat(mav_.current_pose().pose.orientation);
    sp_.pose.orientation = quat_from_yaw(cyaw);
  }

  // normal setpoint target
  sp_.pose.position.x = it.x;
  sp_.pose.position.y = it.y;
  sp_.pose.position.z = it.z;
}

// Advance to next mission item, or loop, or land-after-loop if stop was requested
void MissionExecutor::advance_after_item()
{
  idx_++;

  if (idx_ < mission_.size()) {
    start_item(mission_[idx_]);
    return;
  }

  // End of loop reached
  if (land_at_loop_end_) {
    if (!landing_active_) {
      RCLCPP_WARN(get_logger(), "End of loop reached -> LANDING now (stop requested)");
      mav_.land();
      landing_active_ = true;
    }
    phase_ = Phase::DONE;  // DONE will keep calling land until z<0.2
    return;
  }

  // Loop forever
  idx_ = 0;
  RCLCPP_INFO(get_logger(), "Loop restart");
  start_item(mission_[idx_]);
}

void MissionExecutor::step_item(const MissionItem& it)
{
  const std::string cmd = it.command;
  auto do_publish = [&]() { publish_hold_setpoint(); };

  if (cmd == "-" || cmd.empty()) {
    do_publish();
    if (reached(it.x, it.y, it.z, it.tol)) {
      RCLCPP_INFO(get_logger(), "Reached waypoint %zu", idx_);
      advance_after_item();
    }
    return;
  }

  if (cmd == "takeoff") {
    if (!cmd_sent_) {
      RCLCPP_INFO(get_logger(), "Command: TAKEOFF to alt=%.2f", it.z);
      cmd_sent_ = mav_.takeoff(it.z);
    }
    if (mav_.have_pose() && mav_.current_pose().pose.position.z >= it.z - 0.15) {
      RCLCPP_INFO(get_logger(), "Takeoff altitude reached, continue");
      advance_after_item();
    }
    return;
  }

  if (cmd == "land") {
    if (!cmd_sent_) {
      RCLCPP_INFO(get_logger(), "Command: LAND");
      cmd_sent_ = mav_.land();
    }
    if (mav_.have_pose() && mav_.current_pose().pose.position.z < 0.20) {
      RCLCPP_INFO(get_logger(), "Landed");
      // If we're looping and user did NOT request stop, continue loop.
      // If stop was requested, DONE phase will keep it landed.
      if (land_at_loop_end_) {
        phase_ = Phase::DONE;
      } else {
        advance_after_item();
      }
    }
    return;
  }

  if (cmd == "landtakeoff") {
    // IMPORTANT: start landing only after we reached the landtakeoff waypoint
    // Otherwise landing happens at the previous point and the next waypoint can be unsafe.
    if (lt_phase_ == LTPhase::NONE) {
      do_publish(); // keep flying to (it.x,it.y,it.z)
      if (!reached(it.x, it.y, it.z, it.tol)) {
        return; // still approaching
      }

      lt_phase_ = LTPhase::LANDING;
      lt_last_action_ = now();
      RCLCPP_INFO(get_logger(), "Command: LANDTAKEOFF (landing phase at waypoint)");
      mav_.land();
      return;
    }

    // Keep streaming setpoints during phases where GUIDED control is needed.
    if (lt_phase_ == LTPhase::SET_GUIDED || lt_phase_ == LTPhase::ARMING || lt_phase_ == LTPhase::TAKEOFFING) {
      do_publish();
    }

    // 1) Wait until on ground (do NOT require disarm)
    if (lt_phase_ == LTPhase::LANDING) {
      if (mav_.have_pose() && mav_.current_pose().pose.position.z < 0.20) {
        lt_phase_ = LTPhase::SET_GUIDED;
        lt_last_action_ = now() - rclcpp::Duration::from_seconds(2.0);
        RCLCPP_INFO(get_logger(), "LANDTAKEOFF: On ground (z=%.2f) -> switching to GUIDED",
                    mav_.current_pose().pose.position.z);
      }
      return;
    }

    // 2) Ensure GUIDED mode again
    if (lt_phase_ == LTPhase::SET_GUIDED) {
      if ((now() - lt_last_action_).seconds() > 1.0) {
        bool sent = mav_.set_mode("GUIDED");
        RCLCPP_INFO(get_logger(), "LANDTAKEOFF: Request GUIDED (sent=%s), current=%s",
                    sent ? "true" : "false", mav_.mode().c_str());
        lt_last_action_ = now();
      }

      if (mav_.mode() == "GUIDED") {
        lt_phase_ = LTPhase::ARMING;
        lt_last_action_ = now() - rclcpp::Duration::from_seconds(2.0);
        RCLCPP_INFO(get_logger(), "LANDTAKEOFF: GUIDED confirmed -> arming (if needed)");
      }
      return;
    }

    // 3) Arm if needed (sometimes stays armed)
    if (lt_phase_ == LTPhase::ARMING) {
      if (!mav_.armed()) {
        if ((now() - lt_last_action_).seconds() > 1.0) {
          bool sent = mav_.arm(true);
          RCLCPP_INFO(get_logger(), "LANDTAKEOFF: Request ARM (sent=%s), armed=%s",
                      sent ? "true" : "false", mav_.armed() ? "true" : "false");
          lt_last_action_ = now();
        }
        return;
      }

      // Hold XY at the CURRENT ground position (prevents ground-scrape dash)
      if (mav_.have_pose()) {
        lt_hold_x_ = mav_.current_pose().pose.position.x;
        lt_hold_y_ = mav_.current_pose().pose.position.y;
        lt_hold_xy_initialized_ = true;
      } else {
        lt_hold_xy_initialized_ = false;
      }

      lt_reached_alt_ = false;
      lt_phase_ = LTPhase::TAKEOFFING;
      lt_last_action_ = now(); // stabilization timer start
      RCLCPP_INFO(get_logger(), "LANDTAKEOFF: Armed -> takeoff by setpoint (hold XY) to alt=%.2f", it.z);

      if (mav_.have_pose()) sp_.pose.orientation = mav_.current_pose().pose.orientation;
      return;
    }

    // 4) Takeoff by setpoint: hold XY, climb Z, then stabilize 1s, then continue mission
    if (lt_phase_ == LTPhase::TAKEOFFING) {
      do_publish();

      // Hold XY where we landed until safely at altitude
      if (lt_hold_xy_initialized_) {
        sp_.pose.position.x = lt_hold_x_;
        sp_.pose.position.y = lt_hold_y_;
      } else {
        sp_.pose.position.x = it.x;
        sp_.pose.position.y = it.y;
      }

      sp_.pose.position.z = it.z;

      if (!lt_reached_alt_ && mav_.have_pose() && mav_.current_pose().pose.position.z >= it.z - 0.15) {
        lt_reached_alt_ = true;
        lt_last_action_ = now(); // start stabilize timer
        RCLCPP_INFO(get_logger(), "LANDTAKEOFF: Altitude reached (z=%.2f). Stabilizing...",
                    mav_.current_pose().pose.position.z);
      }

      if (lt_reached_alt_ && (now() - lt_last_action_).seconds() >= 1.0) {
        RCLCPP_INFO(get_logger(), "LANDTAKEOFF completed -> continue mission");
        lt_phase_ = LTPhase::NONE;
        lt_hold_xy_initialized_ = false;
        lt_reached_alt_ = false;
        advance_after_item();
      }
      return;
    }

    return;
  }

  if (cmd == "yaw180") {
    do_publish();
    if (!yaw_initialized_ && mav_.have_pose()) {
      double cyaw = yaw_from_quat(mav_.current_pose().pose.orientation);
      target_yaw_ = cyaw + M_PI;
      sp_.pose.orientation = quat_from_yaw(target_yaw_);
      yaw_initialized_ = true;
      RCLCPP_INFO(get_logger(), "Command: YAW180");
    }
    if (reached(it.x, it.y, it.z, it.tol)) {
      RCLCPP_INFO(get_logger(), "Yaw180 point reached, continue");
      advance_after_item();
    }
    return;
  }

  if (cmd == "yaw90" || cmd == "-yaw90") {
    do_publish();

    if (!yaw_initialized_ && mav_.have_pose()) {
      double cyaw = yaw_from_quat(mav_.current_pose().pose.orientation);
      const double sign = (cmd == "-yaw90") ? -1.0 : 1.0;
      target_yaw_ = cyaw + sign * (M_PI / 2.0);
      sp_.pose.orientation = quat_from_yaw(target_yaw_);
      yaw_initialized_ = true;
      RCLCPP_INFO(get_logger(), "Command: %s", cmd.c_str());
    }

    if (reached(it.x, it.y, it.z, it.tol)) {
      RCLCPP_INFO(get_logger(), "Yaw90 point reached, continue");
      advance_after_item();
    }
    return;
  }

  // unknown -> treat as waypoint
  do_publish();
  if (reached(it.x, it.y, it.z, it.tol)) {
    advance_after_item();
  }
}

void MissionExecutor::tick()
{
  static rclcpp::Time last_mode_req = now();
  static rclcpp::Time last_arm_req  = now();

  switch (phase_) {
    case Phase::WAIT_CONN:
      if (mav_.connected()) {
        RCLCPP_INFO(get_logger(), "MAVROS connected");
        phase_ = Phase::WAIT_POSE;
      }
      return;

    case Phase::WAIT_POSE:
      if (mav_.have_pose()) {
        RCLCPP_INFO(get_logger(), "Have local pose");
        sp_ = mav_.current_pose();
        sp_.header.frame_id = "map";
        phase_ = Phase::STREAM_SP;
      }
      return;

    case Phase::STREAM_SP:
      publish_hold_setpoint();
      stream_count_++;
      if (stream_count_ > 60) phase_ = Phase::SET_GUIDED;
      return;

    case Phase::SET_GUIDED: {
      publish_hold_setpoint();
      const auto desired = this->get_parameter("flight_mode").as_string();

      if ((now() - last_mode_req).seconds() > 1.0) {
        bool sent = mav_.set_mode(desired);
        RCLCPP_INFO(get_logger(), "Requesting mode '%s' (sent=%s), current='%s'",
                    desired.c_str(), sent ? "true" : "false", mav_.mode().c_str());
        last_mode_req = now();
      }

      if (mav_.mode() == desired) {
        RCLCPP_INFO(get_logger(), "Mode confirmed: %s", desired.c_str());
        phase_ = Phase::ARM;
      }
      return;
    }

    case Phase::ARM:
      publish_hold_setpoint();
      if (!mav_.armed()) {
        if ((now() - last_arm_req).seconds() > 1.0) {
          bool sent = mav_.arm(true);
          RCLCPP_INFO(get_logger(), "Requesting ARM (sent=%s)", sent ? "true" : "false");
          last_arm_req = now();
        }
      } else {
        RCLCPP_INFO(get_logger(), "Armed -> starting mission execute");
        idx_ = 0;
        start_item(mission_[idx_]);
        phase_ = Phase::EXECUTE;
      }
      return;

    case Phase::EXECUTE:
      if (idx_ >= mission_.size()) {
        // should not happen (advance_after_item handles loop), but keep safe
        idx_ = 0;
        start_item(mission_[idx_]);
      }
      step_item(mission_[idx_]);
      return;

    case Phase::DONE:
      publish_hold_setpoint();

      // If stop was requested, keep landing until on ground
      if (land_at_loop_end_) {
        if (!landing_active_) {
          mav_.land();
          landing_active_ = true;
        }

        if (mav_.have_pose() && mav_.current_pose().pose.position.z < 0.20) {
          RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 2000, "Landed. Mission stopped.");
          // optional: uncomment to exit node after landing
          // rclcpp::shutdown();
        } else {
          RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 2000, "Landing...");
          mav_.land();
        }
        return;
      }

      // Otherwise, we do not end (we loop forever). DONE should rarely be reached.
      RCLCPP_INFO_THROTTLE(get_logger(), *get_clock(), 2000, "Mission DONE");
      return;

    case Phase::FAIL:
      RCLCPP_ERROR_THROTTLE(get_logger(), *get_clock(), 2000, "Mission FAIL");
      return;
  }
}
}  // namespace lrs_mission