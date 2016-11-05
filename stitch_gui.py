#!/usr/bin/env python

#Modified from Mandelbrot.py
#http://ftp.ics.uci.edu/pub/centos0/ics-custom-build/BUILD/PyQt-x11-gpl-4.7.2/examples/threads/mandelbrot.py

#This is a skeleton for a real time canvas. It is not sure it is extensible.

from PyQt4.QtCore  import *
from PyQt4.QtGui import *

import stitch
import math
import numpy as np
import cv2

class Renderer(QObject):
    frameRendered = pyqtSignal(QImage)  # it is target of emit()
    finished = pyqtSignal()
    progress = pyqtSignal(int)

    def __init__(self, parent=None, st=None, preview_ratio=1.0):
        super(Renderer, self).__init__(parent)
        self.st = st
        self._isRunning = True
        self.preview_ratio = preview_ratio
        self.st.before()


    def cv2toQImage(self,image):
        tmp = np.zeros_like(image[:,:,0])
        tmp = image[:,:,0].copy()
        image[:,:,0] = image[:,:,2]
        image[:,:,2] = tmp

                
    def task(self):
        if not self._isRunning:
            self._isRunning = True

        while self._isRunning == True:
            result = self.st.onestep()
            canvas = self.st.canvas[0].copy()
            height, width = canvas.shape[0:2]
            h = int(height*self.preview_ratio)
            w = int(width *self.preview_ratio)
            resized = cv2.resize(canvas, (w, h), interpolation = cv2.INTER_CUBIC)
            self.cv2toQImage(resized)
            image = QImage(resized.data, w, h, w*3, QImage.Format_RGB888)
            self.frameRendered.emit(image)
            num,den = self.st.progress()
            self.progress.emit(num*100/den)
            
            if result is not None:
                break
                        
        self.st.after()
        self.finished.emit()
        
    def stop(self):
        self._isRunning = False


class ExtensibleCanvasWidget(QWidget):
    def __init__(self, width, height, parent=None):
        super(ExtensibleCanvasWidget, self).__init__(parent)

        self.pixmap = QPixmap()

        self.setWindowTitle("ExtensibleCanvas")
        self.setCursor(Qt.CrossCursor)
        #This is the initial paint size
        self.resize(width, height)

    def paintEvent(self, event):
        #get the "paint" region"
        #paint is the body image of the widget
        #it is called again and again (who calls it?)
        #This just put the pixmap on the "paint"
        #perhaps the thread calls it.
        #It is called even when the image is just scrolled..... Redundant.
        #No it is required. Otherwise image disappears during scrolling.
        painter = QPainter(self)
        #Always resize. Is it ok here? NO
        #self.resize(self.pixmap.size())
        painter.drawPixmap(QPoint(), self.pixmap)
        #What if the pixmap size is different from painter size?
        #Paint does not expand even if the pixmap becomes larger and larger.
        #So you need resize() it.


    def updatePixmap(self, image):
        self.pixmap = QPixmap.fromImage(image)
        self.update()



    #This will be the trigger for the first rendering
    #def resizeEvent(self, event):
    #    self.thread.render(self.size())


class Example(QWidget):
    thread_invoker = pyqtSignal()

    def __init__(self, parent=None):
        super(Example, self).__init__(parent)

        self.setWindowTitle("Main Window")
        st = stitch.Stitcher(argv=sys.argv)
        #determine the shrink ratio to avoid too huge preview
        preview_ratio = 1.0
        if st.dimen[0] > 10000:
            preview_ratio = 10000.0 / st.dimen[0]
        if st.dimen[1]*preview_ratio > 500:
            preview_ratio = 500.0 / st.dimen[1]

        self.thread = QThread()
        self.thread.start()

        self.worker = Renderer(st=st, preview_ratio=preview_ratio)
        #it might be too early.
        
        #determine the window size
        height,width = st.canvas[0].shape[0:2]
        height = int(height*preview_ratio)
        #determine the preview area size
        width = int(width*preview_ratio)

        self.scrollArea = QScrollArea()
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.resize(500,height)
        self.largecanvas = ExtensibleCanvasWidget(width, height)
        self.worker.frameRendered.connect(self.largecanvas.updatePixmap)
        #Do not close the window when finished.
        #self.worker.finished.connect(self.finishIt)
        self.worker.moveToThread(self.thread)
        self.thread_invoker.connect(self.worker.task)
        self.thread_invoker.emit()

        self.scrollArea.setWidget(self.largecanvas)

        self.btnStop = QPushButton('Stop')
        self.btnStop.clicked.connect(lambda: self.worker.stop())
        self.btnStop.clicked.connect(self.terminateIt)
        
        self.progress = QProgressBar(self)
        self.worker.progress.connect(self.progress.setValue)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.btnStop)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.scrollArea)
        self.setLayout(self.layout)

        
    def terminateIt(self):
        self.close()
        sys.exit(1)  #terminated
        
    def finishIt(self):
        self.close()
        
    def closeEvent(self, event):
        self.stop_thread()
        
    def stop_thread(self):
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()


if __name__ == '__main__':

    import sys

    app = QApplication(sys.argv)
    win = Example()
    win.show()
    win.raise_()
    sys.exit(app.exec_())
