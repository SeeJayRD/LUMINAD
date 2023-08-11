import sys
import os
import subprocess
import threading
import h5py
import hdf5plugin
import io
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer
from DEiger import DEigerClient as DEC

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('/home/quadro/Code/LUMINAD/stage/interface/assets/import.jpg'))
        DCU_IP = '169.254.254.1'
        self.dec = DEC.DEigerClient(DCU_IP)
        self.dec.setFileWriterConfig('mode','enabled')
        self.dec.setFileWriterConfig('name_pattern', 'test_')
        self.model = QtGui.QStandardItemModel()
        self.tree = QtWidgets.QTreeView()
        self.tree.setModel(self.model)
        self.refresh()
        self.tree.setHeaderHidden(True)
        refresh_btn = QtWidgets.QPushButton('Refresh')
        refresh_btn.clicked.connect(self.refresh)
        import_btn = QtWidgets.QPushButton('Import')
        import_btn.clicked.connect(self.import_fn)
        delete_btn = QtWidgets.QPushButton('Delete all')
        delete_btn.clicked.connect(self.delete_all)
        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tree)
        sublayout = QtWidgets.QHBoxLayout()
        sublayout.addWidget(refresh_btn)
        sublayout.addWidget(import_btn)
        sublayout.addWidget(delete_btn)
        layout.addLayout(sublayout)
        wid.setLayout(layout)
        self.show()
    def delete_all(self):
        self.dec.sendFileWriterCommand('clear')
        self.refresh()
    def refresh(self):
        self.model.clear()
        flist = self.dec.fileWriterFiles()['value']
        for fname in flist:
            item = QtGui.QStandardItem(fname)
            self.model.appendRow(item)
        return 
    def import_fn(self):
        src_list = self.tree.selectedIndexes()
        if len(src_list) == 0:
            return
        src = src_list[0].data()
        filedir = os.path.join('/home/quadro', src)
        dst = QtWidgets.QFileDialog.getSaveFileName(self, directory=filedir)[0]
        if dst == '':
            return
        b = self.dec.fileWriterFiles(filename = src)
        with open(dst, 'wb') as f:
            f.write(b)
        #f = h5py.File(io.BytesIO(initial_bytes=self.dec.fileWriterFiles(filename = src)), 'r')

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())

