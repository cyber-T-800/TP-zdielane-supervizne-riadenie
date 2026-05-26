# Running DroneApp v4 on Windows

DroneApp v4 runs on Windows through **MSYS2 UCRT64** because it needs PyQt5,
`gi`, and GStreamer Python bindings.

Setup:

## 1. Install MSYS2 UCRT64

Install MSYS2 from:

```text
https://www.msys2.org/
```

Open:

```text
MSYS2 UCRT64
```

Update MSYS2:

```bash
pacman -Syu
```

If the terminal asks to close, reopen `MSYS2 UCRT64` and run the same command
again.

## 2. Install Windows App Dependencies

In `MSYS2 UCRT64`:

```bash
pacman -S --needed \
  mingw-w64-ucrt-x86_64-python \
  mingw-w64-ucrt-x86_64-python-pip \
  mingw-w64-ucrt-x86_64-python-numpy \
  mingw-w64-ucrt-x86_64-python-pyqt5 \
  mingw-w64-ucrt-x86_64-python-gobject \
  mingw-w64-ucrt-x86_64-python-cffi \
  mingw-w64-ucrt-x86_64-python-cryptography \
  mingw-w64-ucrt-x86_64-gcc \
  mingw-w64-ucrt-x86_64-gstreamer \
  mingw-w64-ucrt-x86_64-gst-python \
  mingw-w64-ucrt-x86_64-gst-plugins-base \
  mingw-w64-ucrt-x86_64-gst-plugins-good \
  mingw-w64-ucrt-x86_64-gst-plugins-bad \
  mingw-w64-ucrt-x86_64-gst-plugins-ugly \
  mingw-w64-ucrt-x86_64-gst-libav
```

Install `roslibpy`:

```bash
python -m pip install roslibpy --break-system-packages
```

Install `autobahn` to a correct version that works reliably in MSYS2 UCRT64:

```bash
python -m pip install --break-system-packages --force-reinstall --no-deps "autobahn==23.6.2"
```


## 3. Allow Video Ports on Windows

Run PowerShell as Administrator:

```powershell
New-NetFirewallRule -DisplayName "DroneApp GStreamer UDP" -Direction Inbound -Protocol UDP -LocalPort 2223-2225 -Action Allow
```

## 4. Start Backend on Ubuntu

Find the Windows IP address with `ipconfig`, then on Ubuntu run:

```bash
cd ~/TP-zdielane-supervizne-riadenie
./start_swarm.sh --gst-host WINDOWS_IP
```

Example:

```bash
./start_swarm.sh --gst-host 192.168.0.189
```

## 5. Run DroneApp on Windows

In `MSYS2 UCRT64`:

```bash
 cd /c/Users/marek/Documents/2.semester/Tímový\ projekt/TP-zdielane-supervizne-riadenie/DroneApp_v4
python DroneAppV4.py --ros-host UBUNTU_IP
```

Example:

```bash
python DroneAppV4.py --ros-host 192.168.0.190
```

## 6. Quick Checks

ROS bridge from Windows:

```powershell
Test-NetConnection UBUNTU_IP -Port 9090
```
