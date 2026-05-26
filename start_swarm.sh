#!/usr/bin/env bash
set -Eeuo pipefail

# Flexible SWARM / REAL launcher.
#
# Modes:
#   --mode sim   starts Gazebo + ArduPilot SITL + MAVROS
#   --mode real  starts only MAVROS connected to real drone autopilot
#
# Drone count:
#   --drones 1
#   --drones 2
#   --drones 3
#
# Examples:
#   ./start_swarm.sh --build --mode sim --drones 3
#   ./start_swarm.sh --mode sim --drones 1
#   ./start_swarm.sh --build --mode real --drones 1 --drone1-fcu "/dev/ttyACM0:57600"
#   ./start_swarm.sh --mode real --drones 1 --drone1-fcu "udp://:14550@"
#
# Stop:
#   ./stop_sim.sh

REPO_DIR="$HOME/TP-zdielane-supervizne-riadenie"
ARDUPILOT_DIR="$HOME/ardupilot"
ROS_DISTRO="${ROS_DISTRO:-humble}"

MODE="sim"
DRONE_COUNT=3
BUILD=0

TERMINAL_CMD=""
SITL_TIMEOUT=240
MAVROS_START_DELAY=25
GST_START_DELAY=5
ROSBRIDGE_PORT=9090

GST_HOST="127.0.0.1"
GST_PORT1=2223
GST_PORT2=2224
GST_PORT3=2225

START_ROSBRIDGE=1
START_COORDINATOR=1
START_GSTREAMER=1
START_MONITOR=0

SIM_DRONE1_FCU_URL="udp://:14560@"
SIM_DRONE2_FCU_URL="udp://:14570@"
SIM_DRONE3_FCU_URL="udp://:14580@"

REAL_DRONE1_FCU_URL="/dev/ttyACM0:57600"
REAL_DRONE2_FCU_URL=""
REAL_DRONE3_FCU_URL=""

DRONE1_FCU_URL=""
DRONE2_FCU_URL=""
DRONE3_FCU_URL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --build) BUILD=1; shift ;;
    --mode) MODE="${2:?--mode needs sim or real}"; shift 2 ;;
    --drones) DRONE_COUNT="${2:?--drones needs 1, 2 or 3}"; shift 2 ;;
    --repo) REPO_DIR="${2:?--repo needs path}"; shift 2 ;;
    --ardupilot) ARDUPILOT_DIR="${2:?--ardupilot needs path}"; shift 2 ;;
    --drone1-fcu) DRONE1_FCU_URL="${2:?--drone1-fcu needs fcu_url}"; shift 2 ;;
    --drone2-fcu) DRONE2_FCU_URL="${2:?--drone2-fcu needs fcu_url}"; shift 2 ;;
    --drone3-fcu) DRONE3_FCU_URL="${2:?--drone3-fcu needs fcu_url}"; shift 2 ;;
    --sitl-timeout) SITL_TIMEOUT="${2:?--sitl-timeout needs seconds}"; shift 2 ;;
    --mavros-start-delay) MAVROS_START_DELAY="${2:?--mavros-start-delay needs seconds}"; shift 2 ;;
    --rosbridge-port) ROSBRIDGE_PORT="${2:?--rosbridge-port needs port}"; shift 2 ;;
    --gst-host) GST_HOST="${2:?--gst-host needs host}"; shift 2 ;;
    --gst-port1) GST_PORT1="${2:?--gst-port1 needs port}"; shift 2 ;;
    --gst-port2) GST_PORT2="${2:?--gst-port2 needs port}"; shift 2 ;;
    --gst-port3) GST_PORT3="${2:?--gst-port3 needs port}"; shift 2 ;;
    --no-rosbridge) START_ROSBRIDGE=0; shift ;;
    --no-coordinator) START_COORDINATOR=0; shift ;;
    --no-gstreamer) START_GSTREAMER=0; shift ;;
    --monitor) START_MONITOR=1; shift ;;
    -h|--help)
      cat <<EOF
Usage:
  $0 [--build] --mode sim|real --drones 1|2|3

Simulation examples:
  $0 --build --mode sim --drones 3
  $0 --mode sim --drones 1

Real drone examples:
  $0 --build --mode real --drones 1 --drone1-fcu "/dev/ttyACM0:57600"
  $0 --mode real --drones 1 --drone1-fcu "udp://:14550@"

