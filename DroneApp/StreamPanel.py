from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import  QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)


DRONE_COLORS = ["#ff7200", "#ff0000", "#ffff00"]


class StreamPanel(QFrame):

    clicked = pyqtSignal(int)     

    def __init__(self, drone_idx):
        super().__init__()

        self.drone_idx = drone_idx

        self.drone = "drone "+ str(drone_idx+1 )
        self.last_image = None
        self.drone_color = DRONE_COLORS[drone_idx % len(DRONE_COLORS)]
        self.setStyleSheet(f"StreamPanel {{ border: 4px solid {self.drone_color}; }}")

        self.container = QWidget(self)

        self.image_label = QLabel(self.container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            background: #101010;
            color: #999;
            font-size: 24pt;
        """)
        self.image_label.setText("No image")

        
        self.location_label = QLabel("-|-", self.container)

        self.drone_label = QLabel(self.drone, self.container)

        self.fps_label = QLabel("", self.container)
        self.fps_label.hide()

        self.mode_label = QLabel("-|-", self.container)

        self.battery_label = QLabel("-|-", self.container)

        style = """
        color: white;
        background: rgba(0, 0, 0, 50);
        font-size: 16pt;
        padding: 3px;
        border-radius: 3px;
        """

        for lbl in [self.location_label, self.fps_label, self.drone_label, self.mode_label, self.battery_label]:
            lbl.setStyleSheet(style)


        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        layout.addWidget(self.container)
        self.setLayout(layout)

    def set_location(self, x, y, z):
        self.location_label.setText(f"x = {x:.2f}, y = {y:.2f}, z = {z:.2f}")
        self.location_label.adjustSize()

    def set_battery(self, percentage, voltage):
        battery_percent = percentage * 100.0 if percentage <= 1.0 else percentage
        self.battery_label.setText(f"Battery: {battery_percent:.1f} %")
        self.battery_label.adjustSize()


    def set_fps(self, fps):
        self.fps_label.setText(f"{fps} FPS")
        self.fps_label.adjustSize()
        self.fps_label.show()

    def set_mode(self, mode):

        self.mode_label.setText(f"Mode: {mode}")
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
        if self.fps_label.isVisible():
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
        mode_y = self.container.height() - self.mode_label.height() - margin
        self.mode_label.move(
            margin,
            mode_y
        )

        self.battery_label.adjustSize()
        self.battery_label.move(
            margin, 
            mode_y - self.battery_label.height() - 6
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
