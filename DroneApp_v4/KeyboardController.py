from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget

class KeyboardController(QWidget):
    motion_signal = pyqtSignal(float, float, float, float, float, float)

    t_pressed = pyqtSignal()
    q_pressed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self.keys_pressed = set()

    def keyPressEvent(self, event):
        key = event.key()
        self.keys_pressed.add(key)

        if key == Qt.Key.Key_T:
            self.t_pressed.emit()
        elif key == Qt.Key.Key_Q:
            self.q_pressed.emit()

        self.update_motion()

    def keyReleaseEvent(self, event):
        key = event.key()
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)

        self.update_motion()

    def update_motion(self):
        lin_x = 0.0
        lin_y = 0.0
        lin_z = 0.0
        ang_x = 0.0
        ang_y = 0.0
        ang_z = 0.0

        if Qt.Key.Key_W in self.keys_pressed:
            lin_x += 1.0
        if Qt.Key.Key_S in self.keys_pressed:
            lin_x -= 1.0

        if Qt.Key.Key_Control in self.keys_pressed:
            lin_z += 1.0
        if Qt.Key.Key_Space in self.keys_pressed:
            lin_z -= 1.0


        if Qt.Key.Key_A in self.keys_pressed:
            ang_z += 1.0
        if Qt.Key.Key_D in self.keys_pressed:
            ang_z -= 1.0

        self.motion_signal.emit(lin_x, lin_y, lin_z, ang_x, ang_y, ang_z)