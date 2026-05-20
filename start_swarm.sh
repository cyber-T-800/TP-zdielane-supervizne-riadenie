#!/usr/bin/env bash
set -Eeuo pipefail

# Full SWARM launcher.
#
# Starts in separate terminal windows:
#   SWARM 1  - Gazebo runway world
#   SWARM 2  - SITL drone1
#   SWARM 3  - SITL drone2
#   SWARM 4  - SITL drone3
#   SWARM 5  - MAVROS drone1
#   SWARM 6  - MAVROS drone2
#   SWARM 7  - MAVROS drone3
#   SWARM 8  - rosbridge websocket, port 9090
#   SWARM 9  - swarm coordinator
#   SWARM 10 - GStreamer drone1, /drone1/image_raw -> UDP 127.0.0.1:5601, 640x480@60fps
#   SWARM 11 - GStreamer drone2, /drone2/image_raw -> UDP 127.0.0.1:5602, 640x480@60fps
#   SWARM 12 - GStreamer drone3, /drone3/image_raw -> UDP 127.0.0.1:5603, 640x480@60fps
#
# IMPORTANT:
#   sim_vehicle.py must be available globally in PATH.
#   If it is not, run:
#     echo 'export PATH=$PATH:$HOME/ardupilot/Tools/autotest' >> ~/.bashrc
#     source ~/.bashrc
#
# Usage:
#   chmod +x start_swarm.sh
#   ./start_swarm.sh
#   ./start_swarm.sh --build
#
# Stop:
#   ./stop_sim.sh

REPO_DIR="$HOME/TP-zdielane-supervizne-riadenie"
ARDUPILOT_DIR="$HOME/ardupilot"
ROS_DISTRO="${ROS_DISTRO:-humble}"
BUILD=0
TERMINAL_CMD=""
SITL_TIMEOUT=240
MAVROS_START_DELAY=25
GST_START_DELAY=5
ROSBRIDGE_PORT=9090
GST_HOST="127.0.0.1"
GST_PORT1=5601
GST_PORT2=5602
GST_PORT3=5603

START_ROSBRIDGE=1
START_COORDINATOR=1
START_GSTREAMER=1

# Stable defaults for ArduPilot SITL instances -I1, -I2, -I3.
DRONE1_FCU_URL="udp://:14560@"
DRONE2_FCU_URL="udp://:14570@"
DRONE3_FCU_URL="udp://:14580@"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build)
      BUILD=1
      shift
      ;;
    --repo)
      REPO_DIR="${2:?--repo needs path}"
      shift 2
      ;;
    --ardupilot)
      ARDUPILOT_DIR="${2:?--ardupilot needs path}"
      shift 2
      ;;
    --drone1-fcu)
      DRONE1_FCU_URL="${2:?--drone1-fcu needs fcu_url}"
      shift 2
      ;;
    --drone2-fcu)
      DRONE2_FCU_URL="${2:?--drone2-fcu needs fcu_url}"
      shift 2
      ;;
    --drone3-fcu)
      DRONE3_FCU_URL="${2:?--drone3-fcu needs fcu_url}"
      shift 2
      ;;
    --sitl-timeout)
      SITL_TIMEOUT="${2:?--sitl-timeout needs seconds}"
      shift 2
      ;;
    --mavros-start-delay)
      MAVROS_START_DELAY="${2:?--mavros-start-delay needs seconds}"
      shift 2
      ;;
    --rosbridge-port)
      ROSBRIDGE_PORT="${2:?--rosbridge-port needs port}"
      shift 2
      ;;
    --gst-host)
      GST_HOST="${2:?--gst-host needs host}"
      shift 2
      ;;
    --gst-port1)
      GST_PORT1="${2:?--gst-port1 needs port}"
      shift 2
      ;;
    --gst-port2)
      GST_PORT2="${2:?--gst-port2 needs port}"
      shift 2
      ;;
    --gst-port3)
      GST_PORT3="${2:?--gst-port3 needs port}"
      shift 2
      ;;
    --no-rosbridge)
      START_ROSBRIDGE=0
      shift
      ;;
    --no-coordinator)
      START_COORDINATOR=0
      shift
      ;;
    --no-gstreamer)
      START_GSTREAMER=0
      shift
      ;;
    -h|--help)
      cat <<EOF
Usage:
  $0 [--build] [--repo PATH] [--ardupilot PATH]

Optional:
  --drone1-fcu "udp://:14560@"
  --drone2-fcu "udp://:14570@"
  --drone3-fcu "udp://:14580@"
  --rosbridge-port 9090
  --gst-host 127.0.0.1
  --gst-port1 5601
  --gst-port2 5602
  --gst-port3 5603
  --no-rosbridge
  --no-coordinator
  --no-gstreamer

