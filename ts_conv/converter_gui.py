#!/usr/bin/env python3
#-*- coding: utf-8 -*-

#Core of the GUI and image process
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QApplication, QPushButton, QCheckBox, QFileDialog, QMessageBox, QProgressBar
from PyQt5.QtGui     import QPalette, QPainter
from PyQt5.QtCore    import QFileInfo, QObject, QThread, QTranslator, QLocale, Qt, pyqtSignal, pyqtSlot
from enum import IntEnum
import cv2
import numpy as np
import math
import time
import logging

#File handling
import os
import subprocess

#final image tranformation
from ts_conv import film
from ts_conv import helix
from ts_conv import rect
from tiledimage.cachedimage import CachedImage
#options handler
import sys


#Drag and drop work. Buttons would not be necessary.

class ImageProcessType(IntEnum):
    NONE         = 0
    FINISH_PREF  = 1
    FINISH_HELIX = 2
    FINISH_RECT  = 4

class ImageProcess(QObject):
    def __init__(self, process_type, filenames, parent = None):
        super(ImageProcess, self).__init__(parent)

        self.process_type = process_type
        self.filenames = filenames
        self.progress = 0
        self.stage = 2
        if self.process_type & ImageProcessType.FINISH_PREF:
            self.stage += 2
        if self.process_type & ImageProcessType.FINISH_HELIX:
            self.stage += 2
        if self.process_type & ImageProcessType.FINISH_RECT:
            self.stage += 2

    def increase_progress(self):
        self.progress += 100 / self.stage / len(self.filenames)
        self.progress_changed.emit(self.progress)

    @pyqtSlot()
    def start_process(self):
        logger = logging.getLogger()

        for filename in self.filenames:
            if QThread.currentThread().isInterruptionRequested():
                return
            if filename[-6:] == ".pngs/":
                filename = filename[:-1]
                cachedimage = CachedImage("inherit",
                                          dir=filename,
                                          disposal=False)
                logger.debug(":: {0}".format(cachedimage))
                img = cachedimage.get_region(None)
            else:
                img = cv2.imread(filename)
                self.increase_progress()
                
            if QThread.currentThread().isInterruptionRequested():
                return
            if self.process_type & ImageProcessType.FINISH_PREF:
                img = film.filmify( img )
                self.increase_progress()
                filename += ".film.png"
                cv2.imwrite(filename, img)
                self.increase_progress()
                
            if QThread.currentThread().isInterruptionRequested():
                return
            if self.process_type & ImageProcessType.FINISH_HELIX:
                self.increase_progress()
                himg = helix.helicify( img )
                self.increase_progress()
                cv2.imwrite(filename + ".helix.png", himg)
                self.increase_progress()
                
            if QThread.currentThread().isInterruptionRequested():
                return
            if self.process_type & ImageProcessType.FINISH_RECT:
                self.increase_progress()
                rimg = rect.rectify( img )
                self.increase_progress()
                cv2.imwrite(filename + ".rect.png", rimg)
                self.increase_progress()

        self.progress_changed.emit(100)
        self.finished.emit()

    progress_changed = pyqtSignal(int, name = "progressChanged")
    finished = pyqtSignal()

#https://www.tutorialspoint.com/pyqt/pyqt_qfiledialog_widget.htm
class SettingsGUI(QWidget):
    def __init__(self, parent = None):
        super(SettingsGUI, self).__init__(parent)
        self.setAcceptDrops(True)

        finish_layout = QVBoxLayout()
        self.btn_finish_perf = QCheckBox(self.tr('Add the film perforations'))
        finish_layout.addWidget(self.btn_finish_perf)
        self.btn_finish_helix = QCheckBox(self.tr('Make a helical image'))
        finish_layout.addWidget(self.btn_finish_helix)
        self.btn_finish_rect = QCheckBox(self.tr('Make a rectangular image'))
        finish_layout.addWidget(self.btn_finish_rect)
        self.pbar = QProgressBar()
        finish_layout.addWidget(self.pbar)

        self.setLayout(finish_layout)
        self.setWindowTitle("Drag&Drop files")

        self.thread = QThread()

    def closeEvent(self, event):
        if self.thread.isRunning():
            box = QMessageBox(QMessageBox.Question,
                              "Quit",
                              "Do you want to interrupt processing?",
                              QMessageBox.Yes | QMessageBox.No,
                              self)
            self.thread.finished.connect(box.reject)
            if box.exec() == QMessageBox.Yes:
                self.thread.quit()
                self.thread.requestInterruption()
                self.thread.wait()
                event.accept()
            else:
                event.ignore()

    def dragEnterEvent(self, event):
        if self.thread.isRunning():
            return
        logger = logging.getLogger()
        mimeData = event.mimeData()
        logger.debug('dragEnterEvent')
        for mimetype in mimeData.formats():
            logger.debug('MIMEType: {0}'.format(mimetype))
            logger.debug('Data: {0}'.format(mimeData.data(mimetype)))
        #Check MIME type
        if mimeData.hasUrls():
            for url in mimeData.urls():
                if url.isLocalFile():
                    file_info = QFileInfo(url.toLocalFile())
                    #Check if a file readable
                    if file_info.isFile() and file_info.isReadable():
                        event.acceptProposedAction()

    def dropEvent(self, event):
        logger = logging.getLogger()
        mimeData = event.mimeData()
        logger.debug('dropEvent')
        for mimetype in mimeData.formats():
            logger.debug('MIMEType: {0}'.format(mimetype))
            logger.debug('Data: {0}'.format(mimeData.data(mimetype)))
        logger.debug("len:{0}".format(len(mimeData.formats())))

        filenames = [url for url in mimeData.urls() if url.isLocalFile()]
        filenames = [url.toLocalFile() for url in filenames]

        if len(filenames) > 0:
            process_type = ImageProcessType.NONE
            if self.btn_finish_perf.isChecked():
                process_type = process_type | ImageProcessType.FINISH_PREF
            if self.btn_finish_helix.isChecked():
                process_type = process_type | ImageProcessType.FINISH_HELIX
            if self.btn_finish_rect.isChecked():
                process_type = process_type | ImageProcessType.FINISH_RECT
            self.process = ImageProcess(process_type, filenames)
            self.process.progress_changed.connect(self.pbar.setValue)

            self.process.moveToThread(self.thread)
            self.process.finished.connect(self.thread.quit)
            self.thread.started.connect(self.process.start_process)

            self.thread.start()


#for pyinstaller
def resource_path(relative):
    return os.path.join(
        os.environ.get(
            "_MEIPASS",
            os.path.abspath(".")
        ),
        relative
    )

import pkgutil

def main():
    logging.basicConfig(level=logging.WARN,
                        format="%(asctime)s %(levelname)s %(message)s")
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    path = os.path.dirname(rect.__file__)
    if QLocale.system().language() == QLocale.Japanese:
        translator.load(path+"/i18n/trainscanner_ja")
    app.installTranslator(translator)
    se = SettingsGUI()
    se.show()
    se.raise_()
    sys.exit(app.exec_())
	
if __name__ == '__main__':
    main()
