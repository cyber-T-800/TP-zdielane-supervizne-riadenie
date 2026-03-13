import socket
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage


class UDPReceiver(QThread):

    frame_received = pyqtSignal(QImage)

    def __init__(self, address="127.0.0.1", port=5000):
        super().__init__()
        self.serverAddressPort = (address, port)
    def run(self):

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        sock.sendto("req".encode(),("127.0.0.1",5000))

        while True:

            data, addr = sock.recvfrom(65536)

            image = QImage.fromData(data)

            if not image.isNull():
                print("image+")
                self.frame_received.emit(image)
