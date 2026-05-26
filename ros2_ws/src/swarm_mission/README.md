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

## Manual single-drone simulation with DroneAppV4

This section describes the manual test setup used for running the swarm stack with only one simulated drone and the `DroneApp_v4` visualization/control application.

### 1. Build workspace

Run this first, or after code changes:

```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### 2. Launch Gazebo world (Terminal 1)

```
cd ~/TP-zdielane-supervizne-riadenie
bash runway_world.sh
```

### 3. Launch ArduPilot SITL for one drone (Terminal 2)

```
cd ~/ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter -f gazebo-iris --console -I1
```

***NOTE:** Wait until you see these messages:*
- `EKF3 IMU0 origin set`
- `EKF3 IMU1 origin set`

### 4. Launch MAVROS for drone1 (Terminal 3)

```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run mavros mavros_node --ros-args \
  -r __ns:=/drone1 \
  -p fcu_url:=udp://:14560@ \
  -p tgt_system:=1
```

You can check the MAVROS connection with:

```
ros2 topic echo --once /drone1/state
```

The expected value is:

```
connected: true
```

### 5. Launch rosbridge websocket (Terminal 4)

```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 launch rosbridge_server rosbridge_websocket_launch.xml port:=9090
```

The expected output is:

```
Rosbridge WebSocket server started on port 9090
```

### 6. Launch swarm coordinator for one drone (Terminal 5)

For single-drone testing, the coordinator must receive one drone name, one mission file and one value for each spawn offset parameter:

```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run swarm_mission swarm_coordinator_node --ros-args \
  -p drone_names:="['drone1']" \
  -p mission_paths:="['/home/lrs/TP-zdielane-supervizne-riadenie/ros2_ws/missions/drone_plus.csv']" \
  -p spawn_offset_x:="[0.0]" \
  -p spawn_offset_y:="[0.0]" \
  -p spawn_offset_z:="[0.0]"
```

### 7. Launch GStreamer video bridge for drone1 (Terminal 6)

First check that the image topic exists:

```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 topic list | grep image_raw
```

The expected topic is:

```
/drone1/image_raw
```

Then start the GStreamer bridge:

```
ros2 run swarm_mission gstreamer_image_bridge --ros-args \
  -p topic:=/drone1/image_raw \
  -p host:=127.0.0.1 \
  -p port:=2223 \
  -p width:=640 \
  -p height:=480 \
  -p fps:=60
```

The expected output is:

```
GStreamer VideoWriter opened successfully
```

### 8. Launch DroneAppV4 (Terminal 7)

The application connects to ROS through rosbridge. Use `localhost` if the app runs on the same computer as rosbridge:

```
cd ~/TP-zdielane-supervizne-riadenie/DroneApp_v4
python3 DroneAppV4.py --ros-host localhost --ros-port 9090 --gst 2223 2224 2225
```

***NOTE:** The app expects three GStreamer ports when using `--gst`. For a single-drone test, only the first stream on port `2223` is required, but all three port arguments still need to be provided.*

### 9. Keyboard control in DroneAppV4

Click inside the application window first, so it has keyboard focus.

Basic controls:

- `T` - takeover / release manual control for the selected drone
- `Q` - switch selected drone/panel
- `W` - move forward
- `S` - move backward
- `A` - yaw left
- `D` - yaw right
- `Ctrl` - move up
- `Space` - move down

The application publishes manual-control commands through:

```
/supervisor/takeover_request
/supervisor/release_request
/supervisor/manual_cmd_vel
```

### 10. Stop the test

Use the stop script from the repository root:

```
cd ~/TP-zdielane-supervizne-riadenie
./stop_sim.sh
```


## Links 
https://github.com/KocurMaros/LRS-FEI/

https://drive.google.com/drive/folders/1QdG5tw1aGTgOuVNYAXl9BhDGObsHb8TW?usp=sharing
