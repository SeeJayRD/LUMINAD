import sys
import json
import numpy
import requests
import time
from base64 import b64encode, b64decode
import tifffile
import h5py
import hdf5plugin
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer
from DEiger import DEigerClient as DEC

DETECTOR_PAUSE = 10
DEFAULT = 1

# simple detector client 
class DetectorClient:
    def __init__(self, ip , port):
        self._ip = ip
        self._port = port
        
    def set_config(self, param, value, interface = 'detector'):
        url = 'http://%s:%s/%s/api/1.8.0/config/%s' % (self._ip, self._port, interface, param)
        self._request(url, data = json.dumps({'value': value}))
		
    def send_command(self, command):
        url = 'http://%s:%s/detector/api/1.8.0/command/%s' % (self._ip, self._port, command)
        self._request(url)

    def get_status(self):
        url = 'http://%s:%s/detector/api/1.8.0/status/state' % (self._ip, self._port)
        return requests.get(url).json()['value']

    def get_mask(self, mask):
        url = 'http://%s:%s/detector/api/1.8.0/config/%s' % (self._ip, self._port, mask)
        darray = requests.get(url).json()['value']
        return numpy.frombuffer(b64decode(darray['data']),
            dtype=numpy.dtype(str(darray['type']))).reshape(darray['shape'])
            
    def set_mask(self, ndarray, mask):
        url = 'http://%s:%s/detector/api/1.8.0/config/%s' % (self._ip, self._port, mask)
        data_json = json.dumps({'value': {
                                    '__darray__': (1,0,0),
                                    'type': ndarray.dtype.str,
                                    'shape': ndarray.shape,
                                    'filters': ['base64'],
                                    'data': b64encode(ndarray.data).decode('ascii') }})
        self._request(url, data=data_json, headers={'Content-Type': 'application/json'})
        
    def _request(self, url, data={}, headers={}):
        reply = requests.put(url, data=data, headers=headers)
        assert reply.status_code in range(200, 300), reply.reason

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        DCU_IP = '169.254.254.1'
        self.setWindowIcon(QtGui.QIcon('/home/quadro/Code/LUMINAD/stage/interface/assets/flatfield.jpg'))
        self.client = DetectorClient(DCU_IP, '80')
        self.dec = DEC.DEigerClient(DCU_IP)
        self.dec.setConnectionTimeout(100)
        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        mainlayout = QtWidgets.QVBoxLayout()
        warning = QtWidgets.QLabel('STOP sending triggers to the detector BEFORE proceeding further')
        mainlayout.addWidget(warning)
        sublayout = QtWidgets.QHBoxLayout()
        load_btn = QtWidgets.QPushButton('Load flatfield')
        load_btn.clicked.connect(self.load)
        sublayout.addWidget(load_btn)
        take_btn = QtWidgets.QPushButton('Take flatfield')
        take_btn.clicked.connect(self.take)
        sublayout.addWidget(take_btn)
        cnt_label = QtWidgets.QLabel('Exposure:')
        self.set_pt = QtWidgets.QLineEdit(str(DEFAULT))
        self.set_pt.setMaximumWidth(40)
        unit_label = QtWidgets.QLabel('seconds')
        sublayout.addWidget(cnt_label)
        sublayout.addWidget(self.set_pt)
        sublayout.addWidget(unit_label)
        mainlayout.addLayout(sublayout)
        wid.setLayout(mainlayout)
        self.show()
    def load(self):
        dst, regex = QtWidgets.QFileDialog.getOpenFileName(self)
        if dst == '':
            return
        else:
            flatfield = tifffile.imread(dst)
            flatfield = numpy.median(flatfield) / flatfield.astype('float32')
            self.client.set_mask(flatfield, 'flatfield')
    def take(self):
        return
        exposure = float(self.set_pt.text())
        raw_dst, regex = QtWidgets.QFileDialog.getSaveFileName(self, caption='Save flatfield')
        self.dec.setMonitorConfig('discard_new', False)
        self.dec.setMonitorConfig('buffer_size', 1)
        self.dec.setMonitorConfig('mode', 'enabled')
        self.dec.setDetectorConfig('ntrigger', 1)
        self.dec.setDetectorConfig('nimages', 1)
        self.dec.setDetectorConfig('trigger_mode', 'inte')
        self.dec.sendDetectorCommand('arm')
        tic = time.time()
        self.dec.sendDetectorCommand('trigger', parameter = exposure)
        self.dec.sendDetectorCommand('disarm')
        toc = time.time()
        pause = 1 + exposure - toc + tic
        if pause < 0:
            time.sleep(pause)
        im_data = self.dec.monitorImages('next')
        flatfield = numpy.median(flatfield) / flatfield.astype('float32')
        self.client.set_mask(flatfield, 'flatfield')

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())


