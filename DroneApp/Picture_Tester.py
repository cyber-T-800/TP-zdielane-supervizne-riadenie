# This Python file uses the following encoding: utf-8
import cv2

class Picture_Tester:
    def __init__(self):
        self.cam = cv2.VideoCapture(0)

    def read_img()
        img = self.cam.read()

    def __del__(self):
        cv2.destroyAllWindows()
        self.cam.release()




