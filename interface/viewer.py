import io
import json
import os
import sys
import time

import h5py
import hdf5plugin
import numpy as np

from matplotlib import cm
from PIL import Image
import tifffile
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer, Qt
import pyqtgraph as pg
from scipy.fft import fft2

from DEiger import DEigerClient as DEC

from http.client import HTTPConnection

NpxH = 512
NpxV = 512
WinH = 1080
WinV = 1080
maxCrossWidth = 200
maxCrossHeight = 200
buttonWidth = 400
BLENGTH = 1000
STAGEADDRESS = ('localhost', 8000)
IMBUG = 50

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.nframes = 10
        self.dead = True
        self.setWindowIcon(QtGui.QIcon('/home/quadro/Code/LUMINAD/stage/interface/assets/viewer.jpg'))
        self.row=0
        self.col=0
        self.img_fft = popIm()
        self.is_live = True
        self.rois = [[None, np.zeros(BLENGTH)]]
        self.openArray = np.ones((NpxH, NpxV))
        self.imbuff = np.ones((IMBUG, NpxH, NpxV))
        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        mainlayout = QtWidgets.QHBoxLayout()
        plotlayout = QtWidgets.QVBoxLayout()
        lineoutlayout = QtWidgets.QHBoxLayout()
        buttonlayout = QtWidgets.QVBoxLayout()
        self.image = pg.image(self.openArray, levels=[0,1], 
                autoRange=True, autoHistogramRange=True)
        self.vLine = pg.InfiniteLine(angle=90, movable=False)
        self.hLine = pg.InfiniteLine(angle=0, movable=False)
        self.image.addItem(self.vLine, ignoreBounds=True)
        self.image.addItem(self.hLine, ignoreBounds=True)
        self.cross_h_wid = pg.PlotWidget()
        self.cross_hLine = pg.InfiniteLine(angle=0, movable=True, pen = pg.mkPen('w', 
            width=2, style=Qt.DashLine), hoverPen=pg.mkPen('w', width=4))
        self.cross_h_wid.addItem(self.cross_hLine)
        self.cross_h_wid.setTitle('ROI: full detector X lineout')
        self.cross_h_wid.setMaximumHeight(maxCrossHeight)
        self.cross_h_plt = self.cross_h_wid.plot()
        self.cross_h_plt.setData(range(NpxV), np.ones(NpxV))
        self.cross_v_wid = pg.PlotWidget()
        self.cross_vLine = pg.InfiniteLine(angle=0, movable=True, pen = pg.mkPen('w', 
            width=2, style=Qt.DashLine), hoverPen=pg.mkPen('w', width=4))
        self.cross_v_wid.addItem(self.cross_vLine)
        self.cross_v_wid.setTitle('ROI: full detector Y lineout')
        self.cross_v_wid.setMaximumHeight(maxCrossHeight)
        self.cross_v_plt = self.cross_v_wid.plot()
        self.cross_v_plt.setData(range(NpxH), np.ones(NpxH))
        self.left_menu = self.cross_h_wid.getPlotItem().getViewBox().menu
        left_dataMenu = self.left_menu.addMenu('Plot variable')
        left_pltActionX = QtWidgets.QAction('X profile', self)
        left_pltActionY = QtWidgets.QAction('Y profile', self)
        left_pltActionI = QtWidgets.QAction('integral v time', self)
        left_pltActionX.triggered.connect(self.left_pltX)
        left_pltActionY.triggered.connect(self.left_pltY)
        left_pltActionI.triggered.connect(self.left_pltI)
        left_dataMenu.addAction(left_pltActionX)
        left_dataMenu.addAction(left_pltActionY)
        left_dataMenu.addAction(left_pltActionI)
        self.right_menu = self.cross_v_wid.getPlotItem().getViewBox().menu
        right_dataMenu = self.right_menu.addMenu('Plot variable')
        right_pltActionX = QtWidgets.QAction('X_lineout', self)
        right_pltActionY = QtWidgets.QAction('Y_lineout', self)
        right_pltActionI = QtWidgets.QAction('integral_v_time', self)
        right_pltActionX.triggered.connect(self.right_pltX)
        right_pltActionY.triggered.connect(self.right_pltY)
        right_pltActionI.triggered.connect(self.right_pltI)
        right_dataMenu.addAction(right_pltActionX)
        right_dataMenu.addAction(right_pltActionY)
        right_dataMenu.addAction(right_pltActionI)
        self.left_source = (0, 'X')
        self.right_source = (0, 'Y')
        autorange_btn = QtWidgets.QPushButton('Autorange')
        autorange_btn.setMaximumWidth(buttonWidth)
        autorange_btn.clicked.connect(self.autorange)
        addroi_btn = QtWidgets.QPushButton('Add ROI')
        addroi_btn.setMaximumWidth(buttonWidth)
        addroi_btn.clicked.connect(self.addRoi)
        remove_roi_btn = QtWidgets.QPushButton('Remove ROI')
        remove_roi_btn.setMaximumWidth(buttonWidth)
        remove_roi_btn.clicked.connect(self.removeRoi)
        self.roi_list = QtWidgets.QComboBox()
        self.roi_list.addItem('ROI : full detector')
        self.roi_list.currentIndexChanged.connect(self.comboChanged)
        self.pixel_info_lbl = QtWidgets.QLabel("X = %3d \nY = %3d \nI = %d" % (0, 0, 0))
        self.fft_btn = QtWidgets.QPushButton('FFT')
        self.fft_btn.setStyleSheet("QPushButton { background-color: lime }")
        self.fft_btn.clicked.connect(self.start_fft)
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        openAction = QtWidgets.QAction('&Open', self)
        openAction.setStatusTip('Open image')
        openAction.triggered.connect(self.open)
        fileMenu.addAction(openAction)
        viewMenu = menuBar.addMenu('&View')
        liveAction =  QtWidgets.QAction('&Live', self)
        liveAction.triggered.connect(self.go_live)
        viewMenu.addAction(liveAction)
        offlineAction = QtWidgets.QAction('&Offline', self)
        offlineAction.triggered.connect(self.go_offline)
        viewMenu.addAction(offlineAction)
        plotlayout.addWidget(self.image)
        lineoutlayout.addWidget(self.cross_h_wid)
        lineoutlayout.addWidget(self.cross_v_wid)
        plotlayout.addLayout(lineoutlayout)
        buttonlayout.addWidget(self.pixel_info_lbl)
        buttonlayout.addWidget(autorange_btn)
        buttonlayout.addWidget(self.fft_btn)
        self.filter_btn = QtWidgets.QPushButton('Median filter\n dead pixels')
        self.filter_btn.setStyleSheet("QPushButton { background-color: yellow }")
        self.filter_btn.clicked.connect(self.toggle_filter)
        buttonlayout.addWidget(self.filter_btn)
        save_btn = QtWidgets.QPushButton('Save copy')
        save_btn.clicked.connect(self.save_copy)
        buttonlayout.addWidget(save_btn)
        buttonlayout.addWidget(self.roi_list)
        buttonlayout.addWidget(addroi_btn)
        buttonlayout.addWidget(remove_roi_btn)
        self.post_box = QtWidgets.QCheckBox('Post integrals')
        buttonlayout.addWidget(self.post_box)
        avelayout = QtWidgets.QHBoxLayout()
        self.avecheck = QtWidgets.QCheckBox('ave')
        nave = QtWidgets.QLineEdit(str(self.nframes))
        nave.textEdited.connect(self.update_nframes)
        avelayout.addWidget(nave)
        avelayout.addWidget(self.avecheck)
        buttonlayout.addLayout(avelayout)
        mainlayout.addLayout(plotlayout)
        mainlayout.addLayout(buttonlayout)
        wid.setLayout(mainlayout)
        self.thread = QThread(self)
        self.thread.start()
        self.fetcher = Fetcher()
        self.fetcher.new_data.connect(self.update_view)
        self.fetcher.moveToThread(self.thread)
        self.fetcher.start.emit()
        self.resize(WinH, WinV)
        self.image.view.scene().sigMouseClicked.connect(self.mouseClicked)
        #qtRectangle = self.frameGeometry()
        #centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
        #qtRectangle.moveCenter(centerPoint)
        #self.move(qtRectangle.topRight())
        self.show()
    def update_nframes(self, text):
        try:
            n = int(text)
            self.nframes = n
        except:
            pass
    def toggle_filter(self):
        if self.dead:
            self.filter_btn.setStyleSheet('')
            self.dead = False
        else:
            self.filter_btn.setStyleSheet("QPushButton { background-color: yellow }")
            self.dead = True
    def save_copy(self):
        im = np.copy(self.openArray)
        raw_dst, regex = QtWidgets.QFileDialog.getSaveFileName(self, caption='Save .tif')
        if raw_dst == '':
            return
        if len(raw_dst)>4:
            if raw_dst[-4:]=='.tif':
                dst = raw_dst
            else:
                dst = '{}.tif'.format(raw_dst)
        else:
            dst = '{}.tif'.format(raw_dst)
        tifffile.imwrite(dst, im)
    def right_pltX(self):
        pair = (self.roi_list.currentIndex(), 'X')
        self.cross_v_wid.setTitle('ROI: {} {} {}'.format(*plotlabel(pair)))
        self.right_source = pair
    def right_pltY(self):
        pair = (self.roi_list.currentIndex(), 'Y')
        self.cross_v_wid.setTitle('ROI: {} {} {}'.format(*plotlabel(pair)))
        self.right_source = pair
    def right_pltI(self):
        pair = (self.roi_list.currentIndex(), 'I')
        self.cross_v_wid.setTitle('ROI: {} {} {}'.format(*plotlabel(pair)))
        self.right_source = pair
    def left_pltX(self):
        pair = (self.roi_list.currentIndex(), 'X')
        self.cross_h_wid.setTitle('ROI: {} {} {}'.format(*plotlabel(pair)))
        self.left_source = pair
    def left_pltY(self):
        pair = (self.roi_list.currentIndex(), 'Y')
        self.cross_h_wid.setTitle('ROI: {} {} {}'.format(*plotlabel(pair)))
        self.left_source = pair
    def left_pltI(self):
        pair = (self.roi_list.currentIndex(), 'I')
        self.cross_h_wid.setTitle('ROI: {} {} {}'.format(*plotlabel(pair)))
        self.left_source = pair
    def addRoi(self):
        n = len(self.rois)
        if n == 5:
            return
        key = 'ROI_{}'.format(n)
        roi = customROI(n, [0, 0], [200, 50], pen=pg.mkPen(
        roicol(n), width=2, style=Qt.DashLine), hoverPen=pg.mkPen(roicol(n), width=4))
        roi.addRotateHandle([0, 0], [0.5, 0.5])
        roi.addScaleHandle([1, 1], [0, 0])
        roi.setZValue(1e9)
        roi.setAcceptedMouseButtons(QtCore.Qt.LeftButton)
        roi.sigClicked.connect(self.roiClicked)
        self.rois.append([roi, np.zeros(BLENGTH)])
        self.image.addItem(roi)
        self.roi_list.addItem(key)
        canvas = QtGui.QPixmap(64,64)
        canvas.fill(iconcol(n))
        icon = QtGui.QIcon(canvas)
        self.roi_list.setItemIcon(n, icon)
    def roiClicked(self, roi):
        n = roi.n
        self.roi_list.setCurrentIndex(n)
        self.comboChanged(n)
    def comboChanged(self, n):
        if n>0:
            self.rois[n][0].setPen(pg.mkPen(roicol(n), width=2), hoverPen=pg.mkPen(roicol(n), width=4,style=Qt.DashLine ))
        for k in list(range(1,n)) + list(range(n+1, len(self.rois))):
                self.rois[k][0].setPen(pg.mkPen(roicol(k), width=2, style=Qt.DashLine), hoverPen=pg.mkPen(roicol(k), width=4, style=Qt.DashLine))
    def removeRoi(self):
        n = self.roi_list.currentIndex()
        if n > 0:
            self.image.removeItem(self.rois[n][0])
            del self.rois[n]
            self.roi_list.clear()
            self.roi_list.addItem('ROI : full detector')
            self.roi_list.addItems(['ROI_{}'.format(k) for k in range(0, len(self.rois))])
            if n-1 > 0:
                self.comboChanged(n-1)
                self.roi_list.setCurrentIndex(n-1)
    def update_view(self, array):
        if self.is_live:
            l0 = np.min(array)
            l1 = np.max(array)
            if self.avecheck.isChecked():
                self.imbuff = np.roll(self.imbuff, -1, axis=0)
                self.imbuff[-1,:,:] = array
                self.openArray = np.sum(self.imbuff[-self.nframes:,:,:], axis=0)
            else:
                self.openArray = array
            self.image.setImage(self.openArray, autoLevels=False, 
                autoRange=False, autoHistogramRange=False)
            self.update_subplts()
            self.update_fft()
            self.rois[0][1] = np.roll(self.rois[0][1],-1)
            self.rois[0][1][-1] = np.sum(self.image.image, axis=(0,1))
            for kk in range(1, len(self.rois)):
                self.rois[kk][1] = np.roll(self.rois[kk][1],-1)
                self.rois[kk][1][-1] = np.sum(self.rois[kk][0].getArrayRegion(self.openArray, 
                    self.image.getImageItem()), axis=(0,1))
            if self.post_box.isChecked():
                for kk in range(0, len(self.rois)):
                    conn = HTTPConnection(*STAGEADDRESS)
                    conn.request('POST','/buff{}/val'.format(kk),str(self.rois[kk][1][-1]))
                    response = conn.getresponse()
    def update_subplts(self):
        row_len, col_len = self.openArray.shape
        col = self.col
        row = self.row
        img_pixel_value = self.image.image[col, row]
        lbl_text ="X = {} \nY = {} \nI = {}".format(col, row, img_pixel_value)
        self.pixel_info_lbl.setText(lbl_text)
        for (ROI_n, var), cross_plt in zip([self.left_source, self.right_source], 
                [self.cross_h_plt, self.cross_v_plt]):
            if ROI_n == 0:
                if var == 'X':
                    cross_plt.setData(np.arange(col_len), self.openArray[:, row])
                if var == 'Y':
                    cross_plt.setData(np.arange(row_len), self.openArray[col, :])
                if var == 'I':
                    cross_plt.setData(np.arange(len(self.rois[0][1])), self.rois[0][1])
            elif ROI_n < len(self.rois):
                if var == 'X':
                    data_buff = np.sum(self.rois[ROI_n][0].getArrayRegion(self.openArray, 
                    self.image.getImageItem()), axis=1) 
                    cross_plt.setData(np.arange(len(data_buff)),data_buff)
                if var == 'Y':
                    data_buff = np.sum(self.rois[ROI_n][0].getArrayRegion(self.openArray, 
                    self.image.getImageItem()), axis=0) 
                    cross_plt.setData(np.arange(len(data_buff)),data_buff)
                if var == 'I':
                    cross_plt.setData(np.arange(len(self.rois[ROI_n][1])), self.rois[ROI_n][1])
    def update_fft(self):
        if self.img_fft.fft_on:
            fft_arr = np.roll(np.roll(np.log10(np.power(np.abs(fft2(self.openArray)),2)), 256, axis=0), 256, axis=1)
            self.img_fft.setImage(fft_arr, autoRange=False, autoLevels=False, autoHistogramRange=False)
    def closeEvent(self, event):
        self.fetcher.stop.emit()
        self.thread.quit()
        self.thread.wait()
    def open(self):
        filename, criteria = QtWidgets.QFileDialog.getOpenFileName()
        if len(filename) >= 3:
            if filename[-3:] == '.h5':
                try:
                    file = h5py.File(filename, 'r')
                    self.openArray = np.array(file['data'])
                except KeyError:
                    try:
                        key = list(file['entry']['data'].keys())[0]
                        tempArray = np.array(file['entry']['data'][key])
                        ndim = tempArray.ndim
                        if ndim == 3:
                            nf = tempArray.shape[0]
                            if nf == 1:
                                self.openArray = tempArray[0, :, :]
                            else:
                                text, ok = QtWidgets.QInputDialog.getText(self, 'Multiple frames', 
                                    '\'{}\' contains {} frames.\n Enter frame \'n\' or sum range \'n:m\''.format(os.path.basename(filename), nf))
                                if ':' in text:
                                    try:
                                        itx, jtx = text.split(':')
                                        if itx == '':
                                            ix = 0
                                        else:
                                            ix = int(itx)
                                        if jtx == '':
                                            jx = -1
                                        else:
                                            jx = int(jtx)
                                        self.openArray = np.sum(tempArray[ix:jx,:,:], axis=0)
                                    except Exception as e:
                                        print(e)
                                else:
                                    try:
                                        ixf = int(text)
                                        print(ixf)
                                        self.openArray = tempArray[ixf, :, :]
                                    except:
                                        pass
                    except Exception as e:
                        print(e)
                        pass
            elif len(filename) >= 4:
                print(filename)
                if filename[-4:] == '.tif':
                   im = tifffile.imread(filename)
                   self.openArray = im
        self.go_offline()
        self.update_fft()
    def go_offline(self):
        self.is_live = False
        self.image.setImage(self.openArray, autoLevels=False, 
                autoRange=False, autoHistogramRange=False)
    def go_live(self):
        self.is_live = True
    def mouseClicked(self, ev):
        p = QtCore.QPointF(ev.pos()[0], ev.pos()[1])
        nRows, nCols = self.image.image.shape
        scenePos = self.image.getImageItem().mapFromScene(p)
        self.row, self.col = int(scenePos.y()), int(scenePos.x())
        if (0 <= self.row < nRows) and (0 <= self.col < nCols) and ev.button() == 1:
            self.vLine.setPos(self.col+0.5)
            self.hLine.setPos(self.row+0.5)
        self.update_subplts()
    def autorange(self):
        self.image.autoLevels()
        if self.img_fft.fft_on:
            self.img_fft.autoRange()
            self.img_fft.autoLevels()
            self.img_fft.autoHistogramRange()
    def start_fft(self):
        self.img_fft.switch_on()
        self.update_fft()
        self.img_fft.show()
    def filter_dead_pixels(self, dead_data):
        if self.dead:
            return
        dead_coords = [[222,363],[261,35], [256, 250], [257,250], [256,252],[257,252]] 
        for (cy, cx) in dead_coords:
            neighbours = np.array([dead_data[cy+ii,cx+jj] for (ii, jj) in [[-1,-1],
                                                                           [-1,0],
                                                                           [-1,1],
                                                                           [0,-1],
                                                                           [0,1],
                                                                           [1,-1],
                                                                           [1,0],
                                                                           [1,1]]])
            dead_data[cy,cx]=np.median(neighbours)
    

