from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import PurePosixPath
from urllib.parse import urlsplit
import json
import serial
import time
import math
from stage_driver_bea import Stage

ADDRESS = ('localhost', 8000)
TYPES = {'float' : float}

class StageServer(BaseHTTPRequestHandler):
    stage = Stage()
    PVs = {'/':{'rdbk': {'val':0, 'units': 'ps', 'type':'float'}, 
        'set': {'val':0, 'units': 'ps', 'type':'float'},
        'buff0': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'},
        'buff1': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'},
        'buff2': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'},
        'buff3': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'},
        'buff4': {'val':0, 'stage':0, 'units': 'ps', 'type':'float'}}}
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
            elif path[1] == 'status':
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(bytes(json.dumps(StageServer.stage.report_status()), "utf-8"))
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
                    StageServer.stage.move(StageServer.PVs['/']['set']['val'],
                            StageServer.PVs['/']['set']['units'])
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
