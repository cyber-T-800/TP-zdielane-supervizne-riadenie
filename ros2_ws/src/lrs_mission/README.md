# Simple automatic mission
A short guide on how to launch simple automatic mission (Gazebo + ArduPilot SITL + MAVROS + ROS2 mission node).
## Quick launch using script

Instead of manually opening the Gazebo, ArduPilot SITL and MAVROS terminals, you can use the prepared script.

## Setup simulation using script

### 1. Start simulation environment
```
cd ~/TP-zdielane-supervizne-riadenie
chmod +x start_lrs.sh
./start_lrs.sh
```
***NOTE:** If the workspace needs to be rebuilt after code changes, run:*
```
./start_lrs.sh --build
```
The script opens separate terminal windows for:
- Gazebo world
- ArduPilot SITL
- MAVROS

***NOTE:** The mission node is not started automatically. Start it manually in another terminal after MAVROS is connected.*

## Start mission node manually (Terminal 4)

### 2. Run mission node
```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws
source /opt/ros/$ROS_DISTRO/setup.bash
source install/setup.bash
ros2 run lrs_mission lrs_mission_node
```

---

## Setup simulation

### 1. Launch Gazebo world (Terminal 1)
```
gazebo /home/lrs/TP-zdielane-supervizne-riadenie/World_Dron/worlds/fei_lrs_gazebo_singleCamera.world
```
### 2. Launch ArduPilot SITL (Terminal 2)
```
cd ardupilot/ArduCopter
sim_vehicle.py -f gazebo-iris --console -l 48.15084570555732,17.072729745416016,150,0
```
***NOTE:** Wait until you see these messages:*
- `EKF3 IMU0 origin set`
- `EKF3 IMU1 origin set`
### 3. Launch MAVROS (Terminal 3)
```
ros2 run mavros mavros_node --ros-args -p fcu_url:=udp://127.0.0.1:14551@14555
```
## Start mission node (Terminal 4)

### 4. Build workspace
***NOTE:** Only required after code changes*
```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --symlink-install
source install/setup.bash
```
### 5. Run mission node
```
ros2 run lrs_mission lrs_mission_node
```
### 6. Stop request
```
ros2 topic pub --once /stop std_msgs/msg/Bool "{data: true}"
```
## Links 
https://github.com/KocurMaros/LRS-FEI/

https://drive.google.com/drive/folders/1QdG5tw1aGTgOuVNYAXl9BhDGObsHb8TW?usp=sharing

