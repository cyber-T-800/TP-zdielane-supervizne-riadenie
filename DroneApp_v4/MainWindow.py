from StreamPanel import StreamPanel
from KeyboardController import KeyboardController

from MapPanel import MapPanel

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

    def setup_main_window(self, num_of_panels):

        self.panels = {}
        self.current_idx = 0

        self.control_lock = False

        self.setWindowTitle("DroneApp - Multi Drone Monitor")
        self.setFixedSize(1800, 1000)

        self.num_of_panels = num_of_panels

        self.root = KeyboardController()
        self.root.setStyleSheet("background: #101010;")
        self.setCentralWidget(self.root)

        for i in range(self.num_of_panels): 
            self.panels[i] = StreamPanel(i)
            self.panels[i].clicked.connect(self.swap_panels)


        self.main_layout = QHBoxLayout(self.root)
        self.side_layout = QVBoxLayout()

        self.main_layout.addWidget(self.panels[0])

        for i in range(1, self.num_of_panels):
            self.side_layout.addWidget(self.panels[i])

        self.map = MapPanel()

        self.main_layout.addLayout(self.side_layout)
        self.main_layout.addWidget(self.map)

    def get_current_index(self):
        return self.current_idx

    def swap_panels(self, idx):
        if not self.control_lock:
            if idx == self.current_idx or idx not in self.panels:
                return

            main_panel = self.panels[self.current_idx]
            target_panel = self.panels[idx]

            self.main_layout.removeWidget(main_panel)
            self.side_layout.removeWidget(target_panel)

            self.main_layout.insertWidget(0, target_panel)
            self.side_layout.insertWidget(self.current_idx, main_panel)

            self.current_idx = idx

    def change_left(self):
        self.swap_panels((self.current_idx - 1)%3)

    def change_right(self):
        self.swap_panels((self.current_idx + 1)%3)

    def set_stream_image(self, idx, image):
        self.panels[idx].set_image(image)

    def set_battery(self,idx, percentage, voltage):
        self.panels[idx].set_battery(percentage, voltage)

    def set_location(self,idx, x, y, z):
        self.panels[idx].set_location(x, y, z)
        self.map.update_location(idx, x, y)
    
    def set_mode(self,idx, mode):
        self.panels[idx].set_mode(mode)