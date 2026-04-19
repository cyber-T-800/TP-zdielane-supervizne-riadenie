from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class StreamPanel(QFrame):

    clicked = pyqtSignal(int)     

    def __init__(self, drone_idx):
        super().__init__()

        self.drone_idx = drone_idx

        self.drone = "drone "+ str(drone_idx+1 )
        self.last_image = None

        self.container = QWidget(self)

        self.image_label = QLabel(self.container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: #101010; color: #999;font-size: 24pt;" )
        self.image_label.setText("No image")
        
        self.location_label = QLabel("-|-", self.container)

        self.drone_label = QLabel(self.drone, self.container)

        self.fps_label = QLabel("-|-", self.container)

        self.mode_label = QLabel("-|-", self.container)

        self.battery_label = QLabel("-|-", self.container)

        self.battery_label_V = QLabel("-|-", self.container)

        style = """
        color: white;
        background: rgba(0, 0, 0, 50);
        font-size: 16pt;
        padding: 3px;
        border-radius: 3px;
        """

        for lbl in [self.location_label, self.fps_label, self.drone_label, self.mode_label, self.battery_label, self.battery_label_V]:
            lbl.setStyleSheet(style)


        layout = QVBoxLayout()
        layout.addWidget(self.container)
        self.setLayout(layout)

    def set_location(self, x, y, z):
        self.location_label.setText(f"x = {x}, y = {y}, z = {z}")
        self.location_label.adjustSize()

    def set_battery(self, percentage, voltage):
        self.battery_label.setText(f"bat: {percentage} %")
        self.battery_label_V.setText(f"bat_volt: {voltage} V")
        self.battery_label.adjustSize()
        self.battery_label_V.adjustSize()


    def set_fps(self, fps):
        self.fps_label.setText(f"{fps} FPS")
        self.fps_label.adjustSize()

    def set_mode(self, connected, armed, guided, manual_input, mode):
        parts = []

        if connected:
            parts.append("connected")
        if armed:
            parts.append("armed")
        if guided:
            parts.append("guided")
        if manual_input:
            parts.append("manual_input")

        parts.append(mode)

        self.mode_label.setText(", ".join(parts))
        self.mode_label.adjustSize()

    def set_image(self, image):
        self.last_image = image
        self._rescale_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.container.resize(self.size())
        self.image_label.resize(self.container.size())

        margin = 20

        self.location_label.adjustSize()
        self.location_label.move(margin, margin)

        self.fps_label.adjustSize()
        self.fps_label.move(
            self.container.width() - self.fps_label.width() - margin,
            margin
        )

        self.drone_label.adjustSize()
        self.drone_label.move(
            self.container.width() - self.drone_label.width() - margin,
            self.container.height() - self.drone_label.height() - margin
        )

        self.mode_label.adjustSize()
        self.mode_label.move(
            margin,
            self.container.height() - self.mode_label.height() - margin
        )

        self.battery_label.adjustSize()
        self.battery_label.move(
            margin, 
            self.container.height() - self.location_label.height() - self.battery_label.height()- margin
        )

        self.battery_label_V.adjustSize()
        self.battery_label_V.move(
            margin,
            self.container.height() - self.location_label.height() - self.battery_label.height() - self.battery_label_V.height() - margin
        )

    def _rescale_image(self): 
        if self.last_image is None: 
            return 
        pix = QPixmap.fromImage(self.last_image).scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(pix)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if event.pos() in self.rect():
                self.clicked.emit(self.drone_idx)
