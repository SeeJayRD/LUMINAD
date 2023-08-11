import sys
import json
import numpy
import requests
import time
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer


FIFO_PATH = '/tmp/script_editor_fifo'
DETECTOR_PAUSE = 10

TEMPLATE_HEADER=\
'''import sys
from time import time, sleep
from datetime import datetime
import http.client
import json
import math
import numpy as np
from DEiger import DEigerClient as DEC

data_dir = sys.argv[1]

ADDRESS = ('localhost', 8000)
MAX = 375
MIN = -333
DELAYPAUSE = 1
THRESH = 0.1
WAITPERPS = 0.03
NEWYEARS = 1672531200
UNITS = 1e-3 #ms''' 

TEMPLATE_OPT_A=\
'''MAX_PER_PIXEL_PER_MILLISECOND = 1000

Ndelays = {Ndelays}
DelayMin = {DelayMin}
DelayMax = {DelayMax}
Delays = np.linspace(DelayMin, DelayMax, Ndelays)'''

TEMPLATE_OPT_B=\
'''Delays = np.array({arb_seq})
Ndelays = len(Delays)
Delays.sort()'''

TEMPLATE_BODY=\
'''
count_time = {count_time}
frame_time = {frame_time}
nimages = {nimages}

NCycles = {NCycles}
indices = [*np.arange(0, Ndelays, 2, dtype=int), *np.flip(np.arange(1, Ndelays, 2, dtype=int))]

DCU_IP = '169.254.254.1'
dec = DEC.DEigerClient(DCU_IP)
dec.setConnectionTimeout(((frame_time*nimages)*UNITS)+2)
dec.setDetectorConfig('trigger_mode', 'ints')
dec.setDetectorConfig('ntrigger', Ndelays)
dec.setDetectorConfig('count_time', count_time*UNITS)
dec.setDetectorConfig('frame_time', frame_time*UNITS)
dec.setDetectorConfig('nimages', nimages)
dec.setFileWriterConfig('mode', 'enabled')
dec.setFileWriterConfig('nimages_per_file', nimages)

conn = http.client.HTTPConnection(*ADDRESS)
conn.request("GET", "/rdbk/val")
response = conn.getresponse()
raw = response.read()
rdbk = float(json.loads(raw.decode('utf-8')))
conn.request('POST','/set/val',str(Delays[0]))
response = conn.getresponse()
first_pause = WAITPERPS*math.fabs(Delays[0]-rdbk)
print('sleeping for {{}}'.format(first_pause))
sleep(first_pause)

fname_list = []

def copydata():
    print('Copying data from server')
    file_suffix = '_data_000001.h5'
    for name in fname_list:
        server_filename = '{{}}{{}}'.format(name, file_suffix)
        dec.fileWriterSave(server_filename, data_dir)

def handler(signum, frame):
    copydata()
    conn.close()

for k in range(0, NCycles):
    for j in range(0, Ndelays):
        ii = indices[j]
        print('now at {{}},{{}}'.format(k,ii))
        conn.request("GET", "/rdbk/val")
        response = conn.getresponse()
        raw = response.read()
        rdbk = float(json.loads(raw.decode('utf-8')))
        print('stage pos = {{}}'.format(rdbk))
        now = datetime.now()
        fname_prefix = '{{:02d}}_{{:02d}}_{{:02d}}_{{:02d}}_{{:02d}}'.format(now.month, now.day, now.hour, now.minute, now.second)
        fname = '{{}}_{{:03d}}_{{:06d}}_fs'.format(fname_prefix,k, int(rdbk*1e3))
        fname_list.append(fname)
        dec.setFileWriterConfig('name_pattern', fname)
        dec.sendDetectorCommand('arm')
        tic = time()
        dec.sendDetectorCommand('trigger')
        toc = time()
        print('exposure sleep for {{}}'.format(toc-tic))
        if toc - tic < (frame_time*nimages*UNITS):
            sleep(toc - toc)
        ii_next = indices[(j+1)%Ndelays]
        print('moving to {{}}'.format(Delays[ii_next]))
        pause = math.fabs(Delays[ii_next]-Delays[ii])*WAITPERPS
        conn.request('POST','/set/val',str(Delays[ii_next]))
        response = conn.getresponse()
        print('sleeping for {{}}'.format(pause))
        sleep(pause)
conn.close()

copydata()

sys.exit()'''

