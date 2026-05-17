#!/usr/bin/env bash
set -Eeuo pipefail

# LRS simple automatic mission spustac po MAVROS.
#
# Tento skript vykona iba pripravu simulacie:
#   LRS 1 - Gazebo
#   LRS 2 - ArduPilot SITL
#   LRS 3 - MAVROS
#
# Automaticku misiu uz nespusta.
# Misiu spustis manualne v dalsom terminali:
#   ros2 run lrs_mission lrs_mission_node
#
# Pouzitie:
#   chmod +x start_lrs_until_mavros.sh
#   ./start_lrs_until_mavros.sh
#   ./start_lrs_until_mavros.sh --build
#
# Stop:
#   zavri jednotlive terminaly alebo:
#   pkill -f "gazebo.*fei_lrs_gazebo_singleCamera.world"
#   pkill -f "sim_vehicle.py.*gazebo-iris"
#   pkill -f "mavros_node"

REPO_DIR="$HOME/TP-zdielane-supervizne-riadenie"
ARDUPILOT_DIR="$HOME/ardupilot"
ROS_DISTRO="${ROS_DISTRO:-humble}"
BUILD=0
TERMINAL_CMD=""
SITL_TIMEOUT=180
MAVROS_START_DELAY=10

# Port, ktory ti fungoval pri manualnom spusteni simple automatic mission.
LRS_FCU_URL="udp://:14550@"

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
    --fcu)
      LRS_FCU_URL="${2:?--fcu potrebuje fcu_url}"
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
  --fcu "udp://:14550@"

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
WORLD="${REPO_DIR}/World_Dron/worlds/fei_lrs_gazebo_singleCamera.world"
LOG_DIR="${WS_DIR}/sim_logs/$(date +%Y%m%d_%H%M%S)_lrs_until_mavros"

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
  local log_file="$1"
  local timeout_s="$2"
  local elapsed=0

  echo "Cakam na SITL EKF origin:"
  echo "  AP: EKF3 IMU1 origin set"
  echo "  AP: EKF3 IMU0 origin set"

  while (( elapsed < timeout_s )); do
    if [[ -f "$log_file" ]] \
       && grep -q "AP: EKF3 IMU1 origin set" "$log_file" \
       && grep -q "AP: EKF3 IMU0 origin set" "$log_file"; then
      echo "SITL EKF origin OK."
      return 0
    fi

    if [[ -f "$log_file" ]] && grep -q "SIM_VEHICLE: MAVProxy exited" "$log_file"; then
      echo "Chyba: MAVProxy skoncil pred EKF inicializaciou."
      echo "Log: $log_file"
      return 1
    fi

    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo "Chyba: SITL nevypisal obidva EKF origin riadky do ${timeout_s}s."
  echo "Log: $log_file"
  return 1
}

require_file "$ROS_SETUP"
require_file "$WS_DIR"
require_file "$WORLD"
require_file "${ARDUPILOT_DIR}/ArduCopter"

require_cmd gazebo
require_cmd sim_vehicle.py
require_cmd ros2
detect_terminal

mkdir -p "$LOG_DIR"

SITL_LOG="$LOG_DIR/sitl_drone1.log"

echo "Repo:       $REPO_DIR"
echo "Workspace:  $WS_DIR"
echo "ArduPilot:  $ARDUPILOT_DIR"
echo "ROS_DISTRO: $ROS_DISTRO"
echo "Terminal:   $TERMINAL_CMD"
echo "Logy:       $LOG_DIR"
echo "FCU URL:    $LRS_FCU_URL"
echo

if (( BUILD == 1 )); then
  echo "[build] colcon build --symlink-install"
  cd "$WS_DIR"
  bash -lc "source '$ROS_SETUP' && colcon build --symlink-install"
  echo "[build] OK"
fi

open_terminal "LRS 1 - Gazebo" \
  "cd '$REPO_DIR' && gazebo '$WORLD' 2>&1 | tee '$LOG_DIR/gazebo.log'"

echo "Cakam 8 sekund na nacitanie Gazeba..."
sleep 8

open_terminal "LRS 2 - ArduPilot SITL" \
  "cd '$ARDUPILOT_DIR/ArduCopter' && sim_vehicle.py -f gazebo-iris --console -l 48.15084570555732,17.072729745416016,150,0 2>&1 | tee '$SITL_LOG'"

wait_for_sitl_ekf_origin "$SITL_LOG" "$SITL_TIMEOUT"

open_terminal "LRS 3 - MAVROS" \
  "source '$ROS_SETUP' && ros2 run mavros mavros_node --ros-args -p fcu_url:=$LRS_FCU_URL 2>&1 | tee '$LOG_DIR/mavros_drone1.log'"

echo "Cakam ${MAVROS_START_DELAY}s, aby MAVROS nacital heartbeat/parametre..."
sleep "$MAVROS_START_DELAY"

echo
echo "Hotovo. Skript skoncil po LRS 3 - MAVROS."
echo
echo "Otvorene terminaly:"
echo "  LRS 1 - Gazebo"
echo "  LRS 2 - ArduPilot SITL"
echo "  LRS 3 - MAVROS"
echo
echo "Logy:"
echo "  $LOG_DIR"
echo
echo "Manualna kontrola:"
echo "  cd '$WS_DIR'"
echo "  source '$ROS_SETUP'"
echo "  source install/setup.bash"
echo "  ros2 node list"
echo "  ros2 topic echo --once /mavros/state"
echo
echo "Manualne spustenie simple automatic mission:"
echo "  cd '$WS_DIR'"
echo "  source '$ROS_SETUP'"
echo "  source install/setup.bash"
echo "  ros2 run lrs_mission lrs_mission_node"
echo
echo "Stop:"
echo "  zavri jednotlive terminaly"
echo "  alebo pouzi:"
echo "  pkill -f 'gazebo.*fei_lrs_gazebo_singleCamera.world'"
echo "  pkill -f 'sim_vehicle.py.*gazebo-iris'"
echo "  pkill -f 'mavros_node'"
