#include <rclcpp/rclcpp.hpp>
#include "swarm_mission/mission_executor.hpp"

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<lrs_mission::MissionExecutor>());
  rclcpp::shutdown();
  return 0;
}