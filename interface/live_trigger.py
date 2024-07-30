import traceback
import sys
import os
import subprocess
import threading
import numpy as np
import math
import time
from PIL import Image
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer
from DEiger import DEigerClient as DEC

#Irene was here
TIMEOUT = 60
PARAM = 'count_time'
SCALE = 1000
DEFAULT = 100
TYPE = float
LOCK_PATH = "/tmp/.trigger_lock"

def freq2period(freq):
    return int(1000.0/freq)

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        if os.path.exists(LOCK_PATH):
            print("\033[1;38;5;196mA SCAN IS RUNNING:\033[m:\nA lock file indicates that another script is already sending triggers to the detector. If you are certain that no other scans are running, remove the lock file by opening a terminal and typing\n rm /tmp/.trigger_lock\n and try starting this trigger module again.")
            sys.exit()
        else:
            os.mknod(LOCK_PATH)
        self.setWindowIcon(QtGui.QIcon('/home/quadro/Code/LUMINAD/stage/interface/assets/trigger.jpg'))
        ### flags ###
        self.busy = False
        ### gui widgets ###
        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        mainlayout = QtWidgets.QVBoxLayout()
        exposurelayout = QtWidgets.QHBoxLayout()
        cnt_label = QtWidgets.QLabel('Exposure')
        self.exposure = DEFAULT/SCALE
        self.set_pt = QtWidgets.QLineEdit(str(DEFAULT))
        cnt_units = QtWidgets.QLabel('ms')
        exposurelayout.addWidget(cnt_label)
        exposurelayout.addWidget(self.set_pt)
        exposurelayout.addWidget(cnt_units)
        savelayout = QtWidgets.QHBoxLayout()
        fn_lbl = QtWidgets.QLabel('Filename: ')
        self.fn_entry = QtWidgets.QLineEdit('My_data')
        self.fn_cbox = QtWidgets.QCheckBox('Enable Filewriter')
        savelayout.addWidget(fn_lbl)
        savelayout.addWidget(self.fn_entry)
        savelayout.addWidget(self.fn_cbox)
        cyclelayout = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton('Infinite Trig.')
        self.start_btn.clicked.connect(self.start)
        self.single_btn = QtWidgets.QPushButton('Single Trig.')
        self.single_btn.clicked.connect(self.single)
        self.stop_btn = QtWidgets.QPushButton('Stop')
        self.stop_btn.clicked.connect(self.stop)
        cyclelayout.addWidget(self.start_btn)
        cyclelayout.addWidget(self.single_btn)
        cyclelayout.addWidget(self.stop_btn)
        mainlayout.addLayout(exposurelayout)
        mainlayout.addLayout(savelayout)
        mainlayout.addLayout(cyclelayout)
        wid.setLayout(mainlayout)
        ### start ###
        self.init_thread()
        self.show()
    def init_thread(self):
        self.thread = QThread(self)
        self.thread.start()
        self.messenger = Messenger()
        self.messenger.done_sig.connect(self.thread_done)
        self.messenger.moveToThread(self.thread)
        def push():
            new_exposure = float(self.set_pt.text())/SCALE
            if (new_exposure > (TIMEOUT-1)):
                self.exposure = (TIMEOUT-1)
                self.set_pt.setText(str((TIMEOUT-1)*SCALE))
            else:
                self.exposure = float(self.set_pt.text())/SCALE
        self.set_pt.editingFinished.connect(push)
        self.fn_cbox.toggled.connect(self.messenger.save_sig.emit)
        self.fn_entry.editingFinished.connect(lambda : self.messenger.name_sig.emit(self.fn_entry.text()))
        self.messenger.exit_sig.connect(self.kill_thread)
    def kill_thread():
        print('here')
        self.thread.exit()
        time.sleep(1)
        self.init_thread()
    def start(self):
        if self.busy:
            return
        self.busy = True
        self.start_btn.setStyleSheet('QPushButton { background-color: red}') 
        self.messenger.trig_sig.emit(self.exposure)
    def single(self):
        if self.busy:
            return
        self.single_btn.setStyleSheet('QPushButton { background-color: red}') 
        self.messenger.trig_sig.emit(self.exposure)
    def stop(self):
        self.busy = False
    def thread_done(self):
        if self.busy:
            self.messenger.trig_sig.emit(self.exposure)
        else:
            self.clear_btns()
    def clear_btns(self):
        self.single_btn.setStyleSheet('')
        self.start_btn.setStyleSheet('')
        self.stop_btn.setStyleSheet('')
    def closeEvent(self, event):
        os.remove(LOCK_PATH)
        self.messenger.quit_sig.emit()
        self.thread.quit()
        self.thread.wait()

class Messenger(QObject):
    trig_sig = pyqtSignal(float)
    stop_sig = pyqtSignal()
    quit_sig = pyqtSignal()
    done_sig = pyqtSignal()
    exit_sig = pyqtSignal()
    save_sig = pyqtSignal()
    name_sig = pyqtSignal(str)
    def __init__(self, parent = None):
        super(Messenger, self).__init__(parent)
        DCU_IP = '169.254.254.1'
        self.dec = DEC.DEigerClient(DCU_IP)
        self.dec.setConnectionTimeout(TIMEOUT)
        self.dec.setDetectorConfig('ntrigger', 1)
        self.dec.setDetectorConfig('nimages', 1)
        self.dec.setDetectorConfig('trigger_mode', 'inte')
        self.running = False
        self.saving = False
        self.trig_sig.connect(self.trigger)
        self.stop_sig.connect(self.stop)
        self.quit_sig.connect(self.quit)
        self.save_sig.connect(self.save)
        self.name_sig.connect(self.name)
    def stop(self):
        self.running = False
        self.dec.sendDetectorCommand('cancel')
        self.dec.sendDetectorCommand('disarm')
    def trigger(self, exposure):
        if self.running:
            return
        def run_in_thread():
            self.running = True
            try:
                self.dec.sendDetectorCommand('arm')
                self.dec.sendDetectorCommand('trigger', parameter = exposure)
                self.dec.sendDetectorCommand('disarm')
            except RuntimeError as ex:
                print(ex)
                self.dec.sendDetectorCommand('abort')
                time.sleep(1)
            self.done_sig.emit()
            self.running = False
            return
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    def save(self):
        self.saving = not self.saving
        if self.saving:
            self.dec.setFileWriterConfig('mode', 'enabled')
        else:
            self.dec.setFileWriterConfig('mode', 'disabled')
    def name(self, name_str):
        self.dec.setFileWriterConfig('name_pattern', name_str)
    def quit(self):
        self.stop()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        printtraceback.print_exc()

