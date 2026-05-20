# Swarm control

A short guide on how to launch swarm mission (Gazebo + ArduPilot SITL + MAVROS + ROS2 mission node).

## Quick launch using script

Instead of manually opening all required terminals, you can use the prepared script.

### 1. Start simulation

Run the script from the root directory of the repository. The first run should include the `--build` parameter:

```
cd ~/TP-zdielane-supervizne-riadenie
chmod +x start_swarm.sh
./start_swarm.sh --build
```

***NOTE:** If the workspace is already built and no code changes were made, the `--build` parameter is not required. In that case, run:*

```
./start_swarm.sh
```

The script opens separate terminal windows for:
- Gazebo runway world
- 3x ArduPilot SITL
- 3x MAVROS
- rosbridge websocket on port `9090`
- swarm coordinator
- 3x GStreamer video bridge

The swarm mission coordinator is started automatically by the script.


## Stop simulation using script

Instead of manually closing all opened terminal windows, you can use the prepared stop script.

### 2. Stop all simulation processes

Run the script from the root directory of the repository:

```
cd ~/TP-zdielane-supervizne-riadenie
chmod +x stop_sim.sh
./stop_sim.sh
```

The script stops Gazebo, ArduPilot SITL, MAVProxy, MAVROS, rosbridge, swarm coordinator, GStreamer bridges and opened terminal windows.

***NOTE:** To close terminal windows automatically by title, `wmctrl` is required. If it is not installed, run:*

```
sudo apt update
sudo apt install -y wmctrl
```

---

## Manual launch

## Setup simulation

### 1. Launch Gazebo world (Terminal 1)
```
cd TP-zdielane-supervizne-riadenie/
bash runway_world.sh
```
### 2. Launch 3 ArduPilot SITL (Terminal 2,3,4)
```
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I1
```
```
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I2 --sysid 2
```
```
cd ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I3 --sysid 3
```
***NOTE:** Wait until you see these messages:*
- `EKF3 IMU0 origin set`
- `EKF3 IMU1 origin set`
### 3. Launch MAVROS 3 times (Terminal 5,6,7)
```
ros2 run mavros mavros_node --ros-args -p fcu_url:=udp://127.0.0.1:14561@14561 -p tgt_system:=1 --remap __ns:=/drone1
```
```
ros2 run mavros mavros_node --ros-args -p fcu_url:=udp://127.0.0.1:14571@14575 -p tgt_system:=2 --remap __ns:=/drone2
```
```
ros2 run mavros mavros_node --ros-args -p fcu_url:=udp://127.0.0.1:14581@145581 -p tgt_system:=3 --remap __ns:=/drone3
```
## Start mission node (Terminal 8)

### 4. Build workspace
***NOTE:** Only required after code changes*
```
cd TP-zdielane-supervizne-riadenie/ros2_ws/
colcon build
source install/setup.bash
```
### 5. Run mission node
```
ros2 run swarm_mission swarm_coordinator_node --ros-args \
  -p drone_names:="['drone1','drone2','drone3']" \
  -p mission_paths:="['/home/lrs/TP-zdielane-supervizne-riadenie/ros2_ws/missions/drone1.csv','/home/lrs/TP-zdielane-supervizne-riadenie/ros2_ws/missions/drone2.csv','/home/lrs/TP-zdielane-supervizne-riadenie/ros2_ws/missions/drone3.csv']"
```

## Links 
https://github.com/KocurMaros/LRS-FEI/

https://drive.google.com/drive/folders/1QdG5tw1aGTgOuVNYAXl9BhDGObsHb8TW?usp=sharing