Options:
  --repo PATH
  --ardupilot PATH
  --drone1-fcu FCU_URL
  --drone2-fcu FCU_URL
  --drone3-fcu FCU_URL
  --rosbridge-port 9090
  --gst-host 127.0.0.1
  --gst-port1 2223
  --gst-port2 2224
  --gst-port3 2225
  --no-rosbridge
  --no-coordinator
  --no-gstreamer
  --monitor
EOF
      exit 0
      ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
done

if [[ "$MODE" != "sim" && "$MODE" != "real" ]]; then
  echo "Error: --mode must be 'sim' or 'real'."
  exit 1
fi

if ! [[ "$DRONE_COUNT" =~ ^[1-3]$ ]]; then
  echo "Error: --drones must be 1, 2 or 3."
  exit 1
fi

ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"
WS_DIR="${REPO_DIR}/ros2_ws"
RUNWAY_SCRIPT="${REPO_DIR}/runway_world.sh"
LOG_DIR="${WS_DIR}/sim_logs/$(date +%Y%m%d_%H%M%S)_${MODE}_${DRONE_COUNT}drone"

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

wait_for_gazebo() {
  local timeout_s="${1:-60}"
  local elapsed=0
  echo "Waiting for Gazebo process..."
  while (( elapsed < timeout_s )); do
    if pgrep -f "gzserver|gazebo" >/dev/null 2>&1; then
      echo "Gazebo process detected."
      sleep 5
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "Warning: Gazebo process was not detected within ${timeout_s}s. Continuing anyway."
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

get_fcu_url() {
  local i="$1"
  local url=""

  if [[ "$MODE" == "sim" ]]; then
    case "$i" in
      1) url="${DRONE1_FCU_URL:-$SIM_DRONE1_FCU_URL}" ;;
      2) url="${DRONE2_FCU_URL:-$SIM_DRONE2_FCU_URL}" ;;
      3) url="${DRONE3_FCU_URL:-$SIM_DRONE3_FCU_URL}" ;;
    esac
  else
    case "$i" in
      1) url="${DRONE1_FCU_URL:-$REAL_DRONE1_FCU_URL}" ;;
      2) url="${DRONE2_FCU_URL:-$REAL_DRONE2_FCU_URL}" ;;
      3) url="${DRONE3_FCU_URL:-$REAL_DRONE3_FCU_URL}" ;;
    esac
  fi

  if [[ -z "$url" ]]; then
    echo "Error: FCU URL for real drone$i is not set." >&2
    echo "Use --drone${i}-fcu, for example:" >&2
    echo "  --drone${i}-fcu \"/dev/ttyUSB0:57600\"" >&2
    exit 1
  fi

  echo "$url"
}

get_gst_port() {
  case "$1" in
    1) echo "$GST_PORT1" ;;
    2) echo "$GST_PORT2" ;;
    3) echo "$GST_PORT3" ;;
  esac
}

require_file "$ROS_SETUP"
require_file "$WS_DIR"
require_cmd bash
require_cmd ros2
detect_terminal

if [[ "$MODE" == "sim" ]]; then
  require_file "$RUNWAY_SCRIPT"
  require_file "${ARDUPILOT_DIR}/ArduCopter"
  require_cmd sim_vehicle.py
fi

mkdir -p "$LOG_DIR"

MISSION_PATHS=()
DRONE_NAMES=()
SPAWN_X=()
SPAWN_Y=()
SPAWN_Z=()

for i in $(seq 1 "$DRONE_COUNT"); do
  mission="${WS_DIR}/missions/drone${i}.csv"
  require_file "$mission"
  MISSION_PATHS+=("$mission")
  DRONE_NAMES+=("drone${i}")
  SPAWN_X+=("0.0")
  SPAWN_Y+=("0.0")
  SPAWN_Z+=("0.0")
done

echo "Repo:       $REPO_DIR"
echo "Workspace:  $WS_DIR"
echo "ROS_DISTRO: $ROS_DISTRO"
echo "Mode:       $MODE"
echo "Drones:     $DRONE_COUNT"
echo "Terminal:   $TERMINAL_CMD"
echo "Logs:       $LOG_DIR"
echo

