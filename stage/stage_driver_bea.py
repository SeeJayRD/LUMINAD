import serial
import time
import math
import sys
import os

#The password to the PC with the stage firmware is: common
#---bea was here ----

MINIPAUSE = 1e-3
PAUSE = 1
BIGPAUSE = 15
dtdN = -8.33910238e-4 #picoseconds per DAC count
MAXC = 800000
POS_LIM = 16
THRESH = 100
t0_dac = 450000
SPEEDC = 2.99792458e-1
LOGFILE = '/home/quadro/Logs/stage.log'

class Stage:
    def __init__(self, init=True, usb_dev_path = '/dev/ttyUSB0'):
        self.ser = serial.Serial(usb_dev_path, 9600)
        with open(LOGFILE, 'rb') as f:
            try:
                f.seek(-2, os.SEEK_END)
                while f.read(1) != b'\n':
                    f.seek(-2, os.SEEK_CUR)
            except OSError:
                f.seek(0)
            self.init_pos_dac = int(f.readline().decode().strip().split()[-1])
        self.pos_dac = self.init_pos_dac
        self.logfile = open(LOGFILE, 'a')
        self.err = None
        self.status_record = {}
        if init:
            self.stage_init()
        else:
            self.address_controller()
            self.status()
    def __del__(self):
        self.shutdown()
        self.logfile.close()
    def address_controller(self):
        self.ser.write(b'\x010\r')
        time.sleep(PAUSE)
        Nchar = self.ser.in_waiting
        self.ser.read(Nchar)
    def enable_amp(self):
        self.ser.write(b'bf\r')
    def find_negative_edge(self):
        self.tp()
        old_pos = self.pos_dac
        self.ser.write(b'fe1\r')
        print('\033[1;38;5;226mSeeking', end=' ')
        time.sleep(PAUSE)
        self.tp()
        while(math.fabs(old_pos - self.pos_dac)>THRESH):
            print('#', end='')
            old_pos = self.pos_dac
            self.tp()
            time.sleep(PAUSE)
            sys.stdout.flush()
        print("\033[m")
    def define_home(self):
        self.ser.write(b'dh\r')
    def init_params(self):
        self.ser.write(b'dp140\r')
        self.ser.write(b'di20\r')
        self.ser.write(b'dd600\r')
        self.ser.write(b'dl2000\r')
        self.ser.write(b'sv120000\r')
        self.ser.write(b'sa800000\r')
    def stage_init(self):
        self.address_controller()
        print('\033[1;38;5;42m[\u2713]\033[m Controller connected')
        time.sleep(PAUSE)
        self.define_home()
        time.sleep(PAUSE)
        self.enable_amp()
        print('\033[1;38;5;42m[\u2713]\033[m Amplifier powered on')
        self.find_negative_edge()
        self.init_params()
        print('\033[1;38;5;42m[\u2713]\033[m Motion parameters (speed etc.) initialized')
        time.sleep(PAUSE)
        self.find_negative_edge()
        print('\033[1;38;5;42m[\u2713]\033[m Edge found')
        self.status()
        print('\033[1;38;5;226mREADY\033[m')
    def reset_logfile(self):
        self.find_negative_edge()
        time.sleep(PAUSE)
        self.define_home()
        self.logfile.close()
        self.init_pos_dac = 0
        self.logfile = open(LOGFILE, 'w')
        self.tp()
    def move(self, t, units='ps'):
        if units == 'ps':
            counts = int(t/dtdN) + t0_dac
        elif units == 'mm':
            counts = int((2*t/SPEEDC)/dtdN) + t0_dac
        else:
            raise Exception('Units must be ps or mm')
        cmdstr = 'ma{}\r'.format(counts-self.init_pos_dac)
        self.ser.write(bytes(cmdstr, 'ascii'))
    def tp(self):
        cmdstr = 'tp\r'
        self.ser.write(bytes(cmdstr, 'ascii'))
        time.sleep(MINIPAUSE)
        response = self.ser.readline()
        self.pos_dac = int(response.decode('ascii').strip().split(':')[-1]) + self.init_pos_dac
        print("{} {}".format(time.asctime(time.localtime()),
            self.pos_dac), file = self.logfile, flush=True)
    def pos(self, units='ps'):
        '''Units must be ps or mm'''
        self.tp()
        if units=='ps':
            return dtdN*(self.pos_dac-t0_dac)
        elif units=='mm':
            return dtdN*(self.pos_dac-t0_dac)*0.5*SPEEDC
        else:
            raise Exception('Units must be ps or mm')
    def status(self):
        self.ser.write(b'ts\r')
        time.sleep(PAUSE)
        Nchar = self.ser.in_waiting
        raw_msg = self.ser.read(Nchar).decode().strip('S:\r\n\x03')
        print("\033[1mStage status:\033[m")
        codes = [int(s, 16) for s in raw_msg.split()]
        formats = [["{}",
                    "\033[1;38;5;196m{}\033[m",
                    "{}",
                    "{}",
                    "\033[1;38;5;196m{}\033[m",
                    "\033[1;38;5;196m{}\033[m",
                    "{}",
                    "\033[1;38;5;196m{}\033[m"],
                   ["{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}"],
                   ["{}",
                    "{}",
                    "{}",
                    "\033[1;38;5;196m\033[m",
                    "{}",
                    "{}",
                    "\033[1;38;5;196m{}\033[m",
                    "{}"],
                   ["{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}"],
                   ["{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}",
                    "{}"],
                   ["\033[1;38;5;42m{}\033[m",
                    "\033[1;38;5;196m{}\033[m",
                    "\033[1;38;5;196m{}\033[m",
                    "\033[1;38;5;196m{}\033[m",
                    "\033[1;38;5;196m{}\033[m",
                    "\033[1;38;5;196m{}\033[m",
                    "\033[1;38;5;196m{}\033[m",
                    "\033[1;38;5;196m{}\033[m",
                    "\033[1;38;5;196m{}\033[m"]]
        legends = [["Microcontroller busy",
                    "Microcontroller command error",
                    "Trajectory complete",
                    "Index pulse received",
                    "Position limit exceeded",
                    "Excessive position error",
                    "Breakpoint reached",
                    "Motor loop OFF"],
                   ["Echo ON",
                    "Wait in progress",
                    "Internal operation flags: command error",
                    "Leading zero suppression active",
                    "Macro command called",
                    "Leading zerio suppression disabled",
                    "Number mode in effect",
                    "Board addressed"],
                   [" ",
                    " ",
                    "Move direction polarity",
                    "Move error (MF condition occured in WS)",
                    " ",
                    " ",
                    "Move error (Excess following error in WS)",
                    "Internal microcontroller communication in progress"],
                   ["Limit Switch ON",
                    "Limit switch active state HIGH",
                    "Find edge oeration in progress",
                    "Brake ON",
                    " ",
                    " ",
                    " ",
                    " "],
                   [" ",
                    "Reference signal input",
                    "Positive limit signal input",
                    "Negative limit signal input",
                    " ",
                    " ",
                    " ",
                    " "],
                   ["No other errors",
                    "Command not found",
                    "First command character was not a letter",
                    "Character followng command was not a digit",
                    "Value too large",
                    "Value too small",
                    "Continuation character was not a comma",
                    "Command buffer overflow",
                    "Macro storage overflow"]]
        for code, fmat, legend in zip(codes, formats, legends):
            for k, (ft, msg) in enumerate(zip(fmat, legend)):
                mask = 2**k
                if code&mask:
                    print("\u2022  {}".format(msg.format(ft)))
                    self.status_record[msg] = True
                else:
                    self.status_record[msg] = False
    def report_status(self):
        self.status()
        return self.status_record
    def shutdown(self):
        self.pos()
        return 0
