from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image


class ROSReceiver(QThread):
    frame_received = pyqtSignal(int, QImage)
    status_message = pyqtSignal(int, str)

    def __init__(self, drone_id,topic: str, compressed: bool = True):
        super().__init__()
        self.topic = topic
        self.drone_idx = drone_id
        self.compressed = compressed
        self._running = True
        self.node = None

    def stop(self):
        self._running = False
        self.wait()

    def _on_compressed(self, msg):
        image = QImage.fromData(bytes(msg.data))
        if not image.isNull():
            self.frame_received.emit(self.drone_idx, image.copy())

    def _on_raw(self, msg):
        image = self.image_msg_to_qimage(msg)
        if image is not None and not image.isNull():
            self.frame_received.emit(self.drone_idx, image)


    def run(self):
        rclpy.init(args=None)

        self.node = Node(f"drone_viewer_{self.drone_idx + 1}")

        self.status_message.emit(self.drone_idx, f"subscribing: {self.topic}")

        if self.compressed:
            self.subscription = self.node.create_subscription(
                CompressedImage,
                self.topic,
                self._on_compressed,
                10,
            )
        else:
            self.subscription = self.node.create_subscription(
                Image,
                self.topic,
                self._on_raw,
                10,
            )

        self.status_message.emit(self.drone_idx, "waiting for frames...")


        while rclpy.ok() and self._running:
            rclpy.spin_once(self.node, timeout_sec=0.1)

        self.node.destroy_node()
        rclpy.shutdown()

    def image_msg_to_qimage(self, msg):
        width = msg.width
        height = msg.height
        step = msg.step
        encoding = msg.encoding.lower()

        data = bytes(msg.data)

        if encoding == "rgb8":
            img = QImage(data, width, height, step, QImage.Format_RGB888)
            return img.copy()

        if encoding == "bgr8":
            img = QImage(data, width, height, step, QImage.Format_RGB888)
            return img.rgbSwapped().copy()

        if encoding == "mono8":
            img = QImage(data, width, height, step, QImage.Format_Grayscale8)
            return img.copy()

        if encoding == "rgba8" and hasattr(QImage, "Format_RGBA8888"):
            img = QImage(data, width, height, step, QImage.Format_RGBA8888)
            return img.copy()

        if encoding == "bgra8" and hasattr(QImage, "Format_RGBA8888"):
            img = QImage(data, width, height, step, QImage.Format_RGBA8888)
            return img.rgbSwapped().copy()

        return None