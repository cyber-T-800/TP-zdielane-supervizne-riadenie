import sys
from MainWindow import MainWindow
from GSTReceiver import GSTReceiver
from ROSReceiver import ROSReceiver


from PyQt5.QtWidgets import QApplication

def main():
    port = [2222, 2223, 2224]

    topics = ["drone1/front_camera/image_raw","drone2/front_camera/image_raw","drone3/front_camera/image_raw"]

    web_cam_topic = "/image_raw/compressed"

    app = QApplication(sys.argv)

    window = MainWindow()


    receiver = GSTReceiver(drone_id=0,port=port[0])
    receiver.frame_received.connect(window.set_stream_image)
    receiver.status_message.connect(window.set_atribute)

    receiver = GSTReceiver(drone_id=1,port=port[1])
    receiver.frame_received.connect(window.set_stream_image)
    receiver.status_message.connect(window.set_atribute)
        
    app.aboutToQuit.connect(receiver.stop)

    receiver.start()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()