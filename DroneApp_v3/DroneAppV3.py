import sys
import argparse

from PyQt5.QtWidgets import QApplication

from DroneCom import DroneCom
from MainWindow import MainWindow
from NodeManager import NodeManager
from GSTReceiver import GSTReceiver
from VRInputThread import VRInputThread

class DroneApp(MainWindow):
    def __init__(self, args):
        super().__init__()

        self.num_of_drones = 3
        self.args = args

        if self.args.imgtopic:
            self.topics = self.args.inputs
        else:
            self.topics = ["image_raw","image_raw","image_raw"]

        self.vrthread = VRInputThread()

        self.setup_main_window(num_of_panels=self.num_of_drones)

        if self.args.gst:
            self.receivers = []

            try:
                ports = [int(p) for p in self.args.inputs]
            except ValueError:
                print("Error: Ports must be integers")
                sys.exit(1)

            for i in range(self.num_of_drones):
                r = GSTReceiver(
                    drone_id=i,
                    port=ports[i]
                )
                self.receivers.append(r)

            for r in self.receivers:
                r.frame_received.connect(self.set_stream_image)
                r.start()




        self.node_manager = NodeManager()
        self.droneCom = DroneCom()

        cam = not self.args.gst

        for i in range(self.num_of_drones):
            self.node_manager.create_node(drone_id=i,cam=cam, comunicator=self.droneCom, img_topic= self.topics[i])

        if cam:
            self.droneCom.frame_received.connect(self.set_stream_image)
        
        self.droneCom.battery_recived.connect(self.set_battery)
        self.droneCom.position_recived.connect(self.set_location)
        self.droneCom.state_recived.connect(self.set_mode)

        self.vrthread.joystick_changed.connect(self.droneCom.update_vel)
        self.vrthread.select_next.connect(self.change_right)
        self.vrthread.mode_next.connect(self.node_manager.nodes[self.get_current_index()].change_mode_request)

        self.node_manager.start()


        self.show()
    
    def stop(self):
        if self.args.gst:
            for r in self.receivers:
                r.stop()
        self.node_manager.stop()


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
