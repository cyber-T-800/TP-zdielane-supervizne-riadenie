#!/usr/bin/env python3
import argparse
import sys
import time
from dataclasses import dataclass

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

import rclpy
from rclpy.context import Context
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from sensor_msgs.msg import CompressedImage, Image


@dataclass
class StreamConfig:
    name: str
    topic: str


@dataclass
class DroneState:
    status: str = "waiting for frames..."
    frames: int = 0
    fps: float = 0.0
    last_frame_ts: float = 0.0
    width: int = 0
    height: int = 0


class DroneSupervisorModel:
    """State layer prepared for future drone control and supervision features."""

    def __init__(self, streams):
        self.streams = streams
        self.state = {stream.topic: DroneState() for stream in streams}
        self.command_queue = []

    def update_status(self, topic, status):
        if topic in self.state:
            self.state[topic].status = status

    def mark_frame(self, topic, width, height):
        if topic not in self.state:
            return False

        now = time.monotonic()
        st = self.state[topic]

        if st.last_frame_ts > 0:
            dt = now - st.last_frame_ts
            if dt > 0:
                st.fps = 1.0 / dt

        st.last_frame_ts = now
        st.frames += 1

        resolution_changed = (st.width != width) or (st.height != height)
        st.width = width
        st.height = height
        return resolution_changed

    def queue_command(self, topic, command, payload=None):
        self.command_queue.append(
            {
                "topic": topic,
                "command": command,
                "payload": payload or {},
                "ts": time.time(),
            }
        )


class StreamPanel(QFrame):
    def __init__(self, title, topic, compact=False):
        super().__init__()
        self.title = title
        self.topic = topic
        self.status = "waiting for frames..."
        self.last_image = None

        self.setFrameShape(QFrame.Box)
        self.setStyleSheet("background: #151515; border: 1px solid #333;")

        title_font = "14px" if not compact else "12px"
        self.title_label = QLabel(f"{self.title}\n{self.topic}")
        self.title_label.setStyleSheet(
            f"color: #efefef; font-size: {title_font}; font-weight: 600;"
        )

        self.status_label = QLabel(self.status)
        self.status_label.setStyleSheet("color: #b5b5b5; font-size: 12px;")

        self.image_label = QLabel("No image")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: #101010; color: #999;")

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.image_label, 1)
        self.setLayout(layout)

    def set_status(self, text):
        self.status = text
        self.status_label.setText(text)

    def set_image(self, image):
        self.last_image = image
        self._rescale_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale_image()

    def _rescale_image(self):
        if self.last_image is None:
            return
        pix = QPixmap.fromImage(self.last_image).scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.image_label.setPixmap(pix)


class ROSMultiReceiver(QThread):
    frame_received = pyqtSignal(str, QImage)
    status_changed = pyqtSignal(str, str)

    def __init__(self, streams):
        super().__init__()
        self.streams = streams
        self._running = True
        self._context = None

    def stop(self):
        self._running = False
        if self._context is not None and self._context.ok():
            self._context.try_shutdown()

    def _on_compressed(self, topic, msg):
        image = QImage.fromData(bytes(msg.data))
        if not image.isNull():
            self.frame_received.emit(topic, image.copy())

    def _on_raw(self, topic, msg):
        image = image_msg_to_qimage(msg)
        if image is not None and not image.isNull():
            self.frame_received.emit(topic, image)

    def run(self):
        self._context = Context()
        rclpy.init(args=None, context=self._context)

        node = Node("droneapp_multi_viewer", context=self._context)
        executor = SingleThreadedExecutor(context=self._context)
        executor.add_node(node)
        subscriptions = []

        for stream in self.streams:
            self.status_changed.emit(stream.topic, f"subscribing: {stream.topic}")
            if stream.topic.endswith("/compressed"):
                sub = node.create_subscription(
                    CompressedImage,
                    stream.topic,
                    lambda msg, t=stream.topic: self._on_compressed(t, msg),
                    10,
                )
            else:
                sub = node.create_subscription(
                    Image,
                    stream.topic,
                    lambda msg, t=stream.topic: self._on_raw(t, msg),
                    10,
                )
            subscriptions.append(sub)
            self.status_changed.emit(stream.topic, "waiting for frames...")

        try:
            while self._running and self._context.ok():
                executor.spin_once(timeout_sec=0.1)
        except ExternalShutdownException:
            pass
        finally:
            executor.remove_node(node)
            node.destroy_node()
            if self._context.ok():
                self._context.try_shutdown()


