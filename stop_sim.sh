#!/usr/bin/env bash
set -Eeuo pipefail

# Stop script for LRS / SWARM simulations.
#
# Ukonci procesy:
#   - Gazebo
#   - ArduPilot SITL / sim_vehicle.py / MAVProxy
#   - MAVROS
#   - lrs_mission_node
#   - swarm_coordinator_node
#   - terminaly otvorene skriptami start_lrs.sh / start_swarm.sh
#
# Pouzitie:
#   chmod +x stop_sim.sh
#   ./stop_sim.sh

echo "Stopping LRS / SWARM simulation processes..."
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
    echo "  killing PIDs: $pids"
    pkill -TERM -f "$pattern" || true
  fi
}

# Mission / ROS nodes
kill_pattern "LRS mission node" "lrs_mission_node"
kill_pattern "Swarm coordinator node" "swarm_coordinator_node"
kill_pattern "MAVROS node" "mavros_node"
kill_pattern "MAVROS router" "mavros_router"

# ArduPilot / MAVProxy / SITL
kill_pattern "sim_vehicle.py" "sim_vehicle.py.*gazebo-iris"
kill_pattern "ArduCopter SITL" "arducopter"
kill_pattern "MAVProxy" "mavproxy.py"
kill_pattern "ArduPilot terminal helper" "run_in_terminal_window.sh.*ArduCopter"

# Gazebo worlds
kill_pattern "Gazebo single camera world" "gazebo.*fei_lrs_gazebo_singleCamera.world"
kill_pattern "Gazebo runway world script" "runway_world.sh"
kill_pattern "Gazebo server/client" "gzserver|gzclient|gazebo"

echo
echo "Waiting for graceful shutdown..."
sleep 3

echo
echo "Force killing remaining simulation processes if needed..."

force_kill_pattern() {
  local description="$1"
  local pattern="$2"

  local pids
  pids="$(pgrep -f "$pattern" || true)"
  if [[ -n "$pids" ]]; then
    echo "[$description] force killing PIDs: $pids"
    pkill -KILL -f "$pattern" || true
  fi
}

force_kill_pattern "LRS mission node" "lrs_mission_node"
force_kill_pattern "Swarm coordinator node" "swarm_coordinator_node"
force_kill_pattern "MAVROS node" "mavros_node"
force_kill_pattern "MAVROS router" "mavros_router"
force_kill_pattern "sim_vehicle.py" "sim_vehicle.py.*gazebo-iris"
force_kill_pattern "ArduCopter SITL" "arducopter"
force_kill_pattern "MAVProxy" "mavproxy.py"
force_kill_pattern "ArduPilot terminal helper" "run_in_terminal_window.sh.*ArduCopter"
force_kill_pattern "Gazebo" "gzserver|gzclient|gazebo"
force_kill_pattern "runway_world.sh" "runway_world.sh"

echo
echo "Closing LRS/SWARM terminal windows..."

# Zavrie gnome-terminal/ine okna otvorene nasimi skriptami podla nazvu okna.
# Funguje, ak je nainstalovany wmctrl.
if command -v wmctrl >/dev/null 2>&1; then
  while IFS= read -r window_id; do
    [[ -n "$window_id" ]] && wmctrl -ic "$window_id" || true
  done < <(wmctrl -l | grep -E "LRS |SWARM " | awk '{print $1}')
else
  echo "  wmctrl is not installed, skipping terminal window close by title."
  echo "  To enable this, install:"
  echo "    sudo apt update && sudo apt install -y wmctrl"
fi

echo
echo "Remaining related processes:"
pgrep -af "lrs_mission_node|swarm_coordinator_node|mavros_node|sim_vehicle.py|mavproxy.py|arducopter|gazebo|gzserver|gzclient|runway_world.sh" || echo "  none"

echo
echo "Done."
