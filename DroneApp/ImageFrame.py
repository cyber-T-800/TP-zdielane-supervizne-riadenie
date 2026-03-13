from PyQt6.QtWidgets import QFrame
from PyQt6.QtGui import QPainter


class ImageFrame(QFrame):

    def __init__(self):
        super().__init__()
        self.image = None

    def setImage(self, image):
        self.image = image
        self.update()

    def paintEvent(self, event):

        super().paintEvent(event)

        if not self.image:
            return

        painter = QPainter(self)

        painter.drawImage(0, 0, self.image)
