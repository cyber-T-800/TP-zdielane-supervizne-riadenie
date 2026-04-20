# Swarm control
A short guide on how to launch swarm mission (Gazebo + ArduPilot SITL + MAVROS + ROS2 mission node).
## Setup simulation

### 1. Launch Gazebo world (Terminal 1)
```
gazebo /home/lrs/TP-zdielane-supervizne-riadenie/World_Dron/worlds/iris_arducopter_runway.world
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

