**1. Komunikačné rozhranie**

Backend `swarm_mission` má byť hlavný riadiaci bod. Appka na Windowse má posielať len tieto veci:

```text
/supervisor/takeover_request    std_msgs/msg/String
/supervisor/release_request     std_msgs/msg/String
/supervisor/manual_cmd_vel      geometry_msgs/msg/Twist
```

A backend má publikovať späť:

```text
/drone1/supervisor/handover_state
/drone2/supervisor/handover_state
/drone3/supervisor/handover_state
```

**2. Doplniť handover do swarm_mission**
V `swarm_coordinator` treba pridať logiku:

```text
AUTO_MISSION
-> HOLD_FOR_HANDOVER
-> MANUAL_CONTROL
-> RETURN_TO_MISSION
-> AUTO_MISSION
```

Technicky:

```text
takeover_request drone2
  -> uložiť mission_idx drona2
  -> hold_current_position(drone2)
  -> zastaviť vykonávanie CSV pre drone2
  -> ostatné drony pokračujú

manual_cmd_vel
  -> posielať len aktívnemu dronovi

release_request drone2
  -> poslať nulovú rýchlosť
  -> hold
  -> pokračovať od uloženého waypointu
```

**3. Otestovať backend **

```bash
ros2 topic pub --once /supervisor/takeover_request std_msgs/msg/String "{data: 'drone2'}"
```

Potom:

```bash
ros2 topic pub -r 10 /supervisor/manual_cmd_vel geometry_msgs/msg/Twist \
"{linear: {x: 0.4, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.2}}"
```

A release:

```bash
ros2 topic pub --once /supervisor/release_request std_msgs/msg/String "{data: 'drone2'}"
```

Overiť:

```text
drone2 reaguje manuálne
drone1 a drone3 pokračujú v CSV misii
po release drone2 pokračuje v CSV
pri výpadku manual_cmd_vel drone2 ostane v HOLD
```