import sys
import argparse

from PyQt5.QtWidgets import QApplication

from DroneCom import DroneCom
from MainWindow import MainWindow
from NodeManager import NodeManager
from GSTReceiver import GSTReceiver

class DroneApp(MainWindow):
    def __init__(self, args):
        super().__init__()

        self.num_of_drones = 3
        self.args = args
        self.topics = self.args.inputs

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

        else:
            self.node_manager = NodeManager()
            self.droneCom = DroneCom()

            for i in range(self.num_of_drones):
                self.node_manager.create_node(drone_id=i, comunicator=self.droneCom, img_topic= self.topics[i])

            self.droneCom.frame_received.connect(self.set_stream_image)

            self.node_manager.start()


        self.show()
    
    def stop(self):
        if self.args.gst:
            for r in self.receivers:
                r.stop()
        else:
            self.node_manager.stop()


def parse_args():
    parser = argparse.ArgumentParser(description="Run drone app for supervising drones with Ros or Gstreamer")

    parser.add_argument(
        "--gst",
        action="store_true",
        help="Use Gstreamer for camera instead ros topic"
    )

    parser.add_argument(
        "inputs",
        nargs=3,
        help="3 topics (if ros) OR 3 ports (if Gstreamer)"
    )

    return parser.parse_args()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    droneapp = DroneApp(args=parse_args())
    app.aboutToQuit.connect(droneapp.stop)
    sys.exit(app.exec_())
