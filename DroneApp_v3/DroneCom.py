from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QImage


class DroneCom(QObject):
    frame_received = pyqtSignal(int, QImage)
    def __init__(self):
        super().__init__()


    def handle_image(self, drone_id : int , qimage : QImage):
        self.frame_received.emit(drone_id, qimage)