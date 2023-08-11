import sys
from multiprocessing.connection import Client
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer, Qt
from DEiger import DEigerClient as DEC

TIMEOUT = 2
DCU_IP = '169.254.254.1'
dec = DEC.DEigerClient(DCU_IP)
dec.setConnectionTimeout(TIMEOUT)

def mybool(s):
    return s=='True' or s=='1' or s=='T'

LIST = ["auto_summation","beam_center_x","beam_center_y",
        "bit_depth_image","bit_depth_readout","chi_increment",
        "chi_start","compression","count_time","counting_mode",
        "countrate_correction_applied","countrate_correction_count_cutoff",
        "data_collection_date",
        "description","detector_distance","detector_number",
        "detector_orientation","detector_readout_time",
        "detector_translation","eiger_fw_version",
        "extg_mode","fast_arm",
        "flatfield_correction_applied",
        "frame_count_time","frame_time",
        "incident_energy",
        "incident_particle_type",
        "instrument_name","kappa_increment",
        "kappa_start","mask_to_zero","nexpi",
        "nimages","ntrigger","number_of_excluded_pixels",
        "omega_increment","omega_start","phi_increment",
        "phi_start","pixel_mask_applied",
        "roi_bit_depth","roi_mode","roi_y_size","sample_name",
        "sensor_material","sensor_thickness","software_version","source_name",
        "test_image_mode","test_image_value","threshold/difference/lower_threshold",
        "threshold/difference/mode","threshold/difference/upper_threshold",
        "total_flux","trigger_mode",
        "trigger_start_delay","two_theta_increment",
        "two_theta_start","virtual_pixel_correction_applied",
        "x_pixel_size","x_pixels_in_detector",
        "y_pixel_size","y_pixels_in_detector"]
CHANGE = ["count_time", "frame_time", "incident_energy",
        "nimages", "ntrigger", "pixel_mask_applied"]
TYPES = dict(zip(CHANGE, [float, float, float, int, int, mybool]))

class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('/home/quadro/Code/LUMINAD/stage/interface/assets/settings.jpg'))
        self.active = LIST[0]
        wid = QtWidgets.QWidget()
        self.setCentralWidget(wid)
        mainlayout = QtWidgets.QHBoxLayout()
        cb = QtWidgets.QComboBox()
        for k, item in enumerate(LIST):
            cb.addItem(item)
            if item in CHANGE:
                font = QtGui.QFont()
                font.setBold(True)
                myitem = cb.model().item(k,0)
                myitem.setFont(font)
        cb.currentIndexChanged.connect(self.cb_change)
        mainlayout.addWidget(cb)
        setptlb = QtWidgets.QLabel('set pt:')
        mainlayout.addWidget(setptlb)
        self.set_pt = QtWidgets.QLineEdit(' ')
        self.set_pt.setReadOnly(self.active not in CHANGE)
        self.set_pt.editingFinished.connect(self.valuechange)
        mainlayout.addWidget(self.set_pt)
        self.rdbklb = QtWidgets.QLabel()
        self.rdbk()
        mainlayout.addWidget(self.rdbklb)
        wid.setLayout(mainlayout)
        self.show()
    def rdbk(self):
        rdbk = dec.detectorConfig(param = self.active)
        self.rdbklb.setText('rdbk: {}'.format(rdbk['value']))
    def cb_change(self, index):
        self.active = LIST[index]
        self.set_pt.setReadOnly(self.active not in CHANGE)
        self.set_pt.setText(' ')
        self.rdbk() 
    def valuechange(self):
        try:
            if self.active in CHANGE:
                new = TYPES[self.active](self.set_pt.text())
                print(new)
                dec.setDetectorConfig(self.active, new)
        except ValueError:
            pass
        self.rdbk()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ex = App()
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        printtraceback.print_exc()

