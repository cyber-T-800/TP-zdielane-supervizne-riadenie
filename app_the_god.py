import sys
from MainWindow import MainWindow
from GSTReceiver import GSTReceiver
from ROSReceiver import ROSReceiver


from PyQt5.QtWidgets import QApplication

def main():

    sim = True
    ports = [2222, 2223, 2224]

    topics = ["drone1/front_camera/image_raw","drone2/front_camera/image_raw","drone3/front_camera/image_raw"]

    app = QApplication(sys.argv)

    window = MainWindow()

    if sim:
        receiver = ROSReceiver(drone_id=0,topic=topics[0],compressed=True)
        receiver.frame_received.connect(window.set_stream_image)
        receiver.status_message.connect(window.set_atribute)
    else:
        receiver = GSTReceiver(drone_id=0,port=ports[0])
        receiver.frame_received.connect(window.set_stream_image)
        receiver.status_message.connect(window.set_atribute)

        
    app.aboutToQuit.connect(receiver.stop)

    receiver.start()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()