cmake_minimum_required(VERSION 3.8)
project(lrs_mission)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(mavros_msgs REQUIRED)
find_package(tf2 REQUIRED)

include_directories(include)

add_executable(lrs_mission_node
)

ament_target_dependencies(lrs_mission_node
  rclcpp
  geometry_msgs
  visualization_msgs
  mavros_msgs
  tf2
)

install(TARGETS lrs_mission_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
