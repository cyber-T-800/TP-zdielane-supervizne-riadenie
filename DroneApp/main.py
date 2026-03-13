from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PyQt6.QtGui import QImage
import sys
import ImageFrame
import UDPReceiver

class Window(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Supervision of Drone Swarm")
        self.resize(800, 600)

        # hlavný layout
        main_layout = QHBoxLayout()

        # VEĽKÉ okno
        big_widget = ImageFrame.ImageFrame()
        big_widget.setFrameShape(QFrame.Shape.Box)

        big_label = QLabel("Veľké okno", big_widget)
        big_label.move(20, 20)

        # pravý layout (2 malé okná)
        right_layout = QVBoxLayout()

        small1 = ImageFrame.ImageFrame()
        small1.setFrameShape(QFrame.Shape.Box)

        label1 = QLabel("Malé okno 1", small1)
        label1.move(10, 10)

        small2 = ImageFrame.ImageFrame()
        small2.setFrameShape(QFrame.Shape.Box)

        label2 = QLabel("Malé okno 2", small2)
        label2.move(10, 10)

        # pridanie do pravého layoutu
        right_layout.addWidget(small1)
        right_layout.addWidget(small2)

        # pridanie do hlavného layoutu
        main_layout.addWidget(big_widget, 3)
        main_layout.addLayout(right_layout, 1)

        self.setLayout(main_layout)

        self.receiver = UDPReceiver.UDPReceiver(5000)
        self.receiver.frame_received.connect(big_widget.setImage)

        self.receiver.start()


app = QApplication(sys.argv)

window = Window()
window.show()

sys.exit(app.exec())
