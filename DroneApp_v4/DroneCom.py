from functools import partial

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QImage
import roslibpy

class DroneCom(QObject):
    frame_received = pyqtSignal(int, QImage)
    position_recived = pyqtSignal(int, float, float, float)
    battery_recived = pyqtSignal(int, float, float)
    state_recived = pyqtSignal(int, bool, bool, bool, bool, str)

    def __init__(self, num_of_drones, ros_host='192.168.0.190', ros_port=9090):
        super().__init__()

        self.num_of_drones = num_of_drones

        self.freq = 100

        self.is_publishing = False

        self.null_vel()

        self.position_listeners = []
        self.battery_listeners = []
        self.state_listeners = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.publish_cmd)

        self.client = roslibpy.Ros(host=ros_host, port=ros_port)
        self.client.run()

        for i in range(self.num_of_drones):
            pos_topic = roslibpy.Topic(
                self.client,
                f'/drone{i+1}/local_position/pose',
                'geometry_msgs/PoseStamped'
            )
            pos_topic.subscribe(partial(self._position_callback, i))
            self.position_listeners.append(pos_topic)

            bat_topic = roslibpy.Topic(
                self.client,
                f'/drone{i+1}/battery',
                'sensor_msgs/BatteryState'
            )
            bat_topic.subscribe(partial(self._battery_callback, i))
            self.battery_listeners.append(bat_topic)

            state_topic = roslibpy.Topic(
                self.client,
                f'/drone{i+1}/state',
                'mavros_msgs/State'
            )
            state_topic.subscribe(partial(self._state_callback, i))
            self.state_listeners.append(state_topic)

        self.takeover= roslibpy.Topic(self.client,'/supervisor/takeover_request','std_msgs/String')
        self.release = roslibpy.Topic(self.client, '/supervisor/release_request', 'std_msgs/String')
        self.cmd_vel_publisher = roslibpy.Topic(self.client, '/supervisor/manual_cmd_vel','geometry_msgs/Twist')

    def toggle_publishing(self, drone_id):
        if not self.is_publishing:
            self.takeover.publish(roslibpy.Message({'data': f'drone{drone_id+1}'}))
            self.start_publishing()
            self.is_publishing = True
        else:
            self.release.publish(roslibpy.Message({'data': f'drone{drone_id+1}'}))
            self.stop_publishing()
            self.is_publishing = False
            self.null_vel()

        return self.is_publishing

    def start_publishing(self):
        self.timer.start(self.freq)

    def stop_publishing(self):
        self.timer.stop()

    def publish_cmd(self):
        msg = {
            'linear': {'x': self.x, 'y': self.y, 'z': self.z},
            'angular': {'x': self.a_x, 'y': self.a_y, 'z': self.a_z}
        }
        self.cmd_vel_publisher.publish(msg)

    def update_vel(self, x, y, z, a_x, a_y, a_z):
        if self.is_publishing:
            self.x = x
            self.y = y
            self.z = z
            self.a_x = a_x
            self.a_y = a_y
            self.a_z = a_z


    def emergency_stop(self):
        self.null_vel()
        if self.is_publishing:
            self.stop_publishing()
            self.is_publishing = False

    def null_vel(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.a_x = 0.0
        self.a_y = 0.0
        self.a_z = 0.0

    def _position_callback(self, drone_id, message):
        pos = message['pose']['position']
        self.handle_position(drone_id, pos['x'], pos['y'], pos['z'])

    def _battery_callback(self, drone_id, message):
        self.handle_battery(drone_id,
                            message.get('percentage', 0.0),
                            message.get('voltage', 0.0))

    def _state_callback(self, drone_id, message):
        self.handle_state(
            drone_id,
            message.get('connected', False),
            message.get('armed', False),
            message.get('guided', False),
            message.get('manual_input', False),
            message.get('mode', '')
        )


    def handle_position(self, drone_id: int, x: float, y: float, z: float):
        self.position_recived.emit(drone_id, x, y, z)

    def handle_battery(self, drone_id: int, percentage: float, voltage: float):
        self.battery_recived.emit(drone_id, percentage, voltage)

    def handle_state(self, drone_id: int, connected: bool, armed: bool,
                     guided: bool, manual_input: bool, mode: str):
        self.state_recived.emit(
            drone_id, connected, armed, guided, manual_input, mode
        )
