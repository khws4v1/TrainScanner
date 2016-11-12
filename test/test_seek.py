#!/usr/bin/env python

from __future__ import print_function
import cv2

cap = cv2.VideoCapture("/Users/matto/Desktop/Martinacek96CLC - Czech Level Crossing (2014).mp4")
cap.set(cv2.CAP_PROP_POS_FRAMES, 3000)
ret, frame = cap.read()
#cv2.imwrite("set{0}.png".format(3000), frame)

cap = cv2.VideoCapture("/Users/matto/Desktop/Martinacek96CLC - Czech Level Crossing (2014).mp4")
for i in range(3103):
    print(i,end="\r")
    ret = cap.grab()
ret, frame = cap.read()
cv2.imwrite("grab{0}.png".format(i), frame)


