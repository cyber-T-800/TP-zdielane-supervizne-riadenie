# World_Dron

Single-camera Gazebo world package with only important files:

- `worlds/fei_lrs_gazebo_singleCamera.world`
- `models/hangar/`
- `models/fei_lrs_drone/`

## Prerequisites

- Gazebo 11 installed
- ROS 2 Humble installed
- `ardupilot_gazebo` built (`ardupilot_gazebo/build/libArduPilotPlugin.so`)
- ArduPilot repo at `ardupilot/`

## Run (manual commands)

Open repo root:

```bash
cd /home/lrs/TP-zdielane-supervizne-riadenie
```

### Terminal 1: Gazebo world

```bash
source /usr/share/gazebo/setup.sh
source /opt/ros/humble/setup.bash
gazebo --verbose /home/lrs/TP-zdielane-supervizne-riadenie/World_Dron/worlds/fei_lrs_gazebo_singleCamera.world
```

### Terminal 2: SITL - drone with single camera

First run (clean):

```bash
cd /home/lrs/TP-zdielane-supervizne-riadenie/ardupilot
./Tools/autotest/sim_vehicle.py -w -v ArduCopter -f gazebo-iris --console -l 48.15084570555732,17.072729745416016,150,0
```

Next runs:

```bash
cd /home/lrs/TP-zdielane-supervizne-riadenie/ardupilot
./Tools/autotest/sim_vehicle.py -N -v ArduCopter -f gazebo-iris --console -l 48.15084570555732,17.072729745416016,150,0
```