from functools import partial

from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from PyQt5.QtGui import QImage
import roslibpy

class DroneCom(QObject):
    frame_received = pyqtSignal(int, QImage)
    position_recived = pyqtSignal(int, float, float, float)
    battery_recived = pyqtSignal(int, float, float)
    state_recived = pyqtSignal(int, str)

    def __init__(self, num_of_drones, ros_host='192.168.0.190', ros_port=9090):
        super().__init__()

        print(f'[DroneCom] init: num_of_drones={num_of_drones}, ros_host={ros_host}, ros_port={ros_port}', flush=True)

        self.num_of_drones = num_of_drones
        self.freq = 100
        self.is_publishing = False
        self.manual_control_enabled = False
        self.active_manual_drone = None
        self.handover_states = [""] * self.num_of_drones
        self.null_vel()

        self.position_listeners = []
        self.battery_listeners = []
        self.state_listeners = []

        self.timer = QTimer()
        self.timer.timeout.connect(self.publish_cmd)

        self.client = roslibpy.Ros(host=ros_host, port=ros_port)
        print('[DroneCom] pripajam sa na rosbridge...', flush=True)
        self.client.run()
        print(f'[DroneCom] rosbridge connected={self.client.is_connected}', flush=True)

        for i in range(self.num_of_drones):
            pos_topic = roslibpy.Topic(
                self.client,
                f'/drone{i+1}/local_position/pose',
                'geometry_msgs/PoseStamped'
            )
            pos_topic.subscribe(partial(self._position_callback, i))
            self.position_listeners.append(pos_topic)
            print(f'[DroneCom] subscribe: /drone{i+1}/local_position/pose', flush=True)

            bat_topic = roslibpy.Topic(
                self.client,
                f'/drone{i+1}/battery',
                'sensor_msgs/BatteryState'
            )
            bat_topic.subscribe(partial(self._battery_callback, i))
            self.battery_listeners.append(bat_topic)
            print(f'[DroneCom] subscribe: /drone{i+1}/battery', flush=True)

            state_topic = roslibpy.Topic(
                self.client,
                f'/drone{i+1}/supervisor/handover_state',
                'std_msgs/String'
            )
            state_topic.subscribe(partial(self._state_callback, i))
            self.state_listeners.append(state_topic)
            print(f'[DroneCom] subscribe: /drone{i+1}/supervisor/handover_state', flush=True)

        self.takeover = roslibpy.Topic(self.client, '/supervisor/takeover_request', 'std_msgs/String')
        self.release = roslibpy.Topic(self.client, '/supervisor/release_request', 'std_msgs/String')
        self.cmd_vel_publisher = roslibpy.Topic(self.client, '/supervisor/manual_cmd_vel', 'geometry_msgs/Twist')
        print('[DroneCom] publish topics pripravene', flush=True)

    def toggle_publishing(self, drone_id):
        print(
            f'[DroneCom] toggle_publishing(drone_id={drone_id}) predtym '
            f'is_publishing={self.is_publishing}, manual_control_enabled={self.manual_control_enabled}',
            flush=True
        )

        if not self.is_publishing:
            self.active_manual_drone = drone_id
            self.manual_control_enabled = False
            self.null_vel()

            msg = {'data': f'drone{drone_id+1}'}
            print(f'[DroneCom] TAKEOVER publish: {msg}', flush=True)
            self.takeover.publish(roslibpy.Message(msg))
            self.is_publishing = True
            self.start_publishing()

            if self.handover_states[drone_id] == 'MANUAL_CONTROL':
                self.enable_manual_publishing(drone_id)
            else:
                print(
                    f'[DroneCom] cakam na /drone{drone_id+1}/supervisor/handover_state == MANUAL_CONTROL',
                    flush=True
                )
        else:
            release_drone = self.active_manual_drone if self.active_manual_drone is not None else drone_id
            msg = {'data': f'drone{release_drone+1}'}
            print(f'[DroneCom] RELEASE publish: {msg}', flush=True)
            self.release.publish(roslibpy.Message(msg))
            self.disable_manual_session()

        print(
            f'[DroneCom] toggle_publishing koniec is_publishing={self.is_publishing}, '
            f'manual_control_enabled={self.manual_control_enabled}',
            flush=True
        )
        return self.is_publishing

    def enable_manual_publishing(self, drone_id):
        if self.manual_control_enabled:
            return

        self.active_manual_drone = drone_id
        self.manual_control_enabled = True
        self.null_vel()
        print(f'[DroneCom] manualne publikovanie POVOLENE pre drone{drone_id+1}', flush=True)

    def disable_manual_session(self):
        self.stop_publishing()
        self.is_publishing = False
        self.manual_control_enabled = False
        self.active_manual_drone = None
        self.null_vel()

    def start_publishing(self):
        print(f'[DroneCom] start_publishing() timer={self.freq} ms', flush=True)
        self.timer.start(self.freq)

    def stop_publishing(self):
        print('[DroneCom] stop_publishing()', flush=True)
        self.timer.stop()

    def publish_cmd(self):
        if not self.manual_control_enabled:
            return

        msg = {
            'linear': {'x': self.x, 'y': self.y, 'z': self.z},
            'angular': {'x': self.a_x, 'y': self.a_y, 'z': self.a_z}
        }

        print(f'[DroneCom] publish_cmd /supervisor/manual_cmd_vel: {msg}', flush=True)
        self.cmd_vel_publisher.publish(msg)

    def update_vel(self, x, y, z, a_x, a_y, a_z):
        print(
            f'[DroneCom] update_vel prijate: lin=({x:.2f},{y:.2f},{z:.2f}) '
            f'ang=({a_x:.2f},{a_y:.2f},{a_z:.2f}) '
            f'is_publishing={self.is_publishing}, manual_control_enabled={self.manual_control_enabled}',
            flush=True
        )

        if self.manual_control_enabled:
            self.x = x
            self.y = y
            self.z = z
            self.a_x = a_x
            self.a_y = a_y
            self.a_z = a_z
            print('[DroneCom] update_vel ulozene pre publish_cmd', flush=True)
        elif self.is_publishing:
            print('[DroneCom] update_vel ignorovane, cakam na stav MANUAL_CONTROL.', flush=True)
        else:
            print('[DroneCom] update_vel ignorovane, lebo is_publishing=False. Stlac RIGHT A / toggle_control.', flush=True)

    def emergency_stop(self):
        print('[DroneCom] emergency_stop()', flush=True)
        self.null_vel()
        if self.is_publishing:
            self.disable_manual_session()
        print('[DroneCom] emergency_stop koniec: rychlosti=0, is_publishing=False', flush=True)

    def null_vel(self):
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.a_x = 0.0
        self.a_y = 0.0
        self.a_z = 0.0

    def _position_callback(self, drone_id, message):
        print(f'[DroneCom] RX position drone{drone_id+1}: {message}', flush=True)
        pos = message['pose']['position']
        self.handle_position(drone_id, pos['x'], pos['y'], pos['z'])

    def _battery_callback(self, drone_id, message):
        print(f'[DroneCom] RX battery drone{drone_id+1}: {message}', flush=True)
        self.handle_battery(
            drone_id,
            message.get('percentage', 0.0),
            message.get('voltage', 0.0)
        )

    def _state_callback(self, drone_id, message):
        print(f'[DroneCom] RX state drone{drone_id+1}: {message}', flush=True)
        self.handle_state(
            drone_id,
            message.get('data', '')
        )

    def handle_position(self, drone_id: int, x: float, y: float, z: float):
        print(f'[DroneCom] emit position_recived drone{drone_id+1}: x={x}, y={y}, z={z}', flush=True)
        self.position_recived.emit(drone_id, x, y, z)

    def handle_battery(self, drone_id: int, percentage: float, voltage: float):
        print(f'[DroneCom] emit battery_recived drone{drone_id+1}: percentage={percentage}, voltage={voltage}', flush=True)
        self.battery_recived.emit(drone_id, percentage, voltage)

    def handle_state(self, drone_id: int, mode: str):
        mode = (mode or '').strip()
        print(f'[DroneCom] emit state_recived drone{drone_id+1}: mode={mode}', flush=True)
        self.handover_states[drone_id] = mode

        if self.is_publishing and self.active_manual_drone == drone_id:
            if mode == 'MANUAL_CONTROL':
                self.enable_manual_publishing(drone_id)
            elif self.manual_control_enabled:
                self.manual_control_enabled = False
                self.null_vel()
                print(
                    f'[DroneCom] manualne publikovanie BLOKOVANE, stav drone{drone_id+1}={mode}',
                    flush=True
                )

        self.state_recived.emit(drone_id, mode)