for i in $(seq 1 "$DRONE_COUNT"); do
  echo "drone$i FCU URL: $(get_fcu_url "$i")"
done

echo
echo "GStreamer:"
for i in $(seq 1 "$DRONE_COUNT"); do
  echo "  drone$i: /drone$i/image_raw -> udp://${GST_HOST}:$(get_gst_port "$i")"
done
echo

if (( BUILD == 1 )); then
  echo "[build] colcon build --symlink-install"
  cd "$WS_DIR"
  bash -lc "source '$ROS_SETUP' && colcon build --symlink-install"
  echo "[build] OK"
fi

COMMON_SOURCE="source '$ROS_SETUP' && source '$WS_DIR/install/setup.bash'"

if (( START_ROSBRIDGE == 1 )); then
  if ! bash -lc "$COMMON_SOURCE && ros2 pkg prefix rosbridge_server >/dev/null 2>&1"; then
    echo "Error: ROS package 'rosbridge_server' not found."
    echo "Install it with:"
    echo "  sudo apt update"
    echo "  sudo apt install -y ros-${ROS_DISTRO}-rosbridge-server"
    exit 1
  fi
fi

if (( START_GSTREAMER == 1 )); then
  if ! bash -lc "$COMMON_SOURCE && ros2 pkg executables swarm_mission 2>/dev/null | awk '{print \$2}' | grep -qx 'gstreamer_image_bridge'"; then
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

DRONE_NAMES_PARAM="["
MISSION_PATHS_PARAM="["
SPAWN_X_PARAM="["
SPAWN_Y_PARAM="["
SPAWN_Z_PARAM="["

for idx in "${!DRONE_NAMES[@]}"; do
  if [[ "$idx" -gt 0 ]]; then
    DRONE_NAMES_PARAM+=","
    MISSION_PATHS_PARAM+=","
    SPAWN_X_PARAM+=","
    SPAWN_Y_PARAM+=","
    SPAWN_Z_PARAM+=","
  fi

  DRONE_NAMES_PARAM+="'${DRONE_NAMES[$idx]}'"
  MISSION_PATHS_PARAM+="'${MISSION_PATHS[$idx]}'"
  SPAWN_X_PARAM+="${SPAWN_X[$idx]}"
  SPAWN_Y_PARAM+="${SPAWN_Y[$idx]}"
  SPAWN_Z_PARAM+="${SPAWN_Z[$idx]}"
done

DRONE_NAMES_PARAM+="]"
MISSION_PATHS_PARAM+="]"
SPAWN_X_PARAM+="]"
SPAWN_Y_PARAM+="]"
SPAWN_Z_PARAM+="]"

TERM_INDEX=1

if [[ "$MODE" == "sim" ]]; then
  open_terminal "SWARM ${TERM_INDEX} - Gazebo runway world" \
    "cd '$REPO_DIR' && bash '$RUNWAY_SCRIPT' 2>&1 | tee '$LOG_DIR/gazebo_runway.log'"
  TERM_INDEX=$((TERM_INDEX + 1))

  wait_for_gazebo 60

  for i in $(seq 1 "$DRONE_COUNT"); do
    sitl_log="$LOG_DIR/sitl_drone${i}.log"

    if [[ "$i" -eq 1 ]]; then
      sitl_cmd="cd '$ARDUPILOT_DIR/ArduCopter' && sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I1 2>&1 | tee '$sitl_log'"
    else
      sitl_cmd="cd '$ARDUPILOT_DIR/ArduCopter' && sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I${i} --sysid ${i} 2>&1 | tee '$sitl_log'"
    fi

    open_terminal "SWARM ${TERM_INDEX} - SITL drone${i}" "$sitl_cmd"
    TERM_INDEX=$((TERM_INDEX + 1))
  done

  for i in $(seq 1 "$DRONE_COUNT"); do
    wait_for_sitl_ekf_origin "drone${i}" "$LOG_DIR/sitl_drone${i}.log" "$SITL_TIMEOUT"
  done
else
  echo "Real mode selected: Gazebo, SITL and MAVProxy will NOT be started."
  echo "SAFETY CHECK: remove propellers or secure drone before testing."
fi

