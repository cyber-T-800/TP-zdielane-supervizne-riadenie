from StreamPanel import StreamPanel

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

        self.setWindowTitle("DroneApp - Multi Drone Monitor")
        self.setFixedSize(1800, 500)

        self.num_of_panels = num_of_panels

        root = QWidget()
        root.setStyleSheet("background: #101010;")
        self.setCentralWidget(root)

        for i in range(self.num_of_panels): 
            self.panels[i] = StreamPanel(i)
            self.panels[i].clicked.connect(self.swap_panels)


        self.main_layout = QHBoxLayout(root)
        self.side_layout = QVBoxLayout()

        self.main_layout.addWidget(self.panels[0])

        for i in range(1, self.num_of_panels):
            self.side_layout.addWidget(self.panels[i])

        self.main_layout.addLayout(self.side_layout)

    def swap_panels(self, idx):
        if idx == self.current_idx or idx not in self.panels:
            return

        main_panel = self.panels[self.current_idx]
        target_panel = self.panels[idx]

        self.main_layout.removeWidget(main_panel)
        self.side_layout.removeWidget(target_panel)

        self.main_layout.insertWidget(0, target_panel)
        self.side_layout.insertWidget(self.current_idx, main_panel)

        self.current_idx = idx

    #def change_left():
        

    #def change_right():

    def set_stream_image(self, idx, image):
        self.panels[idx].set_image(image)

    def set_battery(self,idx, percentage, voltage):
        self.panels[idx].set_battery(percentage, voltage)

    def set_location(self,idx, x, y, z):
        self.panels[idx].set_location(x, y, z)
    
    def set_mode(self,idx, connected, armed, guided, manual_input, mode):
        self.panels[idx].set_mode(connected, armed, guided, manual_input, mode)