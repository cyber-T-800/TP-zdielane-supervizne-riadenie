#!/usr/bin/env bash
set -Eeuo pipefail

# Stop script for LRS / SWARM simulations.
#
# Stops:
#   - Gazebo / gzserver / gzclient
#   - ArduPilot SITL / sim_vehicle.py / MAVProxy
#   - MAVROS
#   - lrs_mission_node
#   - swarm_coordinator_node
#   - rosbridge_server / rosbridge_websocket / rosapi_node
#   - gstreamer_image_bridge
#   - GStreamer helper processes
#   - terminal windows opened by start_lrs.sh / start_swarm.sh
#
# Usage:
#   chmod +x stop_sim.sh
#   ./stop_sim.sh
#
# Optional:
#   ./stop_sim.sh --no-close-terminals

CLOSE_TERMINALS=1
WAIT_SECONDS=3

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-close-terminals)
      CLOSE_TERMINALS=0
      shift
      ;;
    --wait)
      WAIT_SECONDS="${2:?--wait needs seconds}"
      shift 2
      ;;
    -h|--help)
      cat <<EOF
Usage:
  $0 [--no-close-terminals] [--wait SECONDS]

Options:
  --no-close-terminals   Kill simulation processes, but do not close LRS/SWARM terminal windows.
  --wait SECONDS         Wait time before force killing remaining processes. Default: 3.
EOF
      exit 0
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
done

echo "Stopping LRS / SWARM simulation..."
echo

kill_pattern() {
  local description="$1"
  local pattern="$2"

  echo "[$description]"
  local pids
  pids="$(pgrep -f "$pattern" || true)"

  if [[ -z "$pids" ]]; then
    echo "  no process found"
  else
    echo "  sending TERM to PIDs:"
    echo "$pids" | sed 's/^/  /'
    pkill -TERM -f "$pattern" || true
  fi
}

force_kill_pattern() {
  local description="$1"
  local pattern="$2"

  local pids
  pids="$(pgrep -f "$pattern" || true)"
  if [[ -n "$pids" ]]; then
    echo "[$description]"
    echo "  sending KILL to PIDs:"
    echo "$pids" | sed 's/^/  /'
    pkill -KILL -f "$pattern" || true
  fi
}

close_windows_by_title() {
  if (( CLOSE_TERMINALS == 0 )); then
    echo "Skipping terminal window closing (--no-close-terminals)."
    return 0
  fi

  echo
  echo "Closing LRS/SWARM terminal windows..."

  if ! command -v wmctrl >/dev/null 2>&1; then
    echo "  wmctrl is not installed, skipping terminal window close by title."
    echo "  To enable this, install:"
    echo "    sudo apt update && sudo apt install -y wmctrl"
    return 0
  fi

  # Close all terminal windows opened by our scripts.
  # Window titles are like:
  #   LRS 1 - Gazebo
  #   SWARM 8 - rosbridge websocket
  #   SWARM 12 - GStreamer drone3
  local ids
  ids="$(wmctrl -l | grep -E " LRS [0-9]+ - | SWARM [0-9]+ - " | awk '{print $1}' || true)"

  if [[ -z "$ids" ]]; then
    echo "  no LRS/SWARM windows found"
    return 0
  fi

  echo "$ids" | while read -r window_id; do
    [[ -n "$window_id" ]] || continue
    echo "  closing window $window_id"
    wmctrl -ic "$window_id" || true
  done
}

echo "1/4 Sending graceful stop signals..."
echo

# ROS mission/control nodes
kill_pattern "LRS mission node" "ros2 run lrs_mission lrs_mission_node|lrs_mission_node"
kill_pattern "Swarm coordinator node" "ros2 run swarm_mission swarm_coordinator_node|swarm_coordinator_node"

# ROS bridge for frontend/backend
kill_pattern "rosbridge launch" "ros2 launch rosbridge_server rosbridge_websocket_launch.xml"
kill_pattern "rosbridge websocket" "rosbridge_websocket|rosbridge_websocket.py"
kill_pattern "rosapi node" "rosapi_node"