def image_msg_to_qimage(msg):
    width = msg.width
    height = msg.height
    step = msg.step
    data = bytes(msg.data)
    encoding = msg.encoding.lower()

    if encoding == "rgb8":
        return QImage(data, width, height, step, QImage.Format_RGB888).copy()
    if encoding == "bgr8":
        return QImage(data, width, height, step, QImage.Format_RGB888).rgbSwapped().copy()
    if encoding == "mono8":
        return QImage(data, width, height, step, QImage.Format_Grayscale8).copy()
    if encoding == "rgba8" and hasattr(QImage, "Format_RGBA8888"):
        return QImage(data, width, height, step, QImage.Format_RGBA8888).copy()
    if encoding == "bgra8" and hasattr(QImage, "Format_RGBA8888"):
        return QImage(data, width, height, step, QImage.Format_RGBA8888).rgbSwapped().copy()
    return None


def parse_topic_arg(value):
    if "@" not in value:
        topic = value.strip()
        return StreamConfig(name=topic, topic=topic)
    name, topic = value.split("@", 1)
    topic = topic.strip()
    return StreamConfig(name=name.strip() or topic, topic=topic)


def parse_args():
    parser = argparse.ArgumentParser(
        description="DroneApp multi-stream ROS2 viewer (up to 3 cameras)"
    )
    parser.add_argument(
        "--topic",
        action="append",
        help="Repeatable topic argument in format Topic or Name@Topic",
    )
    return parser.parse_args()


class MainWindow(QMainWindow):
    def __init__(self, streams, supervisor):
        super().__init__()
        self.streams = streams
        self.supervisor = supervisor
        self.panels = {}

        self.setWindowTitle("DroneApp - Multi Drone Monitor")
        self.setFixedSize(1400, 900)

        root = QWidget()
        root.setStyleSheet("background: #101010;")
        self.setCentralWidget(root)

        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.main_panel = StreamPanel(streams[0].name, streams[0].topic, compact=False)
        self.main_panel.setMinimumSize(940, 760)
        self.panels[streams[0].topic] = self.main_panel

        left_col = QVBoxLayout()
        left_col.addStretch(1)
        left_col.addWidget(self.main_panel, 1)
        left_col.addStretch(1)
        main_layout.addLayout(left_col, 5)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        for stream in streams[1:]:
            panel = StreamPanel(stream.name, stream.topic, compact=True)
            panel.setFixedSize(390, 300)
            self.panels[stream.topic] = panel
            right_col.addWidget(panel)

        for _ in range(max(0, 3 - len(streams))):
            placeholder = QLabel("No stream configured")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setFixedSize(390, 300)
            placeholder.setStyleSheet(
                "background: #151515; color: #8a8a8a; border: 1px solid #333; font-size: 13px;"
            )
            right_col.addWidget(placeholder)

        right_col.addStretch(1)
        main_layout.addLayout(right_col, 2)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_panel_status)
        self.refresh_timer.start(400)

    def set_stream_status(self, topic, status):
        panel = self.panels.get(topic)
        if panel:
            panel.set_status(status)
        self.supervisor.update_status(topic, status)

    def set_stream_image(self, topic, image):
        panel = self.panels.get(topic)
        if panel:
            panel.set_image(image)

        width = image.width()
        height = image.height()
        changed = self.supervisor.mark_frame(topic, width, height)
        if changed:
            print(f"[camera] {topic} resolution: {width}x{height}", flush=True)

    def refresh_panel_status(self):
        for stream in self.streams:
            state = self.supervisor.state[stream.topic]
            res = "n/a"
            if state.width > 0 and state.height > 0:
                res = f"{state.width}x{state.height}"
            status = f"{state.status} | {res} | {state.fps:.1f} fps"
            panel = self.panels.get(stream.topic)
            if panel:
                panel.set_status(status)


def main():
    args = parse_args()

    topic_args = args.topic or [
        "Drone 1@/front_camera/image_raw",
        "Drone 2@/stereo_camera/left/image_raw",
        "Drone 3@/stereo_camera/right/image_raw",
    ]

    streams = [parse_topic_arg(item) for item in topic_args[:3]]
    if len(topic_args) > 3:
        print("Only first 3 --topic values are used.")

    app = QApplication(sys.argv)
    supervisor = DroneSupervisorModel(streams)
    window = MainWindow(streams, supervisor)

    receiver = ROSMultiReceiver(streams)
    receiver.frame_received.connect(window.set_stream_image)
    receiver.status_changed.connect(window.set_stream_status)

    app.aboutToQuit.connect(receiver.stop)

    receiver.start()
    window.show()
    rc = app.exec_()
    receiver.wait(2000)
    sys.exit(rc)


if __name__ == "__main__":
    main()
