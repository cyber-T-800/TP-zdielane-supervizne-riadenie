# DroneApp

Minimal ROS-native desktop monitor for up to 3 drone camera streams.

Layout:
- Main stream on the left (large panel)
- Secondary streams on the right (two small stacked panels)
- Fixed app window size (does not keep resizing)
- Camera resolution is printed in terminal when detected/changed

## Install

```bash
cd DroneApp
python3 -m pip install -r requirements.txt
```

## Run

Terminal 1 (Gazebo + drone simulation):

```bash
source /opt/ros/humble/setup.bash
ros2 topic list | grep image_raw
```

Terminal 2 (app):

```bash
source /opt/ros/humble/setup.bash
python3 DroneApp/main.py
```

By default the app subscribes to:

- `/front_camera/image_raw`
- `/stereo_camera/left/image_raw`
- `/stereo_camera/right/image_raw`

You can override topics (up to 3, repeat `--topic`):

```bash
python3 DroneApp/main.py \
  --topic "Drone 1@/front_camera/image_raw" \
  --topic "Drone 2@/fei_lrs_drone/stereo_camera/image_raw" \
  --topic "Drone 3@/another_drone/front_camera/image_raw"
```

## Architecture Notes

- ROS receiver subscribes to all configured topics in one worker thread.
- UI has a main camera panel and two secondary camera panels.
- `DroneSupervisorModel` is a shared state layer prepared for future control and mission-management actions.
