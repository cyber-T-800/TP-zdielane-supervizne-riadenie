# GStreamer Camera Bridge

A short guide on how to stream ROS 2 camera topics from Gazebo simulation through GStreamer.

This setup converts ROS 2 image topics:

```
/drone1/image_raw
/drone2/image_raw
/drone3/image_raw
```
into UDP H264 GStreamer streams:
### Build worskace
```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select swarm_mission
source install/setup.bash
```
## Local test on one computer
For local testing, use:
```
host = 127.0.0.1
```
Each drone needs:
- `one terminal for gstreamer_image_bridge`
- `one terminal for GStreamer receiver`

### Drone1 stream
#### Terminal 1 - launch bridge
```
cd ~/TP-zdielane-supervizne-riadenie/ros2_ws

source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 run swarm_mission gstreamer_image_bridge \
  --ros-args \
  -p topic:=/drone1/image_raw \
  -p host:=127.0.0.1 \
  -p port:=5601 \
  -p width:=640 \
  -p height:=480 \
  -p fps:=60
```
#### Terminal 2 - launch receiver
```
gst-launch-1.0 -v \
  udpsrc port=5601 caps="application/x-rtp, media=video, encoding-name=H264, payload=96" \
  ! rtph264depay \
  ! decodebin \
  ! videoconvert \
  ! autovideosink
```
### Drone2 Stream
#### Terminal 3 - launch bridge
```
ros2 run swarm_mission gstreamer_image_bridge \
  --ros-args \
  -p topic:=/drone2/image_raw \
  -p host:=127.0.0.1 \
  -p port:=5602 \
  -p width:=640\
  -p height:=480 \
  -p fps:=60
```
#### Terminal 4 - launch receiver
```
gst-launch-1.0 -v \
  udpsrc port=5602 caps="application/x-rtp, media=video, encoding-name=H264, payload=96" \
  ! rtph264depay \
  ! decodebin \
  ! videoconvert \
  ! autovideosink
```
### Drone3 Stream
#### Terminal 5 - launch bridge
```
ros2 run swarm_mission gstreamer_image_bridge \
  --ros-args \
  -p topic:=/drone3/image_raw \
  -p host:=127.0.0.1 \
  -p port:=5603 \
  -p width:=640 \
  -p height:=480 \
  -p fps:=60
```
#### Terminal 6 - launch receiver
```
gst-launch-1.0 -v \
  udpsrc port=5603 caps="application/x-rtp, media=video, encoding-name=H264, payload=96" \
  ! rtph264depay \
  ! decodebin \
  ! videoconvert \
  ! autovideosink
```
## Streaming to another computer
If the receiver runs on another computer, replace:
```
-p host:=127.0.0.1
```
with the IP address of the receiving computer.
### Port mapping

drone2 -> port 5602
drone3 -> port 5603
- `drone1 -> port 5601`
- `drone2 -> port 5602`
- `drone3 -> port 5603`


