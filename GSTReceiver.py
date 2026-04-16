import gi
import numpy as np

gi.require_version("Gst", "1.0")
from gi.repository import Gst

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

Gst.init(None)

class GSTReceiver(QThread):
    frame_received = pyqtSignal(int ,QImage)
    status_message = pyqtSignal(int, str)

    def __init__(self, drone_id, port=2222):
        super().__init__()
        self.drone_id = drone_id
        self.port = port
        self.running = False
        self.pipeline = None
        self.appsink = None

    def run(self):
        self.running = True

        pipeline_str = (
            f"udpsrc port={self.port} caps=application/x-rtp,encoding-name=H264,payload=96 ! "
            "rtpjitterbuffer latency=50 ! "
            "rtph264depay ! avdec_h264 ! videoconvert ! "
            "video/x-raw,format=BGR ! appsink name=sink emit-signals=true max-buffers=1 drop=true sync=false"
        )

        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            self.appsink = self.pipeline.get_by_name("sink")

            if self.appsink is None:
                self.status_message.emit(self.drone_id,"Chyba: appsink sa nenašiel.")
                return

            self.appsink.connect("new-sample", self.on_new_sample)

            ret = self.pipeline.set_state(Gst.State.PLAYING)
            if ret == Gst.StateChangeReturn.FAILURE:
                self.status_message.emit(self.drone_id,"Chyba: pipeline sa nepodarilo spustiť.")
                return

            self.status_message.emit(self.drone_id,f"Receiver beží na porte {self.port}")

            while self.running:
                self.msleep(10)

        except Exception as e:
            self.status_message.emit(self.drone_id,f"Chyba GStreamera: {e}")

        finally:
            if self.pipeline is not None:
                self.pipeline.set_state(Gst.State.NULL)
            self.status_message.emit(self.drone_id,"Receiver zastavený.")

    def stop(self):
        self.running = False
        self.wait()

    def on_new_sample(self, sink):
        sample = sink.emit("pull-sample")
        if not sample:
            return Gst.FlowReturn.ERROR

        buffer = sample.get_buffer()
        caps = sample.get_caps()

        if buffer is None or caps is None:
            return Gst.FlowReturn.ERROR

        structure = caps.get_structure(0)
        if structure is None:
            return Gst.FlowReturn.ERROR

        width = structure.get_value("width")
        height = structure.get_value("height")

        success, map_info = buffer.map(Gst.MapFlags.READ)
        if not success:
            return Gst.FlowReturn.ERROR

        try:
            frame = np.frombuffer(map_info.data, dtype=np.uint8)

            expected_size = width * height * 3
            if frame.size != expected_size:
                self.status_message.emit(self.drone_id,
                    f"Zlá veľkosť frame: {frame.size}, očakávané: {expected_size}"
                )
                return Gst.FlowReturn.ERROR

            frame = frame.reshape((height, width, 3))

            image = QImage(
                frame.data,
                width,
                height,
                3 * width,
                QImage.Format.Format_BGR888
            )

            self.frame_received.emit(self.drone_id,image.copy())

        except Exception as e:
            self.status_message.emit(self.drone_id,f"Chyba frame: {e}")
            return Gst.FlowReturn.ERROR

        finally:
            buffer.unmap(map_info)

        return Gst.FlowReturn.OK