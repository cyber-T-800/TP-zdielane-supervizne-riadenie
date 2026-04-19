from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QImage


class DroneCom(QObject):
    frame_received = pyqtSignal(int, QImage)
    position_recived = pyqtSignal(int, float, float, float)
    battery_recived = pyqtSignal(int, float, float)
    state_recived = pyqtSignal(int, bool, bool, bool, bool, str)
    def __init__(self):
        super().__init__()


    def handle_image(self, drone_id : int , qimage : QImage):
        self.frame_received.emit(drone_id, qimage)

    def handle_position(self,drone_id:int, x:float, y:float, z:float):
        self.position_recived.emit(drone_id, x, y, z)
    
    def handle_battery(self,drone_id:int, percentage:float, voltage:float):
        self.battery_recived.emit(drone_id, percentage, voltage)

    def handle_state(self,drone_id:int,connected:bool, armed:bool, guided:bool, manual_input:bool, mode:str):
        self.state_recived.emit(drone_id,connected, armed, guided, manual_input, mode)