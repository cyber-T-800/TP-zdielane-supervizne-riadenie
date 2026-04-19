from StreamPanel import StreamPanel

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    def __init__(self, num_of_panels=3):
        super().__init__()
        self.panels = {}
        self.current_idx = 0
        self.highlight_idx = 0

        self.setWindowTitle("DroneApp - Multi Drone Monitor")
        self.setFixedSize(1800, 900)

        self.num_of_panels = num_of_panels

        root = QWidget()
        root.setStyleSheet("background: #101010;")
        self.setCentralWidget(root)

        for i in range(self.num_of_panels):
            self.panels[i] = StreamPanel(i)
            self.panels[i].clicked.connect(self.on_panel_clicked)

        self.main_layout = QHBoxLayout(root)
        self.side_layout = QVBoxLayout()

        self.main_layout.addWidget(self.panels[0])

        for i in range(1, self.num_of_panels):
            self.side_layout.addWidget(self.panels[i])

        self.main_layout.addLayout(self.side_layout)

        self.update_selection_highlight()

    def update_selection_highlight(self):
        for idx, panel in self.panels.items():
            panel.set_selected(idx == self.highlight_idx)



    def select_next_panel(self):
        self.highlight_idx = (self.highlight_idx + 1) % self.num_of_panels
        self.update_selection_highlight()


    def confirm_selected_panel(self):
        self.swap_panels(self.highlight_idx)

    def handle_joystick(self, x, y):
        # x = -1 .. 1  (ľavá/pravá)
        # y = -1 .. 1  (dopredu/dozadu)
        # 0 = nič sa nedeje (deadzone už aplikovaný)

        print(f"Joystick X={x:.2f}, Y={y:.2f}")

        # TODO:
        # tu treba mapovať na pohyb dronu, napr:
        # forward = y
        # turn = x

        # príklad:
        # if y > 0 → dopredu
        # if y < 0 → dozadu
        # if x > 0 → doprava
        # if x < 0 → doľava

    def select_next_mode(self):
        # ŠIMON TUTO IMPLEMENTUJ ZMENU MODU
        pass

    def on_panel_clicked(self, idx):
        self.highlight_idx = idx
        self.update_selection_highlight()
        self.swap_panels(idx)

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
        self.update_selection_highlight()

    def set_stream_image(self, idx, image):
        self.panels[idx].set_image(image)

    def set_atribute(self, idx, atribute):
        self.panels[idx].set_location(atribute)