#!/usr/bin/env bash
set -Eeuo pipefail

# SWARM terminal spustac po MAVROS.
#
# Tento skript vykona iba kroky po SWARM 7:
#   SWARM 1 - Gazebo runway world
#   SWARM 2 - SITL drone1
#   SWARM 3 - SITL drone2
#   SWARM 4 - SITL drone3
#   SWARM 5 - MAVROS drone1
#   SWARM 6 - MAVROS drone2
#   SWARM 7 - MAVROS drone3
#
# Automaticku misiu uz nespusta.
# Tu si potom spustis manualne v novom terminali.
#
# Pouzitie:
#   chmod +x start_swarm_until_mavros.sh
#   ./start_swarm_until_mavros.sh
#   ./start_swarm_until_mavros.sh --build
#
# Stop:
#   zavri jednotlive terminaly alebo:
#   pkill -f "runway_world.sh"
#   pkill -f "sim_vehicle.py.*gazebo-iris"
#   pkill -f "mavros_node"

REPO_DIR="$HOME/TP-zdielane-supervizne-riadenie"
ARDUPILOT_DIR="$HOME/ardupilot"
ROS_DISTRO="${ROS_DISTRO:-humble}"
BUILD=0
TERMINAL_CMD=""
SITL_TIMEOUT=240
MAVROS_START_DELAY=25

# Stabilne defaulty pre ArduPilot SITL instancie -I1, -I2, -I3.
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
      REPO_DIR="${2:?--repo potrebuje cestu}"
      shift 2
      ;;
    --ardupilot)
      ARDUPILOT_DIR="${2:?--ardupilot potrebuje cestu}"
      shift 2
      ;;
    --drone1-fcu)
      DRONE1_FCU_URL="${2:?--drone1-fcu potrebuje fcu_url}"
      shift 2
      ;;
    --drone2-fcu)
      DRONE2_FCU_URL="${2:?--drone2-fcu potrebuje fcu_url}"
      shift 2
      ;;
    --drone3-fcu)
      DRONE3_FCU_URL="${2:?--drone3-fcu potrebuje fcu_url}"
      shift 2
      ;;
    --sitl-timeout)
      SITL_TIMEOUT="${2:?--sitl-timeout potrebuje sekundy}"
      shift 2
      ;;
    --mavros-start-delay)
      MAVROS_START_DELAY="${2:?--mavros-start-delay potrebuje sekundy}"
      shift 2
      ;;
    -h|--help)
      cat <<EOF
Pouzitie:
  $0 [--build] [--repo PATH] [--ardupilot PATH]

Volitelne:
  --drone1-fcu "udp://:14560@"
  --drone2-fcu "udp://:14570@"
  --drone3-fcu "udp://:14580@"

Priklad:
  $0 --build
EOF
      exit 0
      ;;
    *)
      echo "Neznamy parameter: $1"
      exit 1
      ;;
  esac
done

ROS_SETUP="/opt/ros/${ROS_DISTRO}/setup.bash"
WS_DIR="${REPO_DIR}/ros2_ws"
RUNWAY_SCRIPT="${REPO_DIR}/runway_world.sh"
LOG_DIR="${WS_DIR}/sim_logs/$(date +%Y%m%d_%H%M%S)_swarm_until_mavros"

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "Chyba: nenajdene: $1"
    exit 1
  fi
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Chyba: prikaz '$1' nie je dostupny."
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
    echo "Chyba: nenasiel som podporovany terminal."
    echo "Nainstaluj napriklad:"
    echo "  sudo apt update && sudo apt install -y gnome-terminal"
    exit 1
  fi
}

open_terminal() {
  local title="$1"
  local cmd="$2"

  echo "Otváram terminál: $title"

  case "$TERMINAL_CMD" in
    gnome-terminal)
      gnome-terminal --title="$title" -- bash -lc "$cmd; echo; echo '[$title] proces skoncil. Terminal mozes zavriet.'; exec bash"
      ;;
    konsole)
      konsole --new-tab --title "$title" -e bash -lc "$cmd; echo; echo '[$title] proces skoncil. Terminal mozes zavriet.'; exec bash"
      ;;
    xfce4-terminal)
      xfce4-terminal --title="$title" --command="bash -lc \"$cmd; echo; echo '[$title] proces skoncil. Terminal mozes zavriet.'; exec bash\""
      ;;
    xterm)
      xterm -T "$title" -e bash -lc "$cmd; echo; echo '[$title] proces skoncil. Terminal mozes zavriet.'; exec bash" &
      ;;
  esac
}