class customROI(pg.ROI):
    def __init__(self,n, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n = n

class Fetcher(QObject):
    """All communcation with DCU should go via 
    the Fetcher to avoid clashing commands"""
    new_data = pyqtSignal(np.ndarray)
    start = pyqtSignal()
    stop = pyqtSignal()
    def __init__(self, parent=None):
        super(Fetcher, self).__init__(parent)
        DCU_IP = '169.254.254.1'
        self.dec = DEC.DEigerClient(DCU_IP)
        self.dec.setMonitorConfig('discard_new', False)
        self.dec.setMonitorConfig('buffer_size', 1)
        self.dec.setMonitorConfig('mode', 'enabled')
        self.start.connect(self.start_timer)
        self.stop.connect(self.stop_timer)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch)
        self.running = False
        self.period = 100
        self.buffer_index = []
        self.current_seq = []

    @pyqtSlot()
    def start_timer(self):
        self.running = True
        self.timer.start(self.period)

    @pyqtSlot()
    def stop_timer(self):
        self.running = False
        self.timer.stop()

    def fetch(self):
        if len(self.buffer_index) == 0:
            try:
                self.buffer_index = self.dec.monitorImages()
            except RuntimeError:
                print('No response from DCU')
        else:
            self.current_seq = self.buffer_index.pop(0)
            try:
                im_data = self.dec.monitorImages('next')
                im_data = np.array(Image.open(io.BytesIO(im_data)))
                self.new_data.emit(im_data)
            except RuntimeError:
                self.buffer_index = []
                self.current_seq = []

class popIm(pg.ImageView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fft_on = False
    def closeEvent(self, *args, **kwargs):
        super(pg.ImageView, self).closeEvent(*args, **kwargs)
        self.fft_on = False
    def switch_on(self):
        self.fft_on = True

def plotlabel(pair):
    if pair[0] == 0:
        if pair[1] == 'I':
            return ['full detector', 'integral', 'vs time']
        else:
            return ['full detector', pair[1], 'lineout']
    else:
        if pair[1] == 'I':
            return [pair[0], 'integral', 'vs time']
        else:
            return [pair[0], pair[1], 'projection']
def roicol(n):
    return ['m', 'c', 'y', 'r'][n-1]

def iconcol(n):
    return [Qt.magenta, Qt.cyan, Qt.yellow, Qt.red][n-1]

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())