class App(QtWidgets.QMainWindow):
    def __init__(self):
        self.const_incr = True
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('/home/quadro/Code/LUMINAD/stage/interface/assets/make.jpg'))
        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        mainlayout = QtWidgets.QVBoxLayout()
        options_layout = QtWidgets.QHBoxLayout()
        options_label = QtWidgets.QLabel()
        options_label.setText('Choose delays with:')
        options_layout.addWidget(options_label)
        delay_toggle_0 = QtWidgets.QRadioButton('constant increment')
        delay_toggle_0.setChecked(True)
        options_layout.addWidget(delay_toggle_0)
        delay_toggle_1 = QtWidgets.QRadioButton('arbitrary sequence')
        delay_toggle_1.setChecked(False)
        options_layout.addWidget(delay_toggle_1)
        mainlayout.addLayout(options_layout)
        range_label = QtWidgets.QLabel()
        range_label.setText('————————— constant increment delay sequence —————————')
        mainlayout.addWidget(range_label)
        const_seq_layout = QtWidgets.QHBoxLayout()
        Nd_layout = QtWidgets.QHBoxLayout()
        Nd_label = QtWidgets.QLabel()
        Nd_label.setText('N delays')
        Nd_layout.addWidget(Nd_label)
        self.Nd_text = QtWidgets.QLineEdit('20')
        self.Nd_text.setMaximumWidth(60)
        Nd_layout.addWidget(self.Nd_text)
        const_seq_layout.addLayout(Nd_layout)
        DMin_layout = QtWidgets.QHBoxLayout()
        DMin_label = QtWidgets.QLabel()
        DMin_label.setText('Min delay (ps)')
        DMin_layout.addWidget(DMin_label)
        self.DMin_text = QtWidgets.QLineEdit('-300')
        self.DMin_text.setMaximumWidth(60)
        DMin_layout.addWidget(self.DMin_text)
        const_seq_layout.addLayout(DMin_layout)
        DMax_layout = QtWidgets.QHBoxLayout()
        DMax_label = QtWidgets.QLabel()
        DMax_label.setText('Max delay (ps)')
        DMax_layout.addWidget(DMax_label)
        self.DMax_text = QtWidgets.QLineEdit('300')
        self.DMax_text.setMaximumWidth(60)
        DMax_layout.addWidget(self.DMax_text)
        const_seq_layout.addLayout(DMax_layout)
        mainlayout.addLayout(const_seq_layout)
        arb_label = QtWidgets.QLabel()
        arb_label.setText('———— arbitrary delay sequence (comma seperated values, ps) ————')
        mainlayout.addWidget(arb_label)
        self.arb_text = QtWidgets.QPlainTextEdit('-300, 0, 300')
        self.arb_text.setStyleSheet('color: rgb(200,200,200)')
        mainlayout.addWidget(self.arb_text)
        detector_label = QtWidgets.QLabel()
        detector_label.setText('———————— electron detector acquisition parameters ————————')
        mainlayout.addWidget(detector_label)
        detectorlayout=QtWidgets.QHBoxLayout()
        NC_layout = QtWidgets.QHBoxLayout()
        NC_label = QtWidgets.QLabel()
        NC_label.setText('N cycles')
        NC_label.setMaximumWidth(60)
        NC_layout.addWidget(NC_label)
        self.NC_text = QtWidgets.QLineEdit('2')
        self.NC_text.setMaximumWidth(30)
        NC_layout.addWidget(self.NC_text)
        detectorlayout.addLayout(NC_layout) 
        ct_layout = QtWidgets.QHBoxLayout()
        ct_label = QtWidgets.QLabel()
        ct_label.setText('Count t.')
        ct_layout.addWidget(ct_label)
        self.ct_text = QtWidgets.QLineEdit('100')
        self.ct_text.setMaximumWidth(60)
        ct_layout.addWidget(self.ct_text)
        detectorlayout.addLayout(ct_layout)
        ft_layout = QtWidgets.QHBoxLayout()
        ft_label = QtWidgets.QLabel()
        ft_label.setText('Frame t.')
        ft_layout.addWidget(ft_label)
        self.ft_text = QtWidgets.QLineEdit('101')
        self.ft_text.setMaximumWidth(60)
        ft_layout.addWidget(self.ft_text)
        detectorlayout.addLayout(ft_layout)
        ni_layout = QtWidgets.QHBoxLayout()
        ni_label = QtWidgets.QLabel()
        ni_label.setText('Im./trig.')
        ni_label.setMaximumWidth(50)
        ni_layout.addWidget(ni_label)
        self.ni_text = QtWidgets.QLineEdit('10')
        self.ni_text.setMaximumWidth(30)
        ni_layout.addWidget(self.ni_text)
        detectorlayout.addLayout(ni_layout)
        mainlayout.addLayout(detectorlayout)
        savelayout = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton('Save script')
        save_btn.clicked.connect(self.save)
        save_and_run_btn = QtWidgets.QPushButton('Save and run script')
        save_and_run_btn.clicked.connect(self.save_and_run)
        savelayout.addWidget(save_btn)
        savelayout.addWidget(save_and_run_btn)
        mainlayout.addLayout(savelayout)
        wid.setLayout(mainlayout)
        delay_toggle_0.toggled.connect(self.toggle)
        self.show()
    def toggle(self):
        if self.const_incr:
            print('here')
            self.Nd_text.setStyleSheet('color: rgb(200,200,200)')
            self.DMin_text.setStyleSheet('color: rgb(200,200,200)')
            self.DMax_text.setStyleSheet('color: rgb(200,200,200)')
            self.arb_text.setStyleSheet('color: black')
            self.const_incr = False
        else:
            print('there')
            self.Nd_text.setStyleSheet('color: black')
            self.DMin_text.setStyleSheet('color: black')
            self.DMax_text.setStyleSheet('color: black')
            self.arb_text.setStyleSheet('color: rgb(200,200,200)')
            self.const_incr = True
    def save(self):
        raw_dst, regex = QtWidgets.QFileDialog.getSaveFileName(self, caption='Save script')
        if raw_dst == '':
            return raw_dst
        dst = fix_fname(raw_dst)
        if self.const_incr:
            Ndelays = int(self.Nd_text.text())
            DelayMin = int(self.DMin_text.text())
            DelayMax = int(self.DMax_text.text())
        else:
            arb_seq = [float(s) for s in self.arb_text.toPlainText().split(',')]
        NCycles = int(self.NC_text.text()) 
        count_time = float(self.ct_text.text()) 
        frame_time = float(self.ft_text.text()) 
        nimages = int(self.ni_text.text()) 
        with open(dst, 'w') as f:
            print(TEMPLATE_HEADER, file=f)
            if self.const_incr:
                print(TEMPLATE_OPT_A.format(Ndelays = Ndelays,
                    DelayMin = DelayMin,
                    DelayMax = DelayMax), file = f)
            else:
                print(TEMPLATE_OPT_B.format(arb_seq=arb_seq), file=f)
            print(TEMPLATE_BODY.format(NCycles=NCycles,
                    count_time = count_time,
                    frame_time = frame_time,
                    nimages = nimages), file=f)
        return dst
    def save_and_run(self):
        dst = self.save()
        data_dir = QtWidgets.QFileDialog.getExistingDirectory(self, caption='Select data directory')
        msg = '{},{}'.format(dst,data_dir)
        with open(FIFO_PATH, 'w') as f:
            print(msg, file=f)
        sys.exit()
    def closeEvent(self, event):
        with open(FIFO_PATH, 'w') as f:
            print('none', file=f)
        sys.exit()

def fix_fname(name):
    if len(name) < 3:
        return '{}.py'.format(name)
    elif name[-3:] == '.py':
        return name
    else:
        return '{}.py'.format(name)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
