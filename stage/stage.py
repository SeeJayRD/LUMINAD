from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import PurePosixPath
from urllib.parse import urlsplit
import json
import serial
import time
import math

MINIPAUSE = 1e-3
PAUSE = 1
BIGPAUSE = 15
dtdN = -8.33910238e-4 #picoseconds per DAC count
MAXC = 800000
POS_LIM = 16
THRESH = 100
t0_dac = 450000
SPEEDC = 2.99792458e-1
ADDRESS = ('localhost', 8000)
TYPES = {'float' : float}

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
        self.ser.write(b'sv120000\r')
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
        time.sleep(MINIPAUSE)
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

class StageServer(BaseHTTPRequestHandler):
    PVs = {'/':{'rdbk': {'val':0, 'units': 'ps', 'type':'float'}, 
        'set': {'val':0, 'units': 'ps', 'type':'float'},
        'buff0': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'},
        'buff1': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'},
        'buff2': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'},
        'buff3': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'},
        'buff4': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'}}}
    stage = Stage()
    def __init__(self, *args):
        super().__init__(*args)
    def do_GET(self):
        path = PurePosixPath(urlsplit(self.path).path).parts
        print(path)
        if len(path) == 1:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(json.dumps(StageServer.PVs), "utf-8"))
        elif len(path) > 1:
            if path[1] == 'rdbk':
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                StageServer.PVs['/']['rdbk']['val'] = StageServer.stage.pos(units=StageServer.PVs['/']['rdbk']['units'])
                if len(path) > 2:
                   if path[2] in ['val', 'units', 'type']:
                      self.wfile.write(bytes(json.dumps(StageServer.PVs['/']['rdbk'][path[2]]), "utf-8"))
                else:
                    self.wfile.write(bytes(json.dumps(StageServer.PVs['/']['rdbk']), "utf-8"))
            elif path[1] == 'set':
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                if len(path) > 2:
                    if path[2] in ['val', 'units', 'type']:
                      self.wfile.write(bytes(json.dumps(StageServer.PVs['/']['set'][path[2]]), "utf-8"))
                else:
                    self.wfile.write(bytes(json.dumps(StageServer.PVs['/']['set']), "utf-8"))
            elif path[1] in ['buff0', 'buff1', 'buff2', 'buff3', 'buff4']:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                if len(path) > 2:
                    if path[2] in ['val', 'stage', 'units', 'type']:
                        self.wfile.write(bytes(json.dumps(StageServer.PVs['/'][path[1]][path[2]]), "utf-8"))
                    else:
                        self.wfile.write(bytes(json.dumps(StageServer.PVs['/'][path[1]]), "utf-8"))
                else:
                    self.wfile.write(bytes(json.dumps(StageServer.PVs['/'][path[1]]), "utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    def do_POST(self):
        path = PurePosixPath(urlsplit(self.path).path).parts
        if len(path) != 3:
            self.send_response(404)
            self.end_headers()
        elif path[1] == 'set':
            if path[2] == 'val':
                try:
                    val = self.rfile.read(int(self.headers.get('Content-Length'))).decode('utf-8')
                    StageServer.PVs['/']['set']['val']=TYPES[StageServer.PVs['/']['set']['type']](val)
                    self.send_response(201)
                    self.end_headers()
                    StageServer.stage.move(StageServer.PVs['/']['set']['val'], StageServer.PVs['/']['set']['units'])
                except (KeyError, TypeError, ValueError):
                    self.send_response(400)
                    self.end_headers()
            else:
                self.send_response(403)
                self.end_headers()
        elif path[1] in ['buff0', 'buff1', 'buff2', 'buff3', 'buff4']:
            if path[2] == 'val':
                try:
                    val = self.rfile.read(int(self.headers.get('Content-Length'))).decode('utf-8')
                    StageServer.PVs['/']['rdbk']['val'] = StageServer.stage.pos(units=StageServer.PVs['/']['rdbk']['units'])
                    StageServer.PVs['/'][path[1]]['stage']=StageServer.PVs['/']['rdbk']['val']
                    StageServer.PVs['/'][path[1]]['val']=TYPES[StageServer.PVs['/'][path[1]]['type']](val)
                    self.send_response(201)
                    self.end_headers()
                except (KeyError, TypeError, ValueError):
                    self.send_response(400)
                    self.end_headers()
            else:
                self.send_response(403)
                self.end_headers()
        elif path[1] != 'rdbk':
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(403)
            self.end_headers()
    def find(self):
        path = PurePosixPath(urlsplit(self.path).path).parts
        try:
            pv = reduce(operator.getitem, path, StageServer.PVs)
        except (KeyError, TypeError):
            pv = None
        return pv

if __name__ == '__main__':
    webServer = HTTPServer(ADDRESS, StageServer)
    print("Server started http://%s:%s" % ADDRESS)

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    StageServer.stage.shutdown()
    print("Server stopped.")