# GStreamer image bridge and helpers
kill_pattern "GStreamer image bridge" "ros2 run swarm_mission gstreamer_image_bridge|gstreamer_image_bridge"
kill_pattern "GStreamer helper processes" "gst-launch|gst-inspect|x264enc"

# MAVROS
kill_pattern "MAVROS node" "ros2 run mavros mavros_node|mavros_node"
kill_pattern "MAVROS router" "mavros_router"

# ArduPilot / MAVProxy / SITL
kill_pattern "sim_vehicle.py" "sim_vehicle.py.*gazebo-iris|sim_vehicle.py.*ArduCopter"
kill_pattern "MAVProxy" "mavproxy.py"
kill_pattern "ArduCopter SITL" "arducopter|ArduCopter"
kill_pattern "ArduPilot terminal helper" "run_in_terminal_window.sh.*ArduCopter"

# Gazebo worlds and scripts
kill_pattern "Gazebo runway world script" "runway_world.sh"
kill_pattern "Gazebo single camera world" "gazebo.*fei_lrs_gazebo_singleCamera.world"
kill_pattern "Gazebo server/client" "gzserver|gzclient|gazebo"

# Optional frontend app processes from the repo.
# These are included because the new workflow can involve DroneApp_v4.
kill_pattern "DroneApp frontend/backend Python app" "DroneAppV4.py|DroneCom.py|GSTReceiver.py|MainWindow.py|StreamPanel.py|KeyboardController.py"

echo
echo "2/4 Waiting ${WAIT_SECONDS}s for graceful shutdown..."
sleep "$WAIT_SECONDS"

echo
echo "3/4 Force killing remaining simulation processes..."
echo

force_kill_pattern "LRS mission node" "ros2 run lrs_mission lrs_mission_node|lrs_mission_node"
force_kill_pattern "Swarm coordinator node" "ros2 run swarm_mission swarm_coordinator_node|swarm_coordinator_node"

force_kill_pattern "rosbridge launch" "ros2 launch rosbridge_server rosbridge_websocket_launch.xml"
force_kill_pattern "rosbridge websocket" "rosbridge_websocket|rosbridge_websocket.py"
force_kill_pattern "rosapi node" "rosapi_node"

force_kill_pattern "GStreamer image bridge" "ros2 run swarm_mission gstreamer_image_bridge|gstreamer_image_bridge"
force_kill_pattern "GStreamer helper processes" "gst-launch|gst-inspect|x264enc"

force_kill_pattern "MAVROS node" "ros2 run mavros mavros_node|mavros_node"
force_kill_pattern "MAVROS router" "mavros_router"

force_kill_pattern "sim_vehicle.py" "sim_vehicle.py.*gazebo-iris|sim_vehicle.py.*ArduCopter"
force_kill_pattern "MAVProxy" "mavproxy.py"
force_kill_pattern "ArduCopter SITL" "arducopter|ArduCopter"
force_kill_pattern "ArduPilot terminal helper" "run_in_terminal_window.sh.*ArduCopter"

force_kill_pattern "Gazebo runway world script" "runway_world.sh"
force_kill_pattern "Gazebo single camera world" "gazebo.*fei_lrs_gazebo_singleCamera.world"
force_kill_pattern "Gazebo server/client" "gzserver|gzclient|gazebo"

force_kill_pattern "DroneApp frontend/backend Python app" "DroneAppV4.py|DroneCom.py|GSTReceiver.py|MainWindow.py|StreamPanel.py|KeyboardController.py"

echo
echo "4/4 Closing terminal windows..."
close_windows_by_title

echo
echo "Remaining related processes:"
pgrep -af "lrs_mission_node|swarm_coordinator_node|rosbridge_websocket|rosapi_node|gstreamer_image_bridge|mavros_node|mavros_router|sim_vehicle.py|mavproxy.py|arducopter|ArduCopter|gazebo|gzserver|gzclient|runway_world.sh|DroneAppV4.py|DroneCom.py|GSTReceiver.py|MainWindow.py|StreamPanel.py|KeyboardController.py" || echo "  none"

echo
echo "Done."
