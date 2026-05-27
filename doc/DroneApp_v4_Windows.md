# Run DroneApp_v4 on Windows

This setup uses native Windows Python.

## 1. Install Python Packages

Open PowerShell and install the required packages:

```powershell
py -m pip install --upgrade pip
py -m pip install PyQt5 numpy roslibpy
py -m pip install gstreamer-bundle
py -m pip install openvr
```

## 2. Allow GStreamer UDP Video

Run PowerShell as Administrator:

```powershell
New-NetFirewallRule `
  -DisplayName "DroneApp GStreamer UDP" `
  -Direction Inbound `
  -Action Allow `
  -Protocol UDP `
  -LocalPort 2223-2225 `
  -Profile Any
```

## 3. Start Ubuntu Backend

On Ubuntu, start the simulation and send video to the Windows PC IP:

```bash
cd ~/TP-zdielane-supervizne-riadenie
./start_swarm.sh --gst-host WINDOWS_IP
```

Example:

```bash
./start_swarm.sh --gst-host 192.168.0.189
```

## 4. Run DroneApp_v4

On Windows:

```powershell
cd "C:\Users\marek\Documents\2.semester\Tímový projekt\TP-zdielane-supervizne-riadenie\DroneApp_v4"
py .\DroneAppV4.py --ros-host UBUNTU_IP
```

Example:

```powershell
py .\DroneAppV4.py --ros-host 10.47.61.222
```

Optional custom video ports:

```powershell
py .\DroneAppV4.py --ros-host 10.47.61.222 --ports 2223 2224 2225
```

For VR control, start SteamVR/PICO streaming before launching DroneApp_v4.