Example:
  $0 --build
EOF
      exit 0
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
done

ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"
WS_DIR="${REPO_DIR}/ros2_ws"
RUNWAY_SCRIPT="${REPO_DIR}/runway_world.sh"
LOG_DIR="${WS_DIR}/sim_logs/$(date +%Y%m%d_%H%M%S)_swarm_full"

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "Error: not found: $1"
    exit 1
  fi
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: command '$1' is not available in PATH."
    if [[ "$1" == "sim_vehicle.py" ]]; then
      echo
      echo "Add ArduPilot autotest tools to PATH:"
      echo "  echo 'export PATH=\$PATH:\$HOME/ardupilot/Tools/autotest' >> ~/.bashrc"
      echo "  source ~/.bashrc"
    fi
    exit 1
  fi
}

detect_terminal() {
  if command -v gnome-terminal >/dev/null 2>&1; then
    TERMINAL_CMD="gnome-terminal"
  elif command -v konsole >/dev/null 2>&1; then
    TERMINAL_CMD="konsole"
  elif command -v xfce4-terminal >/dev/null 2>&1; then
    TERMINAL_CMD="xfce4-terminal"
  elif command -v xterm >/dev/null 2>&1; then
    TERMINAL_CMD="xterm"
  else
    echo "Error: no supported terminal found."
    echo "Install for example:"
    echo "  sudo apt update && sudo apt install -y gnome-terminal"
    exit 1
  fi
}

open_terminal() {
  local title="$1"
  local cmd="$2"

  echo "Opening terminal: $title"

  case "$TERMINAL_CMD" in
    gnome-terminal)
      gnome-terminal --title="$title" -- bash -lc "$cmd; echo; echo '[$title] process finished. You can close this terminal.'; exec bash"
      ;;
    konsole)
      konsole --new-tab --title "$title" -e bash -lc "$cmd; echo; echo '[$title] process finished. You can close this terminal.'; exec bash"
      ;;
    xfce4-terminal)
      xfce4-terminal --title="$title" --command="bash -lc \"$cmd; echo; echo '[$title] process finished. You can close this terminal.'; exec bash\""
      ;;
    xterm)
      xterm -T "$title" -e bash -lc "$cmd; echo; echo '[$title] process finished. You can close this terminal.'; exec bash" &
      ;;
  esac
}

wait_for_sitl_ekf_origin() {
  local name="$1"
  local log_file="$2"
  local timeout_s="$3"
  local elapsed=0

  echo "[$name] Waiting for EKF origin:"
  echo "  AP: EKF3 IMU1 origin set"
  echo "  AP: EKF3 IMU0 origin set"

  while (( elapsed < timeout_s )); do
    if [[ -f "$log_file" ]] \
       && grep -q "AP: EKF3 IMU1 origin set" "$log_file" \
       && grep -q "AP: EKF3 IMU0 origin set" "$log_file"; then
      echo "[$name] SITL EKF origin OK."
      return 0
    fi

    if [[ -f "$log_file" ]] && grep -q "SIM_VEHICLE: MAVProxy exited" "$log_file"; then
      echo "[$name] Error: MAVProxy exited before EKF initialization."
      echo "Log: $log_file"
      return 1
    fi

    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo "[$name] Error: SITL did not print both EKF origin lines within ${timeout_s}s."
  echo "Log: $log_file"
  return 1
}

wait_for_ros_topic() {
  local topic="$1"
  local timeout_s="${2:-60}"
  local elapsed=0

  echo "Waiting for ROS topic: $topic"

  while (( elapsed < timeout_s )); do
    if bash -lc "source '$ROS_SETUP' && source '$WS_DIR/install/setup.bash' && tmp_file=\$(mktemp) && ros2 topic list 2>/dev/null > \$tmp_file && grep -qx '$topic' \$tmp_file; rc=\$?; rm -f \$tmp_file; exit \$rc"; then
      echo "Topic available: $topic"
      return 0
    fi

    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo "Warning: topic not found within ${timeout_s}s: $topic"
  return 0
}

require_file "$ROS_SETUP"
require_file "$WS_DIR"
require_file "$RUNWAY_SCRIPT"
require_file "${ARDUPILOT_DIR}/ArduCopter"

require_cmd bash
require_cmd sim_vehicle.py
require_cmd ros2
detect_terminal

mkdir -p "$LOG_DIR"

SITL1_LOG="$LOG_DIR/sitl_drone1.log"
SITL2_LOG="$LOG_DIR/sitl_drone2.log"
SITL3_LOG="$LOG_DIR/sitl_drone3.log"

MISSION1="${WS_DIR}/missions/drone1.csv"
MISSION2="${WS_DIR}/missions/drone2.csv"
MISSION3="${WS_DIR}/missions/drone3.csv"

