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
        self.trails = [[] for _ in range(3)]
        self.min_trail_distance = 0.10

        self._rescale_image()


    def update_location(self, drone_id, x, y):

        self.pos_x[drone_id] = x
        self.pos_y[drone_id] = y
        self._append_trail_point(drone_id, x, y)

        self.paint_locations()

    def _append_trail_point(self, drone_id, x, y):
        trail = self.trails[drone_id]

        if trail:
            last_x, last_y = trail[-1]
            dx = x - last_x
            dy = y - last_y
            if (dx * dx + dy * dy) < (self.min_trail_distance * self.min_trail_distance):
                return

        trail.append((x, y))

    def _map_to_pixmap(self, pixmap, x, y):
        scale = 10
        cx = pixmap.width() // 2
        cy = pixmap.height() // 2

        return (
            int(cx + x * scale),
            int(cy - y * scale)
        )

    def paint_locations(self):

        if not hasattr(self, "base_pixmap"):
            return

        pixmap = self.base_pixmap.copy()

        painter = QPainter(pixmap)

        radius = 6

        trail_pen = QPen()
        trail_pen.setWidth(3)

        for i, trail in enumerate(self.trails):
            if len(trail) < 2:
                continue

            trail_pen.setColor(self.colors[i])
            painter.setPen(trail_pen)

            for start, end in zip(trail, trail[1:]):
                start_x, start_y = self._map_to_pixmap(pixmap, start[0], start[1])
                end_x, end_y = self._map_to_pixmap(pixmap, end[0], end[1])
                painter.drawLine(start_x, start_y, end_x, end_y)

        dot_pen = QPen()
        dot_pen.setWidth(3)
        painter.setPen(dot_pen)

        for i in range(3):

            if self.pos_x[i] is not None and self.pos_y[i] is not None:

                px, py = self._map_to_pixmap(pixmap, self.pos_x[i], self.pos_y[i])
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
