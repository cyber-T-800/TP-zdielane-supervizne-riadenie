import sys
import argparse

from PyQt5.QtWidgets import QApplication

from DroneCom import DroneCom
from MainWindow import MainWindow
from GSTReceiver import GSTReceiver

class DroneApp(MainWindow):
    def __init__(self, args):
        super().__init__()

        self.num_of_drones = 3
        self.args = args

        ports = [2223,2224,2225]

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
            r.start()


        self.droneCom = DroneCom(self.num_of_drones)
       
        self.droneCom.battery_recived.connect(self.set_battery)
        self.droneCom.position_recived.connect(self.set_location)
        self.droneCom.state_recived.connect(self.set_mode)


        self.root.t_pressed.connect(self.change_control)
        self.root.q_pressed.connect(self.change_right)
        self.root.motion_signal.connect(self.droneCom.update_vel)

        self.show()
    
    def change_control(self):
        current_drone = self.get_current_index()
        self.control_lock = self.droneCom.toggle_publishing(current_drone)

    def stop(self):
        for r in self.receivers:
            r.stop()


def parse_args():
    parser = argparse.ArgumentParser(description="Run drone app for supervising drones with Ros or Gstreamer")

    parser.add_argument(
        "--gst",
        nargs=3, 
        type=int,
        help="Use Gstreamer for camera instead ros topic, add ports example: python3 DroneAppv3 --gst 2222 2223 2224"
    )

    parser.add_argument(
        "--imgtopic",
        nargs=3,
        type=str,
        help="3 topics (defaut is image_raw), so /drone1/image_raw, /drone2/image_raw ..."
    )

    return parser.parse_args()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    droneapp = DroneApp(args=parse_args())
    app.aboutToQuit.connect(droneapp.stop)
    sys.exit(app.exec_())