require_file "$MISSION1"
require_file "$MISSION2"
require_file "$MISSION3"

echo "Repo:       $REPO_DIR"
echo "Workspace:  $WS_DIR"
echo "ArduPilot:  $ARDUPILOT_DIR"
echo "ROS_DISTRO: $ROS_DISTRO"
echo "Terminal:   $TERMINAL_CMD"
echo "Logs:       $LOG_DIR"
echo
echo "FCU URL:"
echo "  drone1: $DRONE1_FCU_URL"
echo "  drone2: $DRONE2_FCU_URL"
echo "  drone3: $DRONE3_FCU_URL"
echo
echo "GStreamer:"
echo "  drone1: /drone1/image_raw -> udp://${GST_HOST}:${GST_PORT1}"
echo "  drone2: /drone2/image_raw -> udp://${GST_HOST}:${GST_PORT2}"
echo "  drone3: /drone3/image_raw -> udp://${GST_HOST}:${GST_PORT3}"
echo

if (( BUILD == 1 )); then
  echo "[build] colcon build --symlink-install"
  cd "$WS_DIR"
  bash -lc "source '$ROS_SETUP' && colcon build --symlink-install"
  echo "[build] OK"
fi

# Validate required ROS packages/executables after build.
if (( START_ROSBRIDGE == 1 )); then
  if ! bash -lc "source '$ROS_SETUP' && source '$WS_DIR/install/setup.bash' && ros2 pkg prefix rosbridge_server >/dev/null 2>&1"; then
    echo "Error: ROS package 'rosbridge_server' not found."
    echo "Install it with:"
    echo "  sudo apt update"
    echo "  sudo apt install -y ros-${ROS_DISTRO}-rosbridge-server"
    exit 1
  fi
fi

if (( START_GSTREAMER == 1 )); then
  if ! bash -lc "source '$ROS_SETUP' && source '$WS_DIR/install/setup.bash' && ros2 pkg executables swarm_mission 2>/dev/null | awk '{print \$2}' | grep -qx 'gstreamer_image_bridge'"; then
    echo "Error: executable 'gstreamer_image_bridge' not found in package 'swarm_mission'."
    echo "Try rebuilding:"
    echo "  cd '$WS_DIR'"
    echo "  source '$ROS_SETUP'"
    echo "  colcon build --symlink-install"
    echo "  source install/setup.bash"
    exit 1
  fi

  if command -v gst-inspect-1.0 >/dev/null 2>&1; then
    if ! gst-inspect-1.0 x264enc >/dev/null 2>&1; then
      echo "Error: GStreamer element 'x264enc' not found."
      echo "Install required plugins:"
      echo "  sudo apt update"
      echo "  sudo apt install -y gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav"
      exit 1
    fi
  else
    echo "Warning: gst-inspect-1.0 not found. Cannot verify x264enc."
  fi
fi

COMMON_SOURCE="source '$ROS_SETUP' && source '$WS_DIR/install/setup.bash'"

open_terminal "SWARM 1 - Gazebo runway world" \
  "cd '$REPO_DIR' && bash '$RUNWAY_SCRIPT' 2>&1 | tee '$LOG_DIR/gazebo_runway.log'"

echo "Waiting 8 seconds for Gazebo..."
sleep 8

open_terminal "SWARM 2 - SITL drone1" \
  "cd '$ARDUPILOT_DIR/ArduCopter' && sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I1 2>&1 | tee '$SITL1_LOG'"

open_terminal "SWARM 3 - SITL drone2" \
  "cd '$ARDUPILOT_DIR/ArduCopter' && sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I2 --sysid 2 2>&1 | tee '$SITL2_LOG'"

open_terminal "SWARM 4 - SITL drone3" \
  "cd '$ARDUPILOT_DIR/ArduCopter' && sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I3 --sysid 3 2>&1 | tee '$SITL3_LOG'"

wait_for_sitl_ekf_origin "drone1" "$SITL1_LOG" "$SITL_TIMEOUT"
wait_for_sitl_ekf_origin "drone2" "$SITL2_LOG" "$SITL_TIMEOUT"
wait_for_sitl_ekf_origin "drone3" "$SITL3_LOG" "$SITL_TIMEOUT"

open_terminal "SWARM 5 - MAVROS drone1" \
  "$COMMON_SOURCE && ros2 run mavros mavros_node --ros-args -r __ns:=/drone1 -p fcu_url:=$DRONE1_FCU_URL -p tgt_system:=1 2>&1 | tee '$LOG_DIR/mavros_drone1.log'"

