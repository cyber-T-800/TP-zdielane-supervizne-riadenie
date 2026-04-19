from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from PyQt5.QtGui import QImage

class DroneNode(Node):
    def __init__(self, drone_id, comunicator, img_topic):
        super().__init__(f"drone_node_{drone_id}")
        self.drone_id = drone_id
        self.comunicator = comunicator
        self.img_topic = img_topic

        if img_topic.endswith("/compressed"):
            self.img_sub = self.create_subscription(
                CompressedImage,
                img_topic,
                self._on_compressed,
                10,
            )
        else:
            self.img_sub = self.create_subscription(
                Image,
                img_topic,
                self._on_raw,
                10,
            )

    def _on_compressed(self, msg):
        image = QImage.fromData(bytes(msg.data))
        if not image.isNull():
            self.comunicator.handle_image(drone_id=self.drone_id, qimage=image.copy())

    def _on_raw(self, msg):
        image = self.image_msg_to_qimage(msg)
        if image is not None and not image.isNull():
            self.comunicator.handle_image(drone_id=self.drone_id, qimage=image)


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