#include <rclcpp/rclcpp.hpp>
#include "swarm_mission/swarm_coordinator.hpp"

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<lrs_mission::SwarmCoordinator>());
  rclcpp::shutdown();
  return 0;
}