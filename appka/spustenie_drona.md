## Spustenie

Najskôr je potrebné drona zapojiť do zdroja na vstupné napätie 12V. Dron sa chvíľku bootuje, nahlas pri tom pípa. 

Následne je potrebné sa na drona pripojiť, buď skrze usb kábel, alebo cez hotspot, ktorý vytvára.

wifi: 
- SSID: EduDroneXX
- pass: dronecore


## Pripojenie sa:

S dronom vieme komunikovať pomocov SSH protokolu príkazom: 
```
ssh dcs_user@192.168.55.1
```
- password: dronecore

V tej istej konzole treba reštartovať Mavlink, aby sme vedeli získať dáta z autopilota: 
```
sudo systemctl restart mavlink-router.service
```

A tiež vieme upravovať konfiguráciu mavlink routra: 
```
sudo vim /etc/mavlink-router/main.conf
```
 

10.42.0.100

## Pripojenie na WiFi sieť

S dronom vieme komunikovať aj na vlastnej LAN sieti, treba: 

Vypnúť dronov hotspot:
```
sudo nmcli connection down EduDrone13
```

Pripojiť sa na wifi a spustiť ju: 
```
sudo nmcli device wifi connect SSID password PASS
sudo nmcli connection up SSID
```

## Zobrazenie výstupu z kamery
Najskôr na strane počítača zapneme gstreamer na zobrazenie výstupu z kamery: 

```
gst-launch-1.0 udpsrc port=2222 ! application/x-rtp, encoding-name=H264, payload=96 ! rtph264depay ! avdec_h264 ! fpsdisplaysink sync=false
```

Na túto časť som potreboval doinštalovať nejaké knižnice: 

```
sudo apt update
sudo apt install \
  gstreamer1.0-libav \
  gstreamer1.0-plugins-bad \
  gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-base \
  gstreamer1.0-tools
```

Následne spustíme gstreamer na strane drona: 

```
gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! "video/x-raw(memory:NVMM), width=3280, height=2464, format=NV12, framerate=21/1" ! nvvidconv ! "video/x-raw, format=I420" ! x264enc bitrate=5000 speed-preset=ultrafast tune=zerolatency ! h264parse ! rtph264pay config-interval=1 ! udpsink host=192.168.55.100 port=2222 sync=false async=false
```

Spustíme mapovanie dát z dronu do ros topicov
```
ros2 run mavros mavros_node --ros-args -p fcu_url:=udp://127.0.0.1:14571@14571 -p tgt_system:=2 --remap __ns:=/drone2
```

## qground controll nastavovačky

qgs 
app settings > video >h264 video stream 
udp url: 192.168.55.100:2222 