wait_for_sitl_ekf_origin() {
  local name="$1"
  local log_file="$2"
  local timeout_s="$3"
  local elapsed=0

  echo "[$name] Cakam na EKF origin:"
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
      echo "[$name] Chyba: MAVProxy skoncil pred EKF inicializaciou."
      echo "Log: $log_file"
      return 1
    fi

    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo "[$name] Chyba: SITL nevypisal obidva EKF origin riadky do ${timeout_s}s."
  echo "Log: $log_file"
  return 1
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

echo "Repo:       $REPO_DIR"
echo "Workspace:  $WS_DIR"
echo "ArduPilot:  $ARDUPILOT_DIR"
echo "ROS_DISTRO: $ROS_DISTRO"
echo "Terminal:   $TERMINAL_CMD"
echo "Logy:       $LOG_DIR"
echo
echo "FCU URL:"
echo "  drone1: $DRONE1_FCU_URL"
echo "  drone2: $DRONE2_FCU_URL"
echo "  drone3: $DRONE3_FCU_URL"
echo

if (( BUILD == 1 )); then
  echo "[build] colcon build --symlink-install"
  cd "$WS_DIR"
  bash -lc "source '$ROS_SETUP' && colcon build --symlink-install"
  echo "[build] OK"
fi

open_terminal "SWARM 1 - Gazebo runway world" \
  "cd '$REPO_DIR' && bash '$RUNWAY_SCRIPT' 2>&1 | tee '$LOG_DIR/gazebo_runway.log'"

echo "Cakam 8 sekund na nacitanie Gazeba..."
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
  "source '$ROS_SETUP' && ros2 run mavros mavros_node --ros-args -r __ns:=/drone1 -p fcu_url:=$DRONE1_FCU_URL -p tgt_system:=1 2>&1 | tee '$LOG_DIR/mavros_drone1.log'"

open_terminal "SWARM 6 - MAVROS drone2" \
  "source '$ROS_SETUP' && ros2 run mavros mavros_node --ros-args -r __ns:=/drone2 -p fcu_url:=$DRONE2_FCU_URL -p tgt_system:=2 2>&1 | tee '$LOG_DIR/mavros_drone2.log'"

open_terminal "SWARM 7 - MAVROS drone3" \
  "source '$ROS_SETUP' && ros2 run mavros mavros_node --ros-args -r __ns:=/drone3 -p fcu_url:=$DRONE3_FCU_URL -p tgt_system:=3 2>&1 | tee '$LOG_DIR/mavros_drone3.log'"

echo "Cakam ${MAVROS_START_DELAY}s, aby MAVROS nacital heartbeat/parametre..."
sleep "$MAVROS_START_DELAY"

echo
echo "Hotovo. Skript skoncil po SWARM 7."
echo
echo "Otvorene terminaly:"
echo "  SWARM 1 - Gazebo runway world"
echo "  SWARM 2 - SITL drone1"
echo "  SWARM 3 - SITL drone2"
echo "  SWARM 4 - SITL drone3"
echo "  SWARM 5 - MAVROS drone1"
echo "  SWARM 6 - MAVROS drone2"
echo "  SWARM 7 - MAVROS drone3"
echo
echo "Logy:"
echo "  $LOG_DIR"
echo
echo "Manualna kontrola:"
echo "  cd '$WS_DIR'"
echo "  source '$ROS_SETUP'"
echo "  source install/setup.bash"
echo "  ros2 node list | grep drone"
echo "  ros2 topic list | grep drone"
echo
echo "Manualne spustenie misie:"
echo "  cd '$WS_DIR'"
echo "  source '$ROS_SETUP'"
echo "  source install/setup.bash"
echo "  ros2 run swarm_mission swarm_coordinator_node --ros-args \\"
echo "    -p drone_names:=\"['drone1','drone2','drone3']\" \\"
echo "    -p mission_paths:=\"['$MISSION1','$MISSION2','$MISSION3']\""
echo
echo "Stop:"
echo "  zavri jednotlive terminaly"
echo "  alebo pouzi:"
echo "  pkill -f 'runway_world.sh'"
echo "  pkill -f 'sim_vehicle.py.*gazebo-iris'"
echo "  pkill -f 'mavros_node'"
