#!/usr/bin/env python

from PyQt5.QtWidgets import QWidget, QSlider, QVBoxLayout, QApplication
from PyQt5.QtGui     import QPainter, QImage
from PyQt5.QtCore    import Qt, pyqtSignal
from imagebar import ImageBar
import qrangeslider as rs

class ImageSelector2(QWidget):
    resized = pyqtSignal(int)
    def __init__(self, parent=None):
        super(ImageSelector2, self).__init__()
        layout = QVBoxLayout()
        self.imagebar = ImageBar()  #Difference from IS1
        self.slider   = rs.QRangeSlider()
        self.slider.setRange(0,0)
        layout.addWidget(self.imagebar)
        layout.addWidget(self.slider)
        layout.setSpacing(0)
        self.setLayout(layout)
        
        
    def setThumbs(self, thumbs):
        #move the slide bar and trim indicator
        lastlen = len(self.imagebar.thumbs)
        lasthead = self.slider.start()
        lasttail = self.slider.end()

        self.imagebar.setThumbs(thumbs)
        if lastlen == len(thumbs):
            return
        self.slider.setMax(len(thumbs)-1)
        self.slider.setStart(lasthead)
        if lastlen -1 <= lasttail:
            self.slider.setEnd(len(thumbs)-1)
        else:
            self.slider.setEnd(lasttail)
        


def cv2toQImage(cv2image):
    """
    It breaks the original image
    """
    import numpy as np
    height, width = cv2image.shape[0:2]
    tmp = np.zeros_like(cv2image[:,:,0])
    tmp = cv2image[:,:,0].copy()
    cv2image[:,:,0] = cv2image[:,:,2]
    cv2image[:,:,2] = tmp
    return QImage(cv2image.data, width, height, width*3, QImage.Format_RGB888)



def main():
    import sys
    app = QApplication(sys.argv)
    window = ImageSelector2()
    window.resize(300,50)
    window.show()

    import cv2
    cap      = cv2.VideoCapture("examples/sample2.mov")
    ret = True
    thumbs = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h,w = frame.shape[0:2]
        thumbh = 100
        thumbw = w*thumbh//h
        thumb = cv2.resize(frame,(thumbw,thumbh),interpolation = cv2.INTER_CUBIC)
        thumbs.append(cv2toQImage(thumb))
        for i in range(9):
            ret = cap.grab()
            if not ret:
                break
        if not ret:
            break
    window.setThumbs(thumbs)
        
        
    sys.exit(app.exec_())    

if __name__ == "__main__":
    main()

        
