#!/usr/bin/env python
# -*- coding: utf-8 -*-
import cv2
import numpy as np
import math

import sys

def roundbox(img,p1,p2,r,color):
    cv2.circle(img,(p1[0]+r,p1[1]+r),r,color,-1)
    cv2.circle(img,(p2[0]-r,p1[1]+r),r,color,-1)
    cv2.circle(img,(p1[0]+r,p2[1]-r),r,color,-1)
    cv2.circle(img,(p2[0]-r,p2[1]-r),r,color,-1)
    cv2.rectangle(img,(p1[0],p1[1]+r),(p2[0],p2[1]-r),color,-1)
    cv2.rectangle(img,(p1[0]+r,p1[1]),(p2[0]-r,p2[1]),color,-1)


#if you want to add Creative Commons sign,
cc = ""
while len(sys.argv) > 2:
    option = sys.argv.pop(1)
    if option == "-c":
        cc = sys.argv.pop(1)

if len(sys.argv) != 2:
    print "usage: {0} image".format(sys.argv[0])
    sys.exit(1)

img = cv2.imread(sys.argv[1])

h, w = img.shape[0:2]
filmw = h *35 / 24
pad = h*(35-24-1)/2/24
framew = h* 38 / 24
perf  = framew / 8
perfh = h * 3 / 24
perfw = h * 2 / 24
perfr = h / 2 / 24
thick = pad/20
canh = filmw
oneframe = np.zeros((canh, framew,3), np.uint8)
#perforations
for i in range(0,framew,perf):
    roundbox(oneframe,(i-perfw/2,pad-perfh),(i+perfw/2,pad),perfr,(255,255,255))
    roundbox(oneframe,(i-perfw/2,filmw-pad),(i+perfw/2,filmw-pad+perfh),perfr,(255,255,255))


canvas = np.zeros((canh, w,3), np.uint8)
#frame label
count = 1
font = cv2.FONT_HERSHEY_PLAIN
for i in range(0,w,framew):
    frame = oneframe.copy()
    text = str(count)
    fontsize = pad/32
    box, _ = cv2.getTextSize(text,font,fontsize,thick)
    textw,texth = box
    cv2.putText(frame,text,(int(perf*4.5)-textw/2,int(texth*1.2)),font,fontsize,(0,150,200),thick)
    wend = i + framew
    if wend > w:
        canvas[:,i:i+framew-(wend-w),:] = frame[:,0:framew-(wend-w),:]
    else:
        canvas[:,i:i+framew] = frame[:,:]
    count += 1
    
canvas[(filmw-h)/2:(filmw-h)/2+h,0:w] = img
if cc:
    fontsize = pad/48
    thick    = pad/30
    box, _ = cv2.getTextSize(cc,font,fontsize,thick)
    textw,texth = box
    cv2.putText(canvas,cc,(int(perf*0.5),int(canh)),font,fontsize,(0,150,200),thick)
    
cv2.imwrite("{0}.film.png".format(sys.argv[1]), canvas)