open_terminal "SWARM 6 - MAVROS drone2" \
  "$COMMON_SOURCE && ros2 run mavros mavros_node --ros-args -r __ns:=/drone2 -p fcu_url:=$DRONE2_FCU_URL -p tgt_system:=2 2>&1 | tee '$LOG_DIR/mavros_drone2.log'"

open_terminal "SWARM 7 - MAVROS drone3" \
  "$COMMON_SOURCE && ros2 run mavros mavros_node --ros-args -r __ns:=/drone3 -p fcu_url:=$DRONE3_FCU_URL -p tgt_system:=3 2>&1 | tee '$LOG_DIR/mavros_drone3.log'"

echo "Waiting ${MAVROS_START_DELAY}s for MAVROS heartbeat/parameters..."
sleep "$MAVROS_START_DELAY"

if (( START_ROSBRIDGE == 1 )); then
  open_terminal "SWARM 8 - rosbridge websocket" \
    "$COMMON_SOURCE && ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=$ROSBRIDGE_PORT 2>&1 | tee '$LOG_DIR/rosbridge.log'"
fi

if (( START_COORDINATOR == 1 )); then
  open_terminal "SWARM 9 - swarm coordinator" \
    "cd '$WS_DIR' && $COMMON_SOURCE && ros2 run swarm_mission swarm_coordinator_node --ros-args -p drone_names:=\"['drone1','drone2','drone3']\" -p mission_paths:=\"['$MISSION1','$MISSION2','$MISSION3']\" 2>&1 | tee '$LOG_DIR/swarm_coordinator.log'"
fi

if (( START_GSTREAMER == 1 )); then
  echo "Waiting for image topics before starting GStreamer bridges..."
  wait_for_ros_topic "/drone1/image_raw" 90
  wait_for_ros_topic "/drone2/image_raw" 90
  wait_for_ros_topic "/drone3/image_raw" 90
  sleep "$GST_START_DELAY"

  open_terminal "SWARM 10 - GStreamer drone1" \
    "cd '$WS_DIR' && $COMMON_SOURCE && ros2 run swarm_mission gstreamer_image_bridge --ros-args -p topic:=/drone1/image_raw -p host:=$GST_HOST -p port:=$GST_PORT1 -p width:=640 -p height:=480 -p fps:=60 2>&1 | tee '$LOG_DIR/gstreamer_drone1.log'"

  open_terminal "SWARM 11 - GStreamer drone2" \
    "cd '$WS_DIR' && $COMMON_SOURCE && ros2 run swarm_mission gstreamer_image_bridge --ros-args -p topic:=/drone2/image_raw -p host:=$GST_HOST -p port:=$GST_PORT2 -p width:=640 -p height:=480 -p fps:=60 2>&1 | tee '$LOG_DIR/gstreamer_drone2.log'"

  open_terminal "SWARM 12 - GStreamer drone3" \
    "cd '$WS_DIR' && $COMMON_SOURCE && ros2 run swarm_mission gstreamer_image_bridge --ros-args -p topic:=/drone3/image_raw -p host:=$GST_HOST -p port:=$GST_PORT3 -p width:=640 -p height:=480 -p fps:=60 2>&1 | tee '$LOG_DIR/gstreamer_drone3.log'"
fi

echo
echo "Done. Started terminals:"
echo "  SWARM 1  - Gazebo runway world"
echo "  SWARM 2  - SITL drone1"
echo "  SWARM 3  - SITL drone2"
echo "  SWARM 4  - SITL drone3"
echo "  SWARM 5  - MAVROS drone1"
echo "  SWARM 6  - MAVROS drone2"
echo "  SWARM 7  - MAVROS drone3"
if (( START_ROSBRIDGE == 1 )); then echo "  SWARM 8  - rosbridge websocket"; fi
if (( START_COORDINATOR == 1 )); then echo "  SWARM 9  - swarm coordinator"; fi
if (( START_GSTREAMER == 1 )); then
  echo "  SWARM 10 - GStreamer drone1, UDP ${GST_HOST}:${GST_PORT1}"
  echo "  SWARM 11 - GStreamer drone2, UDP ${GST_HOST}:${GST_PORT2}"
  echo "  SWARM 12 - GStreamer drone3, UDP ${GST_HOST}:${GST_PORT3}"
fi
echo
echo "Logs:"
echo "  $LOG_DIR"
echo
echo "Frontend endpoints:"
echo "  Rosbridge websocket: ws://localhost:${ROSBRIDGE_PORT}"
echo "  Drone1 video UDP: ${GST_HOST}:${GST_PORT1}"
echo "  Drone2 video UDP: ${GST_HOST}:${GST_PORT2}"
echo "  Drone3 video UDP: ${GST_HOST}:${GST_PORT3}"
echo
echo "Stop:"
echo "  ./stop_sim.sh"