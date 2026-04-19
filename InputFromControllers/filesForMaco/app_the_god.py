import sys
from PyQt5.QtWidgets import QApplication

from MainWindow import MainWindow
from GSTReceiver import GSTReceiver
from InputFromControllers.filesForMaco.VRInputThread import VRInputThread

def main():
    ports = [2222, 2223, 2224]

    app = QApplication(sys.argv)
    window = MainWindow(num_of_panels=3)

    receivers = []
    for i in range(3):
        r = GSTReceiver(drone_id=i, port=ports[i])
        r.frame_received.connect(window.set_stream_image)
        r.status_message.connect(window.set_atribute)
        app.aboutToQuit.connect(r.stop)
        receivers.append(r)

    vr_input = VRInputThread()
    vr_input.select_next.connect(window.select_next_panel)
    vr_input.confirm_selection.connect(window.confirm_selected_panel)
    vr_input.joystick_changed.connect(window.handle_joystick) #
    vr_input.mode_next.connect(window.select_next_mode)


    app.aboutToQuit.connect(vr_input.stop)

    for r in receivers:
        r.start()

    vr_input.start()

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()