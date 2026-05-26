from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout


class MapPanel(QFrame):

    def __init__(self):
        super().__init__()

        self.last_image = QImage("Data/Map.png")

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)

        self.image_label.setStyleSheet("""
            background: #101010;
            color: #999;
            font-size: 24pt;
        """)

        self.colors = [QColor(255, 114, 0), QColor(255, 0, 0), QColor(255, 255, 0)]

        layout = QVBoxLayout(self)
        layout.addWidget(self.image_label)

        self.pos_x = [None] * 3
        self.pos_y = [None] * 3

        self._rescale_image()


    def update_location(self, drone_id, x, y):

        self.pos_x[drone_id] = x
        self.pos_y[drone_id] = y

        self.paint_locations()

    def paint_locations(self):

        if not hasattr(self, "base_pixmap"):
            return

        pixmap = self.base_pixmap.copy()

        painter = QPainter(pixmap)

        pen = QPen()
        pen.setWidth(3)

        painter.setPen(pen)

        cx = pixmap.width() // 2
        cy = pixmap.height() // 2

        radius = 6
        scale = 10

        for i in range(3):

            if self.pos_x[i] is not None and self.pos_y[i] is not None:

                px = cx + self.pos_x[i]*scale
                py = cy - self.pos_y[i]*scale
                painter.setBrush(self.colors[i])

                painter.drawEllipse(
                    px - radius,
                    py - radius,
                    radius * 2,
                    radius * 2
                )

        painter.end()

        self.image_label.setPixmap(pixmap)

    def _rescale_image(self):

        if self.last_image.isNull():
            return

        self.base_pixmap = QPixmap.fromImage(self.last_image).scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.paint_locations()