for i in $(seq 1 "$DRONE_COUNT"); do
  fcu_url="$(get_fcu_url "$i")"
  open_terminal "SWARM ${TERM_INDEX} - MAVROS drone${i}" \
    "$COMMON_SOURCE && ros2 run mavros mavros_node --ros-args -r __ns:=/drone${i} -p fcu_url:=$fcu_url -p tgt_system:=${i} 2>&1 | tee '$LOG_DIR/mavros_drone${i}.log'"
  TERM_INDEX=$((TERM_INDEX + 1))
done

echo "Waiting ${MAVROS_START_DELAY}s for MAVROS heartbeat/parameters..."
sleep "$MAVROS_START_DELAY"

if (( START_ROSBRIDGE == 1 )); then
  open_terminal "SWARM ${TERM_INDEX} - rosbridge websocket" \
    "$COMMON_SOURCE && ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=$ROSBRIDGE_PORT 2>&1 | tee '$LOG_DIR/rosbridge.log'"
  TERM_INDEX=$((TERM_INDEX + 1))
fi

if (( START_COORDINATOR == 1 )); then
  open_terminal "SWARM ${TERM_INDEX} - swarm coordinator" \
    "cd '$WS_DIR' && $COMMON_SOURCE && ros2 run swarm_mission swarm_coordinator_node --ros-args -p drone_names:=\"$DRONE_NAMES_PARAM\" -p mission_paths:=\"$MISSION_PATHS_PARAM\" -p spawn_offset_x:=\"$SPAWN_X_PARAM\" -p spawn_offset_y:=\"$SPAWN_Y_PARAM\" -p spawn_offset_z:=\"$SPAWN_Z_PARAM\" 2>&1 | tee '$LOG_DIR/swarm_coordinator.log'"
  TERM_INDEX=$((TERM_INDEX + 1))
fi

if (( START_GSTREAMER == 1 )); then
  echo "Starting GStreamer bridges..."
  sleep "$GST_START_DELAY"

  for i in $(seq 1 "$DRONE_COUNT"); do
    topic="/drone${i}/image_raw"
    port="$(get_gst_port "$i")"

    open_terminal "SWARM ${TERM_INDEX} - GStreamer drone${i}" \
      "cd '$WS_DIR' && $COMMON_SOURCE && ros2 run swarm_mission gstreamer_image_bridge --ros-args -p topic:=$topic -p host:=$GST_HOST -p port:=$port -p width:=640 -p height:=480 -p fps:=60 2>&1 | tee '$LOG_DIR/gstreamer_drone${i}.log'"
    TERM_INDEX=$((TERM_INDEX + 1))
  done
fi

if (( START_MONITOR == 1 )); then
  monitor_regex=""
  for i in $(seq 1 "$DRONE_COUNT"); do
    [[ -n "$monitor_regex" ]] && monitor_regex+="|"
    monitor_regex+="drone${i}"
  done

  open_terminal "SWARM ${TERM_INDEX} - Monitor" \
    "cd '$WS_DIR' && $COMMON_SOURCE && watch -n 1 'echo NODES:; ros2 node list | grep -E \"$monitor_regex|swarm|rosbridge|gstreamer\" || true; echo; echo TOPICS:; ros2 topic list | grep -E \"/($monitor_regex)/(state|image_raw|local_position|global_position)\" || true'"
  TERM_INDEX=$((TERM_INDEX + 1))
fi

echo
echo "Done."
echo "Mode: $MODE"
echo "Drones: $DRONE_COUNT"
echo
echo "Coordinator parameters:"
echo "  drone_names:      $DRONE_NAMES_PARAM"
echo "  mission_paths:    $MISSION_PATHS_PARAM"
echo "  spawn_offset_x:   $SPAWN_X_PARAM"
echo "  spawn_offset_y:   $SPAWN_Y_PARAM"
echo "  spawn_offset_z:   $SPAWN_Z_PARAM"
echo
echo "Logs:"
echo "  $LOG_DIR"
echo
echo "Frontend endpoints:"
if (( START_ROSBRIDGE == 1 )); then
  echo "  Rosbridge websocket: ws://localhost:${ROSBRIDGE_PORT}"
fi
if (( START_GSTREAMER == 1 )); then
  for i in $(seq 1 "$DRONE_COUNT"); do
    echo "  Drone${i} video UDP: ${GST_HOST}:$(get_gst_port "$i")"
  done
fi
echo
echo "Stop:"
echo "  ./stop_sim.sh"
