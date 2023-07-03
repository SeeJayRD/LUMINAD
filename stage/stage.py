import serial
import time
import math

PAUSE = 1
BIGPAUSE = 15
dtdN = 8.33910238e-4 #picoseconds per DAC count
MAXC = 800000
POS_LIM = 16
THRESH = 100
t0_dac = 450000
SPEEDC = 2.99792458e-1

class Stage:
    '''Hi Bea, figure it out yourself!'''
    def __init__(self):
        self.ser = serial.Serial('/dev/ttyUSB0', 9600)
        self.pos_dac = 0
        self.stage_init()
    def address_controller(self):
        self.ser.write(b'\x011\r')
        time.sleep(PAUSE)
        self.ser.readline()
    def enable_amp(self):
        self.ser.write(b'bf\r')
    def find_negative_edge(self):
        self.tp()
        old_pos = self.pos_dac
        self.ser.write(b'fe1\r')
        print('seeking')
        time.sleep(PAUSE)
        self.tp()
        while(math.fabs(old_pos - self.pos_dac)>THRESH):
            old_pos = self.pos_dac
            self.tp()
            print('seeking')
            time.sleep(PAUSE)
    def define_home(self):
        self.ser.write(b'dh\r')
    def init_params(self):
        self.ser.write(b'dp140\r')
        self.ser.write(b'di20\r')
        self.ser.write(b'dd600\r')
        self.ser.write(b'dl2000\r')
        self.ser.write(b'sv70000\r')
        self.ser.write(b'sa800000\r')
    def stage_init(self):
        print('connecting to controller')
        self.address_controller()
        print('controller connected')
        print('powering on amplifier')
        self.enable_amp()
        print('amplified powered on')
        print('seeking edge')
        self.find_negative_edge()
        print('edge found')
        print('initializing')
        self.init_params()
        self.find_negative_edge()
        self.define_home()
        print('ready')
    def move(self, t, units='ps'):
        if units == 'ps':
            counts = int(t/dtdN) + t0_dac
        elif units == 'mm':
            counts = int((2*t/SPEEDC)/dtdN) + t0_dac
        else:
            raise Exception('Units must be ps or mm')
        if (math.fabs(counts) > 8.8e5) or counts < 0:
            return
        cmdstr = 'ma{}\r'.format(counts)
        self.ser.write(bytes(cmdstr, 'ascii'))
    def tp(self):
        cmdstr = 'tp\r'
        self.ser.write(bytes(cmdstr, 'ascii'))
        time.sleep(PAUSE)
        response = self.ser.readline()
        self.pos_dac = int(response.decode('ascii').strip().split(':')[-1])
    def pos(self, units='ps'):
        '''Units must be ps or mm'''
        self.tp()
        if units=='ps':
            return dtdN*(self.pos_dac-t0_dac)
        elif units=='mm':
            return dtdN*(self.pos_dac-t0_dac)*0.5*SPEEDC
        else:
            raise Exception('Units must be ps or mm') 
    def shutdown(self):
        self.ser.write(b'rt\r')
