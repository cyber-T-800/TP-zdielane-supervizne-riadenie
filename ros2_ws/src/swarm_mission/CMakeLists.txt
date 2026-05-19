cmake_minimum_required(VERSION 3.8)
project(swarm_mission)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(mavros_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(OpenCV REQUIRED)

include_directories(include)

add_executable(swarm_mission_node
  src/main.cpp
  src/mission_loader.cpp
  src/mavros_interface.cpp
  src/mission_executor.cpp
)

ament_target_dependencies(swarm_mission_node
  rclcpp
  geometry_msgs
  visualization_msgs
  mavros_msgs
  tf2
)

target_include_directories(swarm_mission_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

add_executable(swarm_coordinator_node
  src/swarm_main.cpp
  src/swarm_coordinator.cpp
  src/mavros_interface.cpp
  src/mission_loader.cpp
)

ament_target_dependencies(swarm_coordinator_node
  rclcpp
  geometry_msgs
  std_msgs
  mavros_msgs
  tf2
)

target_include_directories(swarm_coordinator_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

add_executable(gstreamer_image_bridge src/gstreamer_image_bridge.cpp)

ament_target_dependencies(gstreamer_image_bridge
  rclcpp
  sensor_msgs
  cv_bridge
)

target_link_libraries(gstreamer_image_bridge
  ${OpenCV_LIBS}
)

install(TARGETS
  swarm_coordinator_node
  swarm_mission_node
  gstreamer_image_bridge
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
