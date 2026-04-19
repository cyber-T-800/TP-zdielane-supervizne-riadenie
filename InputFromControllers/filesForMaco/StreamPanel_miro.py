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
        self.drone = "drone " + str(drone_idx + 1)
        self.last_image = None
        self.is_selected = False

        self.container = QWidget(self)

        self.image_label = QLabel(self.container)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background: #101010; color: #999;font-size: 24pt;")
        self.image_label.setText("No image")

        self.location_label = QLabel("-|-", self.container)
        self.drone_label = QLabel(self.drone, self.container)
        self.fps_label = QLabel("-|-", self.container)
        self.mode_label = QLabel("-|-", self.container)

        style = """
        color: white;
        background: rgba(0, 0, 0, 50);
        font-size: 24pt;
        padding: 3px;
        border-radius: 3px;
        """

        for lbl in [self.location_label, self.fps_label, self.drone_label, self.mode_label]:
            lbl.setStyleSheet(style)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.container)
        self.setLayout(layout)

        self.update_border()

    def update_border(self):
        if self.is_selected:
            self.setStyleSheet("""
                StreamPanel {
                    border: 4px solid #00ff66;
                    background-color: #101010;
                }
            """)
        else:
            self.setStyleSheet("""
                StreamPanel {
                    border: 2px solid #2a2a2a;
                    background-color: #101010;
                }
            """)

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update_border()

    def set_location(self, loc):
        self.location = loc
        self.location_label.setText(loc)

    def set_fps(self, fps):
        self.fps_label.setText(f"{fps} FPS")

    def set_image(self, image):
        self.last_image = image
        self._rescale_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.container.resize(self.size())
        self.image_label.resize(self.container.size())

        self._rescale_image()

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