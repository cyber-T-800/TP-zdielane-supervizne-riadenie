#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source /opt/ros/humble/setup.bash
source /home/lrs/ardupilot/Tools/completion/completion.bash
source "${PROJECT_ROOT}/ros2_ws/install/setup.bash"

export GAZEBO_MODEL_PATH="${PROJECT_ROOT}/World_Dron/model:${GAZEBO_MODEL_PATH:-}"

gazebo "${PROJECT_ROOT}/World_Dron/worlds/iris_arducopter_runway.world"
