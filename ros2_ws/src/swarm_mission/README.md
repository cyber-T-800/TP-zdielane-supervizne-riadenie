# Swarm control

A short guide on how to launch the swarm stack either in simulation or with real drones.

The automatic launch script can start:
- Gazebo runway world
- ArduPilot SITL, only in simulation mode
- MAVROS for selected drones
- rosbridge websocket
- swarm coordinator
- GStreamer video bridge for selected drones

The number of drones can be selected with `--drones 1`, `--drones 2` or `--drones 3`.

## Quick launch using script

Instead of manually opening all required terminals, you can use the prepared script.

### 1. Simulation mode

Simulation mode starts Gazebo, ArduPilot SITL, MAVROS, rosbridge, swarm coordinator and GStreamer video bridges.

Run the script from the root directory of the repository. The first run should include the `--build` parameter:

```
cd ~/TP-zdielane-supervizne-riadenie
chmod +x start_swarm.sh
./start_swarm.sh --build --mode sim --drones 3
```

***NOTE:** If the workspace is already built and no code changes were made, the `--build` parameter is not required. In that case, run:*

```
./start_swarm.sh --mode sim --drones 3
```

For a simulation test with only one drone, run:

```
./start_swarm.sh --mode sim --drones 1
```

### 2. Real drone mode

Real drone mode does **not** start Gazebo, ArduPilot SITL or MAVProxy. It only starts MAVROS connected to the real autopilot, rosbridge, swarm coordinator and GStreamer bridge according to the selected number of drones.

For one real drone connected through USB, run:

```
cd ~/TP-zdielane-supervizne-riadenie
chmod +x start_swarm.sh
./start_swarm.sh --build --mode real --drones 1 --drone1-fcu "/dev/ttyACM0:57600"
```

***NOTE:** If the workspace is already built and no code changes were made, run without `--build`:*

```
./start_swarm.sh --mode real --drones 1 --drone1-fcu "/dev/ttyACM0:57600"
```

If the real drone is connected through another serial device, use for example:

```
./start_swarm.sh --mode real --drones 1 --drone1-fcu "/dev/ttyUSB0:57600"
```

If the real drone is connected through UDP telemetry, use for example:

```
./start_swarm.sh --mode real --drones 1 --drone1-fcu "udp://:14550@"
```

***SAFETY NOTE:** For real-drone testing, remove propellers or secure the drone before starting control nodes. The script does not start Gazebo or SITL in real mode.*

### 3. Drone count

The number of active drones is selected with:

```
--drones 1
--drones 2
--drones 3
```

Examples:

```
./start_swarm.sh --mode sim --drones 1
./start_swarm.sh --mode sim --drones 2
./start_swarm.sh --mode sim --drones 3
```

For real drones, provide FCU URLs for every selected drone:

```
./start_swarm.sh --mode real --drones 2 \
  --drone1-fcu "/dev/ttyACM0:57600" \
  --drone2-fcu "/dev/ttyUSB0:57600"
```

### 4. Optional arguments

Disable rosbridge:

```
./start_swarm.sh --mode sim --drones 3 --no-rosbridge
```

Disable swarm coordinator:

```
./start_swarm.sh --mode sim --drones 3 --no-coordinator
```

Disable GStreamer video bridges:

```
./start_swarm.sh --mode sim --drones 3 --no-gstreamer
```

Start monitor terminal:

```
./start_swarm.sh --mode sim --drones 3 --monitor
```

Change GStreamer target host, for example when the application runs on another computer:

```
./start_swarm.sh --mode sim --drones 3 --gst-host 192.168.1.100
```

### 5. Frontend endpoints

By default, rosbridge is available at:

```
ws://localhost:9090
```

Default GStreamer video streams:

```
drone1: UDP 127.0.0.1:2223
drone2: UDP 127.0.0.1:2224
drone3: UDP 127.0.0.1:2225
```

### 6. DroneAppV4

If rosbridge and GStreamer are running on the same computer as the application, start DroneAppV4 with:

```
cd ~/TP-zdielane-supervizne-riadenie/DroneApp_v4
python3 DroneAppV4.py --ros-host localhost --ros-port 9090 --gst 2223 2224 2225
```

If the application runs on another computer, replace `localhost` with the IP address of the computer running rosbridge.

## Stop simulation using script

Instead of manually closing all opened terminal windows, you can use the prepared stop script.

### Stop all processes

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
