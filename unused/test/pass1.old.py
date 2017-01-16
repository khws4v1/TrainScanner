#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import cv2
import numpy as np
import math
import trainscanner
import sys

    

def diffImage(frame1,frame2,dx,dy,focus=None,slitpos=None):
    affine = np.matrix(((1.0,0.0,dx),(0.0,1.0,dy)))
    h,w = frame1.shape[0:2]
    frame1 = cv2.warpAffine(frame1, affine, (w,h))
    diff = 255 - cv2.absdiff(frame1,frame2)
    if focus is not None:
        trainscanner.draw_focus_area(diff, focus, delta=dx)
    if slitpos is not None:
        trainscanner.draw_slit_position(diff, slitpos, dx)
    return diff


#Automatically extensible canvas.
def canvas_size(canvas_dimen, image, x, y):
    absx, absy = canvas_dimen[2:4]   #absolute coordinate of the top left of the canvas
    cxmin = absx
    cymin = absy
    cxmax = canvas_dimen[0]+ absx
    cymax = canvas_dimen[1]+ absy
    ixmin = x
    iymin = y
    ixmax = image.shape[1] + x
    iymax = image.shape[0] + y

    xmin = min(cxmin,ixmin)
    xmax = max(cxmax,ixmax)
    ymin = min(cymin,iymin)
    ymax = max(cymax,iymax)
    if (xmax-xmin, ymax-ymin) != (canvas_dimen[0], canvas_dimen[1]):
        canvas_dimen = [xmax-xmin,ymax-ymin,xmin,ymin]
    return canvas_dimen


def Usage(argv):
    print("usage: {0} [-a x][-d][-f xmin,xmax,ymin,ymax][-g n][-p tl,bl,tr,br][-q][-s r][-t x][-w x][-z] filename".format(argv[0]))
    print("\t-a x\tAntishake.  Ignore motion smaller than x pixels (5).")
    print("\t-f xmin,xmax,ymin,ymax\tMotion detection area relative to the image size. (0.333,0.666,0.333,0.666)")
    print("\t-p a,b,c,d\tSet perspective points. Note that perspective correction works for the vertically scrolling picture only.")
    print("\t-q\tDo not show the snapshots.")
    print("\t-s r\tSet slit position to r (1).")
    print("\t-S n\tSeek the nth frame (0).")
    print("\t-t x\tAdd trailing frames after the motion is not detected. (5).")
    print("\t-w r\tSet slit width (1=same as the length of the interframe motion vector).")
    print("\t-z\tSuppress drift.")
    sys.exit(1)


