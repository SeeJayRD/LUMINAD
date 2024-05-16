import sys
import http.client
import json
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer, Qt

ADDRESS = ('localhost', 8000)
DEFAULT = 0
MAX = 375
MIN = -333

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('/home/quadro/Code/LUMINAD/stage/interface/assets/delay.jpg'))
        self.stale = True
        self.delay = DEFAULT
        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        mainlayout = QtWidgets.QHBoxLayout()
        self.set_box = QtWidgets.QCheckBox('enable set point:')
        mainlayout.addWidget(self.set_box)
        self.sl = QtWidgets.QSlider(Qt.Horizontal)
        self.sl.setMinimumWidth(400)
        self.sl.setMinimum(MIN)
        self.sl.setMaximum(MAX)
        self.sl.setValue(int(self.delay)) #Qt slider only accepts ints
        self.sl.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.sl.setTickInterval(80)
        self.sl.valueChanged.connect(self.sl_valuechange)
        mainlayout.addWidget(self.sl)
        self.set_pt = QtWidgets.QLineEdit(str(self.delay))
        self.set_pt.setMaximumWidth(40)
        self.set_pt.editingFinished.connect(self.txt_valuechange)
        mainlayout.addWidget(self.set_pt)
        unit_label = QtWidgets.QLabel()
        unit_label.setText('ps')
        mainlayout.addWidget(unit_label)
        self.rdbk = QtWidgets.QLabel()
        self.rdbk.setMinimumWidth(100)
        self.rdbk.setText('   rdbk: {}'.format(self.delay))
        mainlayout.addWidget(self.rdbk)
        wid.setLayout(mainlayout)
        self.timer=QTimer()
        self.timer.timeout.connect(self.update_rdbk)
        self.timer.start(1000)
        self.show()
    def sl_valuechange(self):
        self.delay = self.sl.value()
        self.set_pt.setText(str(self.delay))
        self.stale = True
    def txt_valuechange(self):
        set_pt = float(self.set_pt.text())
        if (set_pt < MIN):
            self.delay = MIN
            self.set_pt.setText(str(self.delay))
        elif (set_pt > MAX):
            self.delay = MAX
            self.set_pt.setText(str(self.delay))
        else:
            self.delay = set_pt
        self.sl.setValue(int(self.delay))
        self.stale = True
    def update_rdbk(self):
        conn = http.client.HTTPConnection(*ADDRESS)
        conn.request("GET", "/rdbk/val")
        response = conn.getresponse()
        raw = response.read()
        rdbk = json.loads(raw.decode('utf-8'))
        if self.stale and self.set_box.isChecked():
            conn.request('POST','/set/val',str(self.delay))
            response = conn.getresponse()
            self.stale = False
        self.rdbk.setText('   rdbk: {}'.format(rdbk))
        conn.close()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        printtraceback.print_exc()

