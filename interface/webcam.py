import cv2
import numpy as np
import sys

wnam = 'webcam'

cv2.namedWindow(wnam)
cap = cv2.VideoCapture(0)
H = 640
V = 480
scale = 1.9
X = 0
Y = 0

def callback(event, x, y, flags, param):
    global X, Y
    if event == cv2.EVENT_LBUTTONDOWN:
        X=int(x/scale)
        Y=int(y/scale)

cv2.setMouseCallback(wnam, callback)

def myfun():
    while cv2.getWindowProperty(wnam, cv2.WND_PROP_VISIBLE) >= 1:
         ret, frame = cap.read()
         frame[:,X,:] = 255*np.ones((480,3), dtype=np.uint8)
         frame[Y,:,:] = 255*np.ones((640,3), dtype=np.uint8)
         frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
         cv2.imshow(wnam, frame)
         c = cv2.waitKey(1)

myfun()
cv2.destroyAllWindows()
sys.exit()