class Pass1():
    def __init__(self,argv=None,filename="",seek=0,angle=0,pers=None,crop=[0,1000],every=1, identity=2.0, margin=0, focus=[333,666,333,666], zero=False, trailing=10, antishake=5, ):
        if argv is not None:
            self.initWithArgv(argv)
        else:
            self.initWithParams(filename=filename, seek=seek, angle=angle, pers=pers, crop=crop, every=every, identity=identity, margin=margin, focus=focus, zero=zero, trailing=trailing, antishake=antishake)
            
    def initWithArgv(self, argv):
        seek  = 0
        zero  = False
        pers = None 
        antishake = 5
        trailing = 10
        angle = 0   #angle in degree
        every = 1
        identity = 2.0
        crop = 0,1000
        margin = 0 # pixels, work in progress.
        #It may be able to unify with antishake.
        focus = [333, 666, 333, 666]
        while len(argv) > 2:
            if argv[1] in ("-a", "--antishake"):
                antishake = int(argv.pop(2))
            elif argv[1] in ("-c", "--crop"):
                param = argv.pop(2)
                crop = [int(x) for x in param.split(",")]
            elif argv[1] in ("-e", "--every"):
                every = int(argv.pop(2))
            elif argv[1] in ("-f", "--focus", "--frame"):
                param = argv.pop(2)
                focus = [int(x) for x in param.split(",")]
            elif argv[1] in ("-i", "--identity"):
                identity = float(argv.pop(2))
            elif argv[1] in ("-m", "--margin"):
                margin = int(argv.pop(2))
            elif argv[1] in ("-p", "--pers", "--perspective"):
                #followed by four numbers separated by comma.
                #left top, bottom, right top, bottom
                param = argv.pop(2)
                pers  = [int(x) for x in param.split(",")]
            elif argv[1] in ("-r", "--rotate"):
                angle = float(argv.pop(2))
            elif argv[1] in ("-S", "--seek"):
                seek = int(argv.pop(2))
            elif argv[1] in ("-t", "--trail"):
                trailing = int(argv.pop(2))
            elif argv[1] in ("-z", "--zero"):
                zero  = True
            elif argv[1][0] == "-":
                print("Unknown option: ", argv[1])
                Usage(argv)
            argv.pop(1)

        if len(argv) != 2:
            Usage(argv)

        filename = argv[1]
        #call it as a normal method instead of a constructor.
        self.initWithParams(filename=filename, seek=seek,angle=angle,pers=pers,crop=crop,every=every, identity=identity, margin=margin, focus=focus, zero=zero, trailing=trailing, antishake=antishake, )
        
    def initWithParams(self,filename="",seek=0,angle=0,pers=None,crop=[0,1000],every=1, identity=2.0, margin=0, focus=[333,666,333,666], zero=False, trailing=10, antishake=5, ):
        self.filename    = filename
        self.cap      = cv2.VideoCapture(filename)
        self.every    = every
        self.identity = identity
        self.margin   = margin
        self.zero     = zero
        self.trailing = trailing
        self.angle    = angle
        self.focus    = focus
        self.antishake= antishake
        self.nframes  = 0  #1 is the first frame
        self.crop     = crop
        ret = True
        for i in range(seek):  #skip frames
            ret = self.cap.grab()
            if not ret:
                break
            #ret, frame = cap.read()
            self.nframes += 1
        if not ret:
            sys.exit(0)
        ret, frame = self.cap.read()
        self.nframes += 1
        if not ret:
            sys.exit(0)
        self.rawframe = frame.copy()
        original_h, original_w, d = frame.shape
        self.rotated_h, self.rotated_w = original_h,original_w
        if angle:
            #Apply rotation
            self.R, self.rotated_w,self.rotated_h = trainscanner.rotate_matrix(-angle*math.pi/180, original_w, original_h)
            frame = cv2.warpAffine(frame, self.R, (self.rotated_w,self.rotated_h))

        if pers is not None:
            self.M = trainscanner.warp_matrix(pers,self.rotated_w,self.rotated_h)
            frame = cv2.warpPerspective(frame,self.M,(self.rotated_w,self.rotated_h))
        else:
            self.M = None
        #cropping
        self.frame = frame[crop[0]*self.rotated_h/1000:crop[1]*self.rotated_h/1000, :, :]
        self.cropped_h,self.cropped_w = self.frame.shape[0:2]

        #Prepare a scalable canvas with the origin.
        self.canvas = [self.cropped_w,self.cropped_h,100,0,0]
        #sys.stderr.write("canvas size{0} {1} {2} {3}\n".format(self.canvas[0],self.canvas[1],*self.crop))
        #sys.exit(1)
        self.LOG = sys.stdout
        self.LOG.write("{0}\n".format(filename))
        self.LOG.write("#-r {0}\n".format(angle))
        if pers is not None:
            self.LOG.write("#-p {0},{1},{2},{3}\n".format(*pers))
        self.LOG.write("#-c {0},{1}\n".format(*crop))
        #end of the header
        self.LOG.write("\n")
        
    def before(self):
        """
        prepare for the loop
        """
        self.onWork = 0
        self.absx,self.absy = 0, 0
        self.lastdx, self.lastdy = 0, 0
        self.tr = 0
        self.preview_size = 500
        self.preview = trainscanner.fit_to_square(self.frame, self.preview_size)
        self.preview_ratio = float(self.preview.shape[0]) / self.frame.shape[0]


    def after(self):
        self.LOG.write("@ {0} {1} {2} {3}\n".format(*self.canvas))

    def onestep(self):
        ret = True
        ##### Pick up every x frame
        for i in range(self.every-1):
            ret = self.cap.grab()
            self.nframes += 1
            if not ret:
                return None
        ret, nextframe = self.cap.read()
        self.nframes += 1
        ##### return None if the frame is empty
        if not ret:
            return None
        ##### compare with the previous raw frame
        diff = cv2.absdiff(nextframe,self.rawframe)
        diff = np.sum(diff) / np.product(diff.shape)
        if diff < self.identity:
            sys.stderr.write("skip identical frame #{0}\n".format(diff))
            #They are identical frames
            #This happens when the frame rate difference is compensated.
            return True
        ##### preserve the raw frame for next comparison.
        self.rawframe = nextframe.copy()
        ##### Warping the frame
        #######(1) rotation
        if self.angle:
            nextframe = cv2.warpAffine(nextframe, self.R, (self.rotated_w,self.rotated_h))
            #w and h are sizes after rotation
        #######(2) skew deformation
        if self.M is not None:
            #this does not change the aspect ratio
            nextframe = cv2.warpPerspective(nextframe,self.M,(self.rotated_w,self.rotated_h))
        #######(3) top-bottom crop
        nextframe = nextframe[self.crop[0]*self.rotated_h/1000:self.crop[1]*self.rotated_h/1000, :, :]
        ##### Make the preview image
        nextpreview = trainscanner.fit_to_square(nextframe,self.preview_size)
        ##### motion detection.
        #if margin is set, motion detection area becomes very narrow
        #assuming that the train is running at constant speed.
        #This mode is activated after the 10th frames.
        
        if self.margin > 0 and self.onWork > 10:
            #do not apply margin for the first 10 frames
            #because the velocity uncertainty.
            dx,dy = trainscanner.motion(self.frame, nextframe, focus=self.focus, margin=self.margin, delta=(self.lastdx,self.lastdy) )
        else:
            dx,dy = trainscanner.motion(self.frame, nextframe, focus=self.focus)
            
        sys.stderr.write("{0} {1} {2} #{3}\n".format(self.nframes,dx,dy,np.amax(diff)))

        if self.zero:
            if abs(dx) < abs(dy):
                dx = 0
            else:
                dy = 0
        diff_img = diffImage(nextpreview,self.preview,int(dx*self.preview_ratio),int(dy*self.preview_ratio),focus=self.focus)
        if (abs(dx) > self.antishake or abs(dy) > self.antishake):
            self.onWork += 1
            self.tr = 0
        else:
            if self.onWork:
                if self.tr <= self.trailing:
                    self.tr += 1
                    dx = self.lastdx
                    dy = self.lastdy
                    sys.stderr.write(">>({2}) {0} {1} #{3}\n".format(dx,dy,self.tr,np.amax(diff)))
                else:
                    #end of work
                    return None
        self.absx += dx
        self.absy += dy
        if self.onWork:
            self.lastdx, self.lastdy = dx,dy
            self.canvas = canvas_size(self.canvas, nextframe, self.absx, self.absy)
            #sys.stderr.write("canvas size{0} {1}\n".format(self.canvas[0],self.canvas[1]))
            self.LOG.write("{0} {1} {2} {3} {4}\n".format(self.nframes,self.absx,self.absy,dx,dy))
            self.LOG.flush()
            #This flushes the buffer, that causes immediate processing in the next command connected by a pipe "|"
        self.frame   = nextframe
        self.preview = nextpreview
        return diff_img


if __name__ == "__main__":
    pass1 = Pass1(argv=sys.argv)
    pass1.before()
    while True:
        ret = pass1.onestep()
        if ret is None:
            break
        if ret is not True: #True means skipping
            cv2.imshow("pass1", ret)
            cv2.waitKey(1)
            
    pass1.after()
