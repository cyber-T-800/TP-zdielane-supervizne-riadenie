from PyQt5.QtCore import QThread

import rclpy
from rclpy.executors import MultiThreadedExecutor

from DroneNode import DroneNode

class NodeManager(QThread):
    def __init__(self):
        super().__init__()
        self.nodes = []
        self._running = True
        rclpy.init()
        self.executor = MultiThreadedExecutor()

    def create_node(self, drone_id, comunicator, img_topic):
        node = DroneNode(drone_id=drone_id, comunicator=comunicator, img_topic=img_topic)
        self.nodes.append(node)
        self.executor.add_node(node)

    def run(self):
        while rclpy.ok() and self._running:
            self.executor.spin_once(timeout_sec=0.1)

        for node in self.nodes:
            node.destroy_node()
        
        rclpy.shutdown()

    def stop(self):
        self._running = False
        self.wait()
