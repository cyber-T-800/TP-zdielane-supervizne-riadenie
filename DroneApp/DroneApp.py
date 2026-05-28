import sys
import argparse

from PyQt5.QtWidgets import QApplication

from DroneCom import DroneCom
from MainWindow import MainWindow
from GSTReceiver import GSTReceiver
from VRInputThread import VRInputThread

class DroneApp(MainWindow):
    def __init__(self, args):
        super().__init__()
        print('[APP] DroneApp sa spusta...', flush=True)

        self.num_of_drones = 3
        self.args = args

        ports = [2223,2224,2225]

        if self.args.ports:
            ports = self.args.ports

        self.setup_main_window(num_of_panels=self.num_of_drones)

        self.receivers = []

        for i in range(self.num_of_drones):
            r = GSTReceiver(
                drone_id=i,
                port=ports[i]
            )
            self.receivers.append(r)

        for r in self.receivers:
            r.frame_received.connect(self.set_stream_image)
            r.status_message.connect(
                lambda drone_id, msg: print(f'[GST] drone{drone_id+1}: {msg}', flush=True)
            )
            r.start()


        print('[APP] Vytvaram DroneCom...', flush=True)
        self.droneCom = DroneCom(
            self.num_of_drones,
            ros_host=args.ros_host,
            ros_port=args.ros_port
        )
       
        self.droneCom.battery_recived.connect(self.set_battery)
        self.droneCom.position_recived.connect(self.set_location)
        self.droneCom.state_recived.connect(self.set_mode)


        print('[APP] Pripajam klavesnicove a VR signaly...', flush=True)
        self.root.t_pressed.connect(self.change_control)
        self.root.q_pressed.connect(self.change_right)
        self.root.motion_signal.connect(self.droneCom.update_vel)

        self.vr_thread = VRInputThread()
        self.vr_thread.status_message.connect(lambda msg: print(f'[VR_STATUS] {msg}', flush=True))
        self.vr_thread.toggle_control.connect(lambda: print('[APP] prijaty VR signal: toggle_control', flush=True))
        self.vr_thread.toggle_control.connect(self.change_control)
        self.vr_thread.next_drone.connect(lambda: print('[APP] prijaty VR signal: next_drone', flush=True))
        self.vr_thread.next_drone.connect(self.change_right)
        self.vr_thread.prev_drone.connect(lambda: print('[APP] prijaty VR signal: prev_drone', flush=True))
        self.vr_thread.prev_drone.connect(self.change_left)
        self.vr_thread.emergency_stop.connect(lambda: print('[APP] prijaty VR signal: emergency_stop', flush=True))
        self.vr_thread.emergency_stop.connect(self.droneCom.emergency_stop)
        self.vr_thread.motion_signal.connect(lambda x,y,z,ax,ay,az: print(f'[APP] prijaty VR motion_signal: lin=({x:.2f},{y:.2f},{z:.2f}) ang=({ax:.2f},{ay:.2f},{az:.2f})', flush=True))
        self.vr_thread.motion_signal.connect(self.droneCom.update_vel)
        print('[APP] Startujem VRInputThread...', flush=True)
        self.vr_thread.start()

        self.show()
    
    def change_control(self):
        current_drone = self.get_current_index()
        print(f'[APP] change_control() zavolana, aktualny drone index={current_drone}', flush=True)
        self.control_lock = self.droneCom.toggle_publishing(current_drone)
        print(f'[APP] control_lock/is_publishing={self.control_lock}', flush=True)

    def stop(self):
        self.vr_thread.stop()
        for r in self.receivers:
            r.stop()


def parse_args():
    parser = argparse.ArgumentParser(description="Run drone app for supervising drones")

    parser.add_argument(
        "--ports",
        nargs=3, 
        type=int,
        help="change ports(default: 2223,2224,2225) example: python3 DroneAppvX --ports 2222 2223 2224"
    )
    parser.add_argument(
        "--ros-host",
        default="192.168.0.190",
        help="ROS bridge host/IP address"
    )
    parser.add_argument(
        "--ros-port",
        default=9090,
        type=int,
        help="ROS bridge websocket port"
    )

    return parser.parse_args()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    droneapp = DroneApp(args=parse_args())
    app.aboutToQuit.connect(droneapp.stop)
    sys.exit(app.exec_())
