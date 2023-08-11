import json
import numpy
import requests
import time
from base64 import b64encode, b64decode
import tifffile

DETECTOR_PAUSE = 10

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
		
if __name__ == '__main__':
    # create detector instance and initialize the detector
    client = DetectorClient('169.254.254.1', '80')
    status = client.get_status()
    print(status)
    if status == 'na':
        client.send_command('initialize')
    client.set_config('pixel_mask_applied', False)
    flatfield = tifffile.imread('/home/quadro/Data/flatfields/flatfield.tif')
    flatfield = numpy.median(flatfield) / flatfield.astype('float32')
    client.set_mask(flatfield, 'flatfield')
