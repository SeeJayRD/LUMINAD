import subprocess
import threading
import sys
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer

VIEWER_CMD = './viewer.py'
TRIGGER_CMD = './live_trigger.py'
IMPORT_CMD = './import.py'
DELAY_CMD = './live_delay.py'
SETTINGS_CMD = './settings.py'
FLATFIELD_CMD = './flatfield.py'
EDITOR_CMD = './editor.py'
FIFO_PATH = '/tmp/script_editor_fifo'

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('/home/quadro/Code/LUMINAD/stage/interface/assets/launcher.jpg'))
        self.viewer_running = False
        self.trigger_running = False
        self.import_running = False
        self.settings_running = False
        self.flatfield_running = False
        self.delay_running = False
        self.editor_running = False
        self.script_running = False
        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        layout = QtWidgets.QVBoxLayout()
        self.viewer_btn = QtWidgets.QPushButton('Viewer')
        self.viewer_btn.clicked.connect(self.launch_viewer)
        layout.addWidget(self.viewer_btn)
        wid.setLayout(layout)
        self.trigger_btn = QtWidgets.QPushButton('Live trigger')
        self.trigger_btn.clicked.connect(self.launch_trigger)
        layout.addWidget(self.trigger_btn)
        self.delay_btn = QtWidgets.QPushButton('Live delay')
        self.delay_btn.clicked.connect(self.launch_delay)
        layout.addWidget(self.delay_btn)
        wid.setLayout(layout)
        self.import_btn = QtWidgets.QPushButton('Import from DCU')
        self.import_btn.clicked.connect(self.launch_import)
        layout.addWidget(self.import_btn)
        wid.setLayout(layout)
        self.settings_btn = QtWidgets.QPushButton('Detector settings')
        self.settings_btn.clicked.connect(self.launch_settings)
        layout.addWidget(self.settings_btn)
        self.flatfield_btn = QtWidgets.QPushButton('Change flatfield')
        self.flatfield_btn.clicked.connect(self.launch_flatfield)
        layout.addWidget(self.flatfield_btn)
        wid.setLayout(layout)
        self.editor_btn = QtWidgets.QPushButton('Make scan script')
        self.editor_btn.clicked.connect(self.launch_editor)
        layout.addWidget(self.editor_btn)
        self.run_btn = QtWidgets.QPushButton('Run scan script')
        self.run_btn.clicked.connect(self.run_script)
        layout.addWidget(self.run_btn)
        wid.setLayout(layout)
        self.launch_viewer()
        self.show()
    def launch_viewer(self):
        if self.viewer_running:
            return
        def run_in_thread():
            self.viewer_btn.setStyleSheet('QPushButton { background-color: red }')
            self.viewer_running = True
            proc = subprocess.Popen(['python', VIEWER_CMD])
            proc.wait()
            self.viewer_running = False
            self.viewer_btn.setStyleSheet('')
            return
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    def launch_trigger(self):
        if self.trigger_running:
            return
        def run_in_thread():
            self.trigger_btn.setStyleSheet('QPushButton { background-color: red }')
            self.trigger_running = True
            proc = subprocess.Popen(['python', TRIGGER_CMD])
            proc.wait()
            self.trigger_running = False
            self.trigger_btn.setStyleSheet('')
            return
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    def launch_import(self):
        if self.import_running:
            return
        def run_in_thread():
            self.import_btn.setStyleSheet('QPushButton { background-color: red }')
            self.import_running = True
            proc = subprocess.Popen(['python', IMPORT_CMD])
            proc.wait()
            self.import_running = False
            self.import_btn.setStyleSheet('')
            return
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    def launch_delay(self):
        if self.delay_running:
            return
        def run_in_thread():
            self.delay_btn.setStyleSheet('QPushButton { background-color: red }')
            self.delay_running = True
            proc = subprocess.Popen(['python', DELAY_CMD])
            proc.wait()
            self.delay_running = False
            self.delay_btn.setStyleSheet('')
            return
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    def launch_settings(self):
        if self.settings_running:
            return
        def run_in_thread():
            self.settings_btn.setStyleSheet('QPushButton { background-color: red }')
            self.settings_running = True
            proc = subprocess.Popen(['python', SETTINGS_CMD])
            proc.wait()
            self.settings_running = False
            self.settings_btn.setStyleSheet('')
            return
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    def launch_flatfield(self):
        if self.flatfield_running:
            return
        def run_in_thread():
            self.flatfield_btn.setStyleSheet('QPushButton { background-color: red }')
            self.flatfield_running = True
            proc = subprocess.Popen(['python', FLATFIELD_CMD])
            proc.wait()
            self.flatfield_running = False
            self.flatfield_btn.setStyleSheet('')
            return
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    def launch_editor(self):
        if self.editor_running:
            return
        if os.path.exists(FIFO_PATH):
            os.unlink(FIFO_PATH)
        if not os.path.exists(FIFO_PATH):
            os.mkfifo(FIFO_PATH)
        def run_in_thread():
            self.editor_btn.setStyleSheet('QPushButton { background-color: red }')
            self.editor_running = True
            proc = subprocess.Popen(['python', EDITOR_CMD])
            with open(FIFO_PATH, 'r') as f:
                response = f.readline().strip()
            proc.wait()
            self.editor_running = False
            self.editor_btn.setStyleSheet('')
            if 'none' in response:
                return
            elif self.script_running:
                return
            else:
                path, data_dir = response.split(',')
                self._run_script(path, data_dir)
        thread = threading.Thread(target=run_in_thread)
        thread.start()
    def run_script(self):
        if self.script_running:
            return
        path, regex = QtWidgets.QFileDialog.getOpenFileName(self, caption='Select experiment script')
        data_dir = QtWidgets.QFileDialog.getExistingDirectory(self, caption='Select data directory')
        self._run_script(path, data_dir)
    def _run_script(self, path, data_dir):
        if path == '' or data_dir == '':
            return
        def run_in_thread():
            self.run_btn.setStyleSheet('QPushButton { background-color: red }')
            self.script_running = True
            proc = subprocess.Popen(['python', path, data_dir])
            proc.wait()
            self.script_running = False
            self.run_btn.setStyleSheet('')
            return
        thread = threading.Thread(target=run_in_thread)
        thread.start()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    #ex.setWindowIcon(QtGui.QIcon('/home/quadro/Code/GUI_Detector/dectris.jpeg'))
    sys.exit(app.exec_